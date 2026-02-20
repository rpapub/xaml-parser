# ADR: DTO Design for XAML Parser

**Status:** Accepted
**Date:** 2025-10-11
**Context:** Phase 0 - Foundation & Design
**Related:** PLAN.md Phase 0, zweitmeinung.md

---

## Context

The XAML parser needs a stable, deterministic output format that:
1. Separates parsing implementation from output schema
2. Provides stable entity IDs that survive file renames
3. Supports control flow analysis with explicit edges
4. Enables schema versioning and evolution
5. Works across multiple output formats (JSON, YAML, diagrams, docs)
6. Supports multiple consumers (MCP server, diagnostics, documentation)

The existing implementation uses:
- Sequential activity IDs (`activity_1`, `activity_2`) that aren't stable
- No control flow edges, only parent-child tree relationships
- Hardcoded JSON output with limited fields
- No schema versioning or self-describing metadata

---

## Decision

We implement a **Data Transfer Object (DTO) layer** separate from internal parsing models with the following design:

### 1. Stable Content-Hash Based IDs

**Decision:** Use content-hash based IDs: `prefix:sha256:hash[:16]`

**Format:**
- Workflows: `wf:sha256:abc123def456...` (16 hex chars)
- Activities: `act:sha256:abc123def456...` (16 hex chars)
- Edges: `edge:sha256:abc123def456...` (16 hex chars)

**Implementation:**
```python
id = f"{prefix}:sha256:{hashlib.sha256(normalized_xml).hexdigest()[:16]}"
```

**Normalization:** W3C XML Canonicalization (C14N) before hashing:
- Sort attributes lexicographically
- Normalize namespace declarations
- Remove insignificant whitespace
- UTF-8 encoding, LF line endings
- No XML declaration

**Rationale:**
- **Path-independent:** IDs survive file renames and moves
- **Deterministic:** Same content always produces same ID
- **Collision-resistant:** 64-bit hash space adequate for typical projects (100-1000 workflows)
- **Readable:** 16 hex chars balance uniqueness with readability
- **Traceable:** Full hash stored in `SourceInfo.hash` for audit trails

**Alternatives Considered:**
1. **Path-based IDs** (`wf:path/to/Main.xaml`) - Rejected: breaks on renames
2. **UUID v4** - Rejected: not deterministic, can't reproduce
3. **Full hash** (64 chars) - Rejected: too verbose for human readability
4. **Sequential IDs** (`activity_1`) - Rejected: not stable across edits

### 2. Path Tracking with Aliases

**Decision:** Store current path in `SourceInfo.path`, historical paths in `SourceInfo.path_aliases`

**Structure:**
```python
@dataclass
class SourceInfo:
    path: str                    # Current relative path (POSIX format)
    path_aliases: list[str]      # Historical paths for rename tracking
    hash: str                    # Full SHA-256: sha256:abc123...def456
    size_bytes: int
    encoding: str = "utf-8"
```

**Rationale:**
- **Rename tracking:** Historical paths enable tracking file movement
- **Path-ID separation:** ID stability independent of path changes
- **POSIX format:** Consistent path representation across platforms
- **Git-friendly:** Relative paths work across clones

**Example:**
```json
{
  "source": {
    "path": "workflows/Main.xaml",
    "path_aliases": ["Main.xaml", "src/Main.xaml"],
    "hash": "sha256:abc123...def456",
    "size_bytes": 12345,
    "encoding": "utf-8"
  }
}
```

### 3. Self-Describing Metadata

**Decision:** Every DTO includes schema metadata

**Required Fields:**
```python
schema_id: str = "https://rpax.io/schemas/xaml-workflow.json"
schema_version: str = "1.0.0"
collected_at: str = ""  # ISO 8601 UTC: "2025-10-11T07:15:00Z"
```

**Rationale:**
- **Schema evolution:** Consumers can handle multiple schema versions
- **Validation:** JSON Schema URL points to validation schema
- **Reproducibility:** Timestamp enables audit trails (use `--collected-at` flag for reproducible builds)
- **Self-documenting:** Output explains its own structure

