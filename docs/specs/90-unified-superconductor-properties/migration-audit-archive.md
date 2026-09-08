# 本地迁移审计归档（2026-09-08）

用户确认迁移完成后删除三张临时迁移表，取代此前在数据库中保留的决定。本归档保存删除前的完整表结构及全部记录；它是特定环境的历史快照，不是当前业务状态。

- 环境：本地 MySQL 8.4.2，127.0.0.1:3307，scwiki。
- 删除前版本：issue90_contract_v1；检查点 1 行、映射 3 行、异常 0 行。
- SQL 备份：`.data/backups/scwiki-issue90-migration-audit-before-drop-20260908-100207.sql`，7463 字节。
- 备份 SHA-256：`64c8a9aba8d5ac958e65037757b29d836c74ad878232ab5d2979b7768ba35504`。
- SQL 备份保存在本机；本文件中的结构和记录随 Git 保存。数据库时间字段按原值保留，不作时区转换。
- 映射中的 `issue90_chemical_systems`、`issue90_superconductors` 是复制时的影子表名，随后分别更名为 `chemical_systems`、`superconductors`。
- 恢复审计数据可使用 SQL 备份；恢复旧业务模型仍需要完整业务备份，三张审计表不能替代它。

## `issue90_migration_checkpoint`

```sql
CREATE TABLE `issue90_migration_checkpoint` (
  `id` int NOT NULL AUTO_INCREMENT,
  `phase` varchar(20) NOT NULL,
  `writes_blocked` tinyint(1) NOT NULL DEFAULT '0',
  `reads_target` tinyint(1) NOT NULL DEFAULT '0',
  `writes_target` tinyint(1) NOT NULL DEFAULT '0',
  `reconciled` tinyint(1) NOT NULL DEFAULT '0',
  `observed` tinyint(1) NOT NULL DEFAULT '0',
  `checkpoint_json` json NOT NULL,
  `error_json` json NOT NULL,
  `updated_at` datetime NOT NULL DEFAULT (now()),
  PRIMARY KEY (`id`),
  CONSTRAINT `ck_issue90_checkpoint_phase` CHECK ((`phase` in (_utf8mb4'expand',_utf8mb4'copy',_utf8mb4'reconcile',_utf8mb4'read_switch',_utf8mb4'write_switch',_utf8mb4'observe',_utf8mb4'contract')))
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```

全部记录：

```json
[
  {
    "id": 1,
    "phase": "contract",
    "writes_blocked": 0,
    "reads_target": 1,
    "writes_target": 1,
    "reconciled": 1,
    "observed": 1,
    "checkpoint_json": "{\"legacy_tables_dropped\": [\"tc_result_evidences\", \"superconductor_property_evidences\", \"tc_results\", \"superconductor_properties\", \"experimental_contexts\", \"calculation_contexts\", \"legacy_issue90_superconductors\", \"legacy_issue90_chemical_systems\"]}",
    "error_json": "[]",
    "updated_at": "2026-09-08 09:24:00"
  }
]
```

## `issue90_property_migration_map`

