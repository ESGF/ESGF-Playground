from aiokafka import AIOKafkaProducer, helpers
from esgf_playground_utils.config.kafka import Settings


async def get_producer(settings: Settings) -> AIOKafkaProducer:
    ssl_context = (
        helpers.create_ssl_context()
        if settings.security_protocol == "SASL_SSL"
        else None
    )
    producer = AIOKafkaProducer(
        bootstrap_servers=settings.bootstrap_servers,
        sasl_mechanism=settings.sasl_mechanism,
        security_protocol=settings.security_protocol,
        sasl_plain_username=settings.sasl_plain_username,
        sasl_plain_password=settings.sasl_plain_password,
        ssl_context=ssl_context,
    )
    await producer.start()
    return producer
