import time
from typing import Generator, Union

import pytest
from click.testing import CliRunner, Result
from dotenv import find_dotenv, load_dotenv, unset_key
from elasticsearch import Elasticsearch

from esgf_generator.cli import esgf_delete, esgf_generator, esgf_replicate, esgf_update

es = Elasticsearch(["http://localhost:9200"])

ENV_FILE = find_dotenv()
load_dotenv(ENV_FILE)

collection_id: str = ""
item_id: str = ""


@pytest.fixture(autouse=True)
def clean_env() -> Generator[None, None, None]:
    unset_key(ENV_FILE, "TOKEN")
    load_dotenv(ENV_FILE)

    yield

    unset_key(ENV_FILE, "TOKEN")
    load_dotenv(ENV_FILE)


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def get_item_details(result: Result) -> None:
    global collection_id, item_id
    output_lines = result.output.splitlines()
    for line in output_lines:
        if "Sending" in line:
            parts = line.split(", ")
            item_id = parts[0].split()[1]
            collection_id = parts[1].split()[1]


def check_elasticsearch_index(expected_properties: dict[str, Union[str, bool]]) -> None:
    time.sleep(20)
    response = es.get(
        index=f"items_{collection_id}-000001", id=f"{item_id}|{collection_id}"
    )
    source = response["_source"]

    for key, value in expected_properties.items():
        keys = key.split(".")
        current = source
        for k in keys:
            if k not in current:
                pytest.fail(f"Key '{keys}' not found in the document")
            current = current[k]
        if current != value:
            pytest.fail(f"Expected {keys} to be {value}, but got {current}")


def test_add_new_item(runner: CliRunner) -> None:
    """
    Test adding a new item using the esgf_generator CLI command.
    """
    user_input = "test_user\ntest_user"

    result = runner.invoke(
        esgf_generator, ["1", "--node", "east", "--publish"], input=user_input
    )
    time.sleep(15)

    if result.exit_code != 0:
        pytest.fail(f"Command failed with exit code {result.exit_code}")
    get_item_details(result)
    check_elasticsearch_index({"properties.title": f"{item_id}"})


def test_add_replica(runner: CliRunner) -> None:
    """
    Test adding a replica using the esgf_replicate CLI command.
    """
    user_input = "test_user\ntest_user"

    result = runner.invoke(
        esgf_replicate,
        [
            collection_id,
            item_id,
            "--node",
            "east",
            "--publish",
        ],
        input=user_input,
    )
    if result.exit_code != 0:
        pytest.fail(f"Command failed with exit code {result.exit_code}")
    check_elasticsearch_index({"properties.replica": True})


def test_remove_replica(runner: CliRunner) -> None:
    """
    Test removing a replica using the esgf_update CLI command.
    """
    user_input = "test_user\ntest_user"

    result = runner.invoke(
        esgf_update,
        [
            collection_id,
            item_id,
            "--publish",
            "--node",
            "east",
            "--partial",
            '{"properties": {"replica": false}}',
        ],
        input=user_input,
    )
    if result.exit_code != 0:
        pytest.fail(f"Command failed with exit code {result.exit_code}")
    check_elasticsearch_index({"properties.replica": False})


def test_esgf_update_invalid_json(runner: CliRunner) -> None:
    """
    Test updating an item with invalid JSON using the esgf_update CLI command.
    """
    user_input = "test_user\ntest_user"

    result = runner.invoke(
        esgf_update,
        [
            "collection_id",
            "item_id",
            "--node",
            "east",
            "--partial",
            '{"properties": {"replica": False}}',
        ],
        input=user_input,
    )
    if "Invalid JSON string" not in result.output:
        pytest.fail("Expected 'Invalid JSON string' in output")


def test_update_item(runner: CliRunner) -> None:
    """
    Test updating an item using the esgf_update CLI command.
    """
    user_input = "test_user\ntest_user"

    result = runner.invoke(
        esgf_update,
        [
            collection_id,
            item_id,
            "--node",
            "east",
            "--publish",
        ],
        input=user_input,
    )
    if result.exit_code != 0:
        pytest.fail(f"Command failed with exit code {result.exit_code}")
    if "Done" not in result.output:
        pytest.fail("Failed to update item")


def test_retract_item(runner: CliRunner) -> None:
    """
    Test retracting an item using the esgf_delete CLI command.
    """
    user_input = "test_user\ntest_user"

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
        input=user_input,
    )
    if result.exit_code != 0:
        pytest.fail(f"Command failed with exit code {result.exit_code}")
    check_elasticsearch_index({"properties.retracted": True})


def test_unretract_item(runner: CliRunner) -> None:
    """
    Test unretracting an item using the esgf_update CLI command.
    """
    user_input = "test_user\ntest_user"

    result = runner.invoke(
        esgf_update,
        [
            collection_id,
            item_id,
            "--node",
            "east",
            "--publish",
            "--partial",
            '{"properties": {"retracted": false}}',
        ],
        input=user_input,
    )
    if result.exit_code != 0:
        pytest.fail(f"Command failed with exit code {result.exit_code}")
    check_elasticsearch_index({"properties.retracted": False})


def test_role_based_access(runner: CliRunner) -> None:
    """
    Test role-based access using the esgf_generator CLI command.
    """
    user_input = "test_user\ntest_user"

    result = runner.invoke(
        esgf_delete,
        [collection_id, item_id, "--node", "east", "--hard", "--publish"],
        input=user_input,
    )
    if "Not enough permissions" not in result.output:
        pytest.fail("Not enough permissions")


def test_remove_item(runner: CliRunner) -> None:
    """
    Test removing an item using the esgf_delete CLI command.
    """
    user_input = "test_admin\ntest_admin"

    result = runner.invoke(
        esgf_delete,
        [collection_id, item_id, "--node", "east", "--hard", "--publish"],
        input=user_input,
    )
    if result.exit_code != 0:
        pytest.fail(f"Command failed with exit code {result.exit_code}")
    response = es.exists(index="item_{collection_id}-000001", id=item_id)
    if response:
        pytest.fail("Document still exists after deletion")


def test_delete_non_existent_item(runner: CliRunner) -> None:
    """
    Test deleting a non-existent item using the esgf_delete CLI command.
    """
    user_input = "test_admin\ntest_admin"

    result = runner.invoke(
        esgf_delete,
        [collection_id, item_id, "--node", "east", "--hard", "--publish"],
        input=user_input,
    )
    time.sleep(5)

    if "Cannot operate on non-existent item" not in result.output:
        pytest.fail("Expected 'Cannot operate on non-existent item' in output")


def test_update_non_existent_item(runner: CliRunner) -> None:
    """
    Test updating a non-existent item using the esgf_update CLI command.
    """
    user_input = "test_user\ntest_user"

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
        input=user_input,
    )
    time.sleep(5)

    if "Cannot operate on non-existent item" not in result.output:
        pytest.fail("Expected 'Cannot operate on non-existent item' in output")
