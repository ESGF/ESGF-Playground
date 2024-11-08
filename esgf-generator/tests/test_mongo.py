from typing import Any, Dict, Generator

import pytest
from click.testing import CliRunner, Result
from dotenv import find_dotenv, load_dotenv, unset_key
from pymongo import MongoClient

from esgf_generator.cli import esgf_delete, esgf_generator, esgf_replicate, esgf_update

client: MongoClient[Dict[str, Any]] = MongoClient(
    "mongodb://root:example@localhost:27017/"
)
db = client["esgf_playground_db"]
collection = db["esgf_data_collection"]

collection_id: str = ""
item_id: str = ""

ENV_FILE = find_dotenv()
load_dotenv(ENV_FILE)


def get_item_details(result: Result) -> None:
    global collection_id, item_id
    output_lines = result.output.splitlines()
    for line in output_lines:
        if "Sending" in line:
            parts = line.split(", ")
            item_id = parts[0].split()[1]
            collection_id = parts[1].split()[1]


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture(autouse=True)
def clean_env() -> Generator[None, None, None]:
    unset_key(ENV_FILE, "TOKEN")
    load_dotenv(ENV_FILE)

    yield

    unset_key(ENV_FILE, "TOKEN")
    load_dotenv(ENV_FILE)


def test_database_connection() -> None:
    try:
        client.admin.command("ping")
    except Exception as e:
        pytest.fail(f"Database is not running: {e}")


def test_create_event_in_database(runner: CliRunner) -> None:
    result = runner.invoke(
        esgf_generator,
        ["1", "--node", "east", "--publish"],
        input="test_user\ntest_user",
    )
    get_item_details(result)

    event = collection.find_one({"data.payload.method": "POST"})
    if event is None:
        pytest.fail("Create event not found in database")


def test_update_event_in_database(runner: CliRunner) -> None:
    runner.invoke(
        esgf_update,
        ["collection_id", "item_id", "--node", "east", "--publish"],
        input="test_user\ntest_user",
    )
    event = collection.find_one({"data.payload.method": "PUT"})
    if event is None:
        pytest.fail("Update event not found in database")


def test_patch_event_in_database(runner: CliRunner) -> None:
    runner.invoke(
        esgf_replicate,
        [
            collection_id,
            item_id,
            "--node",
            "east",
            "--publish",
        ],
        input="test_user\ntest_user",
    )
    event = collection.find_one({"data.payload.method": "PATCH"})
    if event is None:
        pytest.fail("Patch event not found in database")


def test_delete_event_in_database(runner: CliRunner) -> None:
    runner.invoke(
        esgf_delete,
        ["collection_id", "item_id", "--node", "east", "--publish"],
        input="test_admin\ntest_admin",
    )
    event = collection.find_one({"data.payload.method": "DELETE"})
    if event is None:
        pytest.fail("Delete event not found in database")
