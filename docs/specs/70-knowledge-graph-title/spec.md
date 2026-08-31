# Feature 规格：知识图谱节点专用标题

**GitHub Issue**：[#70](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/70)

**创建日期**：2026-08-31

**状态**：已实现

## 背景与目标

知识图谱（"脉络"页面）当前使用论文原始标题作为节点标签，存在以下问题：

1. **标题冗长**：原始标题往往过长（如 "Further experiments with liquid helium. V. The disappearance of the resistance of mercury"），在图谱节点中显示效果差
2. **系列编号干扰**：含有 "Part II"、"V"、"Further..." 等系列编号，对理解核心贡献无帮助
3. **历史意义不突出**：首篇发现超导体的论文应突出"首次"地位，而非只显示实验描述
4. **可读性差**：用户需要读完整个标题才能理解论文核心贡献

**目标**：为每篇论文生成高度凝练的知识图谱专用标题，限 15-30 字（中文）或 10-15 词（英文），突出核心发现、历史地位、材料体系等关键信息。

**示例对比**：

| 原始标题 | 知识图谱标题 |
|---------|-------------|
| Further experiments with liquid helium. V. The disappearance of the resistance of mercury | 首次发现超导体 Hg |
| High-temperature superconductivity in cuprate superconductors | 铜氧化物高温超导 |
| Theory of Superconductivity | BCS 超导理论 |
| Iron-based superconductor LaFeAsO discovered | 铁基超导体 LaFeAsO |

## 用户场景与验收

### 用户故事 1：查看知识图谱时快速理解论文贡献（P0，已实现）

用户打开知识图谱页面，节点显示简洁的标题，能快速理解每篇论文的核心贡献。

**独立验收**：节点标签优先显示知识图谱标题而非原始标题。

**验收场景**：

1. **假如** 用户打开知识图谱页面，**当** 图谱加载完成，**那么**：
   - 每个节点显示凝练的知识图谱标题（如"首次发现超导体 Hg"）
   - 标题长度适中，不超过节点显示区域
   - 点击节点可查看完整原始标题

2. **假如** 论文有知识图谱标题，**当** 查询 API，**那么** 返回 `knowledge_graph_title`
3. **假如** 论文没有知识图谱标题，**当** 查询 API，**那么** fallback 显示原始 `title`

### 用户故事 2：上传新论文自动生成知识图谱标题（P0，已实现）

用户上传论文 PDF 后，AI 提取时自动生成知识图谱标题。

**独立验收**：提取结果包含 `knowledge_graph_title` 字段。

**验收场景**：

1. **假如** 用户上传新论文 PDF，**当** AI 提取完成，**那么**：
   - 提取结果包含 `knowledge_graph_title` 字段
   - 标题长度在 15-30 字（中文）或 10-15 词（英文）
   - 标题包含核心发现和材料/体系名称
   - 标题突出历史地位（"首次"）或突破性质（"高温"/"常压"）

2. **假如** 管理员审批通过论文，**当** 发布完成，**那么**：
   - `knowledge_graph_title` 保存到 MySQL
   - `knowledge_graph_title` 同步到 Neo4j
   - 知识图谱立即显示新标题

### 用户故事 3：手动优化已有论文的知识图谱标题（P2，待实现）

管理员可手动编辑论文的知识图谱标题，优化 AI 生成结果。

**独立验收**：论文编辑页面有知识图谱标题字段。

**验收场景**：

1. **假如** 管理员编辑论文，**当** 打开编辑弹窗，**那么**：
   - 显示"知识图谱标题"输入框
   - 显示原始标题作为参考
   - 提供字数限制提示（建议 15-30 字）

2. **假如** 管理员修改知识图谱标题并保存，**当** 提交成功，**那么**：
   - MySQL 更新 `knowledge_graph_title`
   - 触发 Neo4j 同步
   - 知识图谱立即显示新标题

### 边界与异常场景

- **空标题处理**：未生成时 fallback 到原始 title
- **长度约束**：数据库字段限制 VARCHAR(200)，但推荐 ≤ 30 字
- **语言一致性**：中文论文用中文标题，英文论文用英文标题
- **唯一性**：同一材料体系应有区分度（如"首次发现"vs"高压实验"）
- **历史论文**：需批量生成或手动补充

## 需求

### 功能需求

- **FR-001**：系统必须在 `papers` 表新增 `knowledge_graph_title` 字段（VARCHAR(200)），
  位于 `methodology` 字段之后

- **FR-002**：AI 提取时必须生成 `knowledge_graph_title`，遵循以下规则：
  - 长度：15-30 字（中文）或 10-15 词（英文）
  - 必须包含：核心发现/贡献 + 材料/体系名称
  - 优先突出：历史地位（"首次"/"第一个"）、突破性质（"高温"/"常压"/"室温"）
  - 避免：系列编号（"V"/"Part II"/"Further..."）、通用描述、冗长修饰

- **FR-003**：知识图谱 API 必须优先返回 `knowledge_graph_title`，未设置时 fallback 到 `title`：
  ```cypher
  coalesce(p.knowledge_graph_title, p.title, p.import_label, 'Untitled') AS display_title
  ```

- **FR-004**：审批发布论文时必须同时同步 `knowledge_graph_title` 到 Neo4j，保存为 Paper 节点属性

- **FR-005**：系统必须在以下 API 端点使用知识图谱标题：
  - `GET /api/knowledge-graph/overview`：图谱总览
  - `GET /api/knowledge-graph/papers/{id}/neighbors`：邻居节点
  - `GET /api/knowledge-graph/stats`：统计信息

- **FR-006**（P2，待实现）：论文编辑页面必须提供知识图谱标题编辑字段，允许管理员手动优化

### 非功能需求

- **NFR-001**：知识图谱标题生成质量应达到 80% 可用率（人工评估）
- **NFR-002**：API 响应时间不因新字段增加而显著增加（< 10ms）
- **NFR-003**：数据库迁移必须向后兼容，已有论文允许 NULL 值

## 技术设计

### 数据库 Schema

```sql
ALTER TABLE papers 
ADD COLUMN knowledge_graph_title VARCHAR(200) DEFAULT NULL 
AFTER methodology;
```

**字段说明**：
- 类型：`VARCHAR(200)`（足够容纳中英文）
- 可空：`NULL`（已有论文无此字段）
- 位置：`methodology` 之后，`key_finding` 之前

### AI 提取提示词

在 `SUMMARY_SYSTEM_PROMPT` 中添加：

```
knowledge_graph_title 用于知识图谱节点显示，高度凝练论文的核心贡献，限 15-30 字（中文）或 10-15 词（英文）。

格式要求：
- 必须包含：核心发现/贡献 + 材料/体系名称
- 优先突出：历史地位（"首次"/"第一个"）、突破性质（"高温"/"常压"）、独特性质
- 避免：冗长修饰、系列编号（"Further..."/"Part II"）、通用描述

示例：
  - "Further experiments with liquid helium. V" → "首次发现超导体 Hg"
  - "High-temperature superconductivity in cuprates" → "铜氧化物高温超导"
  - "BCS theory of superconductivity" → "BCS 超导理论"
  - "Iron-based superconductor LaFeAsO" → "铁基超导体 LaFeAsO"
```

### Neo4j 图数据库

**节点属性**：
```cypher
(:Paper {
  paper_id: Integer,
  title: String,                    // 原始标题
  knowledge_graph_title: String,    // 知识图谱标题（新增）
  doi: String,
  year: Integer,
  journal: String
})
```

**查询优先级**：
```cypher
MATCH (p:Paper)
RETURN coalesce(p.knowledge_graph_title, p.title, 'Untitled') AS display_title
```

### API 响应格式

```json
{
  "nodes": [
    {
      "id": "paper_9",
      "label": "首次发现超导体 Hg",  // 优先使用 knowledge_graph_title
      "year": 1911,
      "doi": null
    }
  ],
  "edges": [],
  "total_edges": 0,
  "message": "从 Neo4j 加载了 1 个节点和 0 条边"
}
```

### 同步流程

```
用户上传 PDF
    ↓
AI 提取（生成 knowledge_graph_title）
    ↓
保存到 MySQL papers.knowledge_graph_title
    ↓
管理员审批通过
    ↓
publish_approved_paper() 触发：
    1. 索引到 Qdrant
    2. 同步到 Neo4j（包含 knowledge_graph_title）
    ↓
知识图谱 API 查询时返回 display_title
    ↓
前端显示凝练标题
```

## 实现文件清单

### 后端修改

1. **数据库迁移**：
   - `alembic/versions/20260831_175226_add_knowledge_graph_title.py`
   
2. **模型定义**：
   - `backend/models.py`：Paper 模型添加 `knowledge_graph_title` 字段
   
3. **AI 提取**：
   - `backend/ingest/upload_jobs.py`：修改 `SUMMARY_SYSTEM_PROMPT`
   
4. **知识图谱 API**：
   - `backend/api/kg_live.py`：
     - `get_live_overview()` 修改查询
     - `get_paper_neighbors()` 修改查询
     - `get_graph_stats()` 修改查询
   
5. **自动同步**：
   - `backend/api/rag.py`：`publish_approved_paper()` 同步到 Neo4j

### 前端修改

- **无需修改**：前端通过 API 获取数据，后端返回的 `label` 字段已自动使用知识图谱标题

## 测试策略

### 单元测试

- `test_knowledge_graph_title_generation()`：验证 AI 生成标题质量
- `test_knowledge_graph_title_fallback()`：验证 NULL 时 fallback 到 title
- `test_neo4j_sync_with_kg_title()`：验证同步包含新字段

### 集成测试

- `test_upload_and_publish_with_kg_title()`：完整流程测试
- `test_knowledge_graph_api_returns_kg_title()`：API 响应验证

### 手工测试

- 上传新论文，验证生成的知识图谱标题质量
- 查看知识图谱页面，验证节点显示效果
- 修改知识图谱标题，验证同步正确

## 质量标准

### 好的知识图谱标题

- ✅ "首次发现超导体 Hg"（历史地位 + 材料）
- ✅ "铜氧化物高温超导"（突破性质 + 体系）
- ✅ "铁基超导体 LaFeAsO"（新体系 + 代表材料）
- ✅ "BCS 超导理论"（重要理论）
- ✅ "常压室温超导 LuH₃"（突破条件 + 材料）

### 需要改进的标题

- ❌ "进一步的液氦实验 V"（系列编号，无核心信息）
- ❌ "超导体的研究"（过于通用）
- ❌ "高温超导材料的电子结构和配对机制的第一性原理研究"（过长）
- ❌ "材料 X"（缺少贡献描述）

## 部署与迁移

### 数据库迁移

```bash
cd ~/work/SC-Wiki-docker
docker compose -f dev.yaml run --rm migrate
```

或手动执行：
```sql
ALTER TABLE papers 
ADD COLUMN knowledge_graph_title VARCHAR(200) DEFAULT NULL 
AFTER methodology;
```

### 历史论文处理

**选项 1：批量生成**（推荐）
```bash
# 待开发：批量生成脚本
docker compose -f dev.yaml run --rm python python backend/scripts/generate_kg_titles.py
```

**选项 2：手动补充**（临时方案）
```sql
UPDATE papers 
SET knowledge_graph_title = '首次发现超导体 Hg' 
WHERE id = 9;
```

然后同步到 Neo4j：
```python
from neo4j import GraphDatabase
driver = GraphDatabase.driver('bolt://neo4j:7687', auth=('neo4j', password))
with driver.session() as s:
    s.run('''
        MATCH (p:Paper {paper_id: 9})
        SET p.knowledge_graph_title = '首次发现超导体 Hg'
    ''')
```

## 后续优化

- [ ] **管理员编辑界面**（P2）：添加知识图谱标题编辑字段
- [ ] **批量生成工具**（P2）：为历史论文批量生成标题
- [ ] **质量评分**（P3）：评估标题质量（长度、关键词、可读性）
- [ ] **多语言支持**（P3）：中英文双语标题
- [ ] **A/B 测试**（P3）：对比原始标题和知识图谱标题的用户偏好

## 依赖与风险

### 依赖

- Neo4j 服务正常运行
- AI 提取流程正常工作
- 数据库迁移成功执行

### 风险

- **AI 生成质量不稳定**：需要人工审核和优化
  - **缓解措施**：添加编辑界面，允许手动优化
  
- **历史论文缺少标题**：需要批量处理
  - **缓解措施**：优雅降级到原始标题
  
- **标题不唯一**：同一体系多篇论文可能重复
  - **缓解措施**：生成提示词强调区分度

## 验收标准

### 必须满足（P0）

- [x] 数据库字段已添加
- [x] AI 提取生成知识图谱标题
- [x] 知识图谱 API 返回凝练标题
- [x] 自动同步到 Neo4j
- [x] 前端显示新标题

### 应该满足（P1）

- [ ] 生成质量达到 80% 可用率
- [ ] 标题长度符合规范
- [ ] 无性能回退

### 可以满足（P2）

- [ ] 管理员可手动编辑
- [ ] 历史论文批量生成
- [ ] 质量评分机制

## 参考文档

- 详细实现：`docs/knowledge-graph-title-feature.md`
- 自动同步方案：`docs/kg-auto-sync-solution.md`
- 数据源说明：`docs/kg-data-source-explained.md`
