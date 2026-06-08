# Contribution & Novelty Reviewer

## Role

Assess novelty, significance, differentiation from prior work, and evidence-to-claim strength.

**IMPORTANT:** You are an independent reviewer. Do NOT read or reference the other reviewers' work. Your assessment must stand entirely on its own. Do not mention what other reviewers might say.

## Rubric (score 1-5 for each)

- Contribution clarity (1=vague, 5=crystal clear)
- Novelty (1=incremental, 5=genuine contribution)
- Evidence-to-claim strength (1=unsupported, 5=conclusive)
- Venue appropriateness (1=mismatched, 5=perfect fit)

## Manuscript Sections

### Introduction
The search for superconductors is now inseparable from data infrastructure. Conventional phonon-mediated superconductors can be analyzed with relatively mature first-principles workflows, while high-pressure hydrides, ambient-pressure candidates, and benchmark datasets have expanded the chemical and structural space that researchers must compare. Recent examples illustrate this shift. High-throughput calculations have charted Bardeen--Cooper--Schrieffer superconductors among experimentally known compounds [REF] . Hydride-focused machine-learning studies have screened millions of candidate structures or built interpretable descriptors for reduced-pressure superconductivity [REF] . HTSC-2025 provides a benchmark dataset for AI-driven critical-temperature prediction in ambient-pressure high-temperature superconductors [REF] . HPCSD, the High-Pressure Crystal Structure Database, further demonstrates the importance of traceable, pressure-resolved data infrastructure for extreme-condition materials research [REF] .
These resources address essential but different parts of the superconductivity data problem. Structure databases and high-throughput archives prioritize crystal structures, energies, phase stability, or computed electron--phonon quantities. Benchmark datasets prioritize comparable model evaluation. Literature-extraction efforts prioritize transforming text into material-property records. However, a researcher often faces a more operational question before model training or mechanistic interpretation begins: for a selected element system, which papers have been reported, what physical parameters were entered from each paper, who contributed the record, which records have been reviewed, and which records are allowed to enter public charts? This question is not only a data-science problem; it is also a collaborative curation and review problem.
The bottleneck is especially visible in superconductivity literature because one paper may report multiple compounds, pressure ranges, structures, samples, or calculated quantities. Reducing a paper to a single formula--Tc pair discards important context. Conversely, storing all evidence in free-form notes makes later filtering and comparison difficult. A useful literature platform must therefore separate paper-level metadata from data-point-level physical parameters, preserve evidence such as screenshots, and expose review status as a first-class part of the workflow.
Conventional-SC-Dataset was developed to meet this practical need. The platform is organized around a simple path: select elements, find the corresponding compound systems, browse papers, submit DOI-linked records with physical parameters, review records in an administrator interface, and expose approved data through charts and statistics. This design is inspired by the infrastructure logic of recent database papers such as HPCSD: the central contribution is not a single prediction, but a standardized and traceable repository that makes fr

### Related data resources
Materials informatics has benefited from several mature database paradigms. The Materials Project [REF] , OQMD [REF] , AFLOW [REF] , and NOMAD [REF] show how standardized computational data can support large-scale discovery, while ICSD [REF] and COD [REF] provide important crystallographic foundations. These resources establish the expectation that materials data should be searchable, reusable, and connected to well-defined metadata.
Superconductivity-specific resources have developed along complementary directions. SuperCon and its subsequent machine-readable or ontology-oriented derivatives are central sources for historical superconducting-property data [REF] . The 3DSC dataset connects superconducting transition temperatures to crystal structures, addressing a key limitation of formula-only datasets [REF] . HTSC-2025 focuses on recent ambient-pressure high-temperature superconductors and is explicitly framed as a benchmark for AI-based Tc prediction [REF] . High-throughput computational studies further provide curated candidate lists and calculated electron--phonon properties [REF] .
HPCSD is particularly relevant as a writing and design reference because it frames a database as infrastructure for a fragmented field [REF] . HPCSD integrates experimental and theoretical high-pressure structures into a pressure-resolved repository, reporting 77,346 structural entries spanning 89 elements in its initial release. Its argument is that high-pressure structural data had remained sparse and disjointed compared with ambient-pressure materials databases. Conventional-SC-Dataset adopts a similar infrastructure stance but targets a different gap: superconductivity papers and physical-parameter records require element-centric browsing, DOI-based submission, screenshot evidence, and human review before they can reliably support downstream statistics or model-building.

