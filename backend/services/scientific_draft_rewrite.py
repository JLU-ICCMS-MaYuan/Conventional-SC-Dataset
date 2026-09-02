"""科学数据整体重写：单事务内删除论文当前科学实体并按请求体重建。

Issue #76：管理员在审核编辑页修改材料状态、Tc、普通物性与结构附件。
语义是整体替换而非增量更新（契约 scientific-draft-api.md C1），
删除顺序严格复用 goserver/handlers/paper_deletion.go 已验证的依赖逆序（R4）。

本模块只负责删除与版本字段更新；重建由 backend/ingest/scientific_drafts.py
的 persist_scientific_draft 承担（与上传提交链路同实现，保证产出一致）。
"""
from __future__ import annotations

from sqlalchemy import text, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Paper, PaperReviewEvent


async def delete_scientific_entities(session: AsyncSession, paper_id: int) -> None:
    """按依赖逆序删除论文的科学实体，共 6 步。

    与 paper_deletion.go 的 cascadeDeleteInDB 前 6 步一致；本模块**不触碰**
    paper_evidences / paper_chunks / paper_files——它们的 paper_revision
    由外键级联自动更新（见 data-model.md 外键迁移）。
    """
    # 1. 证据连接表：引用 tc_results / structure_models / superconductor_properties
    for table in (
        "tc_result_evidences",
        "structure_model_evidences",
        "superconductor_property_evidences",
    ):
        await session.execute(text(f"DELETE FROM {table} WHERE paper_id = :pid"), {"pid": paper_id})

    # 2. 叶子业务表
    for table in ("tc_results", "superconductor_properties"):
        await session.execute(text(f"DELETE FROM {table} WHERE paper_id = :pid"), {"pid": paper_id})

    # 3. 上下文表
    for table in ("calculation_contexts", "experimental_contexts"):
        await session.execute(text(f"DELETE FROM {table} WHERE paper_id = :pid"), {"pid": paper_id})

    # 4. structure_models：自引用 parent_structure_id 先置空再删，
    #    否则同论文内父子结构的删除先后顺序不定，可能触发外键错误。
    await session.execute(
        text(
            "UPDATE structure_models SET parent_structure_id = NULL "
            "WHERE paper_id = :pid AND parent_structure_id IS NOT NULL"
        ),
        {"pid": paper_id},
    )
    await session.execute(
        text("DELETE FROM structure_models WHERE paper_id = :pid"), {"pid": paper_id}
    )

    # 5. 连接表无 paper_id，按本论文的材料状态子查询删除
    await session.execute(
        text(
            "DELETE FROM material_state_structure_families "
            "WHERE material_state_id IN (SELECT id FROM material_states WHERE paper_id = :pid)"
        ),
        {"pid": paper_id},
    )

    # 6. 材料状态（此时全部子表已清空）
    await session.execute(
        text("DELETE FROM material_states WHERE paper_id = :pid"), {"pid": paper_id}
    )


async def bump_paper_revision(session: AsyncSession, paper: Paper) -> None:
    """升版：单条 UPDATE 三个版本字段，触发外键级联迁移血缘数据。

    三个字段必须同一条 UPDATE 写入（R7）：分多条会产生违约的中间状态。
    content_revision 条件同时充当并发保护——行数不为 1 说明版本已被并发修改。

    必须用 `synchronize_session=False`：默认的 auto 会把 UPDATE 结果同步回
    identity map 中已加载的 paper（content_revision 已 +1），再手动同步就会
    重复递增（1 → 2 → 3）。
    """
    result = await session.execute(
        update(Paper)
        .where(Paper.id == paper.id, Paper.content_revision == paper.content_revision)
        .values(
            content_revision=paper.content_revision + 1,
            approved_revision=None,
            review_status="pending",
        )
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        raise RuntimeError("升版失败：论文版本已被并发修改，请刷新后重试")
    # 手动同步 ORM 对象内存值，供 persist_scientific_draft 使用新版本号
    paper.content_revision += 1
    paper.approved_revision = None
    paper.review_status = "pending"


async def record_revision_event(
    session: AsyncSession,
    paper: Paper,
    reviewer_user_id: int,
    comment: str = "科学数据升版重审：内容版本号递增并退回待审核",
) -> None:
    """升版写入一条审核事件（R8），使「已公开 → 待审核」可溯源。"""
    session.add(
        PaperReviewEvent(
            paper_id=paper.id,
            paper_revision=paper.content_revision,
            reviewer_user_id=reviewer_user_id,
            status="pending",
            review_comment=comment,
            source="rewrite",
        )
    )
