import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple, Union

import aiokafka
import httpx
from esgf_playground_utils.config.kafka import Settings
from esgf_playground_utils.models.kafka import (
    Auth,
    AuthData,
    CreatePayload,
    Data,
    KafkaEvent,
    Metadata,
    PartialUpdatePayload,
    Publisher,
    RevokePayload,
    UpdatePayload,
)
from fastapi import Depends, FastAPI, HTTPException
from stac_pydantic.item import Item

from .keycloak import TokenData, get_current_active_admin, get_current_active_user

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
stream_handler = logging.StreamHandler(sys.stdout)
log_formatter = logging.Formatter("[%(levelname)s] %(name)s: %(message)s")
stream_handler.setFormatter(log_formatter)
logger.addHandler(stream_handler)


settings = Settings()
producer: Optional[aiokafka.AIOKafkaProducer] = None

TOKEN = os.getenv("TOKEN")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[Any, Any]:
    global settings, producer

    producer = aiokafka.AIOKafkaProducer(bootstrap_servers=settings.bootstrap_servers)
    await producer.start()

    yield

    await producer.stop()


app = FastAPI(lifespan=lifespan)


async def check_item_exists(collection_id: str, item_id: str) -> bool:
    stac_url = (
        f"http://stac-fastapi-es-east:8080/collections/{collection_id}/items/{item_id}"
    )

    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            response = await client.get(stac_url)
            if response.status_code == 200 or response.status_code == 202:
                logger.info(f"Item '{item_id}' exists in collection '{collection_id}'.")
                return True
            elif response.status_code == 404:
                return False
            else:
                logger.error(
                    f"Unexpected response from STAC server: {response.status_code}"
                )
                return False
        except httpx.HTTPError as e:
            logger.error(f"HTTP error occurred: {str(e)}")
            return False


def create_auth_basis_data(
    token_data: TokenData,
) -> Dict[str, Union[str, List[Dict[str, str]]]]:
    def replace_none(value: Optional[str]) -> str:
        return value if value is not None else "null"

    authorization_basis: List[Dict[str, str]] = []

    for role in token_data.roles or []:
        authorization_basis.append(
            {
                "role": replace_none(role),
                "member_id": replace_none(token_data.sub),
                "member_name": replace_none(token_data.name),
            }
        )

    auth_basis_data: Dict[str, Union[str, List[Dict[str, str]]]] = {
        "authorization_basis_type": "role",
        "authorization_basis_service": "keycloak",
        "authorization_basis": authorization_basis,
    }

    return auth_basis_data


def create_requester_data(token_data: TokenData) -> Dict[str, str]:
    return {
        "auth_service": "auth.esgf-playground",
        "sub": token_data.sub or "null",
        "username": token_data.username or "null",
        "name": token_data.name or "null",
        "email": token_data.email or "null",
        "identity_provider": "null",
        "identity_provider_display_name": "null",
    }


def auth_item_body(token_data: TokenData) -> Tuple[Dict[str, str], Dict[str, Any]]:
    auth_basis_data = create_auth_basis_data(token_data)
    requester_data = create_requester_data(token_data)
    return requester_data, auth_basis_data


def item_body(
    payload: Union[RevokePayload, UpdatePayload, CreatePayload, PartialUpdatePayload],
    token_data: TokenData,
) -> KafkaEvent:

    requester_data, auth_basis_data = auth_item_body(token_data)

    if isinstance(payload, CreatePayload):
        auth = AuthData(
            auth_policy_id="esgf-generator",
            target_data={
                "collection_id": payload.collection_id,
                "item_id": payload.item.id,
            },
            requester_data=requester_data,
            auth_basis_data=auth_basis_data,
        )
    else:
        auth = Auth(client_id="esgf-generator", server="docker-compose-local")

    data = Data(type="STAC", version="1.0.0", payload=payload)
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


async def post_item(collection_id: str, item: Item, token_data: TokenData) -> None:
    payload = CreatePayload(method="POST", collection_id=collection_id, item=item)
    event = item_body(payload, token_data)
    await post_message(event)


async def modify_item(
    collection_id: str, item: Item, item_id: str, token_data: TokenData
) -> None:
    payload = UpdatePayload(
        method="PUT", collection_id=collection_id, item=item, item_id=item_id
    )
    event = item_body(payload, token_data)
    await post_message(event)


async def revoke_item_hard(
    collection_id: str, item_id: str, token_data: TokenData
) -> None:
    payload = RevokePayload(
        method="DELETE", collection_id=collection_id, item_id=item_id
    )
    event = item_body(payload, token_data)
    await alternate_message(event)


async def partial_update_item(
    collection_id: str, item_id: str, item: Dict[str, Any], token_data: TokenData
) -> None:
    payload = PartialUpdatePayload(
        method="PATCH", collection_id=collection_id, item=item, item_id=item_id
    )
    event = item_body(payload, token_data)
    await alternate_message(event)


@app.post("/{collection_id}/items", status_code=202)
async def create_item(
    collection_id: str,
    item: Item,
    current_user: TokenData = Depends(get_current_active_user),
) -> Item:
    """Add CREATE message to kafka event stream.

    Args:
        collection_id (str): The identifier of the collection that contains the item.
        item (stac_types.Item): The new item data.

    Returns:
        Optional[stac_types.Item]: The item, or `None` if the item was successfully deleted.
    """
    logger.info("Creating %s item", collection_id)
    if await check_item_exists(collection_id, item.id):
        raise HTTPException(status_code=409, detail="Item already exists")

    await post_item(collection_id, item, current_user)

    return item


@app.put("/{collection_id}/items/{item_id}")
async def update_item(
    collection_id: str,
    item_id: str,
    item: Item,
    current_user: TokenData = Depends(get_current_active_user),
) -> Item:
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
    if not await check_item_exists(collection_id, item_id):
        raise HTTPException(status_code=409, detail="Cannot update non-existent item")

    try:
        await modify_item(collection_id, item, item_id, current_user)
    except Exception as e:
        (f"Collection {collection_id} not found: {str(e)}")

    return item


@app.delete("/{collection_id}/items/{item_id}")
async def delete_item_hard(
    item_id: str,
    collection_id: str,
    current_user: TokenData = Depends(get_current_active_admin),
) -> None:
    """Add DELETE message to kafka event stream.

    Args:
        item_id (str): The identifier of the item to delete.
        collection_id (str): The identifier of the collection that contains the item.

    Returns:
        Optional[stac_types.Item]: The deleted item, or `None` if the item was successfully deleted.
    """
    logger.info("Deleting %s item", collection_id)

    if not await check_item_exists(collection_id, item_id):
        raise HTTPException(status_code=409, detail="Cannot delete non-existent item")
    await revoke_item_hard(collection_id, item_id, current_user)

    return None


@app.patch("/{collection_id}/items/{item_id}")
async def partial_update(
    item_id: str,
    collection_id: str,
    item: Dict[str, Any],
    current_user: TokenData = Depends(get_current_active_user),
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

    if not await check_item_exists(collection_id, item_id):
        raise HTTPException(status_code=409, detail="Cannot update non-existent item")
    await partial_update_item(collection_id, item_id, item, current_user)

    return None
