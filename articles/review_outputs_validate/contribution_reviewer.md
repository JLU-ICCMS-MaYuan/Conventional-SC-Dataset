# Contribution & Novelty Review

## Recommendation

**Major Revision**

## Rubric Scores

| Dimension | Score | Justification |
|---|---:|---|
| Contribution readability | 4 | The manuscript states a clear infrastructural contribution: an element-centric, DOI-linked, reviewed curation platform for superconductivity literature and physical-parameter records. The distinction from prediction, benchmark construction, and structure databases is mostly explicit. However, the central contribution is partly weakened by unresolved release status and placeholder references. |
| Novelty | 3 | The platform combines useful workflow features, including periodic-table entry, multiple physical-parameter records per paper, screenshot evidence, review status, chart-display control, and import/export utilities. This is a credible applied contribution, but the manuscript does not yet prove that the combination is substantially beyond existing superconductivity databases, extraction pipelines, or lab-level curation systems. |
| Evidence-to-claim strength | 2 | The manuscript is careful not to overclaim predictive performance, but the evidence for platform maturity and data utility is thin. The main database reportedly contains only one compound and no paper or physical-parameter records in the evaluated snapshot, while the richer AI-screened database is separate and not governed by a public synchronization or release policy. |
| Venue appropriateness | 2 | The work could fit a data/software infrastructure venue after stronger public release, dataset description, validation, and comparison. In its current form, it reads more like a project report or software note than a complete journal-ready dataset or database paper. |

## Specific Findings

### 1. The contribution is well framed, but the novelty claim needs sharper differentiation

The **Introduction**, **Related data resources**, and **Comparison with recent datasets** sections correctly position Conventional-SC-Dataset as a curation-layer platform rather than a prediction model, DFT database, or frozen benchmark. This is the manuscript's strongest contribution framing.

The novelty argument still needs more concrete differentiation from SuperCon, 3DSC, HTSC-2025, HPCSD, literature-extraction resources, and general materials databases. The manuscript lists differences, but it should explicitly state which capabilities are unavailable or underdeveloped in prior resources, such as element-combination search modes, reviewed per-paper physical-parameter entries, screenshot evidence, contributor/reviewer workflow, and chart-display gating. A compact comparison table would make the contribution much more defensible.

### 2. Evidence does not yet support a strong database-paper claim

The **Current repository and data status** section is appropriately candid, but it creates a major evidence gap. The main database contains the element dictionary and one compound record but no paper or physical-parameter records in the evaluated snapshot. This makes it difficult to claim that the system currently converts fragmented literature evidence into a reusable data workflow at meaningful scale.

The separate AI-screened database appears to contain more substantial data, but the manuscript does not establish whether it is part of the release, how it was generated, how it is reviewed, or how it synchronizes with the main database. Until this is resolved, the manuscript should avoid claims that imply a curated public corpus and instead present the work as a functional platform prototype with a demonstrated schema and workflow.

### 3. The contribution is infrastructural, but the manuscript needs stronger validation of the workflow

The **User-facing workflow**, **Administrator workflow**, and **Import, export, and maintenance** sections describe a plausible curation system. However, the contribution would be stronger if the manuscript included concrete workflow validation: example submissions, duplicate-DOI behavior, review-state transitions, screenshot attachment checks, import/export round trips, and chart-display gating.

At present, implementation descriptors such as route counts, page counts, and lines of code show that the repository is non-trivial, but they are not sufficient evidence of scientific or data-infrastructure utility. A database/software venue will likely expect reproducible usage examples, schema documentation, release artifacts, or benchmark curation cases.

### 4. Venue fit depends on public release and citation readiness

The **Data and code availability** section still contains placeholders for repository URL, public dataset release, version identifier, and persistent archive DOI. These omissions are significant for any data or software infrastructure submission. The paper should not be submitted as a database/resource article until the release target, license, versioning policy, and archival DOI are settled.

The manuscript also contains multiple `[REF]` placeholders in contribution-critical passages. These are especially important because novelty is argued by comparison with prior resources. Missing references currently weaken the claims in the **Introduction**, **Related data resources**, and **Comparison with recent datasets** sections.

### 5. The limitation section is unusually useful and should be connected back to claim boundaries

The **Limitations and next steps** section is clear and technically credible. It identifies important constraints: missing stable contributor-user foreign keys, BLOB-based screenshot storage, lack of formal schema migrations, incomplete pressure/Tc filtering, and unimplemented community features.

This section should be used to tighten the rest of the manuscript. The contribution should be stated as an auditable platform architecture and workflow implementation, not as a mature public superconductivity dataset unless the data-release gap is closed.

## Required Revisions

1. Add a feature-level comparison table against SuperCon, 3DSC, HTSC-2025, HPCSD, and general materials databases.
2. Clarify whether `hydride_literature_ai.db` is part of the manuscript evidence, public release, or only an internal/experimental artifact.
3. Provide at least one reproducible end-to-end curation example from element selection through paper submission, review, physical-parameter storage, screenshot evidence, and chart inclusion/exclusion.
4. Replace all `[REF]` placeholders with verified citations before submission.
5. Finalize data/code availability with repository URL, license, version identifier, and preferably an archival DOI.
6. Rephrase scale-sensitive claims until the main released database contains reviewed paper and physical-parameter records.

## Summary

The manuscript has a clear and potentially useful infrastructural contribution, especially in treating superconductivity literature curation as an element-centric, reviewed, evidence-linked workflow. The main obstacle is not the idea but the current evidence base: the default database snapshot does not yet demonstrate a substantial curated corpus, and release/citation details remain incomplete. With stronger differentiation, public-release readability, and workflow validation, the work could become suitable for a software or data-resource venue.
