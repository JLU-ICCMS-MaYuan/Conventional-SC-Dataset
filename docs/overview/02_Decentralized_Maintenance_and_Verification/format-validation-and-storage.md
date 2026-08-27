# 格式校验与存储

## 功能说明

解析用户提交的 CIF 或 POSCAR 文本，提取晶胞和空间群等元数据，并保存可去重的原始结构记录。

## 当前行为

- 只接受 CIF/POSCAR 类型的结构载荷。
- 使用 ASE 解析结构并提取晶胞参数、元素列表、原子数和体积等元数据。
- 对原始文本计算 SHA-256 摘要，作为内容标识的一部分。
- 新结构记录保存来源、提交者和审核状态。

## 工作流程

API 接收结构格式和文本；服务层验证非空与格式；解析结构并提取元数据；计算摘要；创建待审核的 `SuperconductorStructure`。论文详情的结构预览来源是 `structure_models`（挂在材料状态下），普通物性表不再保存结构文本与结构格式。（[Issue #57](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/57)）

## 约束

- 无法由 ASE 解析的文本会被拒绝。
- 结构内容当前存储于数据库记录，不是独立对象存储。
- 结构科学正确性与文本可解析性不是同一保证。

## 代码与测试

- `backend/services/structure_storage.py`
- `backend/models.py`
- `tests/01_decentralized_uploading/`

## 相关变更记录

当前未发现可链接的已完成 Feature 或 Debug 记录。

## 已知问题

- 大体积结构文本的存储与性能边界待核验。
