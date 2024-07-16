from datetime import datetime
from random import uniform, random
from typing import List, Dict, Union, Optional

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
    if random() > 0.9:
        result: datetime = start_datetime + random() * (end_datetime - start_datetime)
        return result
    else:
        return None
