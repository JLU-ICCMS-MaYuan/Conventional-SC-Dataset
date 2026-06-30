# Formula Expression Parser for Similarity Search

The search experience needs to accept exact formulas, fractional stoichiometry, variables, ranges, and nested parentheses while still returning only superconductors in the same element system. We will build a search-specific formula expression parser that produces element-system and constraint data for ranking, rather than replacing the existing ingestion-time formula normalization or relying on `pymatgen.Composition`, because those paths are designed for concrete compositions rather than variable search expressions.

**Consequences**

- Ingestion keeps using the existing normalized concrete formula fields.
- Formula search can evolve its expression language without changing stored superconductor identity.
- The parser must be covered by focused tests because its behavior defines user-facing search semantics.
