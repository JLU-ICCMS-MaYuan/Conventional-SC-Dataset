# Issue #75: 论文引用关系提取与知识图谱展示

**类型**：Feature

**优先级**：P1（重要功能增强）

**状态**：待调研

**创建日期**：2026-09-01

## 问题描述

当前知识图谱的论文关系主要基于：
1. **BUILDS_ON 关系**：AI 提取的"前驱工作"（0-3 个核心方法论依赖），但目标节点是占位符（`paper_id: -1`）
2. **RELATES_TO 关系**：未实现，导致图谱显示稀疏

**核心问题**：缺少最直接、最权威的论文关联证据——**引用关系**（Citation Graph）。

引用关系是学术研究中论文之间联系的黄金标准，通过提取和可视化引用网络，可以：
- 追溯研究脉络和知识传承
- 识别经典论文和重要节点
- 发现研究社区和子领域
- 提供比"前驱工作"更完整的论文关系

## 期望行为

### 用户视角

1. **知识图谱展示**：
   - 论文节点之间有 `CITES` 关系的有向边（A 引用 B → A -[CITES]-> B）
   - 边的方向和强度反映引用方向和引用次数
   - 高被引论文在图谱中突出显示（节点大小、颜色）

2. **论文详情页**：
   - "引用论文"列表：本文引用了哪些论文（References）
   - "被引论文"列表：哪些论文引用了本文（Cited by）
   - 显示引用次数统计

3. **研究脉络追踪**：
   - 从一篇论文出发，查看其引用树（向前追溯）或被引树（向后传播）
   - 识别关键文献和转折点

### 技术视角

1. **数据提取**：
   - 从 PDF 中提取参考文献列表（References 章节）
   - 解析引用信息（作者、标题、年份、DOI）
   - 匹配到数据库中的已有论文或外部数据源（CrossRef、Semantic Scholar）

2. **数据存储**：
   - MySQL 新增 `paper_citations` 表或 `papers.citations` JSON 字段
   - Neo4j 创建 `CITES` 关系

3. **知识图谱更新**：
   - 审批通过后自动同步引用关系到 Neo4j
   - 支持历史论文批量提取和同步

## 当前实现分析

### 已有的相关功能

1. **`builds_on` 字段**（`backend/models.py`）：
   - 存储格式：`[{"work": "Allen-Dynes Tc equation", "hint": "Allen, Dynes, 1975"}]`
   - AI 提取：只取 0-3 个核心依赖
   - 局限性：
     - 只是方法/理论名称，不是完整引用
     - 数量太少（0-3 个），无法反映完整引用网络
     - 目标节点是占位符（`paper_id: -1`），未匹配到真实论文

2. **PDF 文本提取**（`backend/ingest/upload_jobs.py`）：
   - 已有完整的 PDF 解析和分块存储（`paper_chunks`）
   - 可以访问 References 章节的原始文本

3. **Neo4j 同步**（`backend/ingest/sync_neo4j.py`）：
   - 已有自动同步机制
   - 可以轻松添加新的关系类型

### 技术难点

1. **引用信息提取**：
   - PDF 中的 References 格式多样（APS、Nature、arXiv 等）
   - 需要鲁棒的解析器（正则表达式或专用库如 `anystyle`、`grobid`）
   - 需要处理不规范的引用格式

2. **论文匹配**：
   - 提取的引用如何匹配到数据库中的论文？
     - 优先：DOI 精确匹配
     - 次选：标题 + 年份模糊匹配
     - 兜底：查询外部 API（CrossRef、Semantic Scholar、OpenAlex）
   - 外部论文如何处理？
     - 创建占位符节点（只有标题、DOI、年份）
     - 或只保留本地论文之间的引用关系

3. **数据规模**：
   - 一篇论文通常引用 20-100 篇文献
   - 50 篇论文 × 50 引用 = 2500 条关系
   - Neo4j 查询性能需要优化（索引、分页）

4. **更新策略**：
   - 新论文上传时提取引用
   - 历史论文如何批量处理？
   - 外部论文被引次数如何更新？

## 可能的实现方案

### 方案 A：AI 提取引用列表（快速但不完整）

**优点**：
- 复用现有 AI 提取流程
- 开发成本低

**缺点**：
- AI 可能遗漏或错误解析引用
- Token 消耗大（References 可能很长）
- 无法提取完整的引用元数据

**实现**：
```python
# 修改 enrich_papers.py 的 PROMPT
## 任务8：提取引用论文
从参考文献列表中提取所有引用，格式：
[{"title": "...", "authors": "...", "year": 2020, "doi": "10.1103/..."}]
```

### 方案 B：基于规则的引用解析器（准确但复杂）

**优点**：
- 完整提取所有引用
- 可控的准确率

**缺点**：
- 需要处理多种引用格式
- 开发和维护成本高