### Design principles


### Element combinations as the primary entry point
Superconductivity researchers frequently reason from chemical composition. The platform therefore starts from a periodic table instead of a free-text search box. Selected elements are normalized, sorted, and mapped into compound systems. Three search modes are supported: only , combination , and contains . The only mode retrieves records whose element set exactly matches the selected set; combination retrieves existing subsystems of the selected set; and contains retrieves larger systems containing the selected elements. This distinction allows the same interface to support precise binary or ternary searches and broader element-family exploration.

### Paper-level metadata separated from physical-parameter records
The platform separates a literature record from its physical data points. The papers table stores DOI, title, authors, journal, year, abstract, contributor fields, review status, review comments, and chart-display state. The paper\_data table stores one or more entries linked to a paper and a compound, including article type, superconductor type, chemical formula, crystal structure, Tc, pressure, electron--phonon coupling parameter, logarithmic phonon frequency, density of states at the Fermi level, sample name, data-source note, and sequence in the paper. This separation preserves the fact that a single publication can contain multiple superconducting systems or multiple pressure--Tc records.

### Curation as a reviewed workflow
Data entry is treated as a workflow rather than a one-step upload. Ordinary users can register, verify email, log in, and submit papers from a compound page. Administrators can review and edit submissions, and super-administrators can approve administrator accounts or change user permissions. Review status, reviewer identity, review time, review comment, and chart-display control are stored with the paper record. This makes the platform suitable for auditable curation rather than uncontrolled aggregation.

### Prediction kept outside the reviewed database loop
The repository contains an experimental Tc-prediction page for structure and PDOS inputs. This module is intentionally separated from the core database loop: it does not write records into the reviewed database, does not replace literature curation, and is not presented here as a validated predictive contribution. This boundary is important because current evidence supports the platform as data infrastructure, not as a benchmarked machine-learning model.

### System implementation


### Data model
The current data model contains six central object types: elements, compounds, users, papers, physical-parameter records, and images. Elements store the 118 chemical elements and support the periodic-table interface. Compounds store chemical formulas and normalized element lists. Users store ordinary-user, administrator, and super-administrator states. Papers store literature metadata and review fields. Physical-parameter records store per-paper compound and superconductivity data. Image records store literature screenshots and thumbnails.

### User-facing workflow
The main user workflow begins at the home page. A user selects elements from the periodic table, chooses a search mode, and enters a compound page. The compound page loads compound-system information and retrieves literature records through backend APIs. Users can filter literature by review status, keyword, year range, and pagination. Each paper card can display metadata, DOI, authors, article type, superconductor type, chemical formula, crystal structure, abstract, physical-parameter entries, and screenshots.
Authenticated users can submit a paper from a compound page. The submission requires DOI information, element context, article type, superconductor type, and at least one physical-parameter entry. Up to five screenshots can be attached through the current user-facing upload flow. The backend validates login state, parses JSON-formatted element and physical-parameter payloads, validates image input, checks DOI metadata, creates or retrieves a compound, prevents duplicate DOI entries within a compound system, creates the paper, writes physical-parameter records, and stores images.

### Administrator workflow
The administrator interface supports the quality-control side of the platform. Administrators can inspect unreviewed papers, update review status, edit records, inspect screenshots, and decide whether a paper should appear in homepage charts. Super-administrators can approve administrator applications and update user permissions. This role hierarchy allows the platform to separate broad contribution from trusted publication of reviewed records.

### Import, export, and maintenance
The platform also supports batch-oriented data operations. A batch-upload endpoint accepts agreed spreadsheet or text formats and converts them into standard database records. Maintenance scripts support database initialization, JSON export, JSON import, ID migration, super-administrator creation, and backup-oriented operations. These scripts are part of the platform's reproducibility story: the database is not only a website state, but a data object that can be initialized, exported, imported, and maintained.

