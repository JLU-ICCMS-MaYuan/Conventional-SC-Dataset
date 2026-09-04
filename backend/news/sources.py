"""固定官方端点适配；只接收元数据，不请求条目中的外链。"""
import calendar
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
import re
import time

import feedparser
import httpx

from .domain import (CollectionError, PUBLISHER_SOURCES, Record, canonical_url, iso, normalize_doi, parse_time, plain,
                     publisher_for_doi, relevance_evidence, relevant, safe_url)

ENDPOINTS = {
    "arxiv": "https://export.arxiv.org/api/query",
    "crossref": "https://api.crossref.org/works",
    "openalex": "https://api.openalex.org/works",
    "physorg": "https://phys.org/rss-feed/physics-news/superconductivity/",
    "google_news": "https://news.google.com/rss/search",
}
ENDPOINTS.update({source: ENDPOINTS["crossref"] for source in PUBLISHER_SOURCES})


class Transport:
    def __init__(self, client=None, sleep=time.sleep, contact=""):
        self.client = client or httpx.Client(
            timeout=httpx.Timeout(30, connect=10),
            limits=httpx.Limits(max_connections=1, max_keepalive_connections=1),
            follow_redirects=False,
            headers={"User-Agent": "SC-Wiki-News/1.0 (+https://github.com/JLU-ICCMS-MaYuan/SC-Wiki)" +
                     (f" mailto:{contact}" if contact else "")},
        )
        self.sleep = sleep
        self.guard = lambda: None

    def close(self):
        self.client.close()

    def get(self, source, url, params=None):
        if ENDPOINTS.get(source) != url:
            raise CollectionError("invalid_record")
        for attempt in range(3):
            self.guard()
            # 每次请求都等待，跨分页、重试及手动运行保持来源限速。
            self.sleep(3.1 if source == "arxiv" else 1.0)
            try:
                with self.client.stream("GET", url, params=params) as response:
                    if response.status_code == 429 or response.status_code >= 500:
                        code = "rate_limited" if response.status_code == 429 else "http_error"
                        if attempt == 2:
                            raise CollectionError(code)
                        retry = response.headers.get("Retry-After", "")
                        try:
                            delay = float(retry) if retry else 2 ** (attempt + 1)
                        except ValueError:
                            try:
                                delay = (parsedate_to_datetime(retry) - datetime.now(timezone.utc)).total_seconds()
                            except (ValueError, TypeError):
                                delay = 2 ** (attempt + 1)
                        if delay > 60:
                            raise CollectionError(code)
                        self.sleep(max(0, delay))
                        continue
                    if response.status_code != 200:
                        raise CollectionError("http_error")
                    content = bytearray()
                    for chunk in response.iter_bytes():
                        self.guard()
                        content.extend(chunk)
                        if len(content) > 5 * 1024 * 1024:
                            raise CollectionError("invalid_feed")
                    return bytes(content)
            except httpx.HTTPError as exc:
                if attempt == 2:
                    raise CollectionError("http_error") from exc
                self.sleep(2 ** (attempt + 1))
        raise CollectionError("http_error")


def feed(content):
    parsed = feedparser.parse(content)
    if parsed.get("bozo") or not parsed.get("version"):
        raise CollectionError("invalid_feed")
    return parsed


def rss_time(entry, name):
    value = entry.get(name + "_parsed")
    if not value:
        raise CollectionError("invalid_record")
    return iso(datetime.fromtimestamp(calendar.timegm(value), timezone.utc))


def crossref_date(item):
    for field in ("published", "published-online", "published-print"):
        parts = item.get(field, {}).get("date-parts")
        if parts and parts[0]:
            values = parts[0]
            try:
                date = datetime(values[0], values[1] if len(values) > 1 else 1,
                                values[2] if len(values) > 2 else 1, tzinfo=timezone.utc)
            except (ValueError, TypeError):
                raise CollectionError("invalid_record")
            return iso(date), ("year", "month", "day")[min(len(values), 3) - 1]
    return "", "unknown"


