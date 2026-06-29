"""
cross_check.py — 交叉验证模块。

对 extractor 的提取结果进行第二轮验证：
1. 遗漏检查：原文中还有哪些数据点没被提取
2. 纠错检查：已提取的数据点哪些数值不合理
3. 重复检查：是否存在重复提取
"""

from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from backend.rag.config import settings


VERIFY_SYSTEM_PROMPT = """你是一个材料科学专家，负责验证超导数据提取结果。

你面前有一篇论文的原文和第一轮提取出的数据点。
请仔细核对原文，回答三个问题：

## 1. 遗漏检查（missing_data_points）
原文中还有哪些超导数据点没有被提取？
特别注意：
- 表格里每一行数据
- 图表标题中出现的数值
- 正文中明确提到的 Tc、压力、lambda、omega_log 等数值
- 同一化合物的不同压力条件
- 计算设置信息（赝势类型、交换关联泛函、计算软件、k网格、截断能等）
- 稳定性信息（是否热力学稳定、动力学稳定）

## 2. 纠错检查（corrections）
已提取的数据点中，哪些数值不正确？
常见错误：
- Tc 单位错误（比如把 K 写成了摄氏度）
- 压力数值错误
- 化学式解析错误
- lambda 或 omega_log 数值错误
- 空间群符号错误

## 3. 重复检查（duplicates_to_remove）
是否存在同一数据点被重复提取的情况？
比如同一化合物同一压力出现了两次。

返回 JSON 格式：
{
  "missing_data_points": [
    {
      "chemical_formula": "...",
      "pressure_gpa": 200.0,
      "space_group_symbol": "Fm-3m",
      "tc_k": 250.0,
      "allen_dynes_tc": 250.0,
      "experimental_tc": 260.0,
      "lambda_value": 2.5,
      "omega_log": 1200.0,
      "pseudopotential_type": "PAW",
      "exchange_correlation": "PBE",
      "calculation_code": "VASP",
      "k_grid": "16x16x16",
      "thermodynamically_stable": true,
      "dynamically_stable": true,
      "method": "Allen-Dynes",
      "source_label": "paper",
      "evidence": "这段数据在原文中的位置说明"
    }
  ],
  "corrections": [
    {
      "data_point_index": 2,
      "field": "tc_k",
      "original": 250,
      "corrected": 260,
      "reason": "原文第 3 段显示 Tc=260K"
    }
  ],
  "duplicates_to_remove": [0, 3],
  "verification_notes": "整体来看提取质量较好，有两处遗漏..."
}

如果没有遗漏、错误或重复，对应的数组返回空列表。"""


def verify_extraction(
    markdown_text: str,
    first_result_json: dict[str, Any],
    model: str | None = None,
) -> dict[str, Any]:
    """对第一轮提取结果进行交叉验证。"""
    model_name = model or settings.deepseek_model
    client = OpenAI(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
    )

    first_pass_str = json.dumps(first_result_json, ensure_ascii=False, indent=2)
    max_md_chars = 14000
    truncated_md = markdown_text[:max_md_chars]

    user_prompt = f"""## 第一轮提取结果

```json
{first_pass_str}
```

## 论文原文

{truncated_md}

请检查上述提取结果是否有遗漏、错误或重复。"""

    resp = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": VERIFY_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )

    content = resp.choices[0].message.content
    result = json.loads(content)
    return result
