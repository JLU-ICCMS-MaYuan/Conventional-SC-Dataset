# 当前功能现状与数据库承接差距

## 1. 结论摘要

当前系统已经从旧 SQLite 形态切换为 MySQL 优先的结构化数据模型。数据库层面的核心定位是“超导体结构化数据采集、审核、检索、晶体结构存储和图表展示”，不是全文文献平台，也不是学术互动社区。

当前已经落地的主流程：

- 首页元素周期表检索
- 化学式和元素集合检索
- 组合页文献浏览
- 登录、邮箱验证、管理员审批
- 单篇论文上传并写入多条超导记录
- CIF/POSCAR 晶体结构存储、审核、代表结构查询和原文下载
- 管理员审核论文
- 基于 `superconductor_records.show_in_chart` 的图表展示控制
- Alembic 管理 MySQL 表结构
- `mysql-redesign-v1` JSON 导入导出

当前仍未落地或需要重写的能力：

- 新结构下的批量导入
- 图片存储与图片展示
- 点赞、评论、弹幕、热度排序等互动能力

## 2. 当前数据库实际定位

当前核心表为：

- `periodic_table_elements`
- `chemical_systems`
- `superconductors`
- `superconductors_structures`
- `papers`
- `users`
- `superconductor_records`

职责划分：

- `periodic_table_elements` 保存 118 个元素基础信息
- `chemical_systems` 保存排序后的元素体系，例如 `H-La`
- `superconductors` 保存具体超导体化学式及标准化组成，例如 `LaH10`
- `superconductors_structures` 保存 CIF/POSCAR 晶体结构正文、结构哈希、来源、审核状态和默认版本
- `papers` 保存论文元数据、上传用户、审核用户和审核状态
- `users` 保存普通用户、管理员、超级管理员账号，权限由 `role` 表示
- `superconductor_records` 保存具体压强点、空间群、稳定性、Tc、赝势、计算设置和图表显示标记

## 3. 已落地能力

### 3.1 检索

已支持：

- `formula_search`
- `elements_exact_search`
- `elements_combination_search`
- `elements_contained_search`

旧 URL 参数 `only`、`combination`、`contains` 在前端仍会映射到新模式名。

### 3.2 上传

`POST /api/papers/` 现在创建：

- 一条 `papers`
- 一条或多条 `superconductor_records`
- 必要时自动创建 `chemical_systems` 和 `superconductors`

上传不再保存截图，也不再写旧 `paper_data`。

### 3.3 审核

论文审核状态为：

- `pending`
- `approved`
- `rejected`
- `needs_revision`

公开页面可以显示所有审核状态的数据。图表是否显示由 `superconductor_records.show_in_chart` 控制。

### 3.4 图表

已支持：

- `/api/papers/stats/tc-pressure`
- `/api/papers/stats/tc-year`
- `/api/papers/stats/chart-data` 兼容旧 P-Tc 接口

Tc-Year 图只使用有关联论文年份的记录。

### 3.5 晶体结构

已支持：

- `POST /api/structures/` 上传 CIF/POSCAR 结构并使用 ASE 校验
- `POST /api/structures/{structure_id}/review` 审核结构并维护同一化学式、空间群和压强下的默认版本
- `GET /api/structures/by-record/{record_id}` 按超导记录匹配已审核结构
- `GET /api/structures/representative` 按化学式和空间群获取代表结构
- `GET /api/structures/{structure_id}/raw` 下载结构原文
- `mysql-redesign-v1` JSON 导入导出包含 `superconductors_structures`

### 3.6 AI 文献助手（RAG）

已支持：

- React 前端三栏布局：对话历史、流式聊天、文献来源
- SSE 流式问答（`POST /api/rag/chat/stream`）
- 意图解析 → 知识图谱查询 + Chroma 语义检索 → LLM 融合回答
- LaTeX 公式渲染（KaTeX）
- 引用文献顺序编号 [1] [2] [3]，右侧栏对应展示论文标题/期刊/年份/DOI
- 对话和引用元数据持久化到 localStorage
- 多轮对话历史和对话管理（新建/切换/删除）
- RAG 数据存储：SQLite `dev.db` + ChromaDB 向量库，与主 MySQL 业务库分离


## 4. 当前缺口

### 4.1 批量导入

旧批量表格解析脚本包含旧 `Compound/PaperData/PaperImage` 思路。新 MySQL 结构下需要按 `superconductor_records` 重新设计字段映射后再启用。

### 4.2 管理后台细粒度编辑

当前后台已支持用户审批、论文审核、论文列表、论文基础信息编辑和批量图表显示控制。逐条 `superconductor_records` 的完整编辑体验仍需要后续补充。

### 4.3 图片能力

图片存储已下线。图片接口返回 410。后续如果需要重新支持图片，应优先考虑文件或对象存储，而不是写入 MySQL BLOB。

### 4.4 互动能力

当前没有以下表或能力：

- 点赞
- 评论
- 弹幕
- 浏览量
- 热度排序

这些仍属于未实现能力。