```sql
CREATE TABLE `issue90_property_migration_map` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `source_table` varchar(64) NOT NULL,
  `source_id` bigint NOT NULL,
  `paper_id` int NOT NULL,
  `paper_revision` int NOT NULL,
  `target_table` varchar(64) NOT NULL,
  `target_id` bigint DEFAULT NULL,
  `target_record_key` varchar(96) DEFAULT NULL,
  `source_checksum` varchar(64) NOT NULL,
  `target_checksum` varchar(64) DEFAULT NULL,
  `field_map` json NOT NULL,
  `status` varchar(20) NOT NULL DEFAULT 'copied',
  `error_message` text,
  `created_at` datetime NOT NULL DEFAULT (now()),
  `updated_at` datetime NOT NULL DEFAULT (now()),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_issue90_migration_source` (`source_table`,`source_id`,`paper_id`,`paper_revision`,`target_table`),
  CONSTRAINT `ck_issue90_migration_status` CHECK ((`status` in (_utf8mb4'copied',_utf8mb4'reconciled',_utf8mb4'archived',_utf8mb4'error')))
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```

全部记录：

```json
[
  {
    "id": 1,
    "source_table": "chemical_systems",
    "source_id": 9,
    "paper_id": 9,
    "paper_revision": 3,
    "target_table": "issue90_chemical_systems",
    "target_id": 1,
    "target_record_key": null,
    "source_checksum": "d9962145d0fa8aad09c534df7218042487149dde5b2c3a2c0822f779af94dd19",
    "target_checksum": "d9962145d0fa8aad09c534df7218042487149dde5b2c3a2c0822f779af94dd19",
    "field_map": "{\"system_key\": \"system_key\", \"element_count\": \"element_count\", \"elements_list\": \"elements_list\"}",
    "status": "copied",
    "error_message": null,
    "created_at": "2026-09-08 09:13:50",
    "updated_at": "2026-09-08 01:15:09"
  },
  {
    "id": 2,
    "source_table": "superconductors",
    "source_id": 33,
    "paper_id": 9,
    "paper_revision": 3,
    "target_table": "issue90_superconductors",
    "target_id": 1,
    "target_record_key": "legacy-state-54",
    "source_checksum": "67475bbe898665b7f60cfb1439b7d9fc836e8979488d515a11d3865b414d67d6",
    "target_checksum": "67475bbe898665b7f60cfb1439b7d9fc836e8979488d515a11d3865b414d67d6",
    "field_map": "{\"material_state_id\": 54, \"chemical_system_id\": 1}",
    "status": "copied",
    "error_message": null,
    "created_at": "2026-09-08 09:13:50",
    "updated_at": "2026-09-08 01:15:09"
  },
  {
    "id": 3,
    "source_table": "tc_results",
    "source_id": 94,
    "paper_id": 9,
    "paper_revision": 3,
    "target_table": "property_records",
    "target_id": 1,
    "target_record_key": "legacy-tc-94",
    "source_checksum": "407359f75930295c0f215c4c9ebe9ac47728a89b9129ca3484b57b227c56685f",
    "target_checksum": "240c59e0d0712442fc4508031a976137838507730b55a14cc0cd44e87341cb7a",
    "field_map": "{\"mapping\": {\"value\": \"value_number|value_min|value_max|value_text\", \"context\": \"payload\", \"evidence\": \"property_record_evidences\", \"unit_raw\": \"unit_raw\"}, \"evidence\": [], \"expected\": {\"payload\": {\"experimental_conditions\": {\"structure_id\": 5, \"tc_criterion\": \"unknown\"}}, \"name_raw\": \"critical temperature\", \"unit_raw\": \"K\", \"value_max\": null, \"value_min\": null, \"value_raw\": \"4.2\", \"method_raw\": null, \"value_kind\": \"number\", \"value_text\": null, \"method_code\": \"resistivity\", \"record_type\": \"measured_tc\", \"uncertainty\": null, \"value_number\": 4.2, \"criterion_raw\": null, \"property_code\": \"tc\", \"structure_key\": null, \"value_boolean\": null, \"canonical_unit\": \"K\", \"criterion_code\": null, \"is_representative\": false, \"custom_property_key\": null}}",
    "status": "reconciled",
    "error_message": null,
    "created_at": "2026-09-08 09:13:50",
    "updated_at": "2026-09-08 01:15:09"
  }
]
```

## `issue90_migration_anomalies`

```sql
CREATE TABLE `issue90_migration_anomalies` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `source_table` varchar(64) NOT NULL,
  `source_id` bigint NOT NULL,
  `paper_id` int NOT NULL,
  `paper_revision` int NOT NULL,
  `code` varchar(64) NOT NULL,
  `details` json NOT NULL,
  `resolved` tinyint(1) NOT NULL DEFAULT '0',
  `created_at` datetime NOT NULL DEFAULT (now()),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_issue90_anomaly` (`source_table`,`source_id`,`paper_id`,`paper_revision`,`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```

全部记录：

```json
[]
```

## 清理结果

本地数据库已升级至 `issue90_audit_cleanup_v1`，三张临时表已删除，业务库现有 39 张表。
SQL 备份已做隔离恢复及逐字段比对；9 张核心业务表清理前后内容一致。
