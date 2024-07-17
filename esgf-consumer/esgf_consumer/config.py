"""
Configuration for esgf_consumer
"""

from typing import List, Pattern
from pydantic import HttpUrl
from re import compile

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    bootstrap_servers: List[str] = ["localhost"]
    consumer_group: str
    kafka_topics: Pattern[str] = compile(r".*\..*\..*")
    error_topic: str = "esgf_consumer_error"
    stac_server: HttpUrl = HttpUrl("http://localhost:9010")
