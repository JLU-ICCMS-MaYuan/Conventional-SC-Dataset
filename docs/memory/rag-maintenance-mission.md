# Mission: Extend SC-Wiki RAG

## Why
Learn how the SC-Wiki RAG subsystem is built so the user can modify, debug, and extend it independently in future development work.

## Success looks like
- Trace a user question from the `/api/rag` endpoint through retrieval, prompt construction, generation, and frontend streaming.
- Modify retrieval behavior without breaking structured-data queries or citation grounding.
- Add or adjust RAG features with targeted tests around the changed path.

## Constraints
- Teach from the actual SC-Wiki codebase first, using external RAG concepts only when they clarify the local implementation.
- Keep each lesson narrow and tied to code the user can inspect immediately.

## Out of scope
- Building a new RAG framework from scratch.
- Deep theory of language models beyond what is needed to maintain this repository.
