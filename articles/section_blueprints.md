# Section Blueprints

## Title

Use the current title: "Conventional-SC-Dataset: an auditable, element-centric literature and physical-parameter platform for superconductivity research."

Function: name the platform and immediately identify the contribution as auditable, element-centric, and curation-oriented.

## Abstract

Structure: scattered superconductivity evidence -> gap in operational curation -> platform capabilities -> repository/data snapshot -> boundary.

Required anchors: E01-E09, confirmed motivation, citation landscape only as background rather than proof of platform behavior.

## Introduction

Function: make the need for data infrastructure credible without overclaiming. The opening should connect superconductivity research to materials databases, high-throughput screening, hydride work, benchmarks, and high-pressure database exemplars, then narrow to the operational problem that this platform solves.

Citation anchors: C01, C04, C05, C09, C11-C16.

## Related Data Resources

Function: compare resource families fairly: materials databases, structure databases, SuperCon-style resources, 3DSC, HTSC-2025, HPCSD, and recent high-throughput/ML studies. The section should position this work as complementary, not superior.

Citation anchors: C01-C13, C14-C16 as current superconductivity context.

## Design Principles

Function: explain why the platform is organized around element combinations, paper/data-point separation, reviewed curation, and prediction boundaries.

Evidence anchors: E02-E08.

## System Implementation

Function: describe the data model, user workflow, administrator workflow, and import/export maintenance path. Keep this section at system-paper level rather than turning it into a user manual.

Evidence anchors: E01-E08, T01.

## Current Repository and Data Status

Function: report implementation and local data counts with scope control. Distinguish the main metadata database from the AI-screened metadata database.

Evidence anchors: E09, T02.

## Comparison With Recent Datasets

Function: state complementarity to HPCSD, HTSC-2025, 3DSC, SuperCon, and recent high-throughput/ML studies. Make clear that this work sits at the curation layer before benchmark or model claims.

Citation anchors: C08-C16.

## Limitations and Next Steps

Function: define current boundaries and a realistic engineering roadmap. Mention contributor foreign keys, BLOB image storage, schema migration, pressure/Tc filtering, community features, and release/versioning.

Evidence anchors: E06, E08, E10.

## Conclusion

Function: restate the infrastructure contribution and the intended downstream value: reviewed data organization, statistics, future model-training corpora, and benchmark construction.

Boundary: no new mechanism, no validated model.
