- [x] 文件上传与审核
- [x] 管理员界面（论文审核/用户管理/图表管理）
- [x] 上传界面（PDF/TXT/MD/JSON → 管线）
- [x] 图表界面（散点图+组合管理+CSV映射+AI兜底）
- [x] 修复 RAG bug
- [x] Chroma → Qdrant 向量数据库迁移（19 集合 / 79,425 条 / 并发提升 10x）
- [x] 知识图谱可视化（KnowledgeGraphPage + Neo4j 同步）
- [x] 物性名 CSV 映射 + AI 追加
--------------------------------------------RAG----------------------------------------
- [ ] RAG 父子索引：小粒度检索 + 大粒度喂 LLM（chunk 已有 paper_id/section_name 元数据基础）
- [ ] RAG 模式重写：统一普通模式(Mentor) + 灵感模式(Inspiration) 两套状态机入口
- [ ] RAG 提示词重写：各状态机 Prompt 从旧 core/prompts.py 迁移到 agent/ 内部
- [ ] RAG 拼接语序调整：上下文构造层统一为 System→DB概况→结构化数据→文献片段→历史→问题
- [ ] RAG 记忆力机制改进：Inspiration 会话状态从消息内 marker 改为服务端存储（Redis/DB 会话表）
- [ ] RAG Tool 结果裁剪：Mentor 模式下 ToolMessage 原样拼接 → 增加摘要/截断，防上下文噪声堆积
- [ ] RAG 安全防护：System Prompt 加固 + 检索结果清洗（防间接注入）+ 输入正则检测
- [ ] RAG Tool 安全控制：参数注入防护（正则校验+clamp）+ 输出硬截断（≤5条/≤2000字）+ 公开/登录权限分层
- [ ] 限流系统：/rag/chat/stream 用户级令牌桶（3次/分钟）+ LLM API 调用队列 + 全局限流兜底
- [x] Go 后端迁移 Phase 1 + 2：密码/注册/搜索/图谱全部完成

--------------------------------------------架构问题--------------------------------------------
一个网站的标准五层：

  浏览器 → [表现层] → [网关层] → [业务层] → [数据访问层] → [数据层]

每一层的问题：

━━━ 表现层 (React 前端) ━━━
- [x] 前端上传页重构：登录门控 + 历史上传卡片 + 可编辑详情(PaperEditView) [8464b51]
- [x] 前端 Vite 代理目标：8000→8080 统一入口 [8464b51]
- [x] 热点首页：/ 自动跳转 /news [5bfb657]
- [x] 登录认证流程闭环 ✅

━━━ 网关层 (Go :8080) ━━━
- [x] 登录密码 bcrypt 校验 + is_approved 检查 [9908ea2]
- [x] AdminRequired 中间件实现并挂载到 /api/admin/* [9908ea2]
- [x] 反向代理连接池配置(MaxIdleConnsPerHost=100 + Timeout=30s) [9908ea2]
- [x] /api/admin/stats 加 AuthRequired+AdminRequired [0d3d0fd]
- [x] Go 注册端点：POST /api/auth/register + bcrypt [ffd4148]
- [x] Go/Python 职责边界：Go 接管所有 CRUD+搜索+图谱+外部数据，Python 仅 RAG/AI

━━━ 业务层 (Python FastAPI :8000) ━━━
- [x] 上传管线异步改造：文件保存即返回，全链路后台执行 [5794d71]
- [x] 上传管线 uploaded_by_user_id 追踪 [8464b51]
- [x] Go 新增 GET /api/papers/my-uploads [8464b51]
- [x] 知识图谱 GRAPH_FILE 路径修复 [0cd2924]
- [x] 物性名下拉栏：18种预设规范名 [8464b51]
- [ ] 外部依赖降级：Neo4j/DeepSeek/Embedding/Qdrant 断连时重试+退避+备选路径

━━━ 数据访问层 (ORM / 存储接口) ━━━
- [x] Go UpdatePaper 支持 key_properties 增删改 + 审查校验 [8464b51]
- [x] 双 ORM 统一：models.py(25列) vs rag/models/(14列) — 已统一为单一 models.py [d946a5e]

━━━ 数据层 (MySQL / Qdrant / Neo4j) ━━━
- [x] Chroma → Qdrant 向量数据库迁移
- [ ] Docker Compose：一键启动 MySQL + Neo4j + Qdrant + Go + Python

━━━ 横切关注点 (所有层) ━━━
- [x] 硬编码路径/凭据修复：knowledge_graph/enrich_papers/alembic/Go PythonBackend/JWT去重 [0cd2924]
- [x] uvicorn --workers 4 [9908ea2]
- [x] 配置安全加固：默认凭据(work:12345678)移除，JWT_SECRET_KEY 缺失时启动失败 [fd20655]
- [x] 遗留代码清理：ingest/bak/ + data/clean_results copy/ → legacy/ [已整理]