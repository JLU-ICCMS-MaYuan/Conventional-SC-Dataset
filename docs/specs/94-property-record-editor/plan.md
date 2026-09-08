# 实施计划

输入：[Spec](spec.md)、[Research](research.md)、[数据](data-model.md)、[契约](contracts/record-form.md)。

## 技术上下文与职责

React 19 / TypeScript 5.6 / MUI 的 PropertyModuleEditor 负责菜单、定义选择和记录折叠；
SchemaDrivenRecordForm 负责实验条件单框和旧对象的可读投影。Python upload_jobs 的分段及汇总 prompt
负责逐条提取；现有 convert_legacy_state 已支持 Tc 条目级 experimental_conditions，归一化后进入
property_modules。后端 property_modules.validate_record 与前端 validateRecordClient 校验 description 类型。
MySQL 持久化仍使用 payload_json；测试以 SQLite 执行真实写读。

## 质量门

| 来源 | 要求 | 实现方式 |
| --- | --- | --- |
| AGENTS.md | Spec 先行、中文文档、明确提交范围 | 本目录先形成全部文档，再实现并验证 |
| #90 当前事实 | 条件属于记录、定义不可原地修改 | 使用已有开放对象内 description，不改已发布定义 |
| 用户 | 六方向弱约束、单框、记录折叠 | 两阶段 prompt + 共享输入与 Accordion |
| KISS / DRY / YAGNI | 控制复杂度 | 共用组件实现，不增加接口、数据库迁移或依赖 |

## 需求与验证映射

| 来源 | 设计与数据来源 | 任务 | 验证 |
| --- | --- | --- | --- |
| FR-001 / US1 / SC-001 | definitionLabel 只输出类型和方法 | T002 | 菜单、标题、只读标签、提交版本断言 |
| FR-002、004 / US2 / SC-002 | 单框读取本条 description；旧字段无损保留 | T003 | 旧数据、换行、复制、编辑、只读测试 |
| FR-003、004 / US2 / SC-002 | CHUNK/SUMMARY prompt → normalize → persist | T004 | 模拟 LLM 返回，执行真实下游转换和数据库写读；核对真实调用的 prompt |
| FR-005、006 / US3 / SC-003 | Accordion 用 module/record 稳定键维护交互 | T005 | 多条记录独立切换、键盘、复制删除及错误摘要 |
| 全部 | 文档与完整回归 | T006 | [快速验收](quickstart.md) |

## 阶段与依赖

T001 文档门通过后先写定向行为测试，再执行 T002～T005；同文件改动串行，T006 最后验证和回写。
没有新存储和外部服务依赖，不需要数据迁移。旧对象投影只限实验条件显示边界，不扩散到正常数据库查询。
