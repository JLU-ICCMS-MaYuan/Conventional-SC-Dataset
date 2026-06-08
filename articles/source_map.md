# Source Map

| Source | Type | Role In PaperSpine Workflow | Trust Level | Notes |
|---|---|---|---|---|
| `docs/article-draft.md` | Existing Chinese draft and planning note | Primary draft input, claim boundary, paper positioning, figure/table plan | High for author intent and project claims | Contains current title, abstract, introduction, system design, workflow, data status, discussion, conclusion, claim-evidence map, and figure ideas. |
| `articles/raw/literature-shortlist.md` | Literature shortlist | Initial citation seed for materials, structure, and superconductivity database context | Medium until DOI-level verification | Contains 13 representative database references and short relevance notes. |
| `articles/raw/*.pdf` | Local papers and reports | Background and citation support for superconductivity data, ML, hydrides, and database context | Medium to high depending on extraction quality | Use as local-first literature corpus. |
| `docs/business-*.md` | Project documentation | Evidence for platform workflows and implemented capability boundaries | High for system behavior | Supports ingestion, search/discovery, auth/review, visualization, and Tc prediction scope. |
| `docs/current-state-and-gaps.md` | Project state/gap note | Boundary control and future-work evidence | High for implementation limits | Useful for preventing inflated claims. |
| `docs/TC_PREDICTION_MODULE_ANALYSIS.md` | Module analysis | Evidence for treating Tc prediction as experimental rather than core contribution | High for boundary claims | Should constrain algorithmic claims. |
| `articles/final_paper/main.tex` | Existing LaTeX manuscript | Existing final-structure input and possible source for LaTeX output | High for current manuscript state | Must be checked before overwriting or replacing. |
| `articles/final_paper/main.pdf` | Existing PDF manuscript | Verification artifact for current manuscript | Medium | Useful to compare compiled output if needed. |

