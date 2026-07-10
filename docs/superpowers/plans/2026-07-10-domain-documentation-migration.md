# Domain Documentation Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:subagent-driven-development` (recommended) or
> `superpowers:executing-plans` to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the seven numbered, mixed-status feature-document directories
with code- and test-grounded domain documentation that is the authoritative
description of current SC-Wiki behavior.

**Architecture:** `docs/domains/` describes stable business and module
boundaries; `docs/operations/` describes verified runtime constraints; the
Memory Bank links to both but does not duplicate their details. Historical
numbered feature documents are deleted after their confirmed facts have been
absorbed or their unimplemented ideas have been recorded as GitHub Issues.

**Tech Stack:** Markdown, GitHub Issues, FastAPI, React, SQLAlchemy, Alembic,
RAG/ChromaDB.

## Global Constraints

- Only write behavior supported by code, tests, configuration, or a linked
  GitHub Issue; do not turn planned behavior into current fact.
- Preserve no copies of `docs/01-*` through `docs/07-*` after migration.
- Use GitHub `type:idea` for uncommitted concepts and `type:doc-debt` for
  verified but not-yet-documented facts.
- Each domain page must link its code entry points, key tests, related
  operations/decision documents, and known gaps.
- No business code, migrations, dependencies, or existing uncommitted frontend
  files are changed by this migration.

---

## Reconnaissance Map

| File | Role | Read next? | Reason | Source |
| --- | --- | --- | --- | --- |
| `backend/main.py` | FastAPI composition root | Yes | Determines active routers and SPA behavior. | Code explorer |
| `backend/models.py` | Main catalog model | Yes | Defines persisted business entities. | Code explorer |
| `backend/api/admin.py` | Review governance API | Yes | Verifies review and visibility facts. | Code explorer |
| `backend/api/structures.py` | Structure lifecycle API | Yes | Verifies upload, review, and representative selection. | Code explorer |
| `backend/api/rag.py` | RAG HTTP boundary | Yes | Verifies current RAG endpoints and access rules. | Code explorer |
| `backend/rag/rag/engine.py` | RAG orchestration | Yes | Verifies intent, KG, vector, and streaming flow. | Code explorer |
| `backend/api/tc_predict.py` | Tc estimation API | Yes | Verifies prediction inputs and non-persistence. | Code explorer |
| `frontend/src/App.tsx` | User-facing route map | Yes | Separates exposed pages from planned UI. | Code explorer |
| `start.sh` | Operational startup path | Yes | Verifies migration, seed, and Uvicorn sequence. | Operations explorer |
| `backend/rag/config.py` | RAG operational configuration | Yes | Verifies separate data assets and environment variables. | Operations explorer |
| `docs/01-*` ... `docs/07-*` | Historical mixed-status source | Yes | Extract facts, then delete all 28 Markdown files. | Docs explorer |

## Task 1: Establish domain and operations indexes

**Files:**
- Create: `docs/domains/README.md`
- Create: `docs/operations/README.md`
- Modify: `docs/README.md`
- Modify: `docs/memory/README.md`

- [x] Define `docs/domains/` as the sole current-fact layer for business and
  module behavior.
- [x] Define `docs/operations/` as the sole current-fact layer for deployment,
  persistence, environment, imports, and recovery.
- [x] Add links from the documentation root and Memory Bank without duplicating
  detailed content.
- [x] Verify all Markdown links introduced by these indexes resolve locally.

## Task 2: Backfill core catalog, discovery, and contribution domains

**Files:**
- Create: `docs/domains/core-superconductor-catalog.md`
- Create: `docs/domains/search-and-external-catalogs.md`
- Create: `docs/domains/contribution-upload-and-review.md`
- Create: `docs/domains/crystal-structure-lifecycle.md`

**Evidence:** `backend/models.py`, `backend/api/papers.py`,
`backend/api/admin.py`, `backend/api/structures.py`,
`backend/services/structure_storage.py`, `frontend/src/App.tsx`, and related
tests under `tests/01_*`, `tests/02_*`, and `tests/03_*`.

- [x] Record entities, module boundaries, public behavior, invariants, code
  entry points, tests, and known gaps for each domain.
- [x] State that the ordinary `CompoundPage` paper-upload call is not a
  completed end-to-end workflow; do not represent it as available behavior.
- [x] Record structure approval's representative-selection rule and its
  API/test evidence.
- [ ] Convert unimplemented unified uploads, bulk-cleaning, and unverified UI
  workflows into linked GitHub ideas or document debt rather than current facts.

