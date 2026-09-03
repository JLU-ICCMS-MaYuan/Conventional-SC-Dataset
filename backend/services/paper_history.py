"""Append-only paper processing-history writer shared by upload and editing flows."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import PaperHistoryEvent


HistoryEventType = Literal["uploaded", "modified", "reviewed"]
ReviewStatus = Literal["approved", "rejected", "pending"]


async def append_paper_history_event(
    session: AsyncSession,
    *,
    paper_id: int,
    paper_revision: int,
    event_type: HistoryEventType,
    actor_user_id: int | None,
    actor_username_snapshot: str | None,
    operation_id: str | None = None,
    review_status: ReviewStatus | None = None,
    review_comment: str | None = None,
    occurred_at: datetime | None = None,
    classification_snapshot: object | None = None,
) -> bool:
    """Write one event and return whether this call created it.

    `operation_id` is globally unique. The explicit pre-read gives retrying callers a
    normal success path; the nested transaction turns a concurrent duplicate-key race
    into the same result without rolling back the surrounding business transaction.
    """
    if event_type not in {"uploaded", "modified", "reviewed"}:
        raise ValueError("不支持的文献处理事件类型")
    if paper_revision < 1:
        raise ValueError("文献版本必须大于等于 1")
    if event_type == "reviewed":
        if review_status not in {"approved", "rejected", "pending"}:
            raise ValueError("审核事件必须包含有效审核结果")
    elif review_status is not None or review_comment is not None:
        raise ValueError("上传和修改事件不得包含审核结果或审核意见")
    if event_type != "uploaded" and actor_user_id is None:
        raise ValueError("修改和审核事件必须包含操作者")
    if operation_id is not None and len(operation_id) > 64:
        raise ValueError("history_operation_id 过长")

    if operation_id:
        existing = await session.scalar(
            select(PaperHistoryEvent.id).where(PaperHistoryEvent.operation_id == operation_id)
        )
        if existing is not None:
            return False

    event = PaperHistoryEvent(
        paper_id=paper_id,
        paper_revision=paper_revision,
        event_type=event_type,
        actor_user_id=actor_user_id,
        actor_username_snapshot=actor_username_snapshot,
        review_status=review_status,
        review_comment=review_comment,
        operation_id=operation_id,
        occurred_at=occurred_at,
        classification_snapshot=classification_snapshot,
    )
    try:
        async with session.begin_nested():
            session.add(event)
            await session.flush()
    except IntegrityError:
        # The unique operation ID is the cross-service idempotency boundary.
        return False
    return True
