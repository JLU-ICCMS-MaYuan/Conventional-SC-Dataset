# 实施计划：上传 Worker 版本漂移恢复

**GitHub Issue**：[#91](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/91)

**日期**：2026-09-08

**Spec**：[spec.md](spec.md)

## 摘要

在上传 Worker 上注册窄范围 RQ 异常回调，将入口导入/执行边界失败同步到既有 Redis 上传
任务状态机；本地 `scripts/dev.sh` 用 `watchfiles` 监督 Worker 命令，使 Python 源码变更产生
全新解释器进程。两层方案分别处理“用户状态不能卡死”和“本地模块不能长期漂移”。

## 技术上下文

- **语言与版本**：Python 3.12、Bash。
- **主要依赖**：RQ 2.12、Redis 8.1、watchfiles 1.2、FastAPI。
- **数据存储**：Redis 上传任务状态与 RQ job；原始 PDF 保持在 `.data/upload_PDFs/`。
- **测试体系**：pytest；真实隔离 Redis + RQ `SimpleWorker` 边界测试；Shell 启动契约测试。
- **目标平台**：Linux/WSL 本地开发；Docker 生产命令保持兼容。
- **性能目标**：源码变更后 10 秒内产生新 Worker；异常回调只进行常数次 Redis 操作。
- **约束**：不得泄露异常堆栈或 LLM 凭据；不得覆盖终态；不得自动创建/切换分支。
- **规模范围**：单个 RQ job 对应单个上传任务；本地并发仍固定为 1，生产由现有配置控制。

## 质量门

| 约束来源 | 强制要求 | 设计如何满足 | 状态 |
|----------|----------|--------------|------|
| AGENTS.md | 修改后合理验证并仅提交本任务文件 | 定向 pytest、实际任务恢复、显式路径暂存 | 通过 |
| Overview | Redis 状态是解析进度事实来源 | 队列级回调复用 `update_state`，不新增状态副本 | 通过 |
| Spec FR-002 / FR-003 | 只更新合法运行态且错误摘要安全 | 校验 job 参数和当前状态，使用固定用户文案 | 通过 |
| Spec FR-005 / FR-006 | 本地热重载、生产命令不变 | 只修改 `scripts/dev.sh`，Docker compose 不变 | 通过 |
| Spec SC-001 | 覆盖真实 RQ 导入失败边界 | 使用隔离 Redis 和真实 RQ Worker 消费坏入口 | 通过 |

## Feature 文档结构

```text
docs/specs/91-upload-worker-recovery/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── worker-failure.md
├── tasks.md
└── checklists/
    └── requirements.md
```

## 源代码结构

```text
backend/
├── ingest/upload_tasks.py
├── rq_runtime.py
└── scripts/run_upload_workers.py
scripts/dev.sh
tests/01_decentralized_uploading/
└── test_issue91_upload_worker_recovery.py
docs/overview/01_Decentralized_Uploading_of_Superconductivity_Data/
└── pdf-parsing-pipeline.md
```

**结构选择**：上传状态转换保留在 `upload_tasks.py`；Worker 装配只在
`run_upload_workers.py` 注册回调；本地进程监督仍由 `dev.sh` 负责。该划分避免把 RQ 细节
扩散到 API 或解析主流程。

## 需求到设计的映射

| 来源 | 设计组件/接口 | 验证方式 |
|------|---------------|----------|
| FR-001～FR-004 / US1 | `handle_upload_job_failure` 与 RQ `exception_handlers` | 隔离 Redis + RQ 导入失败测试 |
| FR-005 / US2 | `watchfiles` 包装本地 Worker 命令 | 启动脚本契约测试与人工进程替换检查 |
| FR-006 / US2 | 保持 `docker/compose.yaml` 不变 | 既有 compose 测试 |
| FR-007 / US3 | 一次性定向状态恢复和重新入队 | Redis 状态、job ID 与 Worker 日志 |
| SC-001～SC-005 | 测试矩阵与 Quickstart | pytest、导入检查、两条任务运行状态 |

## 阶段与依赖

1. 建立真实 RQ 导入失败回归测试和状态回调测试。
2. 实现队列级状态收敛并注册到所有上传 Worker。
3. 修正 RQ 温和关闭识别，并为本地 Worker 增加 Python 源码监视重启。
4. 执行定向测试与 Quickstart，更新 Overview。
5. 重启本地 Worker 并定向恢复两条历史任务，回写 Issue。

## 复杂度说明

| 必要复杂度 | 为什么需要 | 已拒绝的简单方案及原因 |
|------------|------------|--------------------------|
| RQ 队列级异常回调 | 业务函数尚未导入时，其内部 `try/except` 不可能执行 | 只在 `process_upload_task` 外层再加 `try` 无法覆盖导入失败 |
| 本地监督进程 | Python 已加载模块不能靠磁盘文件变更自动刷新 | 只提示开发者手动重启会重复产生同类故障 |
