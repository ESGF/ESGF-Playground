import random
import time

import click
import httpx

from esgf_generator import ESGFItemFactory


@click.command()
@click.argument("count", type=int)
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
def esgf_generator(count: int, publish: bool, delay: bool) -> None:
    """
    Generate a number of ESGF items.

    COUNT is the number of items to generate.
    """
    click.echo(f"Producing {count} STAC records")

    data = ESGFItemFactory().batch(
        count,
        stac_extensions=[],
    )
    for instance in data:
        if publish:
            click.echo(f"Sending {instance.properties.instance_id} to ESGF")

            with httpx.Client() as client:
                result = client.post(
                    f"http://localhost:9050/{instance.collection}/items",
                    content=instance.model_dump_json(),
                )

        click.echo(instance.model_dump_json(indent=2))

        if delay:
            click.echo("Pausing for random sub-second time")
            time.sleep(random.random())

        click.echo()

    click.echo("Done")
