# 实施计划：论文分类证据作用域与汇总前状态

**GitHub Issue**：[#45](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/45)

**日期**：2026-08-24

**Spec**：[spec.md](spec.md)

## 摘要

扩展临时分段分类契约，为论文类型和材料类型证据增加本文/引用工作作用域；在后端解析预览和
全文汇总输入边界执行确定性筛选；为分类字段增加汇总前状态；版本化分段缓存以安全重读旧结果。
材料类型保持自由文本。通过固定 Li–Mg–H 分段产物覆盖后端磁盘读取、DTO 聚合和前端展示。

## 技术上下文

- **语言与版本**：Python 3.10、TypeScript/React 18、Node.js 20。
- **主要依赖**：FastAPI、RQ、Redis、SQLAlchemy、React、Material UI。
- **数据存储**：临时分段 JSON 和 Redis 任务状态；无 MySQL schema 变化。
- **测试体系**：pytest 9、Vitest 2、Testing Library；后端上传集成测试和前端组件测试。
- **目标平台**：Docker Compose 中的 Python Worker/API 与 Nginx 托管前端。
- **性能目标**：不增加 LLM 调用次数；仅在恢复遇到旧契约缓存时定向重读对应分段。
- **约束**：自由材料类型不受枚举限制；公开 DTO 不泄露提示词、路径或原始响应；非分类冲突不回归。
- **规模范围**：单任务一个正文和任意附件，当前样例 57 个分段；逻辑对候选数线性处理。

## 质量门

| 约束来源 | 强制要求 | 设计如何满足 | 状态 |
|----------|----------|--------------|------|
| AGENTS.md | 先读后写、测试后提交、只提交本任务文件 | 先建立文档门和失败测试，按明确路径暂存 | 通过 |
| #23 / Overview | 按核心贡献分类，材料类型允许自由文本 | 作用域筛选本文证据，不做材料枚举或同义词归一化 | 通过 |
| #27 / Overview | 分段结果实时可见，元数据冲突不静默覆盖 | 引用证据保留在分段页；仅分类字段使用 `pending_summary` | 通过 |
| Spec FR-008 | 旧缓存不得被默认为本文证据 | 分段契约版本化，恢复时定向重读，预览读取时安全降级 | 通过 |
| 安全 DTO | 不公开内部提示词、路径和原始响应 | 复用现有字段白名单，仅公开证据条目的 `scope` | 通过 |

## Feature 文档结构

```text
docs/specs/45-paper-classification-evidence-scope/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── parsing-classification.md
├── tasks.md
└── checklists/
    └── requirements.md
```

## 源代码结构

```text
backend/ingest/upload_jobs.py
backend/tests/test_upload_jobs.py
tests/01_decentralized_uploading/test_issue23_upload_lifecycle.py
tests/01_decentralized_uploading/test_issue24_persistence_and_ui.py
tests/01_decentralized_uploading/upload-task-workspace.test.tsx
frontend/src/components/UploadParsingDetail.tsx
docs/overview/06-rag-literature-assistant/pdf-ingestion.md
```

**结构选择**：证据生产、缓存读取、预览聚合和全文汇总都集中在 `upload_jobs.py`，保持单一业务
边界；前端只解释服务端返回的字段状态，不复制作用域判断。测试分别覆盖后端公开 DTO、Worker
汇总输入和前端用户可见标签。

## 需求到设计的映射

| 来源 | 设计组件/接口 | 验证方式 |
|------|---------------|----------|
| FR-001–003 / US1 | 分段结果作用域契约、预览筛选器 | Li–Mg–H 持久分段产物回放测试 |
| FR-004 / US2 | 论文类型有效候选筛选 | `unknown + theoretical` 后端回归测试 |
| FR-005–006 / US2 | `PreviewField.state=pending_summary` 与前端标签 | DTO 测试和 Testing Library 测试 |
| FR-007 / US3 | 材料类型值透传 | 自定义材料类型后端测试 |
| FR-008 | 分段缓存契约版本 | 缺失版本缓存重读测试、旧产物安全预览测试 |
| FR-009 | 全文汇总输入净化 | Worker 汇总输入捕获测试 |
| FR-010 / SC-001–006 | 固定回放、相关测试集和 quickstart | pytest、Vitest、原始产物回放 |

## 阶段与依赖

1. 建立失败回归测试，固定真实故障边界。
2. 实现分段作用域契约、缓存版本和汇总输入筛选。
3. 实现解析预览状态与前端展示。
4. 运行后端、前端和真实任务产物回放。
5. 更新当前功能 Overview、任务证据和 Issue 状态。

## 复杂度说明

| 必要复杂度 | 为什么需要 | 已拒绝的简单方案及原因 |
|------------|------------|--------------------------|
| 分段结果契约版本 | 旧缓存没有作用域，不能安全复用 | 默认旧数据为本文会继续误分类；永久启发式兼容会扩散复杂度 |
| 独立分类预览状态 | 分类候选与元数据冲突具有不同业务含义 | 全部字段统一改名会掩盖标题、DOI 的真实冲突 |
| 汇总输入确定性筛选 | 不能仅依赖提示词遵守作用域 | 只改提示词无法提供稳定业务保证 |
