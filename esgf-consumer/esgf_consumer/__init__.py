"""
Prototype consumer for ESGF. Takes events frm KAFKA and sends them to an ESGF STAC index.
"""
import asyncio
import traceback
import logging

import httpx
from aiokafka.errors import KafkaError
from pydantic import ValidationError

from esgf_consumer.collection import ensure_collection
from esgf_consumer.config import Settings
from esgf_consumer.consumers import get_consumer
from esgf_consumer.items import create_item
from esgf_consumer.models import KafkaPayload, Error, ErrorType
from esgf_consumer.producers import get_producer

logger = logging.getLogger(__name__)


async def consume(settings: Settings) -> None:
    logger.debug("Configuration: %s", settings)
    logger.info("Waiting 10s before connection to Kafka...")
    await asyncio.sleep(10)

    logger.debug("Starting consumer...")
    consumer = await get_consumer(settings)
    logger.info("Consumer started.")

    logger.debug("Starting producer...")
    producer = await get_producer(settings)
    logger.info("Producer started.")

    logger.debug("Starting http client...")
    async with httpx.AsyncClient() as client:

        logger.info("http client started.")
        try:
            # Consume messages
            async for msg in consumer:
                try:
                    logger.debug("Received message: %s", msg)
                    data = KafkaPayload.model_validate_json(msg.value.decode("utf-8"))

                    await ensure_collection(
                        settings.stac_server, data.data.payload.collection_id, client
                    )
                    logger.debug("Collection %s confirmed on %s", data.data.payload.collection_id, settings.stac_server)
                    await create_item(
                        data.data.payload.collection_id,
                        data.data.payload.payload,
                        settings,
                        client,
                    )
                    logger.info("Item %s created.", data.data.payload.payload.id)

                except httpx.HTTPError:
                    logger.exception("Http exception occurred")
                    error = Error(
                        original_payload=data.model_dump_json(),
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
                        original_payload=data.model_dump_json(),
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
            logger.info("Consumer stopped.")
            await producer.stop()
            logger.info("Producer stopped.")

    return None
