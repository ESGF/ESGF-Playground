from aiokafka import AIOKafkaConsumer

from esgf_consumer.config import Settings


async def get_consumer(settings: Settings) -> AIOKafkaConsumer:
    consumer = AIOKafkaConsumer(
        group_id=settings.consumer_group,
        bootstrap_servers=settings.bootstrap_servers,
    )
    await consumer.start()

    consumer.subscribe(settings.kafka_topics)
    return consumer
