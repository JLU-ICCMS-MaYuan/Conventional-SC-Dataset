# 实施计划：管理端论文列表字段可读编辑

**Issue**：[#95](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/95)
**日期**：2026-09-08
**规格**：[spec.md](spec.md)

## 技术上下文与方案

React 19、TypeScript 5.6、MUI 7、Vitest 2，目标为现有浏览器管理页。
Go Gin/GORM 直接保存论文元数据，三字段为文本列；保持后端接口和数据库不变。

从 PaperEditView 提取已有文本列表解析为 frontend/src/lib/paperTextLists.ts，详情与管理页共用。
AdminPaperEditPage 作者使用 MUI Autocomplete/Chip，受控姓名输入，Enter/失焦提交并在保存时兜底。
关键词和研究方法采用响应式两列多行框，编辑时保留原始文本（含末尾换行），保存时才按换行分项。
仅对已编辑字段序列化；服务端数组输入在请求边界编码一次，原 JSON 文本或空值未编辑则原样提交。
保存失败沿用现有提示并保留状态。

## 质量门

| 来源 | 要求 | 满足方式 | 状态 |
| --- | --- | --- | --- |
| AGENTS.md | 文档先行、明确提交范围 | Issue 编号目录，测试后逐路径提交 | 通过 |
| Overview | 现有管理角色及两段保存 | 只替换三个字段的输入/输出适配 | 通过 |
| FR-004 | 数据完整性 | 保留原值、逗号不切分、真实 Go 持久化契约测试 | 通过 |
| KISS / DRY | 简单且共享 | 提取现有解析函数，不引入新依赖或通用表单框架 | 通过 |

## 文件与职责

- frontend/src/lib/paperTextLists.ts：接口列表读取和按行转换。
- frontend/src/components/PaperEditView.tsx：使用共用读取函数。
- frontend/src/pages/AdminPaperEditPage.tsx：控件、编辑暂存及提交适配。
- frontend/src/i18n/{zh,en}/admin.ts：每行一项提示。
- tests/02_identity_governance/admin-paper-list-fields.test.tsx：真实页面加载、交互、保存与重挂载，API 边界替身。
- goserver/handlers/admin_paper_list_fields_test.go：真实处理器与隔离 SQLite 持久化验证文本列契约。
- 本目录包括 spec、plan、research、data-model、contracts/paper-metadata、quickstart、tasks 和 checklists/requirements。

## 需求到设计与验证映射

| 需求 | 设计/事实来源 | 任务 | 验证 |
| --- | --- | --- | --- |
| FR-001 / US1 / SC-001 | AdminPaperEditPage 作者标签 | T002、T004 | 两种角色作者增删 |
| FR-002 / US2 / SC-001 | 多行框原始文本暂存 | T002、T004 | 回车、多行与标点 |
| FR-003 / US1 / US2 | 共用解析，详情来自 Go | T002、T003 | 数组、JSON 文本、普通文本、空值 |
| FR-004 / SC-002 | 文本列边界单次编码 | T002、T004、T005 | 请求、重挂载、Go 实际落库 |
| FR-005 / SC-002 | 保存合并作者输入，保留失败状态 | T002、T004 | 直接保存及失败重试 |
| SC-003 | 不改变审核和科学保存 | T005 | 现有管理页测试与 tsc |

## 阶段与依赖

先完成文档门，再编写回归测试，提取读取函数和实现编辑适配，最后验证并回写 Overview。
同一页面改动串行。无新增外部依赖，无数据库迁移。功能范围小，两个 P1 故事一起交付。
