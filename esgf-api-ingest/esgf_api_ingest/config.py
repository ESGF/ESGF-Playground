"""
Configuration for esgf_consumer
"""

from typing import List
from pydantic import HttpUrl

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    bootstrap_servers: List[str] = ["localhost"]
