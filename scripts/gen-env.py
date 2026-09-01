#!/usr/bin/env python3
"""从 Docker 栈的 .env 生成本地开发用 .env。

只改写连接地址（容器服务名 → 127.0.0.1、MySQL 端口 → 3307、数据目录 → .data），
密钥原样透传，不经过 shell，不打印到日志。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / ".data"
MYSQL_PORT = 3307

# 容器服务名 → 本地地址
HOST_REWRITES = {
    "mysql": f"127.0.0.1:{MYSQL_PORT}",
    "redis": "127.0.0.1:6379",
    "neo4j": "127.0.0.1:7687",
    "qdrant": "127.0.0.1",
}


def rewrite(key: str, value: str) -> str:
    """改写单个环境变量的值。"""
    if key in ("DATABASE_URL", "RAG_DATABASE_URL"):
        # mysql+pymysql://user:pass@mysql:3306/db → @127.0.0.1:3307/db
        return re.sub(r"@[^/@]+/", f"@127.0.0.1:{MYSQL_PORT}/", value)
    if key == "REDIS_URL":
        return re.sub(r"://[^/]+", "://127.0.0.1:6379", value)
    if key == "NEO4J_URI":
        return "bolt://127.0.0.1:7687"
    if key == "QDRANT_HOST":
        return "127.0.0.1"
    if key == "PYTHON_BACKEND_URL":
        return "http://127.0.0.1:8000"
    if key == "SC_WIKI_DATA_DIR":
        return str(DATA_DIR)
    return value


# 本地环境必须存在、旧 .env 里可能缺失的项
DEFAULTS = {
    "REDIS_URL": "redis://127.0.0.1:6379/0",
    "NEO4J_URI": "bolt://127.0.0.1:7687",
    "QDRANT_HOST": "127.0.0.1",
    "QDRANT_PORT": "6333",
    "SC_WIKI_DATA_DIR": str(DATA_DIR),
    "PYTHON_BACKEND_URL": "http://127.0.0.1:8000",
    "PORT": "8080",
    "AVATAR_DIR": str(DATA_DIR / "avatars"),
}


def main() -> int:
    if len(sys.argv) != 3:
        print("用法: gen-env.py <源 .env> <目标 .env>", file=sys.stderr)
        return 2
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    if not src.is_file():
        print(f"源文件不存在: {src}", file=sys.stderr)
        return 1

    seen: set[str] = set()
    lines: list[str] = [
        "# SC-Wiki 本地开发环境变量（由 scripts/gen-env.py 生成）",
        "# 全部服务跑在宿主机 127.0.0.1，不依赖 Docker。",
        f"# MySQL 用 {MYSQL_PORT}：宿主机 3306 已被系统级 MySQL 占用。",
        "",
    ]

    for raw in src.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            lines.append(raw)
            continue
        key, _, value = stripped.partition("=")
        key = key.strip()
        seen.add(key)
        lines.append(f"{key}={rewrite(key, value.strip())}")

    missing = {k: v for k, v in DEFAULTS.items() if k not in seen}
    if missing:
        lines += ["", "# ── 本地开发补充项 ──"]
        lines += [f"{k}={v}" for k, v in missing.items()]

    dst.write_text("\n".join(lines) + "\n", encoding="utf-8")
    dst.chmod(0o600)
    print(f"已生成 {dst}（{len(seen)} 项透传，{len(missing)} 项补充）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
