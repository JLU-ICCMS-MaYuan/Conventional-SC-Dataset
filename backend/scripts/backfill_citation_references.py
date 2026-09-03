"""Backfill GROBID reference facts for explicitly selected historical papers."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import sys

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
load_dotenv(REPO_ROOT / ".env")


def positive_paper_id(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("论文 ID 必须为正整数")
    return parsed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="用 GROBID 回填当前已审核论文的参考文献，不改变论文版本。"
    )
    targets = parser.add_mutually_exclusive_group(required=True)
    targets.add_argument(
        "--paper-id",
        action="append",
        type=positive_paper_id,
        help="要处理的论文 ID；可重复传入。",
    )
    targets.add_argument(
        "--all-approved",
        action="store_true",
        help="处理全部当前已审核论文。",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只检查处理范围与主 PDF，不调用 GROBID 或写数据库。",
    )
    return parser.parse_args()


async def run(args: argparse.Namespace) -> int:
    from backend.rag.config import settings
    from backend.rag.database import async_session_factory
    from backend.services.citation_backfill import (
        backfill_paper_set,
        list_current_approved_paper_ids,
    )

    paper_ids = (
        await list_current_approved_paper_ids(async_session_factory)
        if args.all_approved
        else args.paper_id
    )
    if not paper_ids:
        print("没有符合条件的当前已审核论文。")
        return 0

    results = await backfill_paper_set(
        async_session_factory,
        paper_ids,
        data_dir=settings.sc_wiki_data_dir,
        dry_run=args.dry_run,
    )
    for result in results:
        message = f"；{result.message}" if result.message else ""
        print(
            f"论文 {result.paper_id}，版本 {result.paper_revision}："
            f"{result.status}，参考文献 {result.reference_count} 条{message}"
        )
    failed = sum(result.failed for result in results)
    if failed:
        print(f"回填未完成：{failed} 篇论文失败或被跳过。", file=sys.stderr)
        return 1
    return 0


def main() -> None:
    args = parse_args()
    raise SystemExit(asyncio.run(run(args)))


if __name__ == "__main__":
    main()
