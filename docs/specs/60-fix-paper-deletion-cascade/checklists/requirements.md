# 需求质量检查表：论文物理删除的级联清理

**目的**：审查删除需求文本自身的完整性、可度量性与一致性，特别是「关联表清单」这类
一旦写漏就会让主路径失效的事实性内容。

**创建日期**：2026-08-31

**Feature**：[spec.md](../spec.md)

## 完整性

- [x] CHK001 删除范围是否穷举了全部关联表？
  **初稿不合格**：FR-001 只列 9 张，实际 14 张，漏掉 `paper_files`、
  `tc_result_evidences`、`structure_model_evidences`、
  `superconductor_property_evidences`、`material_state_structure_families`。
  已按 `information_schema.KEY_COLUMN_USAGE` 实测补齐。
- [x] CHK002 明确声明了哪些表**不删**及理由？
  是。`superconductors`、`material_families`、`structure_families`、
  `property_definitions` 为跨论文共享目录数据（FR-005）。
- [x] CHK003 删除顺序的依据是否可追溯到权威来源？
  **初稿不合格**：顺序来自对 GORM 模型的推测，与真实外键相反，导致
  `Error 1451`。现 plan.md 记录了实测依赖图与拓扑逆序。
- [x] CHK004 外部系统（Qdrant/Neo4j）清理失败的处置是否明确？
  是。FR-002/FR-003 定义清理动作，research.md 决策 2 明确 best-effort 语义。
- [x] CHK005 是否覆盖批量删除的部分失败语义？
  是。FR-008 要求逐篇独立处理；contracts 规定 `206 + failed_ids`。

## 清晰度与可度量性

- [x] CHK006 「彻底删除」是否有可验证判据？
  是。SC-001 要求遍历 `information_schema` 中所有含 `paper_id` 的表均无残留，
  而非仅抽查若干张表。
- [x] CHK007 错误响应是否规定了具体状态码而非「返回错误」？
  是。contracts 列明 400/404/500/206 及各自 body 形状。
- [x] CHK008 是否规定原始数据库错误不得回传前端？
  是。contracts 明确原始 error 只写日志，因其含表名与约束名。

## 一致性与覆盖

- [x] CHK009 需求之间是否存在互相矛盾？
  已消解一处：FR-004 原要求更新 `upload_tasks` 表，但该状态存于 Redis，
  无此表。已撤销 FR-004 与 SC-007 并注明理由。
- [x] CHK010 事务边界是否与「外部清理失败不回滚」自洽？
  是。事务只覆盖 MySQL（FR-006），外部清理在提交后执行，两者不冲突。
- [x] CHK011 是否覆盖并发删除同一篇论文？
  是。边界场景规定第二次操作返回 404 而非报错，由 `ErrPaperNotFound` 实现。
- [x] CHK012 验证手段能否真正暴露顺序类缺陷？
  **初稿不合格**：单元测试用 SQLite 且未开外键强制，顺序写错仍通过。
  现已要求 `PRAGMA foreign_keys = ON` 并断言生效，且上线前须在真实 MySQL
  用事务演练（见 plan.md 验证方式、quickstart.md 步骤 1）。

## 备注

- 本检查表检查需求文本质量，不测试代码或实现行为。
- CHK001、CHK003、CHK012 三项初稿不合格，均为「未核实即写入 spec」造成，
  且直接导致线上删除功能不可用。后续涉及数据库结构的需求，应先查
  `information_schema` 再落笔。
