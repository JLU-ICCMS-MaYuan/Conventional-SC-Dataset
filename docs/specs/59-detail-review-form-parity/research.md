# 技术调研：只读详情页与校对表单一致

**Feature**：[spec.md](spec.md)

**日期**：2026-08-27

本文只记录本 Feature 内的技术决策与实测依据。

## D1：四个根因的实测确认

| 根因 | 位置 | 实测结论 |
|---|---|---|
| 详情页多出 min/max | `PaperEditView.tsx` 数值范围区 | 渲染「最小值」「最大值」两个输入框取自 `value_min`/`value_max`；校对页普通物性只有名称、原始值、单位三项（`UploadTaskEditor.tsx` 物性区）。paper 4 实测 `value_min`/`value_max` 均为 NULL，而真正有值的解析值 200 与 `unit_raw='meV/atom'` 不显示 |
| 缺整套分类字段 | `PaperEditView.tsx` 材料状态分类区 | 只显示材料、材料家族、元素种类数 3 项；校对页含晶系、空间群符号、空间群号、超导类型、维度、类型标签、压强、Tc 共 8 类字段 |
| 结构预览来源错误 | `PaperEditView.tsx` 结构区 | 原从 `key_properties[].structure_text` 取，而该字段是 `gorm:"-"` 兼容字段（#57 已删除）。结构真实存放于 `structure_models`；实测该表全库 0 行 |
| 研究方法形态 + 研究理由错配 | `PaperEditView.tsx` 研究方法与发现区 | `methodology` 以 `JSON.stringify` 回显为 JSON 原文；`rationale` 被标为「研究理由」 |

## D2：研究方法不存在中译英丢失——修正原始需求前提

**核实结论**：库内与草稿两端本就是英文术语列表，不存在中文被翻译成英文。

- 校对页 `UploadTaskEditor.tsx` 用 `['methodology', '研究方法（每行一项）']` + `toLines()` 逐行展示
- 详情页 `PaperEditView.tsx` 用 `JSON.stringify(data.methodology || [])` 展示

**因此用户感知的「提交中文、审核英文」实为展示形态差异**：同一份英文数据，一边按行排版、一边塞进 JSON 文本框。修复方向是统一为可读列表，而非增加翻译。此结论与 Issue 最初描述不同，已写入 spec 假设与 checklist CHK016。

## D3：`rationale` 与 `classification_reason` 的错配性质

后端 `backend/api/rag.py`：

```python
rationale=draft.get("classification_reason") or paper_data.get("rationale"),
```

草稿中两者是不同的两段文本：`paper.rationale` 是 AI 生成的全文工作概述（校对页不可见），`classification_reason` 是用户在校对页填写的分类说明。由于 `or` 短路，只要 `classification_reason` 非空，写进 `papers.rationale` 列的就是分类理由。

**决策**：本 Feature 只改展示标签（`rationale` 列的内容标为「分类理由」），不改写入侧。

**理由**：真正的修复是让两个字段各有归属（为 `rationale` 增设独立列，或明确该字段不入库），但那是数据模型与采集流程变更——需要迁移、需要决定校对页是否新增「研究理由」输入项、需要处理已入库的历史数据。混入一个前端展示 Feature 会越过数据所有权边界。已列入 spec 范围外事项。

**用户可见效果**：标签纠正后，用户在详情页看到的「分类理由」正是他在校对页填过的那段文本，「提交时没有、审核时凭空出现」的错觉消除。

## D4：不复用 `UploadTaskEditor` readOnly 模式

**决策**：改造 `PaperEditView`，不以 readOnly 承载详情页。（用户已确认此路线）

**核查到的有利条件**：`readOnly` 模式已成熟（`pointerEvents: 'none'` + 隐藏按钮 + 只读文案切换），`DraftMaterialState` 已含压强区间、晶系、`reported_space_group_symbol`/`_number`、`state_kind`、`tc_results`、`properties`，与 #57 新增的详情响应高度重合。

**否决理由——三处形态差异会导致丢数据**：

| 差异 | draft 形态 | 详情响应形态 | 后果 |
|---|---|---|---|
| 计算上下文 | `calculation_context`（单数，挂在每条 Tc 结果上） | `calculation_contexts`（材料状态级数组） | 数组→单数须人为定丢弃或合并规则。paper 4 有 2 条，**第一条全为 NULL**、第二条含 λ=2.56/μ*=0.1；简单取首条会使 λ 不可见 |
| 结构 | `structure`（单数） | `structures`（数组） | 同类丢数据风险 |
| 物性条件 | 含 `pressure_gpa`/`temperature_k` | 这些概念已归属材料状态（#57 已确认物性表无此列） | 适配层需反向拼装，与 #57 刚确立的数据归属相悖 |

**代价与对冲**：保留两套代码，未来仍可能漂移。对冲手段是 SC-001 的字段集一致性测试——以校对页字段清单为断言基准，任一侧新增字段而另一侧未跟进时测试失败。

## D5：计算上下文按材料状态级数组完整展示

**决策**：详情页在材料状态内列出全部 `calculation_contexts`，不按 Tc 结果分组、不做筛选合并。

**理由**：读取侧（#57）已确立「全部返回，不擅自判定哪条有效」。展示侧沿用同一原则；paper 4 的全 NULL 记录正是反例——任何「选一条」的规则都可能选中它而丢掉真实数值。

**与校对页的形态差异如实呈现**：校对页把 λ/ωlog/μ* 放在每条 Tc 结果内，因为草稿阶段每条 Tc 自带上下文。详情页按材料状态级数组展示，字段名称与含义一致，仅组织层级不同。这不违反 SC-001——基准是「字段集一致」，不是「DOM 结构一致」。

## D6：结构预览只能验证空态

`structure_models` 全库 0 行（paper 4 亦为 0）。因此：

- 空态分支可在 dev 环境实测；
- 有结构数据的渲染分支只能靠单元测试注入数据验证，dev 人工验收无法覆盖。

已写入 spec 假设、US3 优先级理由与 quickstart 场景 6 的说明，不把「能渲染 3D 预览」写成已在真实数据上验证的能力。

## D7：验证策略

**决策**：新增 Vitest 测试注入构造好的论文对象直接渲染 `PaperEditView`，断言渲染结果；不依赖真实接口。

**理由**：本 Feature 的故障边界是「渲染了什么/没渲染什么」，纯前端展示逻辑。数据契约已由 #57 的 Go 测试覆盖，此处重复请求层无收益。

**关键断言设计**：

- 字段集一致性：以 D1 的校对页字段清单为基准，逐项断言存在；并断言「最小值」「最大值」不存在（负向断言防回归）
- 标签语义：断言含「分类理由」且不含「研究理由」
- 研究方法形态：断言页面文本不含 `["`，且每项独立可见
- 只读性：断言不存在可编辑输入框（无非 readOnly 的 `input`）
- 空态：无材料状态、无结构数据两个分支

**已知环境事实**（沿用 #58 经验）：`jsdom` 缺 `scrollIntoView`；重交互用例在 8 文件并行下需显式 `timeout`（默认 5000ms 余量不足，仓库已有先例）。本 Feature 的测试为纯渲染断言，交互极少，预计不触发该问题。

**执行命令**：

```bash
cd /home/mayuan/code/SC-Wiki/frontend && npm run test:upload-ui && npx tsc --noEmit
```

修复前基线：8 文件 65 用例全绿（含 #58 新增 7 用例与本次 flake 修复后的稳定结果）。
