"""
pdf_extractor.py — PDF 转 Markdown 文本模块（轻量版）。

使用 PyMuPDF 从 PDF 中提取文本内容，输出 Markdown 格式文本。
无需 GPU，纯 CPU 运行，适合批量处理。
"""

from __future__ import annotations

import re
from pathlib import Path

import fitz  # PyMuPDF


def extract_text_from_pdf(pdf_path: str | Path) -> str:
    """从 PDF 提取文本，输出 Markdown 格式。

    Args:
        pdf_path: PDF 文件路径

    Returns:
        Markdown 格式文本
    """
    doc = fitz.open(str(pdf_path))
    md_parts = []

    for page_num, page in enumerate(doc):
        md_parts.append(f"\n<!-- page: {page_num + 1} -->\n")
        # 提取文本块（按位置排序）
        blocks = page.get_text("dict")["blocks"]

        for block in blocks:
            if block["type"] == 0:  # 文本块
                lines = []
                for line in block["lines"]:
                    text = "".join(span["text"] for span in line["spans"])
                    if text.strip():
                        lines.append(text.strip())

                if not lines:
                    continue

                text = " ".join(lines)

                # 判断是否为标题（字体大小或加粗）
                is_heading = False
                for line in block["lines"]:
                    for span in line["spans"]:
                        if span["size"] > 14:
                            is_heading = True
                        break

                if is_heading:
                    md_parts.append(f"\n## {text}\n")
                else:
                    md_parts.append(text)

            elif block["type"] == 1:  # 图片块
                # 提取图片引用（不存实际图片）
                md_parts.append(f"\n![Figure](page_{page_num + 1}_img.png)\n")

    doc.close()
    markdown = "\n\n".join(md_parts)

    # 清理多余空行
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)
    return markdown


def extract_text_simple(pdf_path: str | Path) -> str:
    """快速文本提取（不保留排版，仅纯文本）。

    Args:
        pdf_path: PDF 文件路径

    Returns:
        纯文本
    """
    doc = fitz.open(str(pdf_path))
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text


def batch_extract(pdf_dir: str | Path, output_dir: str | Path, suffix: str = ".md") -> list[Path]:
    """批量处理目录下所有 PDF。

    Args:
        pdf_dir: PDF 目录
        output_dir: 输出目录
        suffix: 输出文件后缀

    Returns:
        生成的 Markdown 文件路径列表
    """
    pdf_dir = Path(pdf_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    md_files = []
    for pdf_path in sorted(pdf_dir.glob("*.pdf")):
        try:
            text = extract_text_from_pdf(pdf_path)
            md_path = output_dir / f"{pdf_path.stem}{suffix}"
            md_path.write_text(text, encoding="utf-8")
            md_files.append(md_path)
            print(f"  ✅ {pdf_path.name} → {md_path.name}")
        except Exception as e:
            print(f"  ❌ {pdf_path.name}: {e}")

    return md_files
