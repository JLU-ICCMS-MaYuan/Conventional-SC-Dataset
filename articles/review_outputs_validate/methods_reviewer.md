# Methods & Reproducibility Review

## Rubric Scores

| Dimension | Score | Justification |
|---|---:|---|
| Method description completeness | 3 | The manuscript describes the platform workflow, data model, review roles, import/export utilities, and current repository status, but it does not yet provide enough operational detail for independent reproduction of the reported repository statistics, database initialization, API behavior, or data-curation workflow. |
| Assumption justification | 3 | Several design assumptions are reasonable and explicitly stated, including element-centric browsing, separation of paper-level metadata from physical-parameter records, and keeping Tc prediction outside the reviewed database loop. However, the manuscript does not sufficiently justify key thresholds and scope choices, such as the duplicate-DOI rule within compound systems, the five-screenshot limit, the selected search modes, or the relationship between the main database and the AI-screened database. |
| Experimental design | 2 | The manuscript is framed as a data-infrastructure/platform paper rather than a predictive or experimental study, which is acceptable. However, the current evaluation is mostly descriptive: line counts, route counts, template counts, and database contents. There is no systematic reproducibility test, user-workflow validation, import/export round-trip test, API test summary, schema consistency audit, or comparison protocol against existing superconductivity data resources. |
| Limitations acknowledgment | 4 | The limitations section is unusually concrete and directly names contributor identity, BLOB image storage, lack of schema migration, incomplete pressure/Tc filtering, and unimplemented community features. It should still more clearly distinguish limitations that affect reproducibility from limitations that affect future product scope. |

## Specific Findings

### 1. Current repository and data status: evaluation is descriptive but not reproducible enough

The manuscript reports that the repository snapshot dated 2 June 2026 contains 15,044 lines, 67 backend routes, nine page templates, and nine non-`__init__` API modules. These are useful implementation descriptors, but the Methods section does not explain how these numbers were computed. A reproducible paper should provide the exact commands, inclusion/exclusion rules, and whether generated files, virtual environments, static assets, migrations, database files, and tests were included.

This matters because these quantities are presented as evidence that the platform is more than a static spreadsheet or isolated prototype. Without a reproducible counting protocol, readers cannot independently verify the claim.

### 2. Import, export, and maintenance: round-trip reproducibility is not demonstrated

The manuscript states that batch upload, database initialization, JSON export, JSON import, ID migration, super-administrator creation, and backup-oriented operations are part of the reproducibility story. However, it does not present a concrete round-trip test such as initialize database -> import fixture -> export JSON -> re-import -> compare record counts and key fields.

For a database-infrastructure manuscript, this is a major methods gap. The platform's central core claim is traceable curation, so the manuscript should show that records can be recreated from documented inputs rather than only existing as website state.

### 3. User-facing workflow: submission validation rules need more precise specification

The user-facing workflow describes DOI information, element context, article type, superconductor type, physical-parameter entries, up to five screenshots, image validation, DOI metadata checks, compound creation, duplicate DOI prevention, and image storage. This is useful, but not yet fully reproducible. The manuscript should specify required fields, accepted data types, allowed null values, file size/type limits for screenshots, DOI metadata failure behavior, and the exact duplicate criterion.

The current statement that duplicate DOI entries are prevented "within a compound system" is especially important. If a paper reports multiple compound systems, the manuscript should clarify whether the same DOI can appear across compounds and how this is represented in the data model.

### 4. Data model: schema-level reproducibility is under-specified

The manuscript names the six central object types and summarizes important fields, but it does not provide a schema table, entity relationship diagram, primary keys, foreign keys, indexes, or validation constraints. Because the paper's core claim is an auditable curation platform, the database schema is not an implementation detail; it is part of the method.

The paper would be stronger if the Methods section included a compact schema summary and explained how paper records, physical-parameter records, image records, compounds, and users are linked. The current limitations also note the absence of a stable contributor-user foreign key, which reinforces the need to make the current schema explicit.

### 5. Current data status: main database and AI-screened database require a clearer reproducibility boundary

The manuscript candidly states that `hydride_literature.db` contains the element dictionary and one compound record but no paper or physical-parameter records, while `hydride_literature_ai.db` contains substantially more literature and physical-parameter data. This distinction is important and should remain.

However, the manuscript should define which database supports each claim. If the platform workflows are evaluated using the main database, the manuscript cannot imply a non-trivial curated corpus. If the AI-screened database supports data-scale claims, the manuscript must describe its generation, provenance, validation state, and synchronization policy. Without that boundary, readers may be unable to reproduce the data status or interpret the platform's maturity.

### 6. Prediction kept outside the reviewed database loop: boundary is well handled

The manuscript appropriately avoids presenting the Tc-prediction module as a validated predictive core claim. This is a methodological strength. It prevents overclaiming and keeps the paper focused on reviewed data infrastructure. The same level of boundary-setting should be applied to the AI-screened database and to any future benchmark or model-training claims.

## Recommendation

**Major Revision**

The manuscript has a coherent infrastructure core claim and a strong awareness of limitations, but the methods and reproducibility package are not yet sufficient for acceptance. The main revision should convert the current descriptive Methods section into a reproducible protocol: provide schema-level documentation, exact repository-statistics commands, fixture-based workflow tests, import/export round-trip validation, clearer database provenance, and explicit validation rules for submission and review workflows.
