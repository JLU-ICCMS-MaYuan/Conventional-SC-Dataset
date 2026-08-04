# ingest 管线全景

```mermaid
flowchart LR
 subgraph extract["📥 提取流程"]
        pdf["pdf_extractor.py<br>PDF → Markdown"]
        ext["extractor.py<br>LLM 提取元信息<br>(DeepSeek)"]
        sto["store_papers.py<br>store_extraction()<br>→ papers 表"]
        enr["enrich_papers.py<br>enrich_single()<br>LLM 二次富化<br>(DeepSeek)"]
        json["data/clean_results<br>/{pid}.json"]
        ing["store_papers.py<br>ingest_paper()"]
        prop["prop_names.py<br>normalize_prop_name()<br>规则匹配 → AI 兜底<br>(DeepSeek)"]
        ai_cache[("prop_name_ai_cache.json<br>AI 分类缓存")]
  end
 subgraph mysql["🗄️ MySQL (v2)"]
        papers["papers 表<br>title/summary/keywords..."]
        kp["key_properties 表<br>name/value_min/max/P/T..."]
  end
 subgraph Chroma["Chroma"]
        chroma[("Chroma 向量库")]
  end
 subgraph neo4j["Neo4j"]
        kg[("知识图谱<br>Paper→Material→Property")]
  end
    PDF["📄 PDF / TXT / MD"] -->|upload-text| ext
    PDF -->|upload-pdf| pdf
    pdf --> ext
    ext --> sto
    sto --> embed["embedder.py<br>chunk_and_embed()<br>(Embedding API)"] & enr & papers
    embed --> chroma
    enr --> json
    json --> ing
    ing --> prop
    prop --> ai_cache
    prop --> kp
    papers -.-> sync["sync_neo4j.py<br>MySQL → Neo4j"]
    kp -.-> sync
    json -.-> sync
    sync --> kg
```

## 模块职责

| 模块 | 职能 | 写入目标 |
|------|------|----------|
| `pdf_extractor.py` | PDF → Markdown | — |
| `extractor.py` | Markdown → ExtractionResult (LLM) | — |
| `store_papers.py` | `store_extraction()` → papers · `ingest_paper()` → key_properties | MySQL |
| `enrich_papers.py` | `enrich_single()` 单篇 LLM 富化 → clean_results JSON | 文件系统 |
| `prop_names.py` | `normalize_prop_name()` 规则匹配 + `ai_normalize()` AI 兜底 | — |
| `embedder.py` | `chunk_and_embed()` 全文 → Chroma | Chroma |
| `chunker.py` | Markdown → `List[Chunk]` | 被 embedder 调用 |
| `pipeline.py` | 编排入口 `ingest_pdf()` | — |
| `sync_neo4j.py` | MySQL + clean_results → Neo4j | Neo4j |
