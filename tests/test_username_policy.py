import pytest

from backend.username_policy import (
    generate_historical_username,
    is_historical_username,
    validate_username,
)


@pytest.mark.parametrize("value", ["Alice", "alice", "A_1", "Researcher_2026"])
def test_valid_usernames(value):
    assert validate_username(value) is None


@pytest.mark.parametrize(
    "value",
    ["ab", "1alice", "a-b", "a b", "管理员", "Admin", "ROOT", "sc_demo", "SC_demo"],
)
def test_invalid_or_reserved_usernames(value):
    assert validate_username(value)


def test_historical_username_is_private_and_well_formed():
    generated = {generate_historical_username() for _ in range(100)}

    assert len(generated) == 100
    assert all(len(value) == 15 and value.startswith("sc_") for value in generated)
    assert all(value[3:].isalnum() and value[3:].islower() for value in generated)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("sc_0123456789ab", True),
        ("SC_0123456789ab", False),
        ("sc_0123456789AB", False),
        ("sc_too_short", False),
    ],
)
def test_historical_username_format(value, expected):
    assert is_historical_username(value) is expected
