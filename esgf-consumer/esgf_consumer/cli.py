import asyncio

import click

from esgf_consumer import consume
from esgf_consumer.config import Settings


@click.command()
def esgf_kafka_consumer() -> None:
    click.echo("Starting Kafka consumer...")
    settings = Settings()
    click.echo(f"Consumer configured with: {settings}")

    asyncio.run(consume(settings))
