import asyncio
import logging
import traceback
from typing import Any

from aiokafka.errors import KafkaError
from consumers import get_consumer
from esgf_playground_utils.config.kafka import Settings
from esgf_playground_utils.models.kafka import Error, ErrorType, KafkaEvent
from pydantic import ValidationError
from pymongo import MongoClient

logging.getLogger().setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


async def consume_to_mongo(settings: Settings) -> None:
    logger.critical("Configuration: %s", settings)
    logger.critical("Waiting 10s before connection to Kafka...")
    await asyncio.sleep(10)

    logger.critical("Starting consumer...")
    consumer = await get_consumer(settings)
    logger.critical("Consumer started.")

    logger.critical("Connecting to MongoDB...")
    client: MongoClient[Any] = MongoClient("mongodb://root:example@mongo:27017/")
    db = client["esgf_playground_db"]
    collection = db["esgf_data_collection"]
    logger.critical("Connected to MongoDB.")

    try:
        async for msg in consumer:
            try:
                logger.critical("Received message: %s", msg)
                event = KafkaEvent.model_validate_json(msg.value.decode("utf-8"))

                collection.insert_one(event.model_dump())
                logger.critical("Message persisted to MongoDB.")

            except ValidationError:
                logger.exception("Payload error occurred")
                error = Error(
                    original_payload=str(msg),
                    node=settings.consumer_group,
                    traceback=traceback.format_exc(),
                    error_type=ErrorType.payload,
                )
                await consumer.send_and_wait(
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
                await consumer.send_and_wait(
                    "esgf_error", error.model_dump_json().encode()
                )

            except Exception as e:
                logger.exception("Failed to process message: %s", e)
                error = Error(
                    original_payload=event.model_dump_json(),
                    node=settings.consumer_group,
                    traceback=traceback.format_exc(),
                    error_type=ErrorType.unknown,
                )
                await consumer.send_and_wait(
                    "esgf_error", error.model_dump_json().encode()
                )

    finally:
        await consumer.stop()
        logger.critical("Consumer stopped.")
        client.close()
        logger.critical("MongoDB client closed.")

    return None


if __name__ == "__main__":
    asyncio.run(consume_to_mongo(Settings()), debug=True)
