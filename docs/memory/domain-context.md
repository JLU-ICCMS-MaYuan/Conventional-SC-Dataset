# SC-Wiki

SC-Wiki is a database-style superconductivity site organized around element systems, superconducting formulas, papers, and structured physical records.

## Language

**Chemical Formula Similarity Search**:
A structured search mode where a user-provided chemical formula expression identifies superconductors in the same element system and ranks them by formula identity, stoichiometric closeness, and satisfiable variable or range constraints. It does not return superconductors with extra, missing, or only partially overlapping elements.
_Avoid_: Formula keyword search, cross-system fuzzy formula search

**SC Explore**:
The user-facing exploration workspace for finding superconducting systems by chemical formula or by selecting elements from the periodic table. It is a primary navigation destination for general users.
_Avoid_: Admin review workflows, user permission management

**Admin Tools**:
Permissioned workflows for reviewing papers, maintaining literature records, and managing users. They are operational tools for authenticated administrators, not primary discovery destinations for general users.
_Avoid_: Main exploration navigation, public literature discovery
