from aiokafka import AIOKafkaProducer
from esgf_playground_utils.config.kafka import Settings


async def get_producer(settings: Settings) -> AIOKafkaProducer:
    producer = AIOKafkaProducer(
        bootstrap_servers=settings.bootstrap_servers,
    )
    await producer.start()
    return producer
