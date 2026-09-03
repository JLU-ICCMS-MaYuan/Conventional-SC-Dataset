# 上传、审核与默认结构

## 功能说明

管理结构从用户提交到管理员审核的状态变化，并为同一结构身份维护唯一默认项。

## 当前行为

- 已认证用户可以上传结构，初始状态为 `pending`。
- 管理员可以将结构批准或驳回。
- 批准结构时，同一“超导体、压力、空间群”身份只保留一个默认结构。
- 审核逻辑保留提交者、审核者和状态信息。
- 上传校对页、用户审核表单和管理员/超级管理员论文编辑页共用 `MaterialStatesEditor`。每条 Tc 先选择 `tc_method`；仅非 `experimental` 方法显示 λ、ωlog、μ*。
- 将一条理论 Tc 切换为 `experimental` 时，编辑器删除该条目的 `calculation_context`，并把 `result_kind` 固定为 `experimental`；保存载荷不再携带计算参数。管理端详情会加载每个 Tc 所关联的计算上下文，以便理论条目可回显并按条目清理。
- `Tc method` 的 API 与草稿值保持英文稳定枚举。中文界面只转换显示标签，例如“McMillan 方法”“各向同性 Migdal-Eliashberg 方法”和“超导密度泛函理论（SCDFT）”。

## 工作流程

用户上传结构；服务创建 pending 记录；管理员调用审核 API；批准时服务撤销同身份旧默认项并设置新默认项；驳回时更新状态而不进入公开代表结构候选。

## 约束

- 审核接口依赖已批准的 admin 或 superadmin 身份。
- 默认项身份取决于超导体、压力和空间群字段的一致性。
- 当前 React 路由未发现独立结构上传与审核页面；论文编辑组件可以编辑关键物性中的 `structure_text` 与 `structure_format` 并在详情侧展示结构。
- 上传草稿保存、上传提交和管理员科学数据整体重写都会校验每条 `tc_method`。实验方法携带条目级 `calculation_context` 时返回 400，错误信息定位到材料状态及 Tc 序号；校验发生在重建科学数据前，避免部分写入。

## 代码与测试

- `backend/api/structures.py`
- `backend/services/structure_storage.py`
- `backend/security.py`
- `frontend/src/components/MaterialStatesEditor.tsx`
- `frontend/src/pages/AdminPaperEditPage.tsx`
- `backend/api/rag.py`
- `tests/01_decentralized_uploading/`
- `tests/02_identity_governance/admin-scientific-data-edit.test.tsx`

## 相关变更记录

- [Feature #84：实验 Tc 的条件字段与计算上下文一致性](../../specs/84-experimental-tc-fields/spec.md)

## 已知问题

- 当前能力主要由后端 API 提供，最终用户入口待核验。
