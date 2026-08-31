import json
from dataclasses import replace
from datetime import datetime, timezone

import httpx
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.news.domain import Record, CollectionError, iso, normalize_doi, relevant
from backend.news.models import NewsFeedItem, NewsFeedIdentity, NewsFeedSource
from backend.news.sources import Sources, Transport
from backend.news.service import collect_source

NOW = datetime(2026, 8, 31, tzinfo=timezone.utc)
ATOM = b'''<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"
 xmlns:arxiv="http://arxiv.org/schemas/atom" xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">
 <opensearch:totalResults>1</opensearch:totalResults><entry>
 <id>http://arxiv.org/abs/2608.12345v2</id><title>Superconductivity in a test material</title>
 <summary>Test abstract</summary><published>2026-08-27T10:00:00Z</published>
 <updated>2026-08-30T10:00:00Z</updated><author><name>Test Author</name></author>
 <arxiv:doi>10.1234/test</arxiv:doi><category term="cond-mat.supr-con"/>
 </entry></feed>'''
RSS = b'''<rss version="2.0"><channel><title>Superconductivity</title><item>
 <title>Original superconductivity headline</title><link>https://phys.org/news/2026-08-test.html</link>
 <description>&lt;p&gt;Test excerpt&lt;/p&gt;</description>
 <pubDate>Sun, 30 Aug 2026 10:00:00 GMT</pubDate></item></channel></rss>'''
CROSSREF = {"message": {"items": [{"DOI": "10.1234/TEST", "type": "journal-article",
 "title": ["Superconductivity in a test material"], "author": [{"given": "Test", "family": "Author"}],
 "container-title": ["Test Journal"], "published": {"date-parts": [[2026, 8]]},
 "indexed": {"date-time": "2026-08-30T10:00:00Z"}, "abstract": "Do not republish"}],
 "next-cursor": "next"}}


@pytest.fixture
def engine():
    db = create_engine("sqlite:///:memory:")
    for table in (NewsFeedItem.__table__, NewsFeedIdentity.__table__, NewsFeedSource.__table__):
        table.create(db)
    yield db
    db.dispose()


def transport(handler):
    return Transport(httpx.Client(transport=httpx.MockTransport(handler)), sleep=lambda _: None)


def record():
    return Record(source="arxiv", external_id="2608.12345", kind="preprint",
                  title="Superconducting test", url="https://arxiv.org/abs/2608.12345",
                  published_at="2026-08-27T10:00:00Z", source_updated_at=iso(NOW),
                  summary="Test abstract", summary_source="arxiv", arxiv_id="2608.12345",
                  version=1)


class FixedSources:
    def __init__(self, values):
        self.values = values

    def fetch(self, source, since, until):
        value = self.values[source]
        if isinstance(value, Exception):
            raise value
        return value


def test_normalization_and_filter():
    assert normalize_doi("https://doi.org/10.1234/ABC") == "10.1234/abc"
    assert normalize_doi("not-a-doi") == ""
    assert relevant("Josephson junctions")
    assert relevant("超导材料")
    assert not relevant("Quantum computing and Tc weather")


def test_three_sources_and_rights():
    def handler(request):
        if request.url.host == "export.arxiv.org":
            return httpx.Response(200, content=ATOM)
        if request.url.host == "api.crossref.org":
            return httpx.Response(200, json=CROSSREF)
        return httpx.Response(200, content=RSS)
    src = Sources(transport(handler))
    since = datetime(2026, 8, 24, tzinfo=timezone.utc)
    arxiv = src.fetch("arxiv", since, NOW)[0]
    crossref = src.fetch("crossref", since, NOW)[0]
    physorg = src.fetch("physorg", since, NOW)[0]
    assert (arxiv.external_id, arxiv.version, arxiv.doi) == ("2608.12345", 2, "10.1234/test")
    assert crossref.summary == ""
    assert crossref.date_precision == "month"
    assert crossref.authors == ["Test Author"]
    assert physorg.title == "Original superconductivity headline"
    assert physorg.summary == "Test excerpt"


@pytest.mark.parametrize("payload", [b"<html>blocked</html>", b"<rss><channel>", b""])
def test_bad_feed_is_failure(payload):
    src = Sources(transport(lambda _: httpx.Response(200, content=payload)))
    with pytest.raises(CollectionError):
        src.fetch("physorg", NOW, NOW)


def test_rate_limit_retries_are_bounded():
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(429, headers={"Retry-After": "0"})
    with pytest.raises(CollectionError, match="rate_limited"):
        transport(handler).get("arxiv", "https://export.arxiv.org/api/query")
    assert len(calls) == 3


