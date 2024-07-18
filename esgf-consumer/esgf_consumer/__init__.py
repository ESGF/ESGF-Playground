"""
Prototype consumer for ESGF. Takes events frm KAFKA and sends them to an ESGF STAC index.
"""

import asyncio
import logging
import traceback

import httpx
from aiokafka.errors import KafkaError
from esgf_consumer.collection import ensure_collection
from esgf_consumer.config import Settings
from esgf_consumer.consumers import get_consumer
from esgf_consumer.items import create_item
from esgf_consumer.producers import get_producer
from esgf_playground_utils.models.kafka import Error, ErrorType, KafkaEvent
from pydantic import ValidationError

logging.getLogger().setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


async def consume(settings: Settings) -> None:
    logger.critical("Configuration: %s", settings)
    logger.critical("Waiting 10s before connection to Kafka...")
    await asyncio.sleep(10)

    logger.critical("Starting consumer...")
    consumer = await get_consumer(settings)
    logger.critical("Consumer started.")

    logger.critical("Starting producer...")
    producer = await get_producer(settings)
    logger.critical("Producer started.")

    logger.critical("Starting http client...")
    async with httpx.AsyncClient() as client:

        logger.critical("http client started.")
        try:
            # Consume messages
            async for msg in consumer:
                try:
                    logger.critical("Received message: %s", msg)
                    event = KafkaEvent.model_validate_json(msg.value.decode("utf-8"))

                    await ensure_collection(
                        settings.stac_server, event.data.payload.collection_id, client
                    )
                    logger.critical(
                        "Collection %s confirmed on %s",
                        event.data.payload.collection_id,
                        settings.stac_server,
                    )
                    await create_item(
                        event.data.payload.collection_id,
                        event.data.payload.item,
                        settings,
                        client,
                    )
                    logger.critical("Item %s created.", event.data.payload.item.id)

                except httpx.HTTPError:
                    logger.exception("Http exception occurred")
                    error = Error(
                        original_payload=event.model_dump_json(),
                        node=settings.consumer_group,
                        traceback=traceback.format_exc(),
                        error_type=ErrorType.stac_server,
                    )
                    await producer.send_and_wait(
                        "esgf_error", error.model_dump_json().encode()
                    )

                except ValidationError:
                    logger.exception("Payload error occurred")
                    error = Error(
                        original_payload=str(msg),
                        node=settings.consumer_group,
                        traceback=traceback.format_exc(),
                        error_type=ErrorType.payload,
                    )
                    await producer.send_and_wait(
                        "esgf_error", error.model_dump_json().encode()
                    )

                except KafkaError:
                    logger.exception("Kafka exception occurred")
                    error = Error(
                        original_payload=event.model_dump_json(),
                        node=settings.consumer_group,
                        traceback=traceback.format_exc(),
                        error_type=ErrorType.kafka,
                    )
                    await producer.send_and_wait(
                        "esgf_error", error.model_dump_json().encode()
                    )

        finally:
            # Will leave consumer group; perform autocommit if enabled.
            await consumer.stop()
            logger.critical("Consumer stopped.")
            await producer.stop()
            logger.critical("Producer stopped.")

    return None


if __name__ == "__main__":
    asyncio.run(consume(Settings()), debug=True)
