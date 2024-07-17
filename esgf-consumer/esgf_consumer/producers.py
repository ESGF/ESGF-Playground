from aiokafka import AIOKafkaProducer

from esgf_consumer.config import Settings


async def get_producer(settings: Settings) -> AIOKafkaProducer:
    producer = AIOKafkaProducer(
        bootstrap_servers=settings.bootstrap_servers,
    )
    await producer.start()
    return producer