def test_dedupe_version_and_late_doi_merge(engine):
    a = record()
    c = replace(a, source="crossref", external_id="10.1234/test", doi="10.1234/test",
                kind="journal_article", url="https://doi.org/10.1234/test", summary="",
                summary_source="", arxiv_id="", version=0)
    for src, rows in [("arxiv", [a]), ("arxiv", [a]), ("crossref", [c]),
                      ("arxiv", [replace(a, doi=c.doi, version=2)])]:
        assert collect_source(engine, src, FixedSources({src: rows}), NOW)
    with Session(engine) as db:
        items = db.scalars(select(NewsFeedItem)).all()
        assert len(items) == 1
        item = items[0]
        assert item.kind == "journal_article"
        assert item.version == 2
        assert item.summary_source == "arxiv"
        assert len(json.loads(item.links)) == 2
        assert item.first_seen_at == iso(NOW)
        assert len(db.scalars(select(NewsFeedIdentity)).all()) == 3


def test_failure_preserves_watermark_and_other_source_runs(engine):
    assert collect_source(engine, "arxiv", FixedSources({"arxiv": [record()]}), NOW)
    later = datetime(2026, 9, 1, tzinfo=timezone.utc)
    assert not collect_source(engine, "arxiv", FixedSources({"arxiv": CollectionError("http_error")}), later)
    assert collect_source(engine, "physorg", FixedSources({"physorg": []}), later)
    with Session(engine) as db:
        state = db.get(NewsFeedSource, "arxiv")
        assert state.last_success_at == iso(NOW)
        assert state.status == "failed"
        assert state.error_code == "http_error"
        assert db.get(NewsFeedSource, "physorg").status == "success"
        assert len(db.scalars(select(NewsFeedItem)).all()) == 1


def test_transaction_rolls_back_partial_batch(engine):
    bad = replace(record(), external_id="bad", title="")
    assert not collect_source(engine, "arxiv", FixedSources({"arxiv": [record(), bad]}), NOW)
    with Session(engine) as db:
        assert db.scalars(select(NewsFeedItem)).all() == []
        assert db.get(NewsFeedSource, "arxiv").last_success_at == ""


def test_older_version_does_not_replace_newer_abstract(engine):
    a = replace(record(), version=2, summary="New abstract")
    assert collect_source(engine, "arxiv", FixedSources({"arxiv": [a]}), NOW)
    assert collect_source(engine, "arxiv", FixedSources({"arxiv": [record()]}), NOW)
    with Session(engine) as db:
        item = db.scalars(select(NewsFeedItem)).one()
        assert item.version == 2 and item.summary == "New abstract"


def test_missing_title_and_unsafe_url_fail_closed():
    for a in [replace(record(), title=""), replace(record(), url="javascript:alert(1)")]:
        with pytest.raises(CollectionError, match="invalid_record"):
            a.validate()


def test_pagination_limit_is_not_success():
    items = [dict(CROSSREF["message"]["items"][0], DOI=f"10.1234/{i}") for i in range(100)]
    src = Sources(transport(lambda _: httpx.Response(200, json={"message": {"items": items, "next-cursor": "more"}})), max_pages=1)
    with pytest.raises(CollectionError, match="page_limit"):
        src.fetch("crossref", NOW, NOW)


def test_crossref_cursor_and_filtered_count():
    seen = []
    def handler(request):
        seen.append(request.url.params["cursor"])
        if len(seen) == 1:
            items = [dict(CROSSREF["message"]["items"][0], DOI=f"10.1234/{i}", title=["Unrelated weather report"]) for i in range(100)]
        else:
            items = CROSSREF["message"]["items"]
        return httpx.Response(200, json={"message": {"items": items, "next-cursor": "cursor-token"}})
    src = Sources(transport(handler))
    assert len(src.fetch("crossref", NOW, NOW)) == 1
    assert src.fetched == 101 and seen == ["*", "cursor-token"]


def test_http_error_retry_after_and_body_limits():
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(503, headers={"Retry-After": "3600"})
    with pytest.raises(CollectionError, match="http_error"):
        transport(handler).get("arxiv", "https://export.arxiv.org/api/query")
    assert len(calls) == 1
    with pytest.raises(CollectionError, match="invalid_feed"):
        transport(lambda _: httpx.Response(200, content=b"x" * (5 * 1024 * 1024 + 1))).get("arxiv", "https://export.arxiv.org/api/query")


def test_lost_collection_lock_rolls_back(engine):
    count = 0
    def guard():
        nonlocal count
        count += 1
        if count == 2:
            raise CollectionError("collection_timeout")
    assert not collect_source(engine, "arxiv", FixedSources({"arxiv": [record()]}), NOW, before_commit=guard)
    with Session(engine) as db:
        assert db.scalars(select(NewsFeedItem)).all() == []
