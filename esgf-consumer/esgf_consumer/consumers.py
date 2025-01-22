from aiokafka import AIOKafkaConsumer, helpers
from esgf_playground_utils.config.kafka import Settings


async def get_consumer(settings: Settings) -> AIOKafkaConsumer:
    ssl_context = (
        helpers.create_ssl_context() if settings.sasl_mechanism == "SASL_SSL" else None
    )
    consumer = AIOKafkaConsumer(
        group_id=settings.consumer_group,
        bootstrap_servers=settings.bootstrap_servers,
        sasl_mechanism=settings.sasl_mechanism,
        security_protocol=settings.security_protocol,
        sasl_plain_username=settings.sasl_plain_username,
        sasl_plain_password=settings.sasl_plain_password,
        ssl_context=ssl_context,
        enable_auto_commit=True,
        auto_commit_interval_ms=5000,
        auto_offset_reset="earliest",
        metadata_max_age_ms=30000,
    )
    await consumer.start()

    consumer.subscribe(pattern=settings.kafka_topics.pattern)
    return consumer
