# 数据导入与导出

## 功能说明

通过离线 JSON 文件交换用户、论文、超导记录和晶体结构数据，并支持在明确参数下清理旧业务数据。

## 当前行为

- 导入器脚本已迁移到 `backend/scripts/`，按用户、论文、超导记录和结构的依赖顺序写入数据。
- `--clear` 参数允许导入前清理现有业务数据。
- 结构导入会填充来源类型等兼容默认值。
- 用户导出保留 `username` 和一次更名资格；可信导入可原样恢复合法公开用户名和精确匹配 `^sc_[a-z0-9]{12}$` 的系统历史用户名，旧载荷缺少用户名时生成新的随机历史用户名。
- 测试文件覆盖新 schema round-trip 和旧载荷兼容路径。

## 工作流程

命令读取 JSON 载荷；可选清理数据库；依次导入用户、论文、记录和结构；提交事务并输出各类对象计数。

## 约束

- `--clear` 会批量删除业务数据，属于需要明确授权的维护操作。
- 导入依赖载荷中的关联标识和当前 schema。
- 本文只记录工具能力，不表示已对生产数据执行过导入或恢复。

## 代码与测试

- `backend/scripts/import_data.py`
- `backend/scripts/export_data.py`
- `backend/crud.py`
- `tests/02_maintenance_and_verification/`
- `tests/test_import_export.py`

## 相关变更记录

- [Feature #31：唯一公开用户名与贡献榜身份](../../specs/31-community-ranking-visuals/spec.md)

## 已知问题

- README 声明的远程备份能力未找到同等明确的当前代码证据，未纳入已实现事实。
