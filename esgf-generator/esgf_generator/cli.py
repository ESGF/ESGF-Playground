import random
import time
from typing import Literal

import click
import httpx
import json

from esgf_generator import ESGFItemFactory

NODE_PORTS = {"east": 9050, "west": 9051}


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
    click.echo(f"Producing {count} STAC records")
    click.echo()

    data = ESGFItemFactory().batch(
        count,
        stac_extensions=[],
    )
    for instance in data:
        if publish:
            click.echo(
                f"Sending {instance.properties.instance_id} to ESGF node '{node}'"
            )

            with httpx.Client() as client:
                result = client.post(
                    f"http://localhost:{NODE_PORTS[node]}/{instance.collection}/items",
                    content=instance.model_dump_json(),
                )
                if result.status_code >= 300:
                    raise Exception(result.content)

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
def esgf_update(collection_id: str, item_id: str, publish: bool,  node: Literal["east", "west"]) -> None:
    """
    Update an ESGF item.

    COLLECTION_ID is the identifier of the collection that contains the item.
    ITEM_ID is the identifier of the item to update.
    """
    click.echo(f"Updating item {item_id} in collection {collection_id}")

    with httpx.Client() as client:
        data = {"data": { "payload": { "item": { "collection": "Test" }}}}
        result = client.put(
            f"http://localhost:{NODE_PORTS[node]}/{collection_id}/items/{item_id}",
            content=json.dumps(data),
        )
        if result.status_code >= 300:
            raise Exception(result.content)

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
def esgf_delete(collection_id: str, item_id: str, publish: bool,  node: Literal["east", "west"]) -> None:
    """
    Delete an ESGF item.

    COLLECTION_ID is the identifier of the collection that contains the item.
    ITEM_ID is the identifier of the item to update.
    """
    click.echo(f"Deleting item {item_id} in collection {collection_id}")
    click.echo()


    with httpx.Client() as client:
        result = client.delete(
            f"http://localhost:{NODE_PORTS[node]}/{collection_id}/items/{item_id}")

        if result.status_code >= 300:
            raise Exception(result.content)

    click.echo("Done")


