"""采集事务和幂等合并；此模块只写 news_feed_* 三表。"""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import logging
import uuid

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from .domain import CollectionError, SOURCES, iso, parse_time
from .models import NewsFeedIdentity, NewsFeedItem, NewsFeedSource

log = logging.getLogger(__name__)


def identity_key(value):
    return sha256(value.encode("utf-8")).hexdigest()


def _links(*groups):
    links = {}
    for group in groups:
        for link in group:
            links[(link["source"], link.get("role", "discovery"))] = link
    return json.dumps(list(links.values()), ensure_ascii=False)


def upsert(db, record, now):
    record.validate()
    keys = [identity_key(record.source + ":" + record.external_id)]
    if record.doi and record.kind != "news":
        keys.append(identity_key("doi:" + record.doi))
    identities = db.scalars(select(NewsFeedIdentity).where(NewsFeedIdentity.key.in_(keys))).all()
    ids = {identity.item_id for identity in identities}
    matches = [db.get(NewsFeedItem, id_) for id_ in ids]
    # 确定 DOI 连接既有期刊和预印本时，优先保留期刊元数据。
    matches.sort(key=lambda row: (row.kind != "journal_article", row.first_seen_at, row.id))
    item = matches[0] if matches else NewsFeedItem(
        id=uuid.uuid4().hex, kind=record.kind, title=record.title, source=record.source,
        url=record.url, summary="", summary_source="", doi="", arxiv_id="", version=0,
        authors="[]", journal="", links="[]", published_at="", date_precision="unknown",
        source_updated_at="", first_seen_at=now, last_seen_at=now,
        content_type="", display_kind="", discovery_source="", original_source="", relevance_evidence="",
    )
    if not matches:
        db.add(item)
        db.flush()
    for other in matches[1:]:
        if not item.summary and other.summary:
            item.summary, item.summary_source = other.summary, other.summary_source
        item.arxiv_id = item.arxiv_id or other.arxiv_id
        item.version = max(item.version, other.version)
        item.links = _links(json.loads(other.links), json.loads(item.links))
        item.first_seen_at = min(item.first_seen_at, other.first_seen_at)
        db.execute(update(NewsFeedIdentity).where(NewsFeedIdentity.item_id == other.id).values(item_id=item.id))
        db.delete(other)
        db.flush()
    stale = record.source == "arxiv" and record.version < item.version
    if not stale and (item.kind != "journal_article" or record.kind == "journal_article"):
        # 来源更新时间相同仍允许补全 DOI；更旧的同源元数据不回退主字段。
        if record.source != item.source or record.source_updated_at >= item.source_updated_at:
            for name in ("kind", "title", "source", "url", "published_at", "date_precision", "journal", "source_updated_at",
                         "content_type", "display_kind", "discovery_source", "original_source", "relevance_evidence"):
                setattr(item, name, getattr(record, name))
            item.authors = json.dumps(record.authors, ensure_ascii=False)
    if record.summary and not stale:
        item.summary, item.summary_source = record.summary, record.summary_source
    item.doi = record.doi or item.doi
    item.arxiv_id = record.arxiv_id or item.arxiv_id
    item.version = max(record.version, item.version)
    item.display_kind = record.display_kind or record.kind
    item.content_type = record.content_type or item.content_type
    item.discovery_source = record.discovery_source or record.source
    item.original_source = record.original_source or item.original_source
    item.relevance_evidence = record.relevance_evidence or item.relevance_evidence
    item.links = _links(json.loads(item.links), [
        {"source": record.discovery_source or record.source, "url": record.url, "role": "discovery"},
        *([{"source": record.original_source, "url": record.url, "role": "original"}] if record.original_source else []),
    ])
    item.last_seen_at = now
    for key in keys:
        existing = db.get(NewsFeedIdentity, key)
        if existing:
            existing.item_id = item.id
        else:
            db.add(NewsFeedIdentity(key=key, item_id=item.id))
    db.flush()
    return item


def collect_source(engine, source, sources, now=None, initial_days=7, before_commit=None):
    if source not in SOURCES:
        raise ValueError("unknown source")
    started = now or datetime.now(timezone.utc)
    with Session(engine) as db, db.begin():
        state = db.get(NewsFeedSource, source)
        if state is None:
            state = NewsFeedSource(source=source)
            db.add(state)
        previous = state.last_success_at
        since = parse_time(previous) - timedelta(days=2) if previous else started - timedelta(days=initial_days)
        state.status, state.last_started_at, state.error_code = "running", iso(started), ""
    try:
        records = sources.fetch(source, since, started)
        with Session(engine) as db, db.begin():
            if before_commit:
                before_commit()
            for record in records:
                if record.source != source:
                    raise CollectionError("invalid_record")
                upsert(db, record, iso(started))
            state = db.get(NewsFeedSource, source)
            state.status, state.error_code = "success", ""
            state.last_success_at = iso(started)
            state.last_finished_at = iso(now or datetime.now(timezone.utc))
            state.fetched = getattr(sources, "fetched", len(records))
            state.accepted = len(records)
            if before_commit:
                before_commit()
        return True
    except Exception as exc:
        code = str(exc) if isinstance(exc, CollectionError) else "collection_error"
        with Session(engine) as db, db.begin():
            state = db.get(NewsFeedSource, source)
            state.status, state.error_code = "failed", code
            state.last_finished_at = iso(now or datetime.now(timezone.utc))
        # 不输出异常原文：HTTP/数据库异常可能含 URL、凭证和响应正文。
        log.warning("news source=%s error=%s exception=%s", source, code, type(exc).__name__)
        return False
