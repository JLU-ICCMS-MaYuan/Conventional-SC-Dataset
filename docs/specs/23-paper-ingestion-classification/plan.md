# 实施计划：论文全文解析与 LLM 自动分类

**GitHub Issue**：[＃23](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/23)

**Spec**：[spec.md](spec.md)

## 摘要

在现有上传、抽取、富化和审核链路上补齐明确状态与错误契约；将论文全文分段汇总交给 LLM 判断论文类型和材料类型；保留用户/AI 新类型并交管理员审核。优先修复已知导入问题，再实现分类和页面展示。

## 技术上下文

- **语言与版本**：Python/FastAPI、Go 代理、React/TypeScript、Docker Compose。
- **主要依赖**：现有 PDF 抽取、异步数据库驱动、LLM 客户端和 SQLAlchemy 模型。
- **数据存储**：现有论文、物性和审核模型；新材料类型建议使用可审核的名称与状态，不把失败历史写入数据库。
- **测试体系**：`pytest`、前端现有测试和 Docker 临时源码环境。
- **目标平台**：Nginx → Go → Python，生产容器及本地 Neo4j 环境。
- **约束**：兼容现有 API；不增加实验论文二级分类和刷新重试按钮。

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
- `frontend/src/components/PaperEditView.tsx`、`frontend/src/pages/AdminPage.tsx`：上传结果与管理员审核。
- `docker/nginx.conf`：上传体积限制。

## 需求到设计的映射

| 来源 | 设计组件/接口 | 验证方式 |
|---|---|---|
| FR-001/002 | 上传状态和错误响应、Nginx 配置 | 413/解析失败集成测试 |
| FR-003/004/005/006 | 全文分段分类器和证据输出 | 五类论文 fixture 测试 |
| FR-007/008/009 | 类型建议与管理员审核契约 | API/UI 审核测试 |
| FR-010 | 论文分类与物性 article_type 分离 | 数据回归测试 |
| FR-011 | 工具导入和统一参数契约 | 导入/重建测试 |

## 阶段与依赖

1. 修复上传错误契约、异步驱动和缺失工具。
2. 建立全文分段读取与 LLM 分类输出契约。
3. 接入论文/物性/材料类型审核和前端展示。
4. 回归测试、Docker 验证和 Overview 更新。

## 复杂度说明

全文分段汇总是必要复杂度，因为固定字符截断无法满足用户明确的“读完整篇论文”要求；动态材料类型和待审核状态是必要复杂度，因为用户明确拒绝固定枚举。
