import click

from esgf_generator import ESGFItemFactory


@click.command()
@click.argument("count", type=int, default=1)
def esgf_generator(count: int) -> None:
    click.echo(f"Producing {count} STAC records")

    for _ in range(count):
        data = ESGFItemFactory.build(
            stac_extensions=[],
        )
        click.echo(data.model_dump_json(indent=2))
        click.echo()

    click.echo("Done")
