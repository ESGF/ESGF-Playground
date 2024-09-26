import logging
import sys
import httpx
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, Optional, Union

import aiokafka
from esgf_playground_utils.config.kafka import Settings
from esgf_playground_utils.models.kafka import (
    Auth,
    CreatePayload,
    Data,
    KafkaEvent,
    Metadata,
    PartialUpdatePayload,
    Publisher,
    RevokePayload,
    UpdatePayload,
)
from fastapi import FastAPI, HTTPException
from stac_pydantic.item import Item
from stac_pydantic.item_collection import ItemCollection
from pystac_client import Client

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
stream_handler = logging.StreamHandler(sys.stdout)
log_formatter = logging.Formatter("[%(levelname)s] %(name)s: %(message)s")
stream_handler.setFormatter(log_formatter)
logger.addHandler(stream_handler)


settings = Settings()
producer: Optional[aiokafka.AIOKafkaProducer] = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[Any, Any]:
    global settings, producer

    producer = aiokafka.AIOKafkaProducer(bootstrap_servers=settings.bootstrap_servers)
    await producer.start()

    yield

    await producer.stop()


app = FastAPI(lifespan=lifespan)


def check_item_exists1(collection_id: str, item_id: str) -> bool:
    stac_url = f"{settings.stac_server}"
    logger.info(f"STAC Server URL: {stac_url}")

    try:
        catalog = Client.open(stac_url)
        collection_exists = any(
            col.id == collection_id for col in catalog.get_collections()
        )

        if not collection_exists:
            return False

        logger.info(
            f"Collection '{collection_id}' exists. Checking for item '{item_id}'..."
        )

        collection_url = f"{stac_url}/collections/{collection_id}/items"
        catalog = Client.open(collection_url)
        search = catalog.search(ids=[item_id])

        search = catalog.search(ids=[item_id])

        item = next(search.get_items(), None)

        if item:
            logger.info(f"Item already exists: {item}")
            return True
        else:
            return False

    except Exception as e:
        logger.error(f"Error accessing STAC server or collection: {str(e)}")
        return False


async def check_item_exists2(collection_id: str, item_id: str) -> bool:
    stac_url = f"{settings.stac_server}collections/{collection_id}/items/{item_id}"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(stac_url)
            if response.status_code == 200:
                logger.info(f"Item '{item_id}' exists in collection '{collection_id}'.")
                return True
            elif response.status_code == 404:
                logger.info(
                    f"Item '{item_id}' does not exist in collection '{collection_id}'."
                )
                return False
            else:
                logger.error(
                    f"Unexpected response from STAC server: {response.status_code}"
                )
                return False
        except httpx.HTTPError as e:
            logger.error(f"HTTP error occurred: {str(e)}")
            return False


def item_body(
    payload: Union[RevokePayload, UpdatePayload, CreatePayload, PartialUpdatePayload]
) -> KafkaEvent:
    data = Data(type="STAC", version="1.0.0", payload=payload)
    auth = Auth(client_id="esgf-generator", server="docker-compose-local")
    publisher = Publisher(package="esgf-generator", version="0.1.0")
    metadata = Metadata(
        auth=auth, publisher=publisher, time=datetime.now(), schema_version="1.0.0"
    )
    event = KafkaEvent(metadata=metadata, data=data)

    return event


def get_topic(item: Item) -> str:
    mip_era = getattr(item.properties, "mip_era")
    experiment = getattr(item.properties, "experiment_id")
    source_id = getattr(item.properties, "source_id")

    return f"{mip_era}.{experiment}.{source_id}"


def get_topic_alternate(item_id: str) -> str:
    parts = item_id.split(".")
    mip_era = parts[0]
    experiment = parts[4]
    source_id = parts[3]

    return f"{mip_era}.{experiment}.{source_id}"


async def post_message(event: KafkaEvent) -> None:
    try:
        value = event.model_dump_json().encode("utf8")
        topic = get_topic(event.data.payload.item)

        if producer is None:
            raise Exception("Kafka producer is not initialized")

        await producer.send_and_wait(topic, value)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=repr(exc)) from exc


