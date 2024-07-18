from aiokafka import AIOKafkaConsumer
from esgf_playground_utils.config.kafka import Settings


async def get_consumer(settings: Settings) -> AIOKafkaConsumer:
    consumer = AIOKafkaConsumer(
        group_id=settings.consumer_group,
        bootstrap_servers=settings.bootstrap_servers,
        enable_auto_commit=True,
        auto_commit_interval_ms=5000,
        auto_offset_reset="earliest",
        metadata_max_age_ms=30000,
    )
    await consumer.start()

    consumer.subscribe(pattern=settings.kafka_topics.pattern)
    return consumer
