import time
from typing import Any

import pytest
from click.testing import CliRunner, Result
from elasticsearch import Elasticsearch

from .cli import esgf_delete, esgf_generator, esgf_update

es = Elasticsearch(["http://localhost:9200"])


collection_id: str = ""
item_id: str = ""


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def get_item_details(result: Result) -> None:
    global collection_id, item_id
    output_lines = result.output.splitlines()
    for line in output_lines:
        if "Generated item with ID" in line:
            parts = line.split()
            item_id = parts[4]
            collection_id = parts[-1]


def check_elasticsearch_index(expected_properties: dict[str, Any]) -> None:
    global collection_id, item_id
    time.sleep(8)
    response = es.get(
        index=f"items_{collection_id}-000001", id=f"{item_id}|{collection_id}"
    )
    source = response["_source"]

    for key, value in expected_properties.items():
        keys = key.split(".")
        current = source
        for k in keys:
            if k not in current:
                raise KeyError(f"Key '{keys}' not found in the document")
            current = current[k]
        if current != value:
            f"Expected {keys} to be {value}, but got {current}"


def test_add_new_item(runner: CliRunner) -> None:
    global collection_id, item_id
    result = runner.invoke(esgf_generator, ["1", "--node", "east", "--publish"])
    time.sleep(20)

    if result.exit_code != 0:
        raise RuntimeError(f"Command failed with exit code {result.exit_code}")
    get_item_details(result)
    check_elasticsearch_index({"properties.title": f"{item_id}"})


def test_add_replica(runner: CliRunner) -> None:
    global collection_id, item_id
    result = runner.invoke(
        esgf_update,
        [
            collection_id,
            item_id,
            "--node",
            "east",
            "--publish",
            "--partial",
            '{"properties": {"Replica": "Node 1"}}',
        ],
    )
    if result.exit_code != 0:
        raise RuntimeError(f"Command failed with exit code {result.exit_code}")
    check_elasticsearch_index({"properties.Replica": "Node 1"})


def test_update_item(runner: CliRunner) -> None:
    global collection_id, item_id
    result = runner.invoke(
        esgf_update,
        [
            collection_id,
            item_id,
            "--node",
            "east",
            "--publish",
            "--partial",
            '{"properties": {"description": "Test Description"}}',
        ],
    )
    if result.exit_code != 0:
        raise RuntimeError(f"Command failed with exit code {result.exit_code}")
    check_elasticsearch_index({"properties.description": "Test Description"})


def test_remove_replica(runner: CliRunner) -> None:
    global collection_id, item_id
    result = runner.invoke(
        esgf_delete,
        [
            collection_id,
            item_id,
            "--node",
            "east",
            "--soft",
            "--publish",
        ],
    )
    if result.exit_code != 0:
        raise RuntimeError(f"Command failed with exit code {result.exit_code}")
    check_elasticsearch_index({"properties.retracted": True})


def test_remove_item(runner: CliRunner) -> None:
    global collection_id, item_id
    result = runner.invoke(
        esgf_delete,
        [collection_id, item_id, "--node", "east", "--hard", "--publish"],
    )
    if result.exit_code != 0:
        raise RuntimeError(f"Command failed with exit code {result.exit_code}")
    response = es.exists(index="item_{collection_id}-000001", id=item_id)
    if response:
        raise ValueError("Document still exists after deletion")
