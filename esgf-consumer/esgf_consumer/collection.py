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
            "description": collection_id,
            "stac_version": "1.0.1",
            "stac_extensions": [],
            "license": "No license",
            "extent": {
                "spatial": {"bbox": [[-180, -90, 180, 90]]},
                "temporal": {
                    "interval": [["1992-01-01T00:00:00Z", "2015-12-31T00:00:00Z"]]
                },
            },
            "links": [
                {
                    "rel": "self",
                    "type": "application/geo+json",
                    "href": f"https://api.stac.ceda.ac.uk/collections/{collection_id}",
                },
                {
                    "rel": "parent",
                    "type": "application/json",
                    "href": "https://api.stac.ceda.ac.uk/",
                },
                {
                    "rel": "queryables",
                    "type": "application/json",
                    "href": f"https://api.stac.ceda.ac.uk/collections/{collection_id}/queryables",
                },
                {
                    "rel": "items",
                    "type": "application/geo+json",
                    "href": f"https://api.stac.ceda.ac.uk/collections/cmip6/{collection_id}",
                },
                {
                    "rel": "root",
                    "type": "application/json",
                    "href": "https://api.stac.ceda.ac.uk/",
                },
            ],
        },
    )

    if create_result.status_code < 300:
        return None

    # TODO: Implement this correctly
    create_result.raise_for_status()

    raise Exception("Could not create collection")