**实现**：
```python
# 新增 backend/ingest/extract_citations.py
def extract_citations_from_pdf(pdf_path: str) -> list[dict]:
    # 1. 定位 References 章节
    # 2. 逐行解析引用（正则表达式 + 启发式规则）
    # 3. 提取 DOI、标题、作者、年份
    # 4. 返回结构化引用列表
```

### 方案 C：集成外部引用解析服务（最准确）

**优点**：
- 专业的引用解析
- 支持多种格式
- 可获取外部论文的元数据

**缺点**：
- 依赖外部 API（可能有费用或速率限制）
- 需要网络连接

**候选服务**：
- **CrossRef API**：通过 DOI 查询论文元数据和引用
- **Semantic Scholar API**：免费，提供论文引用关系
- **OpenAlex API**：开放知识图谱，包含引用数据
- **Grobid**：开源 PDF 引用提取工具（可本地部署）

**实现**：
```python
# 方案 C1: 通过 DOI 查询 CrossRef
import requests
resp = requests.get(f"https://api.crossref.org/works/{doi}")
references = resp.json()['message']['reference']

# 方案 C2: 使用 Semantic Scholar
resp = requests.get(f"https://api.semanticscholar.org/v1/paper/{doi}")
citations = resp.json()['citations']
```

### 方案 D：混合方案（推荐）

1. **PDF 上传时**：
   - 使用规则解析器提取 DOI 列表（快速、低成本）
   - 对于有 DOI 的引用，查询 CrossRef 获取完整元数据

2. **论文审批通过后**：
   - 批量查询 Semantic Scholar 获取引用关系
   - 与数据库中的论文进行 DOI 匹配
   - 创建 Neo4j `CITES` 关系

3. **外部论文处理**：
   - 只保存元数据（标题、DOI、年份），不创建完整 Paper 节点
   - 或查询时动态获取外部论文信息

## 数据库设计（初步）

### 方案 1：JSON 字段（简单）

```sql
ALTER TABLE papers ADD COLUMN citations JSON;

-- 格式
{
  "references": [
    {"doi": "10.1103/...", "title": "...", "year": 2020},
    ...
  ],
  "cited_by_count": 0  -- 定期更新
}
```

### 方案 2：专用表（规范）

```sql
CREATE TABLE paper_citations (
  id INT PRIMARY KEY AUTO_INCREMENT,
  citing_paper_id INT NOT NULL,  -- 引用者
  cited_paper_id INT,             -- 被引者（本地论文）
  cited_doi VARCHAR(255),         -- 被引者 DOI（外部论文）
  cited_title TEXT,
  cited_year INT,
  citation_context TEXT,          -- 引用上下文（可选）
  FOREIGN KEY (citing_paper_id) REFERENCES papers(id),
  FOREIGN KEY (cited_paper_id) REFERENCES papers(id),
  UNIQUE KEY (citing_paper_id, cited_doi)
);
```

## 待调研的问题

1. **引用解析工具选择**：
   - Grobid 本地部署的性能和准确率？
   - Semantic Scholar API 的免费额度和速率限制？
   - CrossRef API 是否需要邮箱注册？

2. **匹配策略**：
   - DOI 匹配率有多高？（很多老论文没有 DOI）
   - 标题模糊匹配的假阳性率？
   - 是否需要人工审核匹配结果？

3. **性能优化**：
   - Neo4j 查询 1000+ 引用关系的性能？
   - 是否需要引入图数据库索引？
   - 前端渲染大规模图谱的策略？

4. **更新机制**：
   - 如何定期更新外部论文的被引次数？
   - 历史论文批量提取的工作量？

## 相关资源

- [Grobid: 机器学习驱动的 PDF 引用提取](https://github.com/kermitt2/grobid)
- [Semantic Scholar API 文档](https://www.semanticscholar.org/product/api)
- [CrossRef REST API](https://www.crossref.org/documentation/retrieve-metadata/rest-api/)
- [OpenAlex API](https://docs.openalex.org/)
- [anystyle: Ruby 引用解析器](https://github.com/inukshuk/anystyle)

## 后续步骤

1. **调研阶段**（1-2 周）：
   - 测试 Grobid、Semantic Scholar、CrossRef API
   - 评估引用解析准确率
   - 确定混合方案的具体实现

2. **原型开发**（1 周）：
   - 实现引用提取脚本
   - 手工测试 10 篇论文
   - 验证匹配策略

3. **完整实现**（2-3 周）：
   - 集成到上传流程
   - 实现 Neo4j 同步
   - 前端展示引用关系

4. **批量处理**（1 周）：
   - 为历史论文补充引用数据

## 相关 Issue

- [Issue #70：知识图谱节点专用标题](../70-knowledge-graph-title/spec.md) - 已完成
- 知识图谱边关系文档：`docs/overview/04_Superconductivity_Development_Knowledge_Graph/knowledge-graph-edges.md`
