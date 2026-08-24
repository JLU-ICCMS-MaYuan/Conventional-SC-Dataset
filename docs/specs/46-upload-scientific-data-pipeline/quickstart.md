# 快速验收：论文上传科学数据结构化

## 前置条件

- Docker 可运行隔离 MySQL 8.4。
- Python 与前端依赖已由项目环境提供。
- 不连接或修改现有业务数据库。

## 自动验证

1. 运行上传归一化、校验和事务测试。
2. 运行上传工作区 Vitest。
3. 运行 Issue #46/32 Schema 与隔离 MySQL Alembic 测试。
4. 运行 Go 模型测试和前端生产构建。

预期：全部命令退出码为 0；旧压力夹具不再失败；新提交实体图全部属于同一 paper revision。

## 行为验收

使用 Li2MgH16 夹具打开 ready 草稿：

- 250 GPa 与 300 GPa 显示在各自材料状态。
- 材料输入只显示 Li2MgH16。
- 空间群显示 Fd-3m，群号显示 227。
- λ 显示 3.35。
- 未报告 ωlog 时输入为空。
- 保存请求体包含 `material_states`，不包含 `key_properties`。

提交后在隔离数据库检查：

- `material_states` 包含正确压力和 reported space group；
- `calculation_contexts.lambda_ep=3.35` 且 `omega_log_k IS NULL`；
- Tc 位于 `tc_results`；
- 其他物性位于 `superconductor_properties`；
- 没有旧 `key_properties` 写入。
