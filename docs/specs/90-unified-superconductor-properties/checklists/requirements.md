# 需求质量检查表：统一材料状态的超导物性记录

**目的**：检查 #90 的领域边界、完整结构、既有约束继承、迁移和验收是否明确可执行。

**创建日期**：2026-09-04

**Feature**：[spec.md](../spec.md)

## 完整性

- [x] CHK001 已明确唯一平级集合和完整记录结构（FR-001–FR-004、`data-model.md` 第 2–5 节）。
- [x] CHK002 已明确禁止的分组名称和无 Context 记录的归属（FR-002、FR-006）。
- [x] CHK003 已覆盖 Tc、λ、ωlog、μ*、DOS、Hc2、超导能隙及可扩展物性（FR-004–FR-005）。
- [x] CHK004 已定义 Context、Structure、Evidence 和 revision 关系（FR-007–FR-011、FR-016）。
- [x] CHK005 已定义 Tc 专用字段、理论/实验互斥和代表结果规则（FR-012–FR-015）。
- [x] CHK006 已定义上传、管理、详情、探索、社区、搜索、图表和删除影响面（FR-018–FR-027）。
- [x] CHK007 已定义旧草稿、详情响应、缓存版本、数据回填和回滚边界（FR-021–FR-025）。
- [x] CHK008 已列出实现后需要更新的全部 Overview，且当前未提前修改（FR-030、`research.md` 第 3.1 节）。

## 清晰度与可度量性

- [x] CHK009 “平级”已定义为无容器关系，不等于无 Context 关联（`data-model.md` 第 1 节）。
- [x] CHK010 `context_key` 已定义为系统管理的接口关联键，不是数据库 ID（FR-008、契约 Context 规则）。
- [x] CHK011 相同 Context 内容冲突、跨状态复用和结构不一致均有明确失败规则（FR-009–FR-011）。
- [x] CHK012 成功标准包含记录数、关系准确率、非法组合拒绝、迁移计数和图表不回退（SC-001–SC-008）。
- [x] CHK013 Evidence 缺失迁移不使用“尽量恢复”等模糊表述，明确禁止编造并要求逐条报告（FR-025）。

## 一致性与覆盖

- [x] CHK014 Issue #90、Spec、数据模型和接口契约均不使用 `TcRelated/OtherProperties/UncontextualizedProperties` 作为结构。
- [x] CHK015 λ、ωlog、μ* 在领域、接口和持久化计划中均为独立记录，没有双重权威来源。
- [x] CHK016 Tc 平级化没有取消 #84 方法规则和 #32/#33 revision/Evidence 约束。
- [x] CHK017 `superconductor_kind` 与 `tc_method` 的职责冲突已按 #84 明确消解。
- [x] CHK018 “不物理合并宽表”与“需要定点 Schema 演进”没有冲突，迁移范围已列明。
- [x] CHK019 每项 FR 均映射到 `tasks.md` 的实施或验证任务。
- [x] CHK020 每个用户故事均有独立验收和对应测试任务。

## 范围控制

- [x] CHK021 已排除完整物性本体、张量/曲线模型、跨论文去重和图表产品改版。
- [x] CHK022 未因统一领域模型而恢复旧 `superconductor_records` 或 `key_properties` 表。
- [x] CHK023 未把 #46/#52 的开放状态误写为已关闭。
- [x] CHK024 未把尚未实现的 #90 设计写入 `docs/overview/`。
- [x] CHK025 结果级方法/判据与共享 Context 的所有权已明确，避免实验 Context 再次只围绕 Tc 建模（FR-031）。

## 备注

- 本检查表检查需求文本质量，不测试代码或实现行为。
- 当前结论：需求、设计、任务和验收覆盖完整，没有阻断实施的待澄清项。
