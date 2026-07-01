# Exemplar Learning Dossier

## Primary Exemplar: HPCSD

HPCSD is useful because it is a database-infrastructure paper, not because it targets the same scientific object. Its transferable writing pattern is:

| Exemplar Feature | How To Use It |
|---|---|
| Opens from a broad research mode and narrows to data fragmentation. | Open Conventional-SC-Dataset from data-driven superconductivity and narrow to fragmented literature/property curation. |
| Names a concrete data bottleneck. | Name the operational gap: selected element systems, multiple records per paper, screenshots, contributor/review state, and chart eligibility are not handled together. |
| Defines a repository with traceability. | Define the platform as auditable/reviewable rather than merely searchable. |
| Uses release-scale numbers as evidence. | Use repository/code/data-file statistics, while separating main database and AI-screened database. |
| Explains complementarity to existing resources. | Contrast against materials databases, structure databases, SuperCon-like datasets, 3DSC, HTSC-2025, and HPCSD. |

## Secondary Exemplar: 3DSC

3DSC is useful because it identifies a specific missing layer in SuperCon: structural information. The transferable lesson is to avoid generic database novelty. The manuscript should say exactly what layer is missing from current resources: not structures alone, but paper-level reviewable physical-parameter records tied to element-centric browsing and evidence attachments.

## Secondary Exemplar: HTSC-2025

HTSC-2025 is useful as a contrast. It is a benchmark dataset for AI-driven Tc prediction. Conventional-SC-Dataset should avoid benchmark language unless a frozen release, split policy, and evaluation protocol are provided. It can still cite HTSC-2025 to show that superconductivity data resources are active and increasingly AI-facing.

## Secondary Exemplar: NOMAD/OPTIMADE

NOMAD and OPTIMADE teach database-infrastructure rhetoric: FAIRness, interoperability, discoverability, reuse, and metadata. Conventional-SC-Dataset can borrow this vocabulary carefully, but should not claim full FAIR compliance unless persistent identifiers, versioned releases, schema documentation, and access policy are in place.

## Writing Constraints Learned From Exemplars

| Constraint | Reason |
|---|---|
| Define the database object precisely. | Reviewers need to know whether this is a dataset, a web platform, a curation workflow, or a benchmark. |
| Separate evidence from planned features. | Database papers are rejected when implementation claims are mixed with roadmap items. |
| Use numbers only where they are traceable. | Current counts must be tied to a specific snapshot and data file. |
| Make complementarity explicit. | The paper should not imply that it replaces SuperCon, 3DSC, HTSC-2025, HPCSD, or materials databases. |

