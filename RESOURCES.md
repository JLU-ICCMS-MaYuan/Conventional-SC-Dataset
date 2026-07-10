# SC-Wiki RAG Resources

## Knowledge

- `backend/api/rag.py`
  FastAPI boundary for RAG health, search, chat, streaming chat, paper/superconductor detail, and PDF upload.
- `backend/rag/service.py`
  Stable service facade that centralizes availability checks, errors, and calls into the RAG internals.
- `backend/rag/rag/engine.py`
  Main question-answering orchestration: intent extraction, structured retrieval, semantic retrieval, fusion prompt construction, LLM generation, and streaming events.
- `backend/rag/knowledge_graph.py`
  Knowledge-graph-style structured query layer over superconductors, papers, and physical-property records.
- `backend/rag/search/engine.py`
  Unified search router for formula, element-system, paper, and semantic search.
- `backend/rag/search/vector_search.py`
  Runtime semantic search over embedded paper chunks.
- `backend/rag/vectordb.py`
  ChromaDB wrapper for storing and querying paper chunks.
- `backend/rag/ingest/chunker.py`
  Text chunking logic for turning publications into retrieval units.
- `backend/rag/ingest/embedder.py`
  Embedding API wrapper used to vectorize text.
- `backend/rag/rag/prompts.py`
  Prompt templates and citation-format constraints used during answer generation.
- `frontend/src/lib/useStreamingChat.ts`
  Frontend SSE client and conversation state manager.
- `frontend/src/pages/RagPage.tsx`
  RAG user interface: conversation panel, streaming answer, evidence panel, and exploration mode.
- `tests/05_rag_question_answering/`
  Test suite for RAG service behavior, internal API behavior, import boundaries, and page availability.

## Wisdom (Communities)

- Project code review with future collaborators.
  Use for validating whether a RAG change preserves the scientific and engineering intent of SC-Wiki.

## Gaps

- No curated external RAG engineering references have been selected yet. Add them only when local code reading needs conceptual support.
