import os
from typing import Generator

import pytest
from click.testing import CliRunner
from dotenv import find_dotenv, load_dotenv, unset_key

from esgf_generator.cli import esgf_generator, validate_token

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


def test_invalid_credentials(runner: CliRunner) -> None:
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
    user_input = "test_user\ntest_user"

    result = runner.invoke(
        esgf_generator, ["1", "--node", "east", "--publish"], input=user_input
    )

    if result.exit_code != 0:
        pytest.fail(f"Expected exit code 0, got {result.exit_code}")

    if not validate_token():
        pytest.fail("Token validation failed")


def test_invalid_token(runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TOKEN", "invalid_token")

    if validate_token():
        pytest.fail("Token validation should have failed for invalid token")


def test_get_token(runner: CliRunner) -> None:
    user_input = "test_user\ntest_user"

    result = runner.invoke(
        esgf_generator, ["1", "--node", "east", "--publish"], input=user_input
    )

    load_dotenv(ENV_FILE)
    token = os.getenv("TOKEN")

    if result.exit_code != 0:
        pytest.fail(f"Expected exit code 0, got {result.exit_code}")

    if not token:
        pytest.fail("Token should be set")
