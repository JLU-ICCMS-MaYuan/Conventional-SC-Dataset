"""Shared public username rules for Python-side user workflows."""

import re
import secrets
import string


USERNAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]{2,31}$")
HISTORICAL_USERNAME_PATTERN = re.compile(r"^sc_[a-z0-9]{12}$")
RESERVED_USERNAMES = {
    "admin",
    "administrator",
    "root",
    "scwiki",
    "superadmin",
    "system",
}
_RANDOM_ALPHABET = string.ascii_lowercase + string.digits


def validate_username(username: str) -> str | None:
    if not USERNAME_PATTERN.fullmatch(username):
        return "用户名须为 3–32 位，以字母开头且只包含字母、数字和下划线"
    normalized = username.lower()
    if normalized.startswith("sc_"):
        return "sc_ 前缀由系统保留"
    if normalized in RESERVED_USERNAMES:
        return "该用户名由系统保留"
    return None


def is_historical_username(username: str) -> bool:
    return HISTORICAL_USERNAME_PATTERN.fullmatch(username) is not None


def generate_historical_username() -> str:
    return "sc_" + "".join(secrets.choice(_RANDOM_ALPHABET) for _ in range(12))
