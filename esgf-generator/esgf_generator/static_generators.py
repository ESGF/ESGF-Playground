from datetime import datetime
from random import random, uniform
from typing import Dict, List, Optional, Union

Coordinates = List[List[List[float]]]


def generate_geometry() -> Dict[str, Union[str, Coordinates]]:
    north = uniform(0, 180)
    south = uniform(-180, 0)
    east = uniform(0, 90)
    west = uniform(-90, 0)
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [south, west],
                [north, west],
                [north, east],
                [south, east],
                [south, west],
            ],
        ],
    }


def generate_datetime(
    start_datetime: datetime, end_datetime: datetime
) -> Optional[datetime]:
    if random() > 0.2:
        result: datetime = start_datetime + random() * (end_datetime - start_datetime)
        return result
    else:
        return None


def instance_id(values: dict[str, str]) -> str:
    return f"{values['mip_era']}.{values['activity_id']}.{values['institution_id']}.{values['source_id']}.{values['experiment_id']}.{values['variant_label']}.{values['table_id']}.{values['variable_id']}.{values['grid_label']}.v20220101"