### Current repository and data status
We evaluated the repository snapshot synchronized with origin/master on 8 June 2026. The codebase contains 15,572 lines across Python, JavaScript, HTML, CSS, and shell scripts. It includes 68 backend routes and nine main page templates. The current backend/api directory contains nine non- \_\_init\_\_ API modules. These numbers are implementation descriptors rather than scientific performance metrics, but they indicate that the platform is beyond a static spreadsheet or isolated prototype script.
The current data status should be interpreted carefully. The main metadata database, hydride\_literature.db , contains the element dictionary and one compound record but no paper or physical-parameter records in this snapshot. A separate AI-screened metadata database, hydride\_literature\_ai.db , contains substantially more literature and physical-parameter data. Therefore, the platform's data model and workflows can support a non-trivial literature corpus, but the manuscript should distinguish between the default main database and the AI-screened data file until a formal public release or synchronization policy is established.

### Comparison with recent datasets
The closest conceptual comparison is not a single dataset but a family of infrastructure efforts. HPCSD standardizes high-pressure crystal structures and pressure-resolved energetics, with two data streams from reported elemental phases and CALYPSO crystal-structure prediction tasks [REF] . HTSC-2025 curates a benchmark of ambient-pressure high-temperature superconductors for AI-driven Tc prediction [REF] . The PRX Energy BCS-superconductor study uses high-throughput first-principles calculations to identify promising phonon-mediated superconductors among experimentally known compounds [REF] . Hydride machine-learning studies expand candidate discovery through large-scale screening or interpretable descriptors [REF] .
Conventional-SC-Dataset is deliberately positioned below these tasks in the data pipeline. It does not recompute all structures with a unified DFT protocol as HPCSD does. It does not define a frozen benchmark split as HTSC-2025 does. It does not claim exhaustive high-throughput electron--phonon calculations. Instead, it supports the curation layer that many downstream tasks require: mapping element systems to papers, recording multiple physical parameters per paper, attaching source evidence, and controlling review status. In this sense, the platform is complementary to structure databases, benchmark datasets, and high-throughput computational screens.

### Limitations and next steps
The present platform has several limitations. First, the relationship between a submitted paper and a registered user is currently represented mainly by contributor name and affiliation fields, not by a stable contributor-user foreign key. This limits reliable contribution statistics and long-term accountability. Second, screenshots are stored as database BLOBs, which is simple at the current scale but may cause database growth and migration pressure as image volume increases. Third, the repository does not yet contain a formal schema-migration system such as Alembic, so long-term field and index evolution will require careful maintenance. Fourth, pressure and Tc fields are available in physical-parameter records but are not yet elevated into fully mature first-class filtering dimensions across the search API and user interface. Fifth, community features such as likes, comments, bullet-screen messages, heat ranking, and database snapshot management are not implemented in the current database model.
These limitations define a practical development path. The next version should prioritize a stable contributor\_user\_id relationship, pressure and Tc range filters, clearer indexing strategy, backend-managed citation export, and formal schema migration. After these foundations are stable, the platform can more safely add public release versioning, dataset cards, benchmark splits, or community-interaction features.

### Conclusion
Conventional-SC-Dataset provides an auditable, element-centric platform for superconductivity literature and physical-parameter curation. By combining periodic-table search, standardized compound matching, DOI-based paper submission, multiple physical-parameter records per paper, screenshot evidence, administrator review, chart-display control, and import/export utilities, it converts fragmented literature evidence into a maintainable data workflow. Its current contribution is infrastructural: it supports reviewed data organization for superconductivity research and prepares the ground for more reliable statistics, model-training corpora, and benchmark construction. Future work should focus on formalizing user--paper relationships, improving physical-parameter filtering, versioning public data releases, and integrating migration and synchronization policies before stronger claims about prediction or community-scale deployment are made.

### Data and code availability
The source code and local database files are available in the project repository at [repository URL or local project path] . A formal public dataset release, version identifier, and persistent archive DOI should be added before journal submission. The current manuscript statistics were computed from the repository snapshot synchronized with origin/master on 8 June 2026.

