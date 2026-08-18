"""四组消融只能获得冻结声明的工具。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


TEST_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TEST_ROOT))

from benchmark.runners.ablation import resolve_ablation_tools  # noqa: E402
from benchmark.scaffold import EXPECTED_ABLATION_TOOLS  # noqa: E402


def test_all_four_groups_receive_only_declared_tools() -> None:
    registry = {name: object() for names in EXPECTED_ABLATION_TOOLS.values() for name in names}

    for group, expected_names in EXPECTED_ABLATION_TOOLS.items():
        selected = resolve_ablation_tools(group, registry)
        assert selected == [registry[name] for name in expected_names]


def test_unknown_group_and_missing_tool_fail_closed() -> None:
    with pytest.raises(ValueError):
        resolve_ablation_tools("invented", {})
    with pytest.raises(KeyError):
        resolve_ablation_tools("qdrant_only", {})
