import os
from typing import Generator

import pytest
from click.testing import CliRunner
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


def test_invalid_credentials(runner: CliRunner) -> None:

    user_input = "invalid_user\ninvalid_user"

    result = runner.invoke(
        esgf_generator, ["1", "--node", "east", "--publish"], input=user_input
    )

    load_dotenv(ENV_FILE)
    token = os.getenv("TOKEN")

    assert "Authentication Failed" in result.output

    assert not token


def test_validate_token(runner: CliRunner) -> None:

    user_input = "test_user\ntest_user"

    result = runner.invoke(
        esgf_generator, ["1", "--node", "east", "--publish"], input=user_input
    )

    assert result.exit_code == 0

    assert validate_token()


def test_invalid_token(runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TOKEN", "invalid_token")

    result = validate_token()

    assert not result


def test_get_token(runner: CliRunner) -> None:

    user_input = "test_user\ntest_user"

    result = runner.invoke(
        esgf_generator, ["1", "--node", "east", "--publish"], input=user_input
    )

    load_dotenv(ENV_FILE)
    token = os.getenv("TOKEN")

    assert result.exit_code == 0

    assert token is not None


def test_user_scope(runner: CliRunner) -> None:

    user_input = "test_user\ntest_user"

    result = runner.invoke(
        esgf_delete,
        ["collection_id", "item_id", "--node", "east", "--hard", "--publish"],
        input=user_input,
    )

    assert result.exit_code == 0

    assert "Not enough permissions" in result.output
