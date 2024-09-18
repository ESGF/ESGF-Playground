from urllib.parse import urljoin

import httpx
from pydantic_core import Url


async def ensure_collection(
    stac_server: Url, collection_id: str, client: httpx.AsyncClient
) -> None:
    """Check the existence of a named collection, create it if it doesn't exist"""

    collection_exists = await _check_collection(stac_server, collection_id, client)

    if not collection_exists:
        await _create_collection(stac_server, collection_id, client)

    return None


async def _check_collection(
    stac_server: Url, collection_id: str, client: httpx.AsyncClient
) -> bool:
    """Check the existence of a named collection"""

    path = f"collections/{collection_id}"
    url = urljoin(str(stac_server), path)

    check_result = await client.get(url)

    if check_result.status_code < 300:
        return True

    return False


async def _create_collection(
    stac_server: Url, collection_id: str, client: httpx.AsyncClient
) -> None:
    """Create a collection"""

    path = "collections"
    url = urljoin(str(stac_server), path)

    create_result = await client.post(
        url,
        json={
            "type": "Collection",
            "id": collection_id,
            "stac_version": "1.0.1",
            "stac_extensions": [],
            "license": "",
        },
    )

    if create_result.status_code < 300:
        return None

    # TODO: Implement this correctly
    create_result.raise_for_status()
    
    raise Exception("Could not create collection")
