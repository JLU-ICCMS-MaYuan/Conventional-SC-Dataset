# SOTA Gap Map

| Resource Family | Representative Works | Strength | Remaining Gap For This Paper |
|---|---|---|---|
| General materials databases | Materials Project, OQMD, AFLOW, NOMAD | Large-scale computed materials data, reusable metadata, structure/property search. | Not optimized for superconductivity literature submission, screenshots, review state, or multi-parameter paper curation. |
| Interoperability layer | OPTIMADE | Federated materials database access and common API language. | Does not by itself define superconductivity-specific curation workflow or evidence review. |
| Structure databases | ICSD, COD | Crystal-structure search and crystallographic reference matching. | Do not organize superconducting Tc/pressure/sample/evidence/review workflow as first-class objects. |
| Superconductivity property datasets | SuperCon, SuperCon derivatives | Large historical superconductivity property source, widely used for Tc prediction. | Often formula/property centered; structure, evidence, and review workflow are limited or external. |
| Literature extraction datasets | SuperMat, SuperCon2-style extraction | Converts text into material/property annotations. | Extraction does not replace human-reviewed deposition, screenshots, and platform-level curation. |
| Structure-augmented superconductor datasets | 3DSC | Adds approximate 3D structures to superconductivity records. | Focuses on structure/Tc matching, not operational literature upload/review/chart workflow. |
| Benchmark datasets | HTSC-2025 | Provides AI-facing benchmark for ambient-pressure high-temperature superconductors. | Benchmark orientation differs from a live auditable curation platform. |
| High-pressure structure infrastructure | HPCSD | Traceable pressure-resolved structural repository; strong database-paper exemplar. | Focuses on high-pressure structures and unified DFT reoptimization, not superconductivity literature curation. |
| This work | Conventional-SC-Dataset | Element-centric browsing, DOI submission, multiple property records, screenshots, role-based review, chart gating, import/export. | Needs formal release/versioning, stronger property search, contributor-user foreign keys, migration system, and public archive policy. |

## Core Gap Sentence

Existing materials, structure, and superconductivity datasets make structures, computed properties, or Tc labels searchable, but they do not jointly support element-centric superconductivity literature browsing, DOI-based deposition, multiple physical-parameter records per paper, screenshot evidence, contributor/reviewer state, and controlled visualization in one auditable workflow.

