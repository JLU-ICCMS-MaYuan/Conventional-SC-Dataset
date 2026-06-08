# Research Dossier

## Working Scene

The paper is best treated as a journal-style resource/database/software-system manuscript. The strongest available evidence supports an auditable superconductivity literature and physical-property curation platform, not a new physical mechanism, a new superconductor-discovery result, or a validated Tc-prediction model.

## Local Evidence Summary

The local draft and documentation support the following bounded claims:

| Claim Area | Evidence | Status |
|---|---|---|
| Element-centric entry point | `docs/business-overview.md`, `docs/article-draft.md`, `frontend/static/js/periodic_table.js`, `backend/api/compounds.py` | Supported. |
| Three search modes | `docs/article-draft.md`, compound/search code references | Supported as `only`, `combination`, and `contains`. |
| DOI-centered paper submission | `docs/business-paper-ingestion.md`, `backend/api/papers.py`, `backend/utils/doi_resolver.py` | Supported. |
| Multiple property rows per paper | `docs/article-draft.md`, `backend/models.py` | Supported. |
| Screenshot evidence | `docs/current-state-and-gaps.md`, `backend/models.py`, image handling utilities | Supported, with BLOB-storage scale caveat. |
| Review workflow | `docs/business-auth-and-review.md`, `backend/api/admin.py` | Supported. |
| Chart gating | `docs/business-visualization-and-tc-predict.md`, `docs/current-state-and-gaps.md` | Supported. |
| Experimental Tc prediction | `docs/business-visualization-and-tc-predict.md`, `docs/TC_PREDICTION_MODULE_ANALYSIS.md` | Supported only as experimental module; not a validated model contribution. |
| Community features | `docs/current-state-and-gaps.md` | Not supported. Do not claim likes/comments/bullet-screen/heat ranking. |

## Literature Landscape

Materials databases such as the Materials Project, OQMD, AFLOW, NOMAD, and OPTIMADE show mature paradigms for high-throughput materials data, FAIR sharing, and interoperability. Structure databases such as ICSD and COD supply the crystallographic backbone. Superconductivity-specific resources such as SuperCon, SuperCon2, 3DSC, ontology-based SuperCon knowledge-base work, HTSC-2025, and HPCSD occupy adjacent but distinct roles.

The gap for this paper is operational rather than purely scientific: researchers need to manage paper-level evidence, multiple physical-property records, screenshots, review state, and element-system browsing in one auditable workflow.

## Exemplar Learning

HPCSD is the strongest structural exemplar because it frames a database as infrastructure for fragmented data. Its abstract and introduction follow this logic:

| Move | HPCSD Pattern | Transfer To Conventional-SC-Dataset |
|---|---|---|
| Field need | High-pressure structures are important for emergent properties. | Superconductivity research depends on comparable literature and property records. |
| Bottleneck | High-pressure structural information is fragmented. | Superconductivity evidence is split across papers, formulas, conditions, screenshots, and manual notes. |
| Repository move | Traceable, pressure-resolved repository. | Auditable, element-centric literature and physical-parameter platform. |
| Scale evidence | 77,346 entries, 89 elements. | Local code scale and AI-screened database record counts. |
| Bounded contribution | Infrastructure for phase identification and ML potentials. | Infrastructure for curation, review, statistics, and future model-ready datasets. |

## Key Risks

| Risk | Mitigation |
|---|---|
| Overclaiming a prediction contribution | Keep Tc prediction in limitations/experimental module language. |
| Confusing main database and AI-screened database | State separate data files and scopes explicitly. |
| Treating citation shortlist as fully verified | Keep DOI checks in citation bank and mark lower-confidence entries. |
| Writing as a software manual rather than journal paper | Use database-paper logic: need, gap, repository design, validation/status, boundary. |
| Claiming community/social features | Exclude from current capabilities; mention only as future work if needed. |

## Recommended Manuscript Direction

Use the current LaTeX manuscript as the base after motivation confirmation. The best controlling structure is:

1. Data infrastructure need in superconductivity.
2. Database/resource landscape and remaining operational curation gap.
3. Conventional-SC-Dataset as an auditable element-centric workflow.
4. Data model and implementation.
5. Current repository/data status.
6. Comparison with adjacent databases/datasets.
7. Limitations and next steps.

