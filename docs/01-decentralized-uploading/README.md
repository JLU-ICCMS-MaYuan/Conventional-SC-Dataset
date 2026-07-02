# 01 去中心化超导数据上传当前规划

## 总体定位

负责让研究者提交论文、超导参数记录和晶体结构，是数据进入 SC-Wiki 的第一入口。

## 当前状态

已部分落地。

## 文档导航

- [总体规划](README.md)
- [前端设计](frontend-design.md)
- [后端设计](backend-design.md)
- [API 设计](api-design.md)

## 核心建设内容

### 前端

- 保留 `/share` 与 `/compound/{element_symbols}` 作为上传入口，页面右上角展示「有待建设」。
- 统一 DOI、论文元数据、压强、空间群、Tc、结构文件和超导参数录入流程。
- 批量上传界面需要展示字段映射、清洗状态、错误行和人工确认入口。

### 后端

- 继续以 `papers`、`superconductor_records`、`superconductors_structures` 为当前事实来源。
- 后续规划把晶体结构与超导参数记录合并为同一数据点，保留历史结构表作为迁移来源。
- 结构上传必须经过 CIF/POSCAR 解析、结构哈希、压强绑定和审核状态控制。

### API

- `POST /api/structures/`：上传结构文本。
- `GET /api/structures/by-record/{record_id}`：按记录读取结构。
- `POST /api/structures/{structure_id}/review`：审核结构。
- 未来新增一体化上传接口，提交论文、参数记录和结构引用。

## 数据模型与数据流

目标数据点应同时包含化学式、压强、空间群、晶体结构、Tc、lambda、omega_log、N(Ef)、来源 DOI 和审核状态。

## 验收标准

- 结构解析失败不入库。
- 同一压强下默认结构可追溯。
- 清洗数据可导出给 GNN 建模。
