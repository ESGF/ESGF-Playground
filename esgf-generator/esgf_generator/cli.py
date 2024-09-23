import json
import random
import time
from typing import Dict, Literal

import click
import httpx
from esgf_playground_utils.models.item import ESGFItem

from esgf_generator import ESGFItemFactory

NODE_PORTS = {"east": 9050, "west": 9051}


def update_topic(item: ESGFItem, item_id: str, collection_id: str) -> ESGFItem:
    item.id = item_id
    item.collection = collection_id
    item.properties.instance_id = item_id
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
                    content=json.dumps(partial_update_data),
                )

            else:
                click.echo(f"Updating item {item_id} in collection {collection_id}")
                click.echo()
                result = client.put(
                    f"http://localhost:{NODE_PORTS[node]}/{collection_id}/items/{item_id}",
                    content=item.model_dump_json(),
                )
            if result.status_code >= 300:
                raise Exception(result.content)

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
    click.echo(f"Deleting item {item_id} in collection {collection_id}")
    click.echo()

    with httpx.Client() as client:
        if hard:
            result = client.delete(
                f"http://localhost:{NODE_PORTS[node]}/{collection_id}/items/{item_id}"
            )
        else:
            click.echo("Soft deleting item")
            click.echo()

            content = {"properties": {"retracted": True}}
            result = client.patch(
                f"http://localhost:{NODE_PORTS[node]}/{collection_id}/items/{item_id}",
                content=json.dumps(content),
            )
        if result.status_code >= 300:
            raise Exception(result.content)

    click.echo("Done")


@click.command()
def esgf_generator_test() -> None:
    """
    Generate a number of ESGF items.

    COUNT is the number of items to generate.
    """
    click.echo("Producing a STAC record to test")
    click.echo()

    data = ESGFItemFactory().batch(
        1,
        stac_extensions=[],
    )
    instance = data[0]
    publish = True

    if publish:
        click.echo(f"Sending {instance.properties.instance_id} to ESGF node 'east'")
        click.echo()

        with httpx.Client() as client:

            # Create Item
            result = client.post(
                f"http://localhost:9050/{instance.collection}/items",
                content=instance.model_dump_json(),
            )
            if result.status_code >= 300:
                click.echo("Test [1/3]: Failed")
                raise Exception(result.content)

            else:
                click.echo("Test [1/3]: Passed")
                click.echo(
                    f"Created item {instance.properties.instance_id} in collection {instance.collection}, Status: {result.status_code}\n"
                )
            click.echo("Waiting 10 seconds...")
            time.sleep(10)

            # Replication
            patch_data = {"properties": {"retracted": True}}
            patch_result = client.patch(
                f"http://localhost:9050/{instance.collection}/items/{instance.properties.instance_id}",
                content=json.dumps(patch_data),
            )
            if patch_result.status_code >= 300:
                click.echo("Test [2/3]: Failed")
                raise Exception(result.content)
            else:
                click.echo("Test [2/3]: Passed")
                click.echo(
                    f"Added  node to item {instance.properties.instance_id} in collection {instance.collection}, Status: {result.status_code}\n"
                )
            click.echo("Waiting 10 seconds...")
            time.sleep(10)

            # Retraction
            remove_patch = {"properties": {"retracted": False}}
            remove_result = client.patch(
                f"http://localhost:9050/{instance.collection}/items/{instance.properties.instance_id}",
                content=json.dumps(remove_patch),
            )
            if remove_result.status_code >= 300:
                click.echo("Test [3/3]: Failed")
                raise Exception(result.content)

            else:
                click.echo("Test [3/3]: Passed")
                click.echo(
                    f"Reomved node from item {instance.properties.instance_id} in collection {instance.collection}, Status: {result.status_code}\n"
                )

    click.echo("Done")
