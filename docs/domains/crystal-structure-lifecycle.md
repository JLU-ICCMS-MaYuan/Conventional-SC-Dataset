# 晶体结构生命周期

## 职责

晶体结构以“超导体、压力、空间群”为身份边界，支持上传、校验、审核和代表结构
读取。

## 当前行为

- `POST /api/structures/` 接收结构；结构记录保存格式、原文、哈希、原子数、元素、
  晶胞参数、来源和审核状态。
- 管理员审核通过后，同一超导体、压力与空间群组合中的通过结构会成为默认代表结构。
- `is_default` 是持久化状态；默认选择由结构存储服务维护，而非由前端推断。

## 证据

- `backend/api/structures.py`
- `backend/services/structure_storage.py`
- `backend/models.py`
- `tests/01_decentralized_uploading/test_structures_api.py`

## 已知缺口

- 后端 API 与测试已闭环，但当前 React 源码没有确认到结构上传调用入口；UI 能力需
  另建 `type:doc-debt` Issue 核验。
