"""
Models for esgf_consumer app.
"""

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel
from stac_pydantic.api import Item


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


class ErrorType(str, Enum):
    payload = "payload"
    stac_server = "stac_server"
    kafka = "kafka"
    unknown = "unknown"


class Error(BaseModel):
    original_payload: str
    node: str
    traceback: str
    error_type: ErrorType
