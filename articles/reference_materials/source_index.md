# Source Index

## Local Draft And Manuscript Sources

| ID | Path | Type | Use |
|---|---|---|---|
| D1 | `docs/article-draft.md` | Chinese planning draft | Primary author-intent source for positioning, evidence boundaries, section plan, and figure/table ideas. |
| D2 | `articles/final_paper/main.tex` | Existing English LaTeX manuscript | Closest current manuscript. Use as the base for later PaperSpine build/rewrite steps after motivation is confirmed. |
| D3 | `articles/final_paper/main.pdf` | Existing compiled PDF | Current output check artifact. |
| D4 | `articles/comments_response.md` | Comments | Review for unresolved author notes before final writing. |

## Local Project Evidence

| ID | Path | Type | Use |
|---|---|---|---|
| P1 | `docs/business-overview.md` | System documentation | Platform role model, module boundaries, API/page mapping, and capability limits. |
| P2 | `docs/business-search-and-discovery.md` | System documentation | Element search modes and discovery workflow evidence. |
| P3 | `docs/business-paper-ingestion.md` | System documentation | DOI submission, upload, screenshots, and batch ingestion evidence. |
| P4 | `docs/business-auth-and-review.md` | System documentation | User/admin/superadmin review workflow evidence. |
| P5 | `docs/business-visualization-and-tc-predict.md` | System documentation | Chart and experimental Tc-prediction scope. |
| P6 | `docs/current-state-and-gaps.md` | Gap analysis | Implemented/unimplemented feature boundaries and next-step priorities. |
| P7 | `backend/models.py` | Code | Database schema evidence for elements, compounds, papers, paper data, paper images, and users. |
| P8 | `backend/api/*.py` | Code | Route and workflow evidence. |
| P9 | `frontend/templates/*.html`, `frontend/static/js/*.js` | Code | User-facing workflow evidence. |
| P10 | `data/*.db`, `data/*.json` | Data | Local data status and database statistics. |

## Local Literature Sources

| ID | Path | Type | Use |
|---|---|---|---|
| L1 | `articles/raw/literature-shortlist.md` | Curated shortlist | Seed citations for materials, structure, and superconductivity databases. |
| L2 | `articles/raw/2026 HPCSD.pdf` | Paper PDF | Strong exemplar for database-infrastructure framing. |
| L3 | `articles/raw/2025 超导数据库 卢仲毅.pdf` | Paper PDF | Local source for HTSC-2025 and superconductivity dataset framing. |
| L4 | `articles/raw/2025 实验已知化合物中 BCS（巴丁 - 库珀 - 施里弗）超导体的分布图谱绘制 PRX energy.pdf` | Paper PDF | Current BCS-superconductor dataset/screening comparison. |
| L5 | `articles/raw/2026 氢基超导体的可解释描述符.pdf` | Paper PDF | Recent hydride ML context. |
| L6 | `articles/raw/2026 常压下机器学习驱动的氢化物超导体探索.pdf` | Paper PDF | Recent ambient-pressure hydride ML context. |
| L7 | `articles/raw/2024 机器学习搜索常压超导体.pdf` | Paper PDF | ML search context and local comparison point. |
| L8 | `articles/raw/2023 机器学习发现常规超导体 Huan Tran.pdf` | Paper PDF | Conventional-superconductor ML context. |
| L9 | `articles/raw/2022 基于 BCS 理论筛选、密度泛函理论与深度学习设计高温超导体.pdf` | Paper PDF | BCS/DFT/deep-learning context. |

## Web-Verified Citation Anchors

| ID | Source | Verification Note |
|---|---|---|
| W1 | arXiv page for HPCSD, arXiv:2605.14471 | Confirms 2026 date, pressure-resolved traceable repository framing, two data streams, and 77,346 entries across 89 elements. |
| W2 | Nature/PMC page for 3DSC, DOI `10.1038/s41597-023-02721-y` | Confirms 3DSC adds approximate 3D structures to superconductors and reports 5,759 MP matches and 9,150 ICSD matches. |
| W3 | NIST/PubMed page for OPTIMADE, DOI `10.1039/D4DD00039K` | Confirms API/federated database interoperability framing. |
| W4 | Springer page for NOMAD, DOI `10.1557/mrs.2018.208` | Confirms FAIR big-data infrastructure framing. |
| W5 | Oxford Academic page for COD, DOI `10.1093/nar/gkr900` | Confirms COD open-access crystallographic database framing. |

