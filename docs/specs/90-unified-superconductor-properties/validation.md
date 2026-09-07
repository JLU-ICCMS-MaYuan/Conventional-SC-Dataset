# #90 验证记录

## 验收结论

#90 的模块化物性、动态定义、论文 revision 材料所有权、跨入口读写切换、完整导出和分阶段历史迁移
均已实现。标准后端、Go、前端测试和生产构建通过；Expand 至 Contract 的完整状态机已在隔离真实
MySQL 验证。仓库验收不等于生产数据库已经部署，实际部署仍须经过相同门禁。

## 自动化验证

| 范围 | 命令或测试 | 结果 |
| --- | --- | --- |
| 后端标准套件 | `bash scripts/run-tests.sh backend` | 178 项通过，18 项跳过 |
| #90 后端定向回归 | 模块、定义、上传、重写、导出与迁移阶段测试 | 89 项通过 |
| 科学草稿事务 | `backend/tests/test_scientific_drafts.py` | 10 项通过 |
| Go | `bash scripts/run-tests.sh go` | 全部通过 |
| 前端上传与详情 | `cd frontend && npm run test:upload-ui` | 29 个测试文件、227 项测试通过 |
| 前端生产构建 | `cd frontend && npm run build` | 通过；仅保留既有 3Dmol `eval` 与 chunk size 警告 |
| 隔离真实 MySQL 迁移 | `tests/02_maintenance_and_verification/test_issue90_migration.py` | 5 项通过；78 条第三方弃用警告 |
| Python 语法 | `PYTHONPATH=. python -m compileall -q backend alembic` | 通过 |
| 补丁格式 | `git diff --check` | 通过 |

## 契约验收

- `FormDefinition` 使用受限 JSON Schema 和完整 JSON Pointer 校验；发布版本不可变，停用不破坏历史
  读取，升级与回滚执行校验和和并发检查并留下审计事件。
- 四个物性模块支持按需新增、删除和排序；记录支持新增、删除、复制、定义切换以及数值、范围、文本、
  布尔值往返，`0` 与 `false` 不会被误判为空。
- 预测 Tc 只接受计算 Conditions，测量 Tc 只接受实验 Conditions；参数和 extensions 属于单条记录，
  复制后互不联动，代表 Tc 唯一约束生效。
- 自定义性质随论文审核保留。普通管理员可幂等提升为全站发布定义；权限、重复代码、源记录并发变化
  和保留代码冲突返回稳定错误，且失败不改写源记录。
- Evidence 必须与 PropertyRecord 属于同一论文 revision，字段级路径受定义约束；MaterialState 导出
  包含材料、状态、结构、模块记录、Evidence 和定义快照。
- 上传缓存使用 Schema v2。旧草稿只在输入边界单向转换；v2 载荷及规范 property identity 不受旧转换
  覆盖，正式提交和管理员重写只写目标契约。
- Go 公开详情、搜索、统计、管理员查询、我的上传、删除和导出使用目标表；Contract 删除四张旧科学
  表后正常访问回归通过。legacy `key_properties` 写入返回 `400 legacy_property_contract`。

## 迁移验收

Alembic revision 链为：

```text
issue90_expand_v1 -> issue90_copy_v1 -> issue90_contract_v1
```

`backend/services/issue90_migration.py` 控制 Expand、Copy、Reconcile、Final sync、Read switch、
Write switch、Observe 和 Contract。`backend/scripts/migrate_issue90_properties.py` 按源表、源 ID 与论文
revision 幂等保存映射和检查点。

隔离 MySQL 专项已验证：

- 旧共享 LaH10 按论文 revision 拆分，新的 `ChemicalSystem`、`Superconductor` 和 MaterialState 关系正确；
- 旧 Tc、普通物性、Conditions、参数和 Evidence 逐字段复制，缺失 Evidence 不被伪造；
- 重复 Copy 不产生重复记录，阶段失败从持久化检查点恢复；
- Final sync 覆盖迁移窗口内的新增、修改、删除和论文升版；
- 未完成 Reconcile、未排空在途事务或未通过读取验收时，后续阶段被阻断；
- Read/Write switch、Observe 与恢复路径不丢失已提交数据；
- Contract 未显式确认时拒绝执行，确认后删除旧科学表且目标读写仍通过；
- `run_migrations.py` 默认停在 `issue90_copy_v1`，只有设置 `ISSUE90_CONTRACT_CONFIRMED=1` 才升级到
  `head`。

## Documentation Impact

已更新以下当前功能总览，使其只描述目标模型的已实现行为，并明确生产部署边界：

- `docs/overview/01_Decentralized_Uploading_of_Superconductivity_Data/data-structure-and-form-mapping.md`
- `docs/overview/02_Decentralized_Maintenance_and_Verification/domain-model-and-schema.md`
- `docs/overview/03_Superconductivity_Data_Search_and_Database_Discovery/paper-and-property-results.md`

Spec、Plan、Research、Data Model、Contracts、Quickstart 和 Tasks 保留 #90 的设计、实施拆解与验证证据。
按用户要求，完成验收回写后 Issue #90 继续保持 Open。