async def alternate_message(event: KafkaEvent) -> None:
    try:
        value = event.model_dump_json().encode("utf8")
        topic = get_topic_alternate(event.data.payload.item_id)

        if producer is None:
            raise Exception("Kafka producer is not initialized")

        await producer.send_and_wait(topic, value)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=repr(exc)) from exc


async def post_item(collection_id: str, item: Item) -> None:
    payload = CreatePayload(method="POST", collection_id=collection_id, item=item)
    event = item_body(payload)
    await post_message(event)


async def modify_item(collection_id: str, item: Item, item_id: str) -> None:
    payload = UpdatePayload(
        method="PUT", collection_id=collection_id, item=item, item_id=item_id
    )
    event = item_body(payload)
    await post_message(event)


async def revoke_item_hard(collection_id: str, item_id: str) -> None:
    payload = RevokePayload(
        method="DELETE", collection_id=collection_id, item_id=item_id
    )
    event = item_body(payload)
    await alternate_message(event)


async def partial_update_item(
    collection_id: str, item_id: str, item: Dict[str, Any]
) -> None:
    payload = PartialUpdatePayload(
        method="PATCH", collection_id=collection_id, item=item, item_id=item_id
    )
    event = item_body(payload)
    await alternate_message(event)


@app.post("/{collection_id}/items", status_code=202)
async def create_item(
    collection_id: str, item: Union[Item, ItemCollection]
) -> Union[Item, ItemCollection]:
    """Add CREATE message to kafka event stream.

    Args:
        collection_id (str): The identifier of the collection that contains the item.
        item (stac_types.Item): The new item data.

    Returns:
        Optional[stac_types.Item]: The item, or `None` if the item was successfully deleted.
    """
    logger.info("Creating %s item", collection_id)
    if await check_item_exists1(collection_id, item.id):
        logger.info("Item already exists")
        raise HTTPException(status_code=409, detail="Item already exists")

    logger.info("Item does not exist")
    if isinstance(item, Item):
        await post_item(collection_id, item)
    else:
        for i in item:
            await post_item(collection_id, i)

    return item


@app.put("/{collection_id}/items/{item_id}")
async def update_item(collection_id: str, item_id: str, item: Item) -> Item:
    """Add UPDATE message to kafka event stream.

    Args:
        collection_id (str): The ID of the collection the item belongs to.
        item_id (str): The ID of the item to be updated.
        item (stac_types.Item): The new item data.
        kwargs: Other optional arguments, including the request object.

    Returns:
        stac_types.Item: The updated item object.

    Raises:
        NotFound: If the specified collection is not found in the database.

    """
    logger.info("Updating %s item", collection_id)

    try:
        await modify_item(collection_id, item, item_id)
    except Exception as e:
        (f"Collection {collection_id} not found: {str(e)}")

    return item


@app.delete("/{collection_id}/items/{item_id}")
async def delete_item_hard(item_id: str, collection_id: str) -> None:
    """Add DELETE message to kafka event stream.

    Args:
        item_id (str): The identifier of the item to delete.
        collection_id (str): The identifier of the collection that contains the item.

    Returns:
        Optional[stac_types.Item]: The deleted item, or `None` if the item was successfully deleted.
    """
    logger.info("Deleting %s item", collection_id)

    await revoke_item_hard(collection_id, item_id)

    return None


@app.patch("/{collection_id}/items/{item_id}")
async def partial_update(
    item_id: str, collection_id: str, item: Dict[str, Any]
) -> None:
    """Add Update message to kafka event stream.

    Args:
        item_id (str): The identifier of the item to partially update.
        collection_id (str): The identifier of the collection that contains the item.
        item (dict): The item data beiing patched.

    Returns:
        None
    """
    logger.info("Updating %s item", collection_id)

    await partial_update_item(collection_id, item_id, item)

    return None
