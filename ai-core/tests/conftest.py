"""Test fixtures for osAfrica AI core."""

import pytest


@pytest.fixture
def sample_code_request():
    return "write a Python function to sort a list of dictionaries by a key"


@pytest.fixture
def sample_command_request():
    return "find all python files modified in the last 24 hours"


@pytest.fixture
def sample_general_request():
    return "what is the capital of France"


@pytest.fixture
def sample_dangerous_command():
    return "rm -rf /"
