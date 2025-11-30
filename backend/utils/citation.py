"""
引用格式生成工具
支持APS和BibTeX格式
"""
from typing import List, Optional
import re


class CitationGenerator:
    """引用格式生成器"""

    @staticmethod
    def generate_aps_citation(
        authors: List[str],
        title: str,
        journal: Optional[str] = None,
        volume: Optional[str] = None,
        pages: Optional[str] = None,
        year: Optional[int] = None,
        doi: Optional[str] = None
    ) -> str:
        """
        生成APS（American Physical Society）格式的引用

        格式示例：
        H. Wang, X. Li, G. Gao, Y. Li, and Y. Ma, Hydrogen-rich
        superconductors at high pressures, WIREs Comput. Mol. Sci.
        8, e1330 (2018).

        Args:
            authors: 作者列表
            title: 文章标题
            journal: 期刊名称
            volume: 卷号
            pages: 页码
            year: 年份
            doi: DOI

        Returns:
            APS格式的引用字符串
        """
        citation_parts = []

        # 1. 处理作者
        if authors:
            formatted_authors = CitationGenerator._format_aps_authors(authors)
            citation_parts.append(formatted_authors)

        # 2. 添加标题
        if title:
            citation_parts.append(title)

        # 3. 添加期刊、卷号、页码、年份
        if journal and volume and pages and year:
            # 简化期刊名称（如果是常见物理期刊）
            journal_abbr = CitationGenerator._abbreviate_journal(journal)
            citation_parts.append(f"{journal_abbr} {volume}, {pages} ({year})")
        elif journal and year:
            citation_parts.append(f"{journal} ({year})")
        elif year:
            citation_parts.append(f"({year})")

        # 组合引用
        if citation_parts:
            citation = ", ".join(citation_parts) + "."
        else:
            citation = title or "Unknown article"

        return citation

    @staticmethod
    def _format_aps_authors(authors: List[str]) -> str:
        """
        格式化APS作者列表

        规则：
        - 1个作者: A. B. Smith
        - 2个作者: A. B. Smith and C. D. Johnson
        - 3+作者: A. B. Smith, C. D. Johnson, and E. F. Brown

        Args:
            authors: 作者名字列表

        Returns:
            格式化的作者字符串
        """
        if not authors:
            return ""

        # 简化作者名字（缩写名字，保留姓氏）
        formatted_authors = []
        for author in authors[:10]:  # 最多显示10个作者
            formatted_authors.append(CitationGenerator._abbreviate_name(author))

        if len(formatted_authors) == 1:
            return formatted_authors[0]
        elif len(formatted_authors) == 2:
            return f"{formatted_authors[0]} and {formatted_authors[1]}"
        else:
            # 多个作者用逗号分隔，最后一个用 "and"
            authors_str = ", ".join(formatted_authors[:-1])
            return f"{authors_str}, and {formatted_authors[-1]}"

    @staticmethod
    def _abbreviate_name(full_name: str) -> str:
        """
        缩写名字

        例如: "Albert Einstein" -> "A. Einstein"
             "Marie Curie" -> "M. Curie"

        Args:
            full_name: 完整名字

        Returns:
            缩写后的名字
        """
        parts = full_name.strip().split()
        if len(parts) == 0:
            return ""
        elif len(parts) == 1:
            return parts[0]
        else:
            # 缩写除最后一个词（姓氏）外的所有部分
            initials = [f"{p[0]}." for p in parts[:-1] if p]
            return " ".join(initials + [parts[-1]])

    @staticmethod
    def _abbreviate_journal(journal: str) -> str:
        """
        缩写期刊名称（常见物理和材料科学期刊）

        Args:
            journal: 完整期刊名称

        Returns:
            缩写期刊名称
        """
        abbreviations = {
            # Physical Review 系列
            "Physical Review Letters": "Phys. Rev. Lett.",
            "Physical Review B": "Phys. Rev. B",
            "Physical Review A": "Phys. Rev. A",
            "Physical Review X": "Phys. Rev. X",
            "Physical Review": "Phys. Rev.",
            "Physical Review Applied": "Phys. Rev. Appl.",
            "Physical Review Materials": "Phys. Rev. Mater.",

            # Nature 系列
            "Nature": "Nature",
            "Nature Physics": "Nat. Phys.",
            "Nature Materials": "Nat. Mater.",
            "Nature Communications": "Nat. Commun.",
            "Nature Chemistry": "Nat. Chem.",

            # Science 系列
            "Science": "Science",
            "Science Advances": "Sci. Adv.",

            # 其他重要期刊
            "Advanced Materials": "Adv. Mater.",
            "Advanced Functional Materials": "Adv. Funct. Mater.",
            "Applied Physics Letters": "Appl. Phys. Lett.",
            "Journal of Applied Physics": "J. Appl. Phys.",
            "Journal of Physics": "J. Phys.",
            "Materials Today": "Mater. Today",
            "Matter and Radiation at Extremes": "Matter Radiat. Extremes",
            "National Science Review": "Natl. Sci. Rev.",
            "Physics Reports": "Phys. Rep.",
            "The Innovation": "The Innovation",
            "WIREs Computational Molecular Science": "WIREs Comput. Mol. Sci.",
        }

        # 尝试精确匹配（不区分大小写）
        for full, abbr in abbreviations.items():
            if full.lower() == journal.lower():
                return abbr

        # 尝试部分匹配
        for full, abbr in abbreviations.items():
            if full.lower() in journal.lower():
                return abbr

        return journal  # 如果没有匹配，返回原名称

    @staticmethod
    def generate_bibtex_citation(
        authors: List[str],
        title: str,
        journal: Optional[str] = None,
        volume: Optional[str] = None,
        pages: Optional[str] = None,
        year: Optional[int] = None,
        doi: Optional[str] = None
    ) -> str:
        """
        生成BibTeX格式的引用

        格式示例:
        @article{Smith2020,
          author = {Smith, A. B. and Johnson, C. D. and Brown, E. F.},
          title = {Article Title},
          journal = {Physical Review Letters},
          volume = {123},
          pages = {456789},
          year = {2020},
          doi = {10.1103/PhysRevLett.123.456789}
        }

        Args:
            authors: 作者列表
            title: 文章标题
            journal: 期刊名称
            volume: 卷号
            pages: 页码
            year: 年份
            doi: DOI

        Returns:
            BibTeX格式的引用字符串
        """
        # 生成cite key（第一作者姓氏+年份）
        cite_key = CitationGenerator._generate_cite_key(authors, year)

        # 开始构建BibTeX
        bibtex_lines = [f"@article{{{cite_key},"]

        # 作者
        if authors:
            bibtex_authors = CitationGenerator._format_bibtex_authors(authors)
            bibtex_lines.append(f"  author = {{{bibtex_authors}}},")

        # 标题
        if title:
            bibtex_lines.append(f"  title = {{{title}}},")

        # 期刊
        if journal:
            bibtex_lines.append(f"  journal = {{{journal}}},")

        # 卷号
        if volume:
            bibtex_lines.append(f"  volume = {{{volume}}},")

        # 页码
        if pages:
            bibtex_lines.append(f"  pages = {{{pages}}},")

        # 年份
        if year:
            bibtex_lines.append(f"  year = {{{year}}},")

        # DOI
        if doi:
            bibtex_lines.append(f"  doi = {{{doi}}}")

        bibtex_lines.append("}")

        return "\n".join(bibtex_lines)

    @staticmethod
    def _format_bibtex_authors(authors: List[str]) -> str:
        """
        格式化BibTeX作者列表

        规则: "Last1, First1 and Last2, First2 and Last3, First3"

        Args:
            authors: 作者列表

        Returns:
            BibTeX格式的作者字符串
        """
        if not authors:
            return ""

        bibtex_authors = []
        for author in authors:
            # 尝试分离名和姓
            parts = author.strip().split()
            if len(parts) >= 2:
                # 假设最后一个词是姓氏
                last_name = parts[-1]
                first_names = " ".join(parts[:-1])
                bibtex_authors.append(f"{last_name}, {first_names}")
            else:
                bibtex_authors.append(author)

        return " and ".join(bibtex_authors)

    @staticmethod
    def _generate_cite_key(authors: List[str], year: Optional[int]) -> str:
        """
        生成BibTeX的cite key

        格式: FirstAuthorLastName + Year

        Args:
            authors: 作者列表
            year: 年份

        Returns:
            cite key字符串
        """
        if authors and len(authors) > 0:
            # 获取第一作者的姓氏
            first_author = authors[0].strip().split()
            if first_author:
                last_name = first_author[-1]
                # 移除非字母字符
                last_name = re.sub(r'[^a-zA-Z]', '', last_name)
            else:
                last_name = "Unknown"
        else:
            last_name = "Unknown"

        year_str = str(year) if year else "0000"
        return f"{last_name}{year_str}"


# 创建全局实例
citation_generator = CitationGenerator()


# 便捷函数
def generate_aps_citation(
    authors: List[str],
    title: str,
    journal: Optional[str] = None,
    volume: Optional[str] = None,
    pages: Optional[str] = None,
    year: Optional[int] = None,
    doi: Optional[str] = None
) -> str:
    """生成APS格式引用的便捷函数"""
    return citation_generator.generate_aps_citation(
        authors, title, journal, volume, pages, year, doi
    )


def generate_bibtex_citation(
    authors: List[str],
    title: str,
    journal: Optional[str] = None,
    volume: Optional[str] = None,
    pages: Optional[str] = None,
    year: Optional[int] = None,
    doi: Optional[str] = None
) -> str:
    """生成BibTeX格式引用的便捷函数"""
    return citation_generator.generate_bibtex_citation(
        authors, title, journal, volume, pages, year, doi
    )
