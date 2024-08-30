import warnings
from datetime import datetime, timezone
from random import random
from typing import Any, Dict, List, Optional, TypeVar
from urllib.parse import urljoin

import httpx
from esgf_generator.data import CHOICES
from esgf_generator.static_generators import (generate_datetime,
                                              generate_geometry, instance_id)
from esgf_playground_utils.models.item import ESGFItem, ESGFItemProperties
from polyfactory import PostGenerated
from polyfactory.factories.pydantic_factory import ModelFactory
from polyfactory.fields import Use
from typing_extensions import ParamSpec

API_URL = "http://ceda.stac.ac.uk"
START_DATETIME = datetime.fromisoformat("1900-01-01T00:00:00").replace(
    tzinfo=timezone.utc
)
END_DATETIME = datetime.fromisoformat("3000-12-12T00:00:00").replace(
    tzinfo=timezone.utc
)

P = ParamSpec("P")
T = TypeVar("T")


def generate_instance_id(
    name: str, values: dict[str, Any], *args: P.args, **kwarg: P.kwargs
) -> str:
    instance_id_value: str = instance_id(values)

    return instance_id_value


def generate_start_datetime(
    name: str, values: dict[str, Any], *args: P.args, **kwarg: P.kwargs
) -> Optional[datetime]:
    if not values["datetime"]:
        return START_DATETIME + random() * (END_DATETIME - START_DATETIME)
    else:
        return None


def generate_end_datetime(
    name: str, values: dict[str, Any], *args: P.args, **kwarg: P.kwargs
) -> Optional[datetime]:
    if values["start_datetime"]:
        result: datetime = values["start_datetime"] + random() * (
            END_DATETIME - values["start_datetime"]
        )
        return result
    else:
        return None


def generate_citation_url(
    name: str, values: dict[str, Any], *args: P.args, **kwarg: P.kwargs
) -> str:
    return f"http://cera-www.dkrz.de/WDCC/meta/{values['mip_era']}/{instance_id(values)}.json"


def generate_further_info_url(
    name: str, values: dict[str, Any], *args: P.args, **kwarg: P.kwargs
) -> str:
    return f"https://furtherinfo.es-doc.org/{instance_id(values)}"


def choose(choices: List[T]) -> T:
    """
    Helper function to choose a random element from a list.

    This is simply to allow MyPy to resolve the inferred type, as the choice function is technically a
    bound method of the class Random.
    """

    return ModelFactory.__random__.choice(choices)


class ESGFPropertiesFactory(ModelFactory[ESGFItemProperties]):
    __model__ = ESGFItemProperties
    variable_long_name = Use(choose, CHOICES["variable_long_name"])
    variable_units = Use(choose, CHOICES["variable_units"])
    cf_standard_name = Use(choose, CHOICES["cf_standard_name"])
    activity_id = Use(choose, CHOICES["activity_id"])
    data_specs_version = Use(choose, CHOICES["data_specs_version"])
    experiment_title = Use(choose, CHOICES["experiment_title"])
    frequency = Use(choose, CHOICES["frequency"])
    grid = Use(choose, CHOICES["grid"])
    grid_label = Use(choose, CHOICES["grid_label"])
    institution_id = Use(choose, CHOICES["institution_id"])
    mip_era = Use(choose, CHOICES["mip_era"])
    source_id = Use(choose, CHOICES["source_id"])
    source_type = Use(choose, CHOICES["source_type"])
    experiment_id = Use(choose, CHOICES["experiment_id"])
    sub_experiment_id = Use(choose, CHOICES["sub_experiment_id"])
    nominal_resolution = Use(choose, CHOICES["nominal_resolution"])
    table_id = Use(choose, CHOICES["table_id"])
    variable_id = Use(choose, CHOICES["variable_id"])
    variant_label = Use(choose, CHOICES["variant_label"])
    instance_id = PostGenerated(generate_instance_id)
    title = PostGenerated(generate_instance_id)
    further_info_url = PostGenerated(generate_further_info_url)
    citation_url = PostGenerated(generate_citation_url)
    datetime = generate_datetime(START_DATETIME, END_DATETIME)
    start_datetime = PostGenerated(generate_start_datetime)
    end_datetime = PostGenerated(generate_end_datetime)


def generate_id(
    name: str, values: dict[str, Any], *args: P.args, **kwarg: P.kwargs
) -> str:
    instance_id_value: str = values["properties"]["instance_id"]
    return instance_id_value


def generate_bbox(
    name: str, values: dict[str, Any], *args: P.args, **kwarg: P.kwargs
) -> List[Any]:
    coordinates = values["geometry"]["coordinates"][0]
    bbox = [
        coordinates[0][0],
        coordinates[0][1],
        coordinates[0][0],
        coordinates[0][1],
    ]

    for coordinate in coordinates[1:]:

        if coordinate[0] < bbox[0]:
            bbox[0] = coordinate[0]

        elif coordinate[0] > bbox[2]:
            bbox[2] = coordinate[0]

        if coordinate[1] < bbox[1]:
            bbox[1] = coordinate[1]

        elif coordinate[1] > bbox[3]:
            bbox[3] = coordinate[1]

    return bbox


def generate_properties() -> Dict[str, Any]:
    result: Dict[str, Any] = ESGFPropertiesFactory.build().to_dict()
    return result


def generate_links(
    name: str, values: dict[str, Any], *args: P.args, **kwarg: P.kwargs
) -> List[Dict[str, Any]]:
    return [
        {
            "rel": "self",
            "type": "application/geo+json",
            "href": urljoin(
                API_URL,
                f"/collections/{values['collection']}/items/{values['id']}",
            ),
        },
        {
            "rel": "parent",
            "type": "application/json",
            "href": urljoin(API_URL, f"/collections/{values['collection']}"),
        },
        {
            "rel": "collection",
            "type": "application/json",
            "href": urljoin(API_URL, f"/collections/{values['collection']}"),
        },
        {
            "rel": "root",
            "type": "application/json",
            "href": API_URL,
        },
    ]


class ESGFItemFactory(ModelFactory[ESGFItem]):
    __model__ = ESGFItem
    collection = Use(choose, CHOICES["collection"])
    properties = Use(generate_properties)
    geometry = Use(generate_geometry)
    id = PostGenerated(generate_id)
    links = PostGenerated(generate_links)
    bbox = PostGenerated(generate_bbox)
    citation_url = PostGenerated(generate_citation_url)
    stac_version = "1.0.0"


def post_to_stac(data: ESGFItem) -> None:
    client = httpx.Client(
        auth=None,
        verify=False,
        timeout=180,
    )

    response = client.post(
        urljoin(API_URL, f"collections/{data.collection}/items"),
        content=data.json(),
    )
    if response.status_code >= 300:
        warnings.warn(f"Failed to post {data.json()}")
