import logging
from urllib.parse import urljoin

import httpx
from esgf_consumer.config import Settings
from stac_pydantic.item import Item

logger = logging.getLogger(__name__)


async def create_item(
    collection_id: str, item: Item, settings: Settings, client: httpx.AsyncClient
) -> None:
    path = f"collections/{collection_id}/items"
    url = urljoin(str(settings.stac_server), path)

    logger.critical("Posting %s to %s", getattr(item.properties, "instance_id"), url)
    result = await client.post(url, content=(item.json()), timeout=5)
    if result.status_code < 300:
        logger.critical("Item posted")

    else:
        logger.critical("Item not posted: %s", result.content)
    return None
