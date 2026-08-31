# 实施计划：知识图谱节点专用标题

**GitHub Issue**：[#70](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/70)

**日期**：2026-08-31

**Spec**：[spec.md](spec.md)

## 摘要

为每篇论文添加知识图谱专用标题（15-30 字），取代冗长的原始标题，突出核心贡献和历史地位。涉及数据库字段、AI 提取、API 展示和自动同步四个层次，但不需要修改前端代码（API 契约保持兼容）。

## 技术上下文

- **语言与版本**：Python 3.13 + FastAPI + SQLAlchemy + Alembic
- **数据库**：MySQL + Neo4j
- **AI 模型**：Claude Opus via Anthropic API
- **测试体系**：手工 curl 验证 + 数据库查询验证
- **约束**：
  - 保持 API 向后兼容（新增字段，不删除旧字段）
  - 对已有论文优雅降级（fallback 到原始标题）
  - 不影响其他功能性能

## 源代码结构

```text
backend/database/models.py           [修改] 添加 knowledge_graph_title 字段
alembic/versions/20260831_175226_*.py [新增] 数据库迁移
backend/ai_services/summary.py       [修改] SUMMARY_SYSTEM_PROMPT
backend/api/kg_live.py               [修改] 优先返回 knowledge_graph_title
backend/rag.py                       [修改] 同步到 Neo4j
docs/knowledge-graph-title-feature.md [新增] 详细实现文档
docs/specs/70-knowledge-graph-title/ [新增] 本 Spec
docs/overview/03_.../paper-and-property-results.md [修改] 回写
```

## 需求到设计的映射

| 来源 | 设计 | 验证方式 |
|------|------|----------|
| FR-001 | `papers` 表新增 `knowledge_graph_title` VARCHAR(200) | 数据库 schema 查询 |
| FR-002 | AI 提取生成 15-30 字凝练标题 | 审查生成结果质量 |
| FR-003 | Neo4j `Paper` 节点同步新字段 | Neo4j 查询节点属性 |
| FR-004 | API 优先返回 `knowledge_graph_title`，fallback 到 `title` | curl 验证有/无标题的论文 |
| SC-001 | 知识图谱节点显示凝练标题 | 浏览器访问知识图谱页面 |
| SC-002 | 新论文自动生成标题 | 上传论文 → 审批 → 验证 |
| SC-003 | 已有论文优雅降级 | 查询无标题论文的展示 |

## 技术决策

### 决策1：字段类型选择 VARCHAR(200)

知识图谱标题限定 15-30 字（中文）或 10-15 词（英文），实际占用：
- 中文：30 字 × 3 字节（UTF-8）= 90 字节
- 英文：15 词 × 平均 7 字符 = 105 字节
- 标点和空格：约 10 字节

总计不超过 120 字节，考虑未来弹性和数据库对齐，选择 VARCHAR(200)。

### 决策2：API 层 fallback 策略

在 `kg_live.py` 的节点构建处使用 `paper.knowledge_graph_title or paper.title`，而非在数据库查询或 AI 提取层做 fallback。原因：
- **责任清晰**：存储层只管存储，展示层负责展示策略
- **灵活调整**：未来可改为显示"[待生成标题]"而不是 fallback
- **性能无损**：字段读取在同一查询，无额外开销

### 决策3：不修改前端代码

API 返回的 JSON 结构不变，只是 `nodes[].label` 字段的值改变。前端不感知数据来源，无需修改。这是典型的后端优化，前端"免费"获得改进。

### 决策4：AI 提示词位置

在 `SUMMARY_SYSTEM_PROMPT` 而非 `USER_PROMPT_TEMPLATE` 中添加标题生成规则。原因：
- System prompt 定义助手的角色和能力范围
- User prompt 是具体任务输入
- 标题生成规则属于"你是什么"而非"你要做什么"

## 实施步骤

1. **数据库层**：
   - 添加 `papers.knowledge_graph_title` 字段到 `models.py`
   - 生成 Alembic 迁移脚本
   - 执行迁移（dev 栈）

2. **AI 提取层**：
   - 修改 `SUMMARY_SYSTEM_PROMPT` 添加标题生成规则
   - 测试生成质量（手工审查）

3. **展示层**：
   - `kg_live.py` 修改节点标签逻辑
   - curl 验证 API 返回

4. **同步层**：
   - `rag.py` 添加 `knowledge_graph_title` 同步到 Neo4j
   - Neo4j 查询验证

5. **文档**：
   - 创建 `knowledge-graph-title-feature.md` 详细文档
   - 创建 Issue #70 及 Spec
   - 回写 Overview

## 验证结果

| 项目 | 结果 |
|------|------|
| 数据库字段 | `SHOW COLUMNS FROM papers LIKE 'knowledge_graph_title'` 返回 VARCHAR(200) |
| AI 生成质量 | 手工审查 10 篇论文，标题长度符合规范，核心信息突出 |
| API 返回 | `curl /api/knowledge-graph/overview` 返回新标题 |
| Neo4j 同步 | `MATCH (p:Paper {doi: '...'}) RETURN p.knowledge_graph_title` 有值 |
| 前端展示 | 浏览器访问知识图谱，节点显示凝练标题 |
| 优雅降级 | 无标题论文 fallback 到原始标题，无 UI 异常 |

## 实施细节

**Alembic 迁移脚本生成。** 使用 `alembic revision --autogenerate -m "add knowledge_graph_title"`，手工检查生成的 `upgrade()` 和 `downgrade()` 逻辑：

```python
def upgrade() -> None:
    op.add_column('papers', sa.Column('knowledge_graph_title', sa.String(length=200), nullable=True))

def downgrade() -> None:
    op.drop_column('papers', 'knowledge_graph_title')
```

**AI 提示词优化。** 初始版本生成的标题过于通用（"铜氧化物超导研究"），添加"突出历史地位"和"包含材料体系"约束后，生成质量提升至"铜氧化物高温超导首次发现"。

**Neo4j 字段名对齐。** Neo4j 节点属性使用 snake_case，与 MySQL 字段保持一致：`knowledge_graph_title` 而非 `knowledgeGraphTitle`。

## 性能影响

- **数据库**：新增 VARCHAR(200) 字段，单行增加约 50-120 字节，百万级论文库约增加 100 MB 存储
- **API 查询**：无额外 JOIN，只是多读一个字段，无性能影响
- **AI 提取**：添加一个输出字段，token 增加约 20-50/篇，成本增加 < 1%
- **Neo4j 同步**：多写一个属性，单次同步增加 < 10 ms

## 遗留事项

- **历史论文批量生成**：当前只对新上传论文生成，已有 50+ 篇历史论文需手工或批量处理（P2）
- **管理员编辑界面**：暂无手工优化标题的 UI，需要直接操作数据库（P2）
- **生成质量评估**：无自动化质量检测，依赖人工审核（P3）
- **标题去重**：同一体系多篇论文可能生成相似标题（如"铁基超导体发现"），未做唯一性约束（P3）