class Sources:
    def __init__(self, transport=None, max_pages=100, contact=""):
        self.transport = transport or Transport(contact=contact)
        self.max_pages = max_pages
        self.contact = contact

    def fetch(self, source, since, until):
        self.fetched = 0
        if source not in ENDPOINTS:
            raise CollectionError("invalid_record")
        result = self.publisher(source, since, until) if source in PUBLISHER_SOURCES else getattr(self, source)(since, until)
        for row in result:
            row.validate()
        return result

    def arxiv(self, since, until):
        result = []
        for page in range(self.max_pages):
            parsed = feed(self.transport.get("arxiv", ENDPOINTS["arxiv"], {
                "search_query": "cat:cond-mat.supr-con", "sortBy": "lastUpdatedDate",
                "sortOrder": "descending", "start": page * 100, "max_results": 100,
            }))
            try:
                total = int(parsed.feed["opensearch_totalresults"])
            except (KeyError, ValueError, TypeError):
                raise CollectionError("invalid_feed")
            if not parsed.entries and page * 100 < total:
                raise CollectionError("invalid_feed")
            self.fetched += len(parsed.entries)
            for entry in parsed.entries:
                match = re.fullmatch(r"https?://arxiv.org/abs/((?:\d{4}\.\d{4,5}|[a-z.-]+/\d{7}))(?:v(\d+))?", entry.get("id", ""))
                if not match:
                    raise CollectionError("invalid_record")
                updated = rss_time(entry, "updated")
                if parse_time(updated) < since:
                    return result
                if parse_time(updated) > until:
                    continue
                if not any(tag.get("term") == "cond-mat.supr-con" for tag in entry.get("tags", [])):
                    continue
                aid, version = match.groups()
                result.append(Record(
                    source="arxiv", external_id=aid, kind="preprint",
                    title=plain(entry.get("title", ""), 4000), url="https://arxiv.org/abs/" + aid,
                    summary=plain(entry.get("summary", "")), summary_source="arxiv",
                    doi=normalize_doi(entry.get("arxiv_doi", "")), arxiv_id=aid, version=int(version or 1),
                    authors=[plain(a.get("name", ""), 120) for a in entry.get("authors", [])][:100],
                    published_at=rss_time(entry, "published"), source_updated_at=updated,
                ))
            if (page + 1) * 100 >= total:
                return result
            if len(parsed.entries) < 100:
                raise CollectionError("invalid_feed")
        raise CollectionError("page_limit")

    def crossref(self, since, until):
        return self._crossref("crossref", since, until)

    def publisher(self, source, since, until):
        return self._crossref(source, since, until, PUBLISHER_SOURCES[source])

    def _crossref(self, source, since, until, prefix=""):
        result, cursor, previous_ids = [], "*", None
        for _ in range(self.max_pages):
            filters = f"type:journal-article,from-index-date:{since.date()},until-index-date:{until.date()}"
            if prefix:
                filters += ",prefix:" + prefix
            params = {"query": "superconduct", "filter": filters,
                "rows": 100, "cursor": cursor}
            if self.contact:
                params["mailto"] = self.contact
            try:
                body = json.loads(self.transport.get(source, ENDPOINTS[source], params))["message"]
                items = body["items"]
                if not isinstance(items, list):
                    raise ValueError("items")
            except (KeyError, ValueError, TypeError):
                raise CollectionError("invalid_feed")
            self.fetched += len(items)
            ids = [item.get("DOI") for item in items]
            if ids and ids == previous_ids:
                raise CollectionError("invalid_feed")
            previous_ids = ids
            for item in items:
                title = plain(" ".join(item.get("title", [])), 4000)
                if not title:
                    raise CollectionError("invalid_record")
                if item.get("type") != "journal-article" or not relevant(title):
                    continue
                doi = normalize_doi(item.get("DOI", ""))
                if not doi:
                    raise CollectionError("invalid_record")
                published, precision = crossref_date(item)
                updated = item.get("indexed", {}).get("date-time", "")
                if updated:
                    updated = iso(parse_time(updated))
                evidence = relevance_evidence(title)
                result.append(Record(
                    source=source, external_id=doi, kind="journal_article",
                    title=title, doi=doi, url="https://doi.org/" + doi,
                    authors=[plain(" ".join(filter(None, [a.get("given"), a.get("family"), a.get("name")])), 120)
                             for a in item.get("author", [])][:100],
                    journal=plain(" ".join(item.get("container-title", [])), 1000),
                    published_at=published, date_precision=precision, source_updated_at=updated,
                    content_type="peer_reviewed", display_kind="journal_article", discovery_source="crossref",
                    original_source=publisher_for_doi(doi) or (source if source in PUBLISHER_SOURCES else ""), relevance_evidence=evidence,
                ))
            if len(items) < 100:
                return result
            next_cursor = body.get("next-cursor")
            if not next_cursor:
                raise CollectionError("invalid_feed")
            cursor = next_cursor
        raise CollectionError("page_limit")

    def openalex(self, since, until):
        result, cursor = [], "*"
        for _ in range(self.max_pages):
            params = {
                "search": "superconduct",
                "filter": f"from_publication_date:{since.date()},to_publication_date:{until.date()}",
                "per-page": 100,
                "cursor": cursor,
            }
            try:
                body = json.loads(self.transport.get("openalex", ENDPOINTS["openalex"], params))
                items = body["results"]
                if not isinstance(items, list):
                    raise ValueError("results")
            except (KeyError, ValueError, TypeError):
                raise CollectionError("invalid_feed")
            self.fetched += len(items)
            for item in items:
                title = plain(item.get("title", ""), 4000)
                abstract = openalex_abstract(item.get("abstract_inverted_index"))
                evidence = relevance_evidence(title, abstract)
                if not title or not evidence:
                    continue
                doi = normalize_doi(item.get("doi", ""))
                location = item.get("primary_location") or {}
                url = safe_url(location.get("landing_page_url") or ("https://doi.org/" + doi if doi else item.get("id", "")))
                published = item.get("publication_date", "")
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", published):
                    raise CollectionError("invalid_record")
                updated = item.get("updated_date", "")
                if updated:
                    updated = iso(parse_time(_openalex_timestamp(updated)))
                authors = [plain((row.get("author") or {}).get("display_name", ""), 120)
                           for row in item.get("authorships", [])][:100]
                journal = plain(((location.get("source") or {}).get("display_name", "")), 1000)
                external_id = str(item.get("id", "")).rsplit("/", 1)[-1]
                if not external_id:
                    raise CollectionError("invalid_record")
                result.append(Record(
                    source="openalex", external_id=external_id, kind="journal_article", title=title, url=url,
                    summary=abstract, summary_source="openalex" if abstract else "", doi=doi, authors=authors,
                    journal=journal, published_at=published + "T00:00:00Z", source_updated_at=updated,
                    content_type="peer_reviewed", display_kind="journal_article", discovery_source="openalex",
                    original_source=publisher_for_doi(doi), relevance_evidence=evidence,
                ))
            next_cursor = (body.get("meta") or {}).get("next_cursor")
            if not next_cursor or not items:
                return result
            cursor = next_cursor
        raise CollectionError("page_limit")

    def physorg(self, since, until):
        parsed = feed(self.transport.get("physorg", ENDPOINTS["physorg"]))
        self.fetched = len(parsed.entries)
        result = []
        for entry in parsed.entries:
            published = rss_time(entry, "published")
            if not since <= parse_time(published) <= until:
                continue
            url = safe_url(entry.get("link", ""))
            # 官方专栏为范围保证；外链仍限制在官方新闻站点。
            if httpx.URL(url).host != "phys.org":
                raise CollectionError("invalid_record")
            title = entry.get("title", "").strip()
            result.append(Record(
                source="physorg", external_id=canonical_url(url), kind="news", title=title,
                url=url, summary=plain(entry.get("summary", "")), summary_source="physorg",
                published_at=published, source_updated_at=published,
                content_type="research_report", display_kind="journal_article", discovery_source="physorg",
                original_source="physorg", relevance_evidence=relevance_evidence(title, entry.get("summary", "")),
            ))
        return result

    def google_news(self, since, until):
        parsed = feed(self.transport.get("google_news", ENDPOINTS["google_news"], {
            "q": "superconduct OR 超导", "hl": "en-US", "gl": "US", "ceid": "US:en",
        }))
        self.fetched = len(parsed.entries)
        result = []
        for entry in parsed.entries:
            title = plain(entry.get("title", ""), 4000)
            summary = plain(entry.get("summary", ""))
            evidence = relevance_evidence(title, summary)
            if not evidence:
                continue
            published = rss_time(entry, "published")
            if not since <= parse_time(published) <= until:
                continue
            url = safe_url(entry.get("link", ""))
            result.append(Record(
                source="google_news", external_id=canonical_url(url), kind="news", title=title, url=url,
                summary=summary, summary_source="google_news", published_at=published, source_updated_at=published,
                content_type="social_industry", display_kind="news", discovery_source="google_news",
                original_source="", relevance_evidence=evidence,
            ))
        return result


def openalex_abstract(index):
    if not isinstance(index, dict):
        return ""
    words = []
    for word, positions in index.items():
        if not isinstance(positions, list):
            return ""
        words.extend((position, word) for position in positions if isinstance(position, int) and position >= 0)
    return " ".join(word for _, word in sorted(words))


def _openalex_timestamp(value):
    """OpenAlex 的 updated_date 文档语义为 UTC，但有时省略时区后缀。"""
    value = str(value or "").strip()
    if value and not re.search(r"(?:Z|[+-]\d{2}:\d{2})$", value, re.I):
        value += "Z"
    return value
