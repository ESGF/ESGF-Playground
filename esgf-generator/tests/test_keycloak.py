import os
import time
from typing import Generator, Optional, Tuple

import pytest
from click.testing import CliRunner, Result
from dotenv import find_dotenv, load_dotenv, unset_key

from esgf_generator.cli import esgf_delete, esgf_generator, validate_token

ENV_FILE = find_dotenv()

if ENV_FILE is None:
    raise Exception("No .env file found, please create one in the root directory")


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


def get_item_details(result: Result) -> Optional[Tuple[str, str]]:
    if result is None:
        return None
    output_lines = result.output.splitlines()

    for line in output_lines:
        if "Sending" in line:
            parts = line.split(", ")
            item_id = parts[0].split()[1]
            collection_id = parts[1].split()[1]
            return collection_id, item_id
    return None


def delete_generated_item(runner: CliRunner, collection_id: str, item_id: str) -> None:
    runner.invoke(
        esgf_delete,
        [
            collection_id,
            item_id,
            "--node",
            "east",
            "--hard",
            "--publish",
        ],
    )


def test_invalid_credentials(runner: CliRunner) -> None:
    """
    Test invalid keycloak credentials when trying to run a command.
    """
    user_input = "invalid_user\ninvalid_user"

    result = runner.invoke(
        esgf_generator, ["1", "--node", "east", "--publish"], input=user_input
    )

    load_dotenv(ENV_FILE)
    token = os.getenv("TOKEN")

    if "Authentication Failed" not in result.output:
        pytest.fail("Expected 'Authentication Failed' in output")

    if token:
        pytest.fail("Token should not be set")


def test_validate_token(runner: CliRunner) -> None:
    """
    Test validating an access token.
    """
    user_input = "test_admin\ntest_admin"

    result = runner.invoke(
        esgf_generator, ["1", "--node", "east", "--publish"], input=user_input
    )

    details = get_item_details(result)

    if details is None:
        pytest.fail("Coould not retreive collection_id and item_id")

    if result.exit_code != 0:
        pytest.fail(f"Expected exit code 0, got {result.exit_code}")

    if not validate_token():
        pytest.fail("Token validation failed")

    collection_id, item_id = details
    time.sleep(15)
    delete_generated_item(runner, collection_id, item_id)


def test_invalid_token(runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Test validating an invalid access token.
    """
    monkeypatch.setenv("TOKEN", "invalid_token")

    if validate_token():
        pytest.fail("Token validation should have failed for invalid token")


def test_get_token(runner: CliRunner) -> None:
    """
    Test retreiving a new access token.
    """
    user_input = "test_admin\ntest_admin"

    result = runner.invoke(
        esgf_generator, ["1", "--node", "east", "--publish"], input=user_input
    )

    details = get_item_details(result)

    if details is None:
        pytest.fail("Coould not retreive collection_id and item_id")

    load_dotenv(ENV_FILE)
    token = os.getenv("TOKEN")

    if result.exit_code != 0:
        pytest.fail(f"Expected exit code 0, got {result.exit_code}")

    if not token:
        pytest.fail("Token should be set")

    collection_id, item_id = details
    time.sleep(15)
    delete_generated_item(runner, collection_id, item_id)
