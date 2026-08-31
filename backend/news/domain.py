"""资讯领域数据和保守筛选规则。"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
import re
from urllib.parse import unquote, urlsplit, urlunsplit

SOURCES = ("arxiv", "crossref", "physorg")


class CollectionError(Exception):
    """只携带可公开的稳定错误代码。"""


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_time(value: str) -> datetime:
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if result.tzinfo is None:
            raise ValueError("missing timezone")
        return result.astimezone(timezone.utc)
    except (ValueError, TypeError, AttributeError) as exc:
        raise CollectionError("invalid_record") from exc


class _PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def plain(value: str, limit: int = 16000) -> str:
    parser = _PlainText()
    parser.feed(str(value or ""))
    return " ".join(" ".join(parser.parts).split())[:limit]


def safe_url(value: str) -> str:
    try:
        parts = urlsplit(value)
        if parts.scheme not in ("http", "https") or not parts.hostname or parts.username or parts.password:
            raise ValueError("unsafe url")
        if any(ord(c) < 32 for c in value) or len(value) > 2000:
            raise ValueError("invalid url")
        return value
    except ValueError as exc:
        raise CollectionError("invalid_record") from exc


def canonical_url(value: str) -> str:
    p = urlsplit(safe_url(value))
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path, p.query, ""))


def normalize_doi(value: str) -> str:
    result = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", str(value or "").strip(), flags=re.I)
    result = unquote(result).lower()
    return result if re.fullmatch(r"10\.\d{4,9}/\S+", result) and len(result) <= 500 else ""


def relevant(text: str) -> bool:
    return bool(re.search(r"superconduct\w*|超导|\bjosephson\b|\bcooper[ -]pairs?\b|\bmeissner\b", text, re.I))


@dataclass(frozen=True)
class Record:
    source: str
    external_id: str
    kind: str
    title: str
    url: str
    summary: str = ""
    summary_source: str = ""
    doi: str = ""
    arxiv_id: str = ""
    version: int = 0
    authors: list[str] = field(default_factory=list)
    journal: str = ""
    published_at: str = ""
    date_precision: str = "day"
    source_updated_at: str = ""

    def validate(self):
        if self.source not in SOURCES or self.kind not in ("news", "preprint", "journal_article"):
            raise CollectionError("invalid_record")
        if not self.title.strip() or not self.external_id or len(self.title) > 4000 or len(self.external_id) > 2000:
            raise CollectionError("invalid_record")
        safe_url(self.url)
        if len(self.arxiv_id) > 100 or len(self.summary) > 16000 or self.version < 0:
            raise CollectionError("invalid_record")
        if self.published_at:
            parse_time(self.published_at)
        if self.source_updated_at:
            parse_time(self.source_updated_at)