**Schema Versioning Policy:**
- **Major:** Breaking changes (field removal, type changes)
- **Minor:** Additive changes (new optional fields)
- **Patch:** Documentation only, no schema changes

### 4. Complete Edge Taxonomy

**Decision:** Explicit edge types covering all control flow patterns

**Edge Kinds:**
```python
EdgeKind = Literal[
    "Then",       # If Then branch
    "Else",       # If Else branch
    "Next",       # Sequence next step
    "True",       # FlowDecision True path
    "False",      # FlowDecision False path
    "Case",       # Switch case branch (with condition)
    "Default",    # Switch default branch
    "Catch",      # TryCatch catch handler
    "Finally",    # TryCatch finally block
    "Link",       # Flowchart link/transition
    "Transition", # StateMachine state transition
    "Branch",     # Parallel/ParallelForEach branch
    "Retry",      # RetryScope retry path
    "Timeout",    # RetryScope timeout path
    "Done",       # Loop/iteration completion
    "Trigger",    # Pick/PickBranch trigger
]
```

**Structure:**
```python
@dataclass
class EdgeDto:
    id: str                     # edge:sha256:...
    from_id: str                # Source activity ID
    to_id: str                  # Target activity ID
    kind: str                   # Edge kind from taxonomy
    condition: str | None       # Condition expression (for Case, If, etc.)
    label: str | None           # Display label (for diagrams)
```

**Rationale:**
- **Explicit modeling:** Control flow separate from tree hierarchy
- **Diagram generation:** Direct mapping to Mermaid/DOT edges
- **Analysis support:** Enable static analysis, path finding, coverage
- **Completeness:** Covers all UiPath activity types

**Example:**
```json
{
  "edges": [
    {
      "id": "edge:sha256:abc123",
      "from_id": "act:sha256:def456",
      "to_id": "act:sha256:789abc",
      "kind": "Then",
      "condition": null,
      "label": null
    },
    {
      "id": "edge:sha256:xyz789",
      "from_id": "act:sha256:def456",
      "to_id": "act:sha256:456def",
      "kind": "Else",
      "condition": null,
      "label": null
    }
  ]
}
```

### 5. First-Class Activity Entity

**Decision:** Activities are self-contained entities with complete business logic

**Structure:**
```python
@dataclass
class ActivityDto:
    # Identity
    id: str                              # act:sha256:...
    type: str                            # Fully-qualified type
    type_short: str                      # Short name
    display_name: str | None

    # Location
    location: LocationInfo | None        # Line, column, xpath

    # Hierarchy
    parent_id: str | None
    children: list[str]                  # Child activity IDs
    depth: int

    # Configuration
    properties: dict[str, Any]           # All properties
    in_args: dict[str, str]              # Input arguments
    out_args: dict[str, str]             # Output arguments

    # Analysis
    annotation: str | None               # Documentation
    expressions: list[str]               # All expressions
    variables_referenced: list[str]      # Variable names

    # UI Activities
    selectors: dict[str, str] | None     # UI selectors
```

**Rationale:**
- **Complete information:** Activity DTO contains everything needed for analysis
- **Hierarchy + Edges:** Both tree structure (parent/children) and control flow (edges) represented
- **Expression capture:** All expressions preserved for static analysis
- **Selector extraction:** UI automation selectors available for analysis
- **Type safety:** Strongly typed with Python type hints

### 6. Deterministic Serialization

**Decision:** All collections sorted deterministically

**Sorting Rules:**
1. **Activities:** Sort by ID (string comparison, UTF-8 binary collation)
2. **Arguments/Variables:** Sort by name (case-sensitive, UTF-8 binary)
3. **Properties:** Sort by key name (case-sensitive, UTF-8 binary)
4. **Edges:** Sort by (from_id, to_id, kind)
5. **Collections:** Always use list, never unordered set in JSON

**Locale Independence:**
- UTF-8 binary collation (byte-wise comparison)
- No locale-sensitive sorting (no strcoll)
- No Unicode normalization (preserve as-is)

