import asyncio
import os
import json
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Union, NoReturn, Optional, Literal, AsyncGenerator, Any

import aiokafka
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from stac_pydantic.item import Item
from stac_pydantic.item_collection import ItemCollection
from esgf_api_ingest.config import Settings

logger = logging.getLogger(__name__)
settings = Settings()
producer: Optional[aiokafka.AIOKafkaProducer] = None


class BaseMessage(BaseModel):
    type: str
    collection_id: str


class Message(BaseMessage):
    item: Item


class ReferenceMessage(BaseMessage):
    item_id: str


class Payload(BaseModel):
    method: Literal["POST"]
    collection_id: str
    payload: Item


class Data(BaseModel):
    type: Literal["STAC"]
    version: Literal["1.0.0"]
    payload: Payload


class Auth(BaseModel):
    client_id: str
    server: str


class Publisher(BaseModel):
    package: str
    version: str


class Metadata(BaseModel):
    auth: Auth
    publisher: Publisher
    time: datetime
    schema_version: str


class KafkaPayload(BaseModel):
    metadata: Metadata
    data: Data


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[Any, Any]:
    global settings, producer

    producer = aiokafka.AIOKafkaProducer(bootstrap_servers=settings.bootstrap_servers)
    await producer.start()

    yield

    await producer.stop()


app = FastAPI(lifespan=lifespan)


def get_topic(item: Item) -> str:
    mip_era = getattr(item.properties, "mip_era")
    experiment = getattr(item.properties, "experiment_id")
    source_id = getattr(item.properties, "source_id")

    return f"{mip_era}.{experiment}.{source_id}"


async def post_message(data: KafkaPayload) -> None:
    try:
        value = data.model_dump_json().encode("utf8")
        topic = get_topic(data.data.payload.payload)

        await producer.send_and_wait(topic, value)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=repr(exc)) from exc


@app.post("/{collection_id}/items", status_code=202)
async def create_item(collection_id: str, item: Union[Item, ItemCollection]) -> Union[Item, ItemCollection]:
    """Add CREATE message to kafka event stream.

    Args:
        collection_id (str): The identifier of the collection that contains the item.
        item (stac_types.Item): The new item data.

    Returns:
        Optional[stac_types.Item]: The item, or `None` if the item was successfully deleted.
    """
    logger.info(f"Creating {collection_id} item")
    if isinstance(item, Item):
        payload = Payload(method="POST", collection_id=collection_id, payload=item)
        data = Data(type="STAC", version="1.0.0", payload=payload)
        auth = Auth(client_id="esgf-generator", server="docker-compose-local")
        publisher = Publisher(package="esgf-generator", version="0.1.0")
        metadata = Metadata(auth=auth, publisher=publisher, time=datetime.now(), schema_version="1.0.0")
        message = KafkaPayload(metadata=metadata, data=data)

        await post_message(message)

    else:
        for item in item:
            payload = Payload(method="POST", collection_id=collection_id, payload=item)
            data = Data(type="STAC", version="1.0.0", payload=payload)
            auth = Auth(client_id="esgf-generator", server="docker-compose-local")
            publisher = Publisher(package="esgf-generator", version="0.1.0")
            metadata = Metadata(auth=auth, publisher=publisher, time=datetime.now(), schema_version="1.0.0")
            message = KafkaPayload(metadata=metadata, data=data)

            await post_message(message)

    return item


# @app.delete("/{collection_id}/items/{item_id}")
# async def delete_item(item_id: str, collection_id: str) -> None:
#     """Add DELETE message to kafka event stream.
#
#     Args:
#         item_id (str): The identifier of the item to delete.
#         collection_id (str): The identifier of the collection that contains the item.
#
#     Returns:
#         Optional[stac_types.Item]: The deleted item, or `None` if the item was successfully deleted.
#     """
#     message = ReferenceMessage(
#         type="remove", collection_id=collection_id, item_id=item_id
#     )
#     await post_message(message=message)
#
#
# @app.put("/{collection_id}/items/{item_id}")
# async def update_item(collection_id: str, item_id: str, item: dict) -> None:
#     """Add UPDATE message to kafka event stream.
#
#     Args:
#         collection_id (str): The ID of the collection the item belongs to.
#         item_id (str): The ID of the item to be updated.
#         item (stac_types.Item): The new item data.
#         kwargs: Other optional arguments, including the request object.
#
#     Returns:
#         stac_types.Item: The updated item object.
#
#     Raises:
#         NotFound: If the specified collection is not found in the database.
#
#     """
#     message = {
#         "type": "update",
#         "collection_id": collection_id,
#         "item_id": item_id,
#         "item": item,
#     }
#     await post_message(message=message)
