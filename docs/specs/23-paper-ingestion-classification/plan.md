# 实施计划：论文全文解析与 LLM 自动分类

**GitHub Issue**：[＃23](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/23)

**Spec**：[spec.md](spec.md)

## 摘要

FastAPI 只负责鉴权、持久化原文件、创建 Redis 状态并入 RQ 队列；独立 Worker 提取 Markdown、全文分段调用统一 LLM 客户端并生成临时草稿。前端轮询五阶段并自动保存草稿，用户提交时才原子写 MySQL。Go 继续承载正式论文编辑和管理员审核。

## 技术上下文

- **语言与版本**：Python/FastAPI、Go 代理、React/TypeScript、Docker Compose。
- **主要依赖**：现有 PDF 抽取、SQLAlchemy、OpenAI 兼容客户端、Redis/RQ。
- **数据存储**：MySQL 保存正式候选/审核数据；Redis 保存 24 小时任务与草稿；挂载目录保存 PDF、Markdown 和临时审核产物。
- **测试体系**：`pytest`、前端现有测试和 Docker 临时源码环境。
- **目标平台**：Nginx → Go → Python，生产容器及本地 Neo4j 环境。
- **约束**：旧类型只读兼容；不公开 PDF/Markdown；不实现 OCR、全局类型目录和成本限制。

## 质量门

| 约束来源 | 强制要求 | 设计如何满足 | 状态 |
|---|---|---|---|
| AGENTS.md | 修改后验证并提交；不自动推送 | 只提交本 Feature 文档 | 通过 |
| Issue #23 | 全文、可解释分类、待审核新类型 | 分段汇总、理由证据、审核状态 | 通过 |
| #19/#22 | 修复上传和缺失工具链 | 基础阶段先修导入、错误传播 | 通过 |

## 源代码结构

- `backend/ingest/extractor.py`：PDF 抽取与论文类型判断。
- `backend/ingest/enrich_papers.py`：LLM 富化和材料类型建议。
- `backend/ingest/store_papers.py`：论文及物性写入。
- `backend/scripts/rebuild_from_clean_results.py`：重建工具契约。
- `backend/models.py`：论文、物性、审核数据模型。
- `backend/ingest/upload_jobs.py`：RQ Worker 五阶段任务、分段产物与恢复。
- `backend/rag/llm.py`：统一 LLM 供应商配置与 JSON 调用。
- `frontend/src/components/PaperEditView.tsx`、`frontend/src/pages/AdminPage.tsx`：上传结果与管理员审核。
- `frontend/src/pages/UploadPage.tsx`：任务轮询、五阶段和草稿入口。
- `docker/*.yaml`、`compose.dev.yaml`：Worker、Redis AOF和持久目录。

## 需求到设计的映射

| 来源 | 设计组件/接口 | 验证方式 |
|---|---|---|
| FR-001/002 | 上传状态和错误响应、Nginx 配置 | 413/解析失败集成测试 |
| FR-003/004/005/006 | 全文分段分类器和证据输出 | 五类论文 fixture 测试 |
| FR-007/008/009 | 类型建议与管理员审核契约 | API/UI 审核测试 |
| FR-010 | 论文分类与物性 article_type 分离 | 数据回归测试 |
| FR-011 | 工具导入和统一参数契约 | 导入/重建测试 |
| FR-012–016 | Redis/RQ、持久目录、任务和草稿 API | API、Worker、Compose 测试 |
| FR-017/018/021 | 原子提交、审核状态和公开边界 | Go/Python 集成测试 |
| FR-019/020 | 统一 LLM 客户端和新类型格式 | 单元与 fixture 测试 |

## 阶段与依赖

1. 完成迁移、目录配置、Redis/RQ 和任务 API。
2. 完成全文分段 LLM 草稿及断点恢复。
3. 完成用户自动保存、原子提交和管理员审核。
4. 完成前端五阶段、草稿表单和证据对比。
5. 完成回归测试、Docker 验证和 Overview 更新。

## 复杂度说明

全文分段汇总是必要复杂度，因为固定字符截断无法满足用户明确的“读完整篇论文”要求；动态材料类型和待审核状态是必要复杂度，因为用户明确拒绝固定枚举。