### Author contributions
[Your Name] designed and implemented the platform, curated the manuscript scope, and prepared the article draft. Additional contributor roles should be filled in after confirming collaborators, code contributors, and data curators.

### Competing interests
The author declares no competing interests. [Revise if needed before submission.]

### Acknowledgements
The author thanks the developers and authors of the public superconductivity, materials, and high-pressure database studies cited in this manuscript. [Add grant numbers, collaborators, and institutional support before submission.]
jain2013materialsproject A. Jain, S. P. Ong, G. Hautier, W. Chen, W. D. Richards, S. Dacek, S. Cholia, D. Gunter, D. Skinner, G. Ceder, and K. A. Persson. The Materials Project: A materials genome approach to accelerating materials innovation. APL Materials 1 , 011002 (2013). doi:10.1063/1.4812323.
kirklin2015oqmd S. Kirklin, J. E. Saal, B. Meredig, A. Thompson, J. W. Doak, M. Aykol, S. Ruehl, and C. Wolverton. The Open Quantum Materials Database (OQMD): assessing the accuracy of DFT formation energies. npj Computational Materials 1 , 15010 (2015). doi:10.1038/npjcompumats.2015.10.
curtarolo2015aflow S. Curtarolo, W. Setyawan, G. L. W. Hart, M. Jahnatek, R. V. Chepulskii, R. H. Taylor, S. Wang, J. Xue, K. Yang, O. Levy, M. J. Mehl, H. T. Stokes, D. O. Demchenko, and D. Morgan. AFLOW: The automatic flow framework for materials discovery. Computational Materials Science 58 , 218--226 (2012). doi:10.1016/j.commatsci.2012.02.005.
draxl2018nomad C. Draxl and M. Scheffler. NOMAD: The FAIR concept for big-data-driven materials science. MRS Bulletin 43 , 676--682 (2018). doi:10.1557/mrs.2018.208.
belsky2002icsd A. Belsky, M. Hellenbrandt, V. L. Karen, and P. Luksch. New developments in the Inorganic Crystal Structure Database (ICSD): accessibility in support of materials research and design. Acta Crystallographica Section B 58 , 364--369 (2002). doi:10.1107/S0108768102006948.
grazulis2012cod S. Grazulis, A. Daskevic, A. Merkys, D. Chateigner, L. Lutterotti, M. Quiros, N. R. Serebryanaya, P. Moeck, R. T. Downs, and A. Le Bail. Crystallography Open Database (COD): an open-access collection of crystal structures and platform for world-wide collaboration. Nucleic Acids Research 40 , D420--D427 (2012). doi:10.1093/nar/gkr900.
nimsSupercon National Institute for Materials Science. SuperCon Datasheet, version v240322. doi:10.48505/nims.4487.
foppiano2023supercon2 L. Foppiano, T. C. T. Ting, J. M. Romary, and coauthors. Automatic extraction of materials and properties from superconductors scientific literature. Science and Technology of Advanced Materials: Methods 3 , 2153633 (2023). doi:10.1080/27660400.2022.2153633.
ishii2023ontology Y. Ishii and T. Sakamoto. Structuring superconductor data with ontology: reproducing historical datasets as knowledge bases. Science and Technology of Advanced Materials: Methods 3 , 2223051 (2023). doi:10.1080/27660400.2023.2223051.
sommer2023threedsc T. Sommer, D. Di Cataldo, and L. Boeri. 3DSC -- a dataset of superconductors including crystal structures. Scientific Data 10 , 816 (2023). doi:10.1038/s41597-023-02721-y.
han2025htsc X.-Q. Han, Z.-F. Gao, X.-D. Wang, Z. Ouyang, P.-J. Guo, and Z.-Y. Lu. HTSC-2025: A benchmark dataset of ambient-pressure high-temperature superconductors for AI-driven critic

## Instructions

1. Score each rubric dimension (1-5) with a brief justification.
2. List at least 3 specific findings. Reference section names.
3. Recommend: Accept / Minor Revision / Major Revision / Reject.
4. Write your review in clear, structured Markdown.

Write only your review. Do NOT produce other files.
