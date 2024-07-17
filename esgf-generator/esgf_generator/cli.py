import click
import httpx

from esgf_generator import ESGFItemFactory


# @click.command()
# @click.argument("count", type=int, default=1)
# @click.option("--publish/--no-publish", default=False)
def esgf_generator(count: int, publish: bool) -> None:
    # click.echo(f"Producing {count} STAC records")

    for _ in range(count):
        data = ESGFItemFactory.build(
            stac_extensions=[],
        )
        if publish:
            # click.echo(f"Sending {data.properties.instance_id} to ESGF")

            with httpx.Client() as client:
                result = client.post(f"http://localhost:9050/{data.collection}/items", content=data.model_dump_json()
                            )

        # click.echo(data.model_dump_json(indent=2))
        # click.echo()

    # click.echo("Done")

import time
while True:
    esgf_generator(1, True)
    time.sleep(1)