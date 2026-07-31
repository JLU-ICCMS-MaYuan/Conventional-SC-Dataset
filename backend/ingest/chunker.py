"""
chunker.py — 论文文本切块模块。

按章节标题和段落边界将论文正文切成语义完整的文本块。
每块长度控制在 500-1000 tokens 之间，方便向量搜索。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List


@dataclass
class Chunk:
    """一个文本块。"""
    paper_id: int
    chunk_index: int
    section_name: str | None
    heading: str | None
    content: str
    token_count: int


def chunk_paper(
    markdown_text: str,
    paper_id: int,
    max_tokens: int = 800,
) -> List[Chunk]:
    """将 Markdown 正文切成文本块。

    切分策略（语义分块）：
    1. 按 ## 二级标题切分为大段
    2. 每段超过 max_tokens 时，按空行再切为子段
    3. 小于 50 tokens 的碎片段合并到前一段

    Args:
        markdown_text: 论文的完整 Markdown 文本
        paper_id: Paper.id
        max_tokens: 每块最大 token 数（按 4 字符/token 估算）

    Returns:
        Chunk 列表
    """
    # 去掉前面的 # 一级标题行（论文标题已有 Paper.title）
    text = _strip_top_heading(markdown_text)

    # 按 ## 二级标题切分
    sections = _split_by_h2(text)

    chunks: List[Chunk] = []
    chunk_index = 0

    for section_name, heading, body in sections:
        # 如果该段很短，直接作为一个块
        token_est = len(body) // 4
        if token_est <= max_tokens:
            if _should_keep(body):
                chunks.append(Chunk(
                    paper_id=paper_id,
                    chunk_index=chunk_index,
                    section_name=section_name,
                    heading=heading,
                    content=body.strip(),
                    token_count=token_est,
                ))
                chunk_index += 1
        else:
            # 超过 max_tokens，按空行切分子段
            sub_sections = _split_by_blank_line(body)
            for sub in sub_sections:
                sub_token_est = len(sub) // 4
                if sub_token_est > max_tokens:
                    # 如果子段仍然太长，按句子切分
                    sub_sub = _split_by_sentence(sub, max_tokens)
                    for ss in sub_sub:
                        if _should_keep(ss):
                            chunks.append(Chunk(
                                paper_id=paper_id,
                                chunk_index=chunk_index,
                                section_name=section_name,
                                heading=heading,
                                content=ss.strip(),
                                token_count=len(ss) // 4,
                            ))
                            chunk_index += 1
                else:
                    if _should_keep(sub):
                        chunks.append(Chunk(
                            paper_id=paper_id,
                            chunk_index=chunk_index,
                            section_name=section_name,
                            heading=heading,
                            content=sub.strip(),
                            token_count=sub_token_est,
                        ))
                        chunk_index += 1

    # 合并太小的碎片段（小于 50 tokens 的）
    chunks = _merge_small_chunks(chunks, min_tokens=50)

    return chunks


def _strip_top_heading(text: str) -> str:
    """去掉开头的 # 一级标题。"""
    lines = text.split("\n")
    if lines and lines[0].startswith("# "):
        return "\n".join(lines[1:])
    return text


def _split_by_h2(text: str):
    """按 ## 二级标题切分文本。

    返回: [(section_name, heading_text, body_text), ...]
    """
    # 找到所有 ## 标题的位置
    pattern = re.compile(r"^(##\s+.+)$", re.MULTILINE)
    matches = list(pattern.finditer(text))

    if not matches:
        # 没有二级标题，整体作为一个段
        return [("全文", None, text)]

    sections = []
    for i, match in enumerate(matches):
        heading = match.group(1).strip()
        section_name = heading.lstrip("#").strip()

        # 计算正文：从当前标题到下一个标题之前
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()

        sections.append((section_name, heading, body))

    return sections


def _split_by_blank_line(text: str) -> list[str]:
    """按空行或段落边界切分。"""
    paragraphs = re.split(r"\n\s*\n", text)
    return [p.strip() for p in paragraphs if p.strip()]


def _split_by_sentence(text: str, max_tokens: int) -> list[str]:
    """按句子切分，每块不超过 max_tokens。"""
    # 按句号、问号、感叹号、分号切分
    sentences = re.split(r"(?<=[。！？；.\!?;])\s*", text)
    sentences = [s.strip() for s in sentences if s.strip()]

    chunks = []
    current = []
    current_len = 0

    for sent in sentences:
        sent_len = len(sent) // 4
        if current_len + sent_len > max_tokens and current:
            chunks.append(" ".join(current))
            current = [sent]
            current_len = sent_len
        else:
            current.append(sent)
            current_len += sent_len

    if current:
        chunks.append(" ".join(current))

    return chunks


def _should_keep(text: str) -> bool:
    """判断一段文本是否应该保留（不保留只有数字/符号/空白的片段）。"""
    cleaned = re.sub(r"\s", "", text)
    # 去掉纯 LaTeX / 公式 / 图片引用
    if len(cleaned) < 10:
        return False
    return True


def _merge_small_chunks(chunks: list[Chunk], min_tokens: int) -> list[Chunk]:
    """将过小的碎片段合并到前一段。"""
    if not chunks:
        return chunks

    merged = [chunks[0]]
    for chunk in chunks[1:]:
        if chunk.token_count < min_tokens and merged:
            # 合并到前一段
            prev = merged[-1]
            prev.content = prev.content + "\n\n" + chunk.content
            prev.token_count = len(prev.content) // 4
        else:
            merged.append(chunk)

    # 重新编号
    for i, chunk in enumerate(merged):
        chunk.chunk_index = i

    return merged
