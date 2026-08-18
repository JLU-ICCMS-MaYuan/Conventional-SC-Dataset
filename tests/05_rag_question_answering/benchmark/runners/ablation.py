"""将冻结的消融组解析为可注入 Mentor 的真实工具对象。"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from benchmark.scaffold import EXPECTED_ABLATION_TOOLS


def resolve_ablation_tools(group: str, registry: Mapping[str, Any]) -> list[Any]:
    """严格按冻结配置选择工具；缺工具或未知组立即失败。"""

    if group not in EXPECTED_ABLATION_TOOLS:
        raise ValueError(f"未知消融组: {group}")
    names = EXPECTED_ABLATION_TOOLS[group]
    missing = [name for name in names if name not in registry]
    if missing:
        raise KeyError(f"工具注册表缺少: {missing}")
    return [registry[name] for name in names]


def production_tool_registry() -> dict[str, Any]:
    """延迟导入生产工具，保持离线配置测试不依赖 LangChain。"""

    from backend.rag.agent import tools as production

    return {tool.name: tool for tool in production.ALL_TOOLS}
