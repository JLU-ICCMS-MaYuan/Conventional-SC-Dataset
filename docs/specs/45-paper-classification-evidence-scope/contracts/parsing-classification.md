# 接口契约：分段分类证据与解析预览

## 分段 LLM 结果

论文类型证据：

```json
{
  "paper_type_evidence": [
    {
      "candidate": "theoretical",
      "scope": "current_paper",
      "page": 2,
      "quote": "The phase diagram is constructed through structure searching simulations."
    },
    {
      "candidate": "experimental",
      "scope": "referenced_work",
      "page": 1,
      "quote": "Subsequent experimental work found two superconducting states."
    }
  ]
}
```

材料类型候选：

```json
{
  "sc_type_candidates": [
    {
      "value": "高压三元氢化物超导体",
      "scope": "current_paper",
      "page": 1,
      "quote": "ternary Li2MgH16"
    }
  ]
}
```

`value` 为自由文本，不进行枚举校验或自动同义词合并。

## 解析详情响应

`GET /api/upload-tasks/{task_id}/parsing` 的字段状态扩展为：

```json
{
  "path": "paper.paper_type",
  "label": "论文类型",
  "state": "pending_summary",
  "candidates": [
    {
      "value": "theoretical",
      "sources": [
        {
          "filename": "paper.pdf",
          "file_role": "main",
          "section": "全文",
          "page_start": 2,
          "page_end": 2,
          "quote": "The phase diagram is constructed through structure searching simulations."
        }
      ]
    }
  ]
}
```

约束：

- 分类字段在任务处于 `reading` 或 `summarizing` 时返回 `pending_summary`。
- `paper.paper_type` 候选只包含 `scope=current_paper` 且非 `unknown` 的条目。
- `sc_type` 候选只包含 `scope=current_paper` 的自由文本条目。
- `referenced_work` 和无作用域条目仍保留在各分段的公开结构化结果中。
- 标题、DOI 等非分类字段继续返回 `waiting|filled|conflict`。
- 现有安全白名单不扩大到提示词、原始响应、内部路径或模型配置。

## 全文汇总输入

- 保持全部成功分段及其顺序。
- 在每个分段副本中，论文类型证据只保留本文作用域的非 `unknown` 条目。
- 在每个分段副本中，材料类型候选只保留本文作用域条目。
- 不修改磁盘上用于证据查看的原始分段结果。

## 兼容性

- 当前契约版本缓存可以复用。
- 缺少版本或作用域的旧缓存由 Worker 重读；公开读取期间不得报错。
- 无作用域分类项不得默认解释为 `current_paper`。
- 本变更不涉及数据库迁移和公开正式论文 API。