## Task 3: Backfill RAG, knowledge relations, prediction, and metrics domains

**Files:**
- Create: `docs/domains/rag-and-knowledge-graph.md`
- Create: `docs/domains/tc-prediction.md`
- Create: `docs/domains/researcher-contribution-metrics.md`

**Evidence:** `backend/api/rag.py`, `backend/rag/service.py`,
`backend/rag/rag/engine.py`, `backend/rag/knowledge_graph.py`,
`backend/rag/ingest/pipeline.py`, `backend/api/tc_predict.py`, and related
tests under `tests/04_*` through `tests/07_*`.

- [x] Describe the knowledge graph only as an internal RAG query projection,
  not as a public standalone graph feature.
- [x] Record RAG's separate database/vector assets and the PDF ingestion
  boundary; explicitly flag unverified authentication and review integration as
  gaps.
- [x] Record Tc estimation as immediate CONTCAR/PDOS feature computation with
  no persisted prediction history.
- [x] Rename the historical community/forum concept to the verified
  contribution-metrics domain; do not assert forum capability.

## Task 4: Backfill runtime operations

**Files:**
- Create: `docs/operations/runtime-and-deployment.md`
- Create: `docs/operations/data-and-rag-assets.md`
- Create: `docs/operations/import-and-recovery.md`
- Modify: `docs/deploy.md`

**Evidence:** `start.sh`, `Procfile`, `backend/main.py`, `backend/database.py`,
`alembic/env.py`, `backend/init_db.py`, `backend/rag/config.py`,
`backend/import_data.py`, `backend/rag/ingest/*.py`, `.gitignore`, and
`docs/deploy.md`.

- [x] Make `start.sh` the documented full startup path and document the
  limitations of direct `Procfile` Uvicorn startup.
- [x] Document the main database, RAG relational database, and Chroma assets as
  separate persistence responsibilities, including relevant environment
  variables and persistence requirements.
- [x] Document destructive imports and collection rebuilds with backup,
  validation, recovery, and external API-cost preconditions.
- [x] Remove historical deployment claims that reference missing `.env.example`
  or treat missing initialization as an acceptable runtime path.

## Task 5: Record verified documentation debt and delete legacy documents

**Files:**
- Modify: `docs/governance/issue-types.md` only if labels or closing criteria
  need clarification
- Delete: `docs/01-decentralized-uploading/`
- Delete: `docs/02-maintenance-and-verification/`
- Delete: `docs/03-data-search-and-database-discovery/`
- Delete: `docs/04-superconductivity-knowledge-graph/`
- Delete: `docs/05-rag-question-answering/`
- Delete: `docs/06-ai-assisted-tc-estimation/`
- Delete: `docs/07-researcher-community-forum/`
- Modify: `docs/README.md`

- [ ] Create or link GitHub `type:doc-debt` Issues for factual gaps discovered
  during evidence review, including unresolved main/RAG synchronization and
  incomplete frontend build inputs.
- [ ] Create or link GitHub `type:idea` Issues for forum, standalone graph, and
  other historical planned capabilities that should remain discoverable.
- [x] Remove all 28 old Markdown files and numbered directories only after
  their verified facts are present in `docs/domains/` or `docs/operations/`.
- [x] Replace the seven-module table in `docs/README.md` with the new domain and
  operations navigation.

## Task 6: Verify the migration

**Files:**
- Verify: `docs/**/*.md`, `AGENTS.md`

- [x] Run `git diff --check`.
- [x] Verify no Markdown links refer to the deleted `docs/01-*` through
  `docs/07-*` paths.
- [x] Verify each domain page includes evidence paths and known gaps.
- [ ] Run targeted existing tests only for documented behavior that was
  revalidated during the migration; report any unrelated test failures without
  changing code.
- [x] Confirm `git status --short` shows only the approved documentation and
  existing user changes; do not stage or commit.

## Execution Handoff

Implementation requires one explicit confirmation because Task 5 deletes 28
existing Markdown files and their seven directories. After confirmation, use
`superpowers:executing-plans` for staged implementation and verify each task
before continuing.

## Execution Notes

- GitHub Issue creation was outside the confirmed migration scope. The two
  unchecked Issue-conversion tasks remain follow-up work.
- The `sc-wiki` Conda baseline run used `PYTHONPATH=.` and produced 125 passed,
  1 failed, and 7 skipped tests. The failed RAG page test expects
  `frontend_build/index.html`, while the committed static asset is under
  `frontend/static/`; no business code was changed to address this pre-existing
  deployment mismatch.
