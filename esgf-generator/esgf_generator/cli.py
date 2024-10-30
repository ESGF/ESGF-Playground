import json
import os
import random
import time
from typing import Any, Dict, Literal

import click
import httpx
import jwt
from dotenv import find_dotenv, load_dotenv, set_key, unset_key
from esgf_playground_utils.models.item import ESGFItem

from esgf_generator import ESGFItemFactory

NODE_PORTS = {"east": 9050, "west": 9051}
ENV_FILE = find_dotenv()

if ENV_FILE is None:
    raise Exception("No .env file found, please create one in the root directory")

load_dotenv(ENV_FILE)

PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA60CVmUcJJ7MoiuihlrSw7+BkhQbQv3HDqveFnjy2OFhKckLFyzczxCjoWq96nGTlrfWz2U4J+e8u0iHEmVaSfVDD5AG02UGNEk9TfMLuaONZjeM2w4OHYzFNaPxEmobthOcJHAsrpRwT3w4JHLEYSFVRQG8HdKha9e9qUublJVwsxFqVgPPgPK0PJpy9MSc48EMp4GbGBx9Hit9tFEIS9VPZ8BVPVm04bxOdXky/aFLsUOTS2V2FY98ABMQ8TKnbZBdXAFUnk0L3TZfkmNnvfKvUJzes79846MZKF4gVEJJ8vnD9a+u4IaMSecFCF17SEB50QMoawn3GXCK3ppZE1QIDAQAB
-----END PUBLIC KEY-----"""


def validate_token() -> bool:
    token = os.getenv("TOKEN")
    if not token:
        return False

    try:
        jwt.decode(
            token,
            PUBLIC_KEY,
            algorithms=["RS256"],
            audience="ec404039-07b4-4a4f-97eb-e0accf60ee76",
        )
        return True
    except jwt.PyJWTError:
        return False


def authenticate() -> str:

    token = os.getenv("TOKEN")
    if token and validate_token():
        return token

    username = click.prompt("Username")
    password = click.prompt("Password", hide_input=True)
    click.echo()

    url = "http://localhost:8086/realms/ESGF-Playground/protocol/openid-connect/token"
    data = {
        "grant_type": "password",
        "client_id": "esgf_client",
        "client_secret": os.getenv("CLIENT_SECRET"),
        "username": username,
        "password": password,
    }

    response = httpx.post(url, data=data)

    if response.status_code == 200:
        token = response.json().get("access_token")

        if token is None:
            click.echo("Failed to retrieve token: Logout and try again")
            exit(1)

        set_key(ENV_FILE, "TOKEN", token)
        return token
    else:
        click.echo()
        click.echo("Authentication Failed")
        exit(1)


def update_topic(item: ESGFItem, item_id: str, collection_id: str) -> ESGFItem:
    item.id = item_id
    item.collection = collection_id
    item.properties.instance_id = item.id
    item.properties.title = item.id

    split_item = item_id.split(".")
    if len(split_item) != 10:
        raise ValueError("Error with item naming format")

    (
        item.properties.mip_era,
        item.properties.activity_id,
        item.properties.institution_id,
        item.properties.source_id,
        item.properties.experiment_id,
        item.properties.variant_label,
        item.properties.table_id,
        item.properties.variable_id,
        item.properties.grid_label,
    ) = split_item[:9]

    return item


@click.command()
@click.argument("count", type=int)
@click.option("--node", type=click.Choice(["east", "west"]))
@click.option(
    "--publish/--no-publish",
    default=False,
    help="Whether to publish items to ESGF, or just print to the console (print happens anyway). Default: --no-publish",
)
@click.option(
    "--delay/--no-delay",
    default=False,
    help="Add a random sub-second delay between publishing items to ESGF. Default: --no-delay",
)
def esgf_generator(
    count: int, node: Literal["east", "west"], publish: bool, delay: bool
) -> None:
    """
    Generate a number of ESGF items.

    COUNT is the number of items to generate.
    """
    token = authenticate()

    click.echo(f"Producing {count} STAC records")
    click.echo()

    data = ESGFItemFactory().batch(
        count,
        stac_extensions=[],
    )
    for instance in data:
        click.echo(
            f"Generated item with ID: {instance.id} in collection: {instance.collection}"
        )
        click.echo()

        if publish:
            click.echo(
                f"Sending {instance.properties.instance_id} to ESGF node '{node}'"
            )
            click.echo()

            with httpx.Client() as client:
                result = client.post(
                    f"http://localhost:{NODE_PORTS[node]}/{instance.collection}/items",
                    headers={"Authorization": f"Bearer {token}"},
                    content=instance.model_dump_json(),
                )
                click.echo()

                if result.status_code == 401:
                    click.echo("You are not Authorised")
                elif result.status_code == 403:
                    click.echo("Not enough permissions")
                elif result.status_code >= 300:
                    raise Exception(result.content)
                else:
                    click.echo(instance.model_dump_json(indent=2))

                    if delay:
                        click.echo("Pausing for random sub-second time")
                        time.sleep(random.random())
                        click.echo()
                        click.echo("Done")


@click.command()
@click.argument("collection_id", type=str)
@click.argument("item_id", type=str)
@click.option("--node", type=click.Choice(["east", "west"]))
@click.option(
    "--publish/--no-publish",
    default=False,
    help="Whether to publish items to ESGF, or just print to the console (print happens anyway). Default: --no-publish",
)
@click.option(
    "--partial",
    type=str,
    default="{}",
    help="JSON string representing the partial update data. Default: empty dictionary",
)
def esgf_update(
    collection_id: str,
    item_id: str,
    publish: bool,
    node: Literal["east", "west"],
    partial: str,
) -> None:
    """
    Update an ESGF item.

    COLLECTION_ID is the identifier of the collection that contains the item.
    ITEM_ID is the identifier of the item to update.
    """

    token = authenticate()

    data = ESGFItemFactory().batch(
        1,
        stac_extensions=[],
    )

    item = data[0]

    partial_update_data: Dict[str, Any] = json.loads(partial)

    item = update_topic(item, item_id, collection_id)

    if publish:
        with httpx.Client() as client:
            if partial_update_data:
                click.echo(
                    f"Partially updating item {item_id} in collection {collection_id}"
                )
                click.echo()

                result = client.patch(
                    f"http://localhost:{NODE_PORTS[node]}/{collection_id}/items/{item_id}",
                    headers={"Authorization": f"Bearer {token}"},
                    content=json.dumps(partial_update_data),
                )

            else:
                click.echo(f"Updating item {item_id} in collection {collection_id}")
                click.echo()
                result = client.put(
                    f"http://localhost:{NODE_PORTS[node]}/{collection_id}/items/{item_id}",
                    headers={"Authorization": f"Bearer {token}"},
                    content=item.model_dump_json(),
                )
            if result.status_code == 401:
                click.echo("You are not Authorised")
            elif result.status_code == 403:
                click.echo("Not enough permissions")
            elif result.status_code >= 300:
                raise Exception(result.content)
            else:
                click.echo()
                click.echo("Done")


@click.command()
@click.argument("collection_id", type=str)
@click.argument("item_id", type=str)
@click.option("--node", type=click.Choice(["east", "west"]))
@click.option(
    "--hard/--soft",
    default=False,
    help="Whether to permanently delete item or note that its deleted. Default: --soft",
)
@click.option(
    "--publish/--no-publish",
    default=False,
    help="Whether to publish items to ESGF, or just print to the console (print happens anyway). Default: --no-publish",
)
def esgf_delete(
    collection_id: str,
    item_id: str,
    hard: bool,
    publish: bool,
    node: Literal["east", "west"],
) -> None:
    """
    Delete an ESGF item.

    COLLECTION_ID is the identifier of the collection that contains the item.
    ITEM_ID is the identifier of the item to update.
    """
    token = authenticate()

    click.echo(f"Deleting item {item_id} in collection {collection_id}")
    click.echo()

    if publish:
        with httpx.Client() as client:
            if hard:
                result = client.delete(
                    f"http://localhost:{NODE_PORTS[node]}/{collection_id}/items/{item_id}",
                    headers={"Authorization": f"Bearer {token}"},
                )
            else:
                click.echo("Soft deleting item")
                click.echo()

                content = {"properties": {"retracted": True}}
                result = client.patch(
                    f"http://localhost:{NODE_PORTS[node]}/{collection_id}/items/{item_id}",
                    headers={"Authorization": f"Bearer {token}"},
                    content=json.dumps(content),
                )
            if result.status_code == 401:
                click.echo("You are not Authorised")
            elif result.status_code == 403:
                click.echo("Not enough permissions")
            elif result.status_code >= 300:
                raise Exception(result.content)
            else:
                click.echo()
                click.echo("Done")


@click.command()
def logout() -> None:
    token = os.getenv("TOKEN")
    if token:
        unset_key(ENV_FILE, "TOKEN")
        click.echo()
        click.echo("Logged out")
    else:
        click.echo()
        click.echo("Not logged in")
