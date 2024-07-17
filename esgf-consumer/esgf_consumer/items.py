from urllib.parse import urljoin

import httpx
from stac_pydantic.item import Item

from esgf_consumer.config import Settings


async def create_item(
    collection_id: str, item: Item, settings: Settings, client: httpx.AsyncClient
) -> None:
    path = f"collections/{collection_id}/items"
    url = urljoin(str(settings.stac_server), path)

    await client.post(url, content=(item.json()), timeout=5)

    return None
