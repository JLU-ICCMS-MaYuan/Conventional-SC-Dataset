# 实施任务

输入：[Spec](spec.md)、[Plan](plan.md)、[Research](research.md)、[契约](contracts/record-form.md)。

- [x] T001 建立 docs/specs/94-property-record-editor/ 全部产物，核对旧数据、Schema 和提取路径。
- [x] T002 [US1] 在 frontend/src/components/PropertyModuleEditor.tsx 移除标签版本后缀；在 tests/01_decentralized_uploading/property-record-editor.test.tsx 固定显示和内部版本断言。
- [x] T003 [US2] 在 frontend/src/components/SchemaDrivenRecordForm.tsx 实现实验条件单框与旧对象投影，前端交互测试覆盖保留旧值、Evidence 与换行。
- [x] T004 [US2] 修改 backend/ingest/upload_jobs.py 两阶段 prompt；在 backend/ingest/property_modules.py、frontend/src/lib/formDefinitions.ts 校验文本类型，并在 backend/tests/test_property_record_conditions.py 验证真实归一化和持久化往返。
- [x] T005 [US3] 在 frontend/src/components/PropertyModuleEditor.tsx 增加独立记录折叠；前端测试覆盖多条记录、编辑、复制、删除、只读与错误摘要。
- [x] T006 运行定向及共享表单回归、TypeScript 编译，使用 Overview Skill 更新 docs/overview/01_Decentralized_Uploading_of_Superconductivity_Data/ 下表单映射和解析流程文档，回写 Issue 并提交明确文件。

## 依赖与验收

T001 是文档门；T002～T005 的测试先于对应实现。T002 与 T005 共享文件串行处理，T003/T004 的描述字段约定一致后联调。
T006 依赖其余任务全部验证通过。三个故事均属最小交付，独立验收见 Plan 映射。