**Rationale:**
- **Reproducibility:** Same workflow always produces identical JSON
- **Diff-friendly:** Consistent ordering enables clean git diffs
- **Cross-platform:** Binary collation works identically everywhere
- **Testing:** Golden tests can compare exact JSON output

---

## Consequences

### Positive

1. **Stable IDs:** Workflows can be renamed without breaking references
2. **Schema Evolution:** DTOs can evolve independently from parsing code
3. **Multiple Outputs:** Same DTO can feed JSON, YAML, diagrams, docs
4. **Type Safety:** Python dataclasses with mypy strict checking
5. **Testability:** DTOs are pure data, easy to test
6. **Validation:** JSON Schema validation ensures output correctness
7. **Determinism:** Reproducible output enables golden tests

### Negative

1. **Complexity:** Additional layer between parsing and output
2. **Memory:** DTOs duplicate some data from internal models
3. **Performance:** Normalization and hashing add overhead (~10-20ms per workflow)
4. **Hash Collisions:** 64-bit hash has ~1 in 10^19 collision probability (acceptable for typical projects)

### Trade-offs

1. **ID Length vs. Uniqueness:** 16 hex chars (64 bits) chosen as balance
   - Shorter would increase collision risk
   - Longer would reduce readability
   - Full hash stored in `SourceInfo.hash` for audit trails

2. **Path Storage:** Path tracked separately from ID
   - Pro: True rename stability
   - Con: Need to maintain `path_aliases` for tracking

3. **Edge Extraction:** Explicit edges vs. implicit tree
   - Pro: Enables control flow analysis and diagram generation
   - Con: Duplicates some information from tree structure

---

## Alternatives Considered

### Alternative 1: Path-Based IDs with Content Hash

**Approach:** `wf:path/to/Main.xaml#sha256:abc123`

**Rejected Because:**
- Path prefix makes ID unstable on rename
- Breaks references between workflows on reorganization
- Hash suffix doesn't help if path changes

### Alternative 2: UUID v5 (Namespace + Name)

**Approach:** `wf:uuid:550e8400-e29b-41d4-a716-446655440000`

**Rejected Because:**
- Requires stable namespace (path would be natural choice, but unstable)
- UUIDs less readable than hex hashes
- No clear advantage over SHA-256 truncation

### Alternative 3: Embedded Control Flow (No Edges)

**Approach:** Store control flow in activity properties

**Rejected Because:**
- Harder to query and analyze
- Duplicates information in multiple places
- Complicates diagram generation
- No clear separation of concerns

### Alternative 4: JSON Schema in Output

**Approach:** Embed full schema in every output file

**Rejected Because:**
- Bloats output size significantly
- Schema URL + version sufficient for validation
- Consumers can cache schemas

---

## Implementation Notes

### Phase 0: Foundation

1. **dto.py** - Complete DTO definitions with type hints
2. **JSON Schemas** - Validation schemas for workflow and collection
3. **This ADR** - Design documentation

### Phase 1: ID Generation

1. **id_generation.py** - IdGenerator with W3C C14N normalization
2. **Tests** - Verify determinism and collision resistance

### Phase 2: Control Flow Extraction

1. **control_flow.py** - ControlFlowExtractor with all edge kinds
2. **Tests** - Verify all activity types covered

### Phase 3: Normalization

1. **normalization.py** - Normalizer transforms ParseResult → WorkflowDto
2. **Tests** - Verify completeness and determinism

---

## References

- **PLAN.md Phase 0:** Foundation & Design tasks
- **zweitmeinung.md:** Analyst requirements for stable IDs and control flow
- **python/xaml_parser/dto.py:** DTO implementation
- **python/schemas/xaml-workflow-1.0.0.json:** JSON Schema
- **W3C XML Canonicalization:** https://www.w3.org/TR/xml-c14n
- **JSON Schema Draft 2020-12:** https://json-schema.org/draft/2020-12/schema

---

## License

This document is licensed under CC-BY-4.0.
