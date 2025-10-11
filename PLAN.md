# XAML Parser: Integrated Architecture Redesign

**Status:** Planning Phase
**Priority:** Critical
**Impact:** Full Architecture
**Date:** 2025-10-11
**Approach:** Option B - Integrated Redesign (no incremental refactoring)

---

## Executive Summary

Complete redesign of xaml-parser to separate parsing from output, add stable entity IDs, extract control flow, support multiple output formats (data/diagrams/docs), and create a pluggable emitter architecture. This replaces the tactical refactoring plan with a strategic redesign that addresses both immediate needs and long-term requirements.

**Key Changes:**
- Stable deterministic IDs for all entities
- Control flow modeling (edges, transitions)
- DTO layer separate from parsing models
- Pluggable emitter system (data, diagrams, docs)
- Self-describing output with schema versioning
- Comprehensive CLI with subcommands

---

## Requirements Synthesis

### From Original Analysis (Output Refactoring)
- ✅ Separate parsing from output/formatting
- ✅ Configurable field selection (profiles)
- ✅ Multiple output formats (JSON in v1.0.0, YAML/CSV in v1.1.0+)
- ✅ Library-first design
- ✅ Reusable components

### From Analyst Requirements (zweitmeinung.md)
- ✅ Stable deterministic IDs (`prefix:path#hash`)
- ✅ Control flow edges (Then/Else/transitions)
- ✅ Diagram generation (Mermaid, DOT, PlantUML)
- ✅ Doc generation (Jinja2 templates → Markdown)
- ✅ Self-describing DTOs (`$schema`, `$id`, `schemaVersion`)
- ✅ Validation subcommand
- ✅ Config file support (`xamlparser.yaml`)
- ✅ Pluggable emitters (entry points)
- ✅ Deterministic ordering

### Combined Architecture Goal

```
┌──────────────────────────────────────────────────────────────┐
│                  CLI / MCP / Library Consumers               │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            ├─► XamlParser / ProjectParser
                            │   └─► ParseResult (internal models)
                            │
                            ├─► Normalizer
                            │   ├─► Generate stable IDs
                            │   ├─► Extract control flow edges
                            │   ├─► Sort deterministically
                            │   └─► Transform to DTOs
                            │
                            ├─► Emitter (pluggable)
                            │   ├─► DataEmitter (JSON/YAML)
                            │   ├─► DiagramEmitter (Mermaid/DOT/PlantUML)
                            │   └─► DocEmitter (Jinja2→Markdown)
                            │
                            └─► Validator
                                ├─► JSON Schema validation
                                └─► Referential integrity
```

---

## Decisions & Answers to Analyst Questions

### Q1: Language - Python first or Go now?
**Decision:** Python first (v0.1-v0.2), Go in v1.0+
**Rationale:** Current implementation is Python, established testing infrastructure, faster iteration.

### Q2: Diagram default - Mermaid only, or also DOT/PlantUML?
**Decision:** Mermaid only in v0.1, DOT/PlantUML in v0.2
**Rationale:** Mermaid is most popular, GitHub-native, simpler implementation. DOT/PlantUML are extensions.

### Q3: Doc templates - minimal or include embedded diagrams?
**Decision:** Minimal tables in v0.1, embedded diagrams in v0.2
**Rationale:** Tables are straightforward, diagram embedding needs coordination with diagram emitter.

### Q4: Output mode - combined JSON or one-file-per-workflow?
**Decision:** One-file-per-workflow default, `--combine` flag for single file
**Rationale:** Matches UiPath project structure, easier to track changes in VCS.

### Q5: IDs - sha256(xml-span) + path?
**Decision:** Content-hash primary ID, path tracked separately: `id = prefix:sha256(xml-span)[:16]`
**Rationale:** True rename-stability requires path-independent IDs. Path stored in `source.path` with `path_aliases` for historical tracking. Hash truncated to 16 chars for readability while maintaining collision-resistance for typical projects.

### Q6: Validation - strict fail or warn on unknown types?
**Decision:** Warn and include `typeRaw` field
**Rationale:** UiPath adds new activities frequently, strict mode would break. Warn + preserve raw.

### Q7: Performance target - repo size?
**Decision:** Optimize for 100-500 XAML files, test with 1000+
**Rationale:** Typical enterprise UiPath projects have 100-500 workflows.

### Q8: Licensing - keep CC-BY?
**Decision:** CC-BY-4.0 for everything (code, documentation, schemas)
**Rationale:** User choice, consistently applied across all project artifacts.

### Q9: Downstream consumers - which first?
**Decision:** MCP server (v0.1) → rpax diagnostics (v0.2) → site docs (v0.3)
**Rationale:** MCP is immediate use case, diagnostics need stable IDs, docs need diagrams.

### Q10: YAML - needed in v0.1?
**Decision:** JSON only in v1.0.0, YAML in v1.1.0
**Rationale:** JSON is canonical format, YAML is nice-to-have for human editing. Defer to keep v1.0.0 scope manageable.

---

## Current State Analysis

### What Works ✅
- Parsing logic is clean and comprehensive
- Models (`Activity`, `WorkflowContent`) are well-designed
- Project-level parsing with dependency traversal
- Test infrastructure (90% coverage target)

### What's Broken ❌
- **No stable IDs** - Uses `activity_1`, `activity_2` (not deterministic)
- **No control flow modeling** - Tree structure only, no edges
- **Formatting in CLI** - 7 functions embedded in cli.py
- **Inflexible JSON** - Hardcoded 5 fields, missing critical data
- **No diagrams** - Cannot visualize workflows
- **No docs** - Cannot generate documentation
- **No extensibility** - Cannot add custom emitters

### Gap Analysis

| Feature         | Current                | Required                                 | Gap                             |
| --------------- | ---------------------- | ---------------------------------------- | ------------------------------- |
| Entity IDs      | `activity_1`           | `act:sha256:abc123...` (content-hash)    | Need ID generation system       |
| Control flow    | Parent/child tree      | Explicit edges                           | Need edge extraction            |
| Output          | 2 formats (text, JSON) | Data + diagrams + docs                   | Need emitter system             |
| Field selection | Hardcoded              | Configurable profiles                    | Need DTO adapter                |
| Schema          | None                   | Self-describing                          | Need `$schema`, `schemaVersion` |
| Validation      | Basic                  | Schema + referential                     | Need validation module          |
| CLI             | Single command         | Subcommands (parse/diagram/doc/validate) | Need CLI redesign               |
| Config          | CLI flags only         | Config file support                      | Need YAML/TOML parser           |

---

## Architecture Design

### Layers

#### 1. Parsing Layer (Existing - Keep)
- `XamlParser` - Parse single XAML file
- `ProjectParser` - Parse project with dependencies
- `ParseResult`, `WorkflowContent`, `Activity` - Internal models

#### 2. Normalization Layer (NEW)
- `IdGenerator` - Generate stable deterministic IDs
- `ControlFlowExtractor` - Extract edges from activity tree
- `Normalizer` - Transform parsing models → DTOs
- `Sorter` - Deterministic ordering

#### 3. DTO Layer (NEW)
- `WorkflowDto` - Self-describing workflow representation
- `ActivityDto` - Activity with stable ID and edges
- `EdgeDto` - Control flow edge (Then/Else/transition)
- `InvocationDto` - Workflow invocation reference

#### 4. Emitter Layer (NEW - Pluggable)
- `Emitter` (ABC) - Base class for all emitters
- `DataEmitter` - JSON/YAML/CSV output
- `DiagramEmitter` - Mermaid/DOT/PlantUML
- `DocEmitter` - Jinja2 → Markdown
- `EmitterRegistry` - Plugin discovery via entry points

#### 5. Validation Layer (NEW)
- `SchemaValidator` - JSON Schema validation
- `ReferentialValidator` - Check ID references
- `Validator` - Orchestrate validation

### Data Flow

```
XAML File(s)
    ↓
XamlParser/ProjectParser
    ↓
ParseResult (internal models)
    ↓
Normalizer
    ├─► IdGenerator (stable IDs)
    ├─► ControlFlowExtractor (edges)
    └─► DTO transformation
    ↓
WorkflowDto[] (self-describing)
    ↓
Emitter (pluggable)
    ├─► DataEmitter → JSON/YAML
    ├─► DiagramEmitter → Mermaid/DOT
    └─► DocEmitter → Markdown
```

---

## Data Model (DTOs)

### WorkflowDto

```python
@dataclass
class WorkflowDto:
    """Self-describing workflow DTO."""
    # Metadata
    schema_id: str = "https://rpax.io/schemas/xaml-workflow.json"
    schema_version: str = "1.0.0"
    collected_at: str  # ISO 8601

    # Identity
    id: str  # wf:sha256:abc123def456... (content-hash, truncated to 16 chars)
    name: str
    source: SourceInfo

    # Metadata
    metadata: WorkflowMetadata

    # Content
    variables: list[VariableDto]
    arguments: list[ArgumentDto]
    dependencies: list[DependencyDto]
    activities: list[ActivityDto]
    edges: list[EdgeDto]
    invocations: list[InvocationDto]

    # Issues
    issues: list[IssueDto] = field(default_factory=list)

@dataclass
class SourceInfo:
    path: str  # Current relative path
    path_aliases: list[str]  # Historical paths (for rename tracking)
    hash: str  # sha256:... (full hash)
    size_bytes: int
    encoding: str = "utf-8"

@dataclass
class ActivityDto:
    """Activity with stable ID."""
    id: str  # act:sha256:abc123... (content-hash, truncated to 16 chars)
    type: str  # Fully-qualified: System.Activities.Statements.Sequence
    type_short: str  # Short: Sequence
    display_name: str | None

    # Location
    location: LocationInfo | None

    # Hierarchy
    parent_id: str | None
    children: list[str]  # Child activity IDs
    depth: int

    # Configuration
    properties: dict[str, Any]
    in_args: dict[str, str]  # Arg name → variable/value
    out_args: dict[str, str]

    # Analysis
    annotation: str | None
    expressions: list[str]
    variables_referenced: list[str]

    # Selectors (UI activities)
    selectors: dict[str, str] | None

@dataclass
class EdgeDto:
    """Control flow edge."""
    id: str  # edge:sha256:... (content-hash)
    from_id: str  # Activity ID
    to_id: str  # Activity ID
    kind: str  # "Then", "Else", "Next", "True", "False", "Case", "Default", "Catch", "Finally", "Link", "Transition", "Branch", "Retry", "Timeout", "Done", "Trigger"
    condition: str | None  # For conditional edges (e.g., Case value, If condition)
    label: str | None  # Display label (e.g., Case value for readability)

@dataclass
class InvocationDto:
    """Workflow invocation."""
    callee_id: str  # wf:sha256:... (target workflow ID)
    callee_path: str  # Original reference path (e.g., "./Sub.xaml")
    via_activity_id: str  # act:sha256:... (InvokeWorkflowFile activity)
    arguments_passed: dict[str, str]  # Arg mappings

@dataclass
class LocationInfo:
    line: int | None
    column: int | None
    xpath: str | None
```

### Container Format

```json
{
  "schemaId": "https://rpax.io/schemas/xaml-workflow-collection.json",
  "schemaVersion": "1.0.0",
  "collectedAt": "2025-10-11T07:15:00Z",
  "project": {
    "name": "MyProject",
    "path": "/path/to/project",
    "mainWorkflow": "wf:sha256:abc123def456..."
  },
  "workflows": [
    {
      "id": "wf:sha256:abc123def456...",
      "name": "Main",
      "source": {
        "path": "Main.xaml",
        "path_aliases": [],
        "hash": "sha256:...",
        "size_bytes": 12345,
        "encoding": "utf-8"
      },
      "activities": [...],
      "edges": [...],
      "invocations": [...]
    }
  ],
  "issues": []
}
```

---

## Determinism Rules

To ensure stable, reproducible output across runs, environments, and tool versions:

### Path Handling
- **Internal Representation**: All paths normalized to POSIX format (`/` separators)
- **Relative Paths**: Stored relative to project root when applicable
- **Path Encoding**: UTF-8 only, reject paths with non-UTF-8 sequences
- **Sorting**: Binary collation (byte-wise) using UTF-8 encoding, locale-independent

### Text Normalization
- **Line Endings**: Normalize to LF (`\n`) internally
- **BOM Handling**: Strip UTF-8 BOM if present, error on other BOMs
- **Encoding**: UTF-8 only for input and output
- **XML Declaration**: Omit from normalized output

### Sorting Rules
- **Collections**: Sort by ID (string comparison, UTF-8 binary collation)
- **Activities**: Sorted by stable ID
- **Arguments/Variables**: Sorted by name (case-sensitive, UTF-8 binary)
- **Properties**: Sorted by key name (case-sensitive, UTF-8 binary)
- **Locale Independence**: Never use locale-sensitive sorting (e.g., no strcoll)

### Floating-Point Values
- **Precision**: Round to 6 decimal places for JSON output
- **Format**: Use fixed-point notation (not scientific) for values < 1e6
- **NaN/Infinity**: Represent as JSON null with warning

### Timestamps
- **Format**: ISO 8601 with UTC timezone (`YYYY-MM-DDTHH:MM:SSZ`)
- **Precision**: Second-level precision (no milliseconds)
- **Reproducibility**: Use explicit `--collected-at` flag for reproducible builds

### Hash Stability
- **Algorithm**: SHA-256 with W3C C14N XML normalization
- **Truncation**: First 16 hex characters (64 bits, collision-resistant for typical projects)
- **Input**: Normalized XML only (no metadata like timestamps)

---

## Privacy & Redaction Policy

### Sensitive Data Classification

**High Risk (PII/Credentials)**:
- UI selectors containing user names, email addresses
- Connection strings with embedded credentials
- API keys, tokens, passwords in activity arguments
- File paths containing user names (e.g., `C:\Users\john.doe\`)

**Medium Risk (Business Logic)**:
- Conditional expressions with business rules
- Variable values with configuration data
- Workflow names revealing internal processes

**Low Risk (Technical)**:
- Activity types, namespaces
- Package dependencies
- Control flow structure

### Default Behavior (v1.0.0)
- **No automatic redaction**: Output preserves all data as-is
- **User responsibility**: Users must sanitize input or filter output
- **Warning**: CLI emits warning if high-risk patterns detected (e.g., `password`, `token` in argument names)

### Future Enhancements (v1.1.0+)
- `--redact-selectors`: Hash or mask UI selectors
- `--redact-paths`: Replace user-specific path components with placeholders
- `--redact-patterns FILE`: Custom regex patterns for sensitive data
- `--allow-list FILE`: Explicitly allowed values (e.g., known safe variable names)

### Security Recommendations
1. **Pre-sanitize XAML**: Remove sensitive data before parsing
2. **Access Control**: Restrict output files to authorized users
3. **Audit Trails**: Log who accessed parsed output
4. **Data Classification**: Tag workflows with sensitivity level in project metadata

---

## Implementation Phases

### Phase 0: Foundation & Design (Week 1)

**Goal:** Establish architecture, design DTOs, update schemas

**Deliverables:**
- DTO model definitions in `dto.py`
- JSON Schema for DTOs in `schemas/xaml-workflow-1.0.0.json`
- Architecture decision record (ADR)
- This PLAN.md finalized

**Tasks:**
- [ ] Create `python/xaml_parser/dto.py` with all DTO dataclasses
- [ ] Create `python/schemas/xaml-workflow-1.0.0.json` (JSON Schema)
- [ ] Create `python/schemas/xaml-workflow-collection-1.0.0.json`
- [ ] Document DTO design in `docs/ADR-DTO-DESIGN.md`
- [ ] Update `docs/ARCHITECTURE.md` with new layer diagram

**Validation:**
- DTOs are well-typed (mypy passes)
- JSON Schema validates against sample DTOs
- Architecture is clear and documented

---

### Phase 1: Stable ID Generation (Week 1-2)

**Goal:** Generate deterministic IDs for workflows, activities, edges

**Deliverables:**
- `IdGenerator` class
- Stable IDs in parsing output
- Deterministic ordering utilities

**Tasks:**

#### 1.1: Create ID Generator
- [ ] Create `python/xaml_parser/id_generation.py`
- [ ] Implement `IdGenerator` class
  ```python
  class IdGenerator:
      def generate_workflow_id(self, xml_content: str) -> str:
          """Generate: wf:sha256:... (content-hash, truncated to 16 chars)"""
          content_hash = self._hash_xml_span(xml_content)
          return f"wf:{content_hash}"

      def generate_activity_id(self, xml_span: str) -> str:
          """Generate: act:sha256:... (content-hash, truncated to 16 chars)"""
          span_hash = self._hash_xml_span(xml_span)
          return f"act:{span_hash}"

      def _hash_xml_span(self, xml_span: str) -> str:
          """SHA-256 hash of normalized XML."""
          normalized = self._normalize_xml(xml_span)
          return f"sha256:{hashlib.sha256(normalized.encode()).hexdigest()[:16]}"

      def _normalize_xml(self, xml: str) -> str:
          """Normalize XML for hashing using W3C Canonical XML (C14N).

          Implements subset of https://www.w3.org/TR/xml-c14n for deterministic hashing:
          1. Parse XML to tree (handle encoding, strip BOM)
          2. Normalize namespace declarations (prefix → URI map)
          3. Sort attributes lexicographically by namespace URI then local name
          4. Remove insignificant whitespace (text-only nodes, inter-element)
          5. Serialize deterministically (UTF-8, LF line endings, no XML declaration)

          This ensures minor serialization differences don't flip hashes.
          """
          # Implementation uses xml.etree or lxml with C14N support
          pass
  ```
- [ ] Implement `_normalize_xml()` using W3C C14N (xml.etree or lxml)
- [ ] Implement `_hash_xml_span()` - SHA-256 truncated to 16 chars

#### 1.2: Extract XML Spans
- [ ] Update `XamlParser._extract_activities()` to capture XML span
- [ ] Store raw XML substring for each activity in `Activity.xml_span`
- [ ] Update `Activity` model with `xml_span: str | None` field

#### 1.3: Integrate ID Generation
- [ ] Update `XamlParser.parse_file()` to generate workflow ID
- [ ] Update activity extraction to generate activity IDs
- [ ] Replace `activity_1`, `activity_2` with stable IDs
- [ ] Update `ParseResult` to include `workflow_id: str`

#### 1.4: Deterministic Ordering
- [ ] Create `python/xaml_parser/ordering.py`
- [ ] Implement `sort_by_id()` - Locale-independent sorting
- [ ] Sort activities, arguments, variables by ID/name
- [ ] Ensure consistent ordering across runs

#### 1.5: Testing
- [ ] Create `python/tests/test_id_generation.py`
- [ ] Test workflow ID generation (same content → same ID)
- [ ] Test activity ID generation (stable across runs)
- [ ] Test hash stability (whitespace changes don't affect hash)
- [ ] Test deterministic ordering
- [ ] Golden test: parse same file 10x, verify IDs identical

**Validation:**
- Same XAML file always produces same IDs
- Whitespace-only changes don't change IDs
- IDs are unique within a workflow
- Sorting is deterministic and locale-independent

---

### Phase 2: Control Flow Extraction (Week 2-3)

**Goal:** Extract explicit edges from activity tree

**Deliverables:**
- `ControlFlowExtractor` class
- Edge extraction for If/Switch/FlowDecision/TryCatch
- `EdgeDto` in output

**Tasks:**

#### 2.1: Design Edge Model
- [ ] Define `EdgeDto` dataclass (already in Phase 0)
- [ ] Define edge kinds: `Next`, `Then`, `Else`, `True`, `False`, `Case`, `Default`, `Catch`, `Finally`, `Link`, `Transition`, `Branch`, `Retry`, `Timeout`, `Done`, `Trigger`
- [ ] Document edge semantics in `docs/CONTROL-FLOW.md`

#### 2.2: Create Control Flow Extractor
- [ ] Create `python/xaml_parser/control_flow.py`
- [ ] Implement `ControlFlowExtractor` class
  ```python
  class ControlFlowExtractor:
      def extract_edges(self, activities: list[Activity]) -> list[EdgeDto]:
          """Extract control flow edges from activity tree."""
          edges = []
          for activity in activities:
              edges.extend(self._extract_from_activity(activity))
          return edges

      def _extract_from_activity(self, activity: Activity) -> list[EdgeDto]:
          """Extract edges based on activity type."""
          if activity.activity_type == 'If':
              return self._extract_if_edges(activity)
          elif activity.activity_type == 'Switch':
              return self._extract_switch_edges(activity)
          elif activity.activity_type == 'FlowDecision':
              return self._extract_flow_decision_edges(activity)
          elif activity.activity_type == 'TryCatch':
              return self._extract_try_catch_edges(activity)
          elif activity.activity_type == 'Sequence':
              return self._extract_sequence_edges(activity)
          elif activity.activity_type == 'Flowchart':
              return self._extract_flowchart_edges(activity)
          elif activity.activity_type == 'StateMachine':
              return self._extract_state_machine_edges(activity)
          elif activity.activity_type in ['Parallel', 'ParallelForEach']:
              return self._extract_parallel_edges(activity)
          elif activity.activity_type in ['Pick', 'PickBranch']:
              return self._extract_pick_edges(activity)
          elif activity.activity_type == 'RetryScope':
              return self._extract_retry_scope_edges(activity)
          else:
              return []
  ```

#### 2.3: Implement Edge Extractors
- [ ] Implement `_extract_if_edges()` - Then/Else branches
- [ ] Implement `_extract_switch_edges()` - Case/Default branches
- [ ] Implement `_extract_flow_decision_edges()` - True/False paths
- [ ] Implement `_extract_try_catch_edges()` - Try/Catch/Finally
- [ ] Implement `_extract_sequence_edges()` - Sequential Next edges
- [ ] Implement `_extract_flowchart_edges()` - Link connections between nodes
- [ ] Implement `_extract_state_machine_edges()` - Transition edges with triggers
- [ ] Implement `_extract_parallel_edges()` - Branch edges for parallel execution
- [ ] Implement `_extract_pick_edges()` - Trigger-based branches
- [ ] Implement `_extract_retry_scope_edges()` - Retry/Timeout/Done edges

#### 2.4: Extract Branch Conditions
- [ ] Extract condition expressions from If activities
- [ ] Extract switch expression from Switch activities
- [ ] Store condition in `EdgeDto.condition`

#### 2.5: Invocation Tracking
- [ ] Create `InvocationDto` model
- [ ] Extract InvokeWorkflowFile references
- [ ] Link invocations to target workflow IDs
- [ ] Extract argument mappings

#### 2.6: Testing
- [ ] Create `python/tests/test_control_flow.py`
- [ ] Test If activity → Then/Else edges
- [ ] Test Switch activity → Case edges
- [ ] Test Sequence → Next edges
- [ ] Test TryCatch → Try/Catch/Finally edges
- [ ] Test invocation extraction
- [ ] Golden test: complex workflow with all edge types

**Validation:**
- All conditional branches extracted as edges
- Edge IDs are stable
- Conditions preserved in edges
- Invocations link to correct workflow IDs

---

### Phase 3: DTO Layer & Normalization (Week 3-4)

**Goal:** Transform parsing models to self-describing DTOs

**Deliverables:**
- `Normalizer` class
- Adapter functions (ParseResult → WorkflowDto)
- Self-describing output with metadata

**Tasks:**

#### 3.1: Create Normalizer
- [ ] Create `python/xaml_parser/normalization.py`
- [ ] Implement `Normalizer` class
  ```python
  class Normalizer:
      def __init__(self, id_generator: IdGenerator,
                   flow_extractor: ControlFlowExtractor):
          self.id_gen = id_generator
          self.flow_extractor = flow_extractor

      def normalize(self,
                    parse_result: ParseResult,
                    project_context: ProjectContext | None = None
                   ) -> WorkflowDto:
          """Transform ParseResult to WorkflowDto."""
          # 1. Generate workflow ID
          # 2. Transform activities with stable IDs
          # 3. Extract edges
          # 4. Extract invocations
          # 5. Sort deterministically
          # 6. Add metadata
          pass
  ```

#### 3.2: Implement Transformations
- [ ] Implement `_transform_activity()` - Activity → ActivityDto
  - Map all fields with stable IDs
- [ ] Add SDK inspection fields for developer debugging
  - Include `apath` (canonical child path), `loc` (line/column), and `debug_ref`
  - `debug_ref` example:
    `"debug_ref": "XamlogueDebug.Dump(XamlogueDebug.Resolve(context, \"aid:9f1c3a7b8c2d4e5f\"))"`
  - Emit only when `--emit-debug` flag or `profile=debug`
  - Deterministic and safe for text logs
  - Document structure in `docs/OUTPUT-FIELDS.md`


  - Extract properties, in_args, out_args
  - Preserve expressions, annotations
- [ ] Implement `_transform_argument()` - WorkflowArgument → ArgumentDto
- [ ] Implement `_transform_variable()` - WorkflowVariable → VariableDto
- [ ] Implement `_transform_dependency()` - Extract from assembly refs

#### 3.3: Self-Describing Metadata
- [ ] Add `schema_id`, `schema_version` to WorkflowDto
- [ ] Add `collected_at` timestamp (ISO 8601)
- [ ] Add `source` info (path, hash, size)
- [ ] Add project context if available

#### 3.4: Field Selection (Profiles)
- [ ] Create `python/xaml_parser/field_profiles.py`
- [ ] Define field profiles: `full`, `minimal`, `mcp`, `datalake`
  ```python
  PROFILES = {
      'full': None,  # All fields
      'minimal': ['id', 'type', 'display_name', 'depth'],
      'mcp': ['id', 'type', 'display_name', 'properties',
              'in_args', 'out_args', 'expressions', 'annotation'],
      'datalake': None  # Full but exclude ViewState
  }
  ```
- [ ] Implement `apply_profile()` - Filter DTO fields
- [ ] Support custom field lists via config

#### 3.5: Testing
- [ ] Create `python/tests/test_normalization.py`
- [ ] Test ParseResult → WorkflowDto transformation
- [ ] Test all field mappings preserved
- [ ] Test stable IDs in DTOs
- [ ] Test edges included in DTO
- [ ] Test self-describing metadata
- [ ] Test field profiles
- [ ] Golden test: complex workflow → DTO with all features

**Validation:**
- DTOs contain all information from ParseResult
- IDs are stable and deterministic
- Edges correctly extracted
- Metadata is complete
- Field profiles work correctly

---

### Phase 4: Emitter Architecture (Week 4-5)

**Goal:** Pluggable emitter system with data emitters

**Deliverables:**
- `Emitter` base class
- `EmitterRegistry` with plugin discovery
- `JsonEmitter`, `YamlEmitter`
- CLI integration

**Tasks:**

#### 4.1: Design Emitter Interface
- [ ] Create `python/xaml_parser/emitters/__init__.py`
- [ ] Define `Emitter` abstract base class
  ```python
  class Emitter(ABC):
      """Base class for all emitters."""

      @property
      @abstractmethod
      def name(self) -> str:
          """Emitter name (e.g., 'json', 'mermaid')."""
          pass

      @property
      @abstractmethod
      def output_extension(self) -> str:
          """Output file extension (e.g., '.json', '.mmd')."""
          pass

      @abstractmethod
      def emit(self,
               workflows: list[WorkflowDto],
               output_path: Path,
               config: EmitterConfig) -> EmitResult:
          """Emit output files."""
          pass

      @abstractmethod
      def validate_config(self, config: EmitterConfig) -> list[str]:
          """Validate emitter configuration."""
          pass

  @dataclass
  class EmitterConfig:
      """Configuration for emitter."""
      field_profile: str = 'full'
      combine: bool = False  # Single file vs. one-per-workflow
      pretty: bool = True
      exclude_none: bool = True
      extra: dict[str, Any] = field(default_factory=dict)

  @dataclass
  class EmitResult:
      """Result of emission."""
      success: bool
      files_written: list[Path]
      errors: list[str]
      warnings: list[str]
  ```

#### 4.2: Implement Emitter Registry
- [ ] Create `python/xaml_parser/emitters/registry.py`
- [ ] Implement `EmitterRegistry`
  ```python
  class EmitterRegistry:
      """Registry for discovering and loading emitters."""

      _emitters: dict[str, type[Emitter]] = {}

      @classmethod
      def register(cls, emitter_class: type[Emitter]):
          """Register an emitter."""
          cls._emitters[emitter_class.name] = emitter_class

      @classmethod
      def get_emitter(cls, name: str) -> Emitter:
          """Get emitter by name."""
          if name not in cls._emitters:
              raise ValueError(f"Unknown emitter: {name}")
          return cls._emitters[name]()

      @classmethod
      def discover_plugins(cls):
          """Discover emitters via entry points."""
          import importlib.metadata

          for entry_point in importlib.metadata.entry_points(
              group='xamlparser.emitters'
          ):
              emitter_class = entry_point.load()
              cls.register(emitter_class)

      @classmethod
      def list_emitters(cls) -> list[str]:
          """List all registered emitters."""
          return list(cls._emitters.keys())
  ```

#### 4.3: Implement JSON Emitter
- [ ] Create `python/xaml_parser/emitters/json_emitter.py`
- [ ] Implement `JsonEmitter`
  ```python
  class JsonEmitter(Emitter):
      name = "json"
      output_extension = ".json"

      def emit(self, workflows, output_path, config):
          if config.combine:
              return self._emit_combined(workflows, output_path, config)
          else:
              return self._emit_per_workflow(workflows, output_path, config)

      def _emit_combined(self, workflows, output_path, config):
          """Emit single combined JSON file."""
          data = {
              "schemaId": "https://rpax.io/schemas/xaml-workflow-collection.json",
              "schemaVersion": "1.0.0",
              "collectedAt": datetime.now(timezone.utc).isoformat(),
              "workflows": [self._to_dict(wf, config) for wf in workflows]
          }

          with open(output_path, 'w', encoding='utf-8') as f:
              json.dump(data, f, indent=2 if config.pretty else None)

          return EmitResult(success=True, files_written=[output_path])

      def _emit_per_workflow(self, workflows, output_dir, config):
          """Emit one JSON file per workflow."""
          output_dir.mkdir(parents=True, exist_ok=True)
          files_written = []

          for workflow in workflows:
              filename = f"{workflow.name}.json"
              file_path = output_dir / filename

              data = self._to_dict(workflow, config)

              with open(file_path, 'w', encoding='utf-8') as f:
                  json.dump(data, f, indent=2 if config.pretty else None)

              files_written.append(file_path)

          return EmitResult(success=True, files_written=files_written)

      def _to_dict(self, workflow: WorkflowDto, config: EmitterConfig) -> dict:
          """Convert WorkflowDto to dict with field selection."""
          data = dataclasses.asdict(workflow)

          # Apply field profile
          if config.field_profile != 'full':
              data = self._apply_profile(data, config.field_profile)

          # Exclude None values
          if config.exclude_none:
              data = self._exclude_none(data)

          return data
  ```
- [ ] Register with `EmitterRegistry`

#### 4.4: Implement YAML Emitter (Deferred to v1.1.0)
- [ ] ~~Create `python/xaml_parser/emitters/yaml_emitter.py`~~ (v1.1.0)
- [ ] ~~Implement `YamlEmitter` (similar to JsonEmitter)~~ (v1.1.0)
- [ ] ~~Add pyyaml as optional dependency~~ (v1.1.0)
- [ ] ~~Register with `EmitterRegistry`~~ (v1.1.0)

#### 4.5: Update pyproject.toml
- [ ] Add entry point for plugin discovery
  ```toml
  [project.entry-points."xamlparser.emitters"]
  json = "xaml_parser.emitters.json_emitter:JsonEmitter"
  # yaml = "xaml_parser.emitters.yaml_emitter:YamlEmitter"  # v1.1.0
  ```
- [ ] Add optional dependencies
  ```toml
  [project.optional-dependencies]
  diagrams = ["jinja2>=3.1"]
  docs = ["jinja2>=3.1"]
  # yaml = ["pyyaml>=6.0"]  # v1.1.0
  # full = ["pyyaml>=6.0", "jinja2>=3.1"]  # v1.1.0
  ```

#### 4.6: Testing
- [ ] Create `python/tests/test_emitters.py`
- [ ] Test JSON emitter (combined mode)
- [ ] Test JSON emitter (per-workflow mode)
- [ ] Test field profiles
- [ ] Test emitter registry discovery
- [ ] Test plugin loading
- [ ] ~~Test YAML emitter~~ (deferred to v1.1.0)

**Validation:**
- JSON emitter produces valid JSON
- Combined mode creates single file
- Per-workflow mode creates multiple files
- Field profiles applied correctly
- Registry discovers built-in emitters
- Output is deterministic across runs

---

### Phase 5: Diagram Generation (Week 5-6)

**Goal:** Generate Mermaid diagrams from workflows

**Deliverables:**
- `MermaidEmitter` class
- Activity graph visualization
- Control flow edges in diagrams

**Tasks:**

#### 5.1: Design Diagram Structure
- [ ] Document Mermaid diagram format in `docs/DIAGRAMS.md`
- [ ] Define node labeling strategy (displayName + type)
- [ ] Define edge labeling (Then/Else/etc.)
- [ ] Define subgraph strategy (Sequence/Flowchart containers)

#### 5.2: Implement Mermaid Emitter
- [ ] Create `python/xaml_parser/emitters/mermaid_emitter.py`
- [ ] Implement `MermaidEmitter`
  ```python
  class MermaidEmitter(Emitter):
      name = "mermaid"
      output_extension = ".mmd"

      def emit(self, workflows, output_path, config):
          output_path.mkdir(parents=True, exist_ok=True)
          files_written = []

          for workflow in workflows:
              diagram = self._generate_diagram(workflow, config)
              filename = f"{workflow.name}.mmd"
              file_path = output_path / filename

              file_path.write_text(diagram, encoding='utf-8')
              files_written.append(file_path)

          return EmitResult(success=True, files_written=files_written)

      def _generate_diagram(self, workflow: WorkflowDto, config) -> str:
          """Generate Mermaid flowchart."""
          lines = ["flowchart TD"]

          # Generate nodes
          for activity in workflow.activities:
              node_id = self._sanitize_id(activity.id)
              label = self._format_label(activity)
              lines.append(f'  {node_id}["{label}"]')

          # Generate edges
          for edge in workflow.edges:
              from_id = self._sanitize_id(edge.from_id)
              to_id = self._sanitize_id(edge.to_id)
              label = f"|{edge.kind}|" if edge.kind else ""
              lines.append(f'  {from_id} -->{label} {to_id}')

          return "\n".join(lines)

      def _sanitize_id(self, id: str) -> str:
          """Sanitize ID for Mermaid (alphanumeric only)."""
          return re.sub(r'[^a-zA-Z0-9_]', '_', id)

      def _format_label(self, activity: ActivityDto) -> str:
          """Format activity label."""
          name = activity.display_name or activity.type_short
          return f"{name}\\n({activity.type_short})"
  ```
- [ ] Register with `EmitterRegistry`

#### 5.3: Handle Complex Structures
- [ ] Implement subgraphs for Sequence activities
- [ ] Implement subgraphs for Flowchart activities
- [ ] Handle nested containers
- [ ] Limit depth for readability (configurable)

#### 5.4: Styling and Customization
- [ ] Add node styling based on activity type
  - Decision nodes (diamond)
  - Action nodes (rectangle)
  - Container nodes (rounded rectangle)
- [ ] Add edge styling based on kind
  - Then/Else (different colors)
  - Error paths (red)
- [ ] Support custom CSS classes via config

#### 5.5: Testing
- [ ] Create `python/tests/test_mermaid_emitter.py`
- [ ] Test simple sequence diagram
- [ ] Test If/Then/Else diagram
- [ ] Test nested containers
- [ ] Test edge labeling
- [ ] Golden test: complex workflow → Mermaid
- [ ] Visual validation: render with Mermaid CLI

**Validation:**
- Mermaid files are syntactically valid
- Diagrams render correctly in Mermaid viewer
- Control flow is accurately represented
- Node labels are clear and readable

---

### Phase 6: Documentation Generation (Week 6-7)

**Goal:** Generate Markdown docs from workflows

**Deliverables:**
- `DocEmitter` class
- Jinja2 templates for workflow docs
- Index generation

**Tasks:**

#### 6.1: Design Doc Structure
- [ ] Document doc structure in `docs/DOCUMENTATION.md`
- [ ] Define per-workflow doc format
  - Header (name, description)
  - Arguments table
  - Variables table
  - Activity list
  - Invocations
- [ ] Define index doc format
  - Project summary
  - Workflow list
  - Call graph

#### 6.2: Create Jinja2 Templates
- [ ] Create `python/xaml_parser/templates/workflow.md.j2`
  ```jinja2
  # {{ workflow.name }}

  {% if workflow.metadata.annotation %}
  {{ workflow.metadata.annotation }}
  {% endif %}

  **Source:** `{{ workflow.source.path }}`
  **Language:** {{ workflow.metadata.expression_language }}

  ## Arguments

  | Name | Type | Direction | Description |
  | ---- | ---- | --------- | ----------- |
  {% for arg in workflow.arguments %}
  | {{ arg.name }} | {{ arg.type }} | {{ arg.direction }} | {{ arg.annotation or "-" }} |
  {% endfor %}

  ## Variables

  | Name | Type | Scope | Default |
  | ---- | ---- | ----- | ------- |
  {% for var in workflow.variables %}
  | {{ var.name }} | {{ var.type }} | {{ var.scope }} | {{ var.default or "-" }} |
  {% endfor %}

  ## Activities

  {% for activity in workflow.activities %}
  ### {{ activity.display_name or activity.type_short }}

  **Type:** {{ activity.type }}
  **ID:** `{{ activity.id }}`

  {% if activity.annotation %}
  {{ activity.annotation }}
  {% endif %}

  {% if activity.properties %}
  **Properties:**
  {% for key, value in activity.properties.items() %}
  - {{ key }}: {{ value }}
  {% endfor %}
  {% endif %}

  {% endfor %}

  ## Invocations

  {% for inv in workflow.invocations %}
  - Calls `{{ inv.callee_id }}` via `{{ inv.via_activity_id }}`
  {% endfor %}
  ```
- [ ] Create `python/xaml_parser/templates/index.md.j2`
  ```jinja2
  # {{ project.name }}

  **Path:** `{{ project.path }}`
  **Main Workflow:** {{ project.main_workflow }}

  ## Workflows

  | Workflow | Activities | Arguments | Variables |
  | -------- | ---------- | --------- | --------- |
  {% for wf in workflows %}
  | [{{ wf.name }}](workflows/{{ wf.name }}.md) | {{ wf.activities|length }} | {{ wf.arguments|length }} | {{ wf.variables|length }} |
  {% endfor %}

  ## Call Graph

  {% for wf in workflows %}
  - **{{ wf.name }}**
    {% for inv in wf.invocations %}
    - → {{ inv.callee_id }}
    {% endfor %}
  {% endfor %}
  ```

#### 6.3: Implement Doc Emitter
- [ ] Create `python/xaml_parser/emitters/doc_emitter.py`
- [ ] Implement `DocEmitter`
  ```python
  class DocEmitter(Emitter):
      name = "doc"
      output_extension = ".md"

      def __init__(self):
          from jinja2 import Environment, PackageLoader
          self.env = Environment(
              loader=PackageLoader('xaml_parser', 'templates')
          )

      def emit(self, workflows, output_path, config):
          output_path.mkdir(parents=True, exist_ok=True)
          workflows_dir = output_path / "workflows"
          workflows_dir.mkdir(exist_ok=True)

          files_written = []

          # Generate per-workflow docs
          for workflow in workflows:
              doc = self._generate_workflow_doc(workflow, config)
              filename = f"{workflow.name}.md"
              file_path = workflows_dir / filename
              file_path.write_text(doc, encoding='utf-8')
              files_written.append(file_path)

          # Generate index
          index = self._generate_index(workflows, config)
          index_path = output_path / "index.md"
          index_path.write_text(index, encoding='utf-8')
          files_written.append(index_path)

          return EmitResult(success=True, files_written=files_written)

      def _generate_workflow_doc(self, workflow, config):
          template = self.env.get_template('workflow.md.j2')
          return template.render(workflow=workflow)

      def _generate_index(self, workflows, config):
          template = self.env.get_template('index.md.j2')
          project_info = self._extract_project_info(workflows, config)
          return template.render(project=project_info, workflows=workflows)
  ```
- [ ] Register with `EmitterRegistry`

#### 6.4: Custom Templates
- [ ] Support `--template-dir` to override templates
- [ ] Document template variables in `docs/TEMPLATE-GUIDE.md`
- [ ] Create example custom template

#### 6.5: Testing
- [ ] Create `python/tests/test_doc_emitter.py`
- [ ] Test workflow doc generation
- [ ] Test index generation
- [ ] Test template rendering
- [ ] Test custom template directory
- [ ] Golden test: complex workflow → Markdown
- [ ] Visual validation: render in Markdown viewer

**Validation:**
- Markdown files are valid
- Tables render correctly
- Links work
- Custom templates can override defaults

---

### Phase 7: CLI & Validation (Week 7-8)

**Goal:** Comprehensive CLI with subcommands and validation

**Deliverables:**
- New CLI with subcommands (parse, diagram, doc, validate, schema)
- Config file support (xamlparser.yaml)
- Validation subcommand

**Tasks:**

#### 7.1: Redesign CLI Structure
- [ ] Create `python/xaml_parser/cli/__init__.py`
- [ ] Create subcommand structure
  ```python
  def main():
      parser = argparse.ArgumentParser(prog='xamlp')
      subparsers = parser.add_subparsers(dest='command')

      # Parse subcommand
      parse_parser = subparsers.add_parser('parse')
      parse_parser.add_argument('--in', required=True)
      parse_parser.add_argument('--out', required=True)
      parse_parser.add_argument('--format', choices=['json'], default='json')  # yaml in v1.1.0
      parse_parser.add_argument('--combine', action='store_true')
      parse_parser.add_argument('--schema-version', default='1.0.0')
      parse_parser.add_argument('--fields', choices=['full', 'minimal', 'mcp', 'datalake'])

      # Diagram subcommand
      diagram_parser = subparsers.add_parser('diagram')
      diagram_parser.add_argument('--in', required=True)
      diagram_parser.add_argument('--out', required=True)
      diagram_parser.add_argument('--type', choices=['mermaid'], default='mermaid')  # dot, plantuml in v1.1.0

      # Doc subcommand
      doc_parser = subparsers.add_parser('doc')
      doc_parser.add_argument('--in', required=True)
      doc_parser.add_argument('--out', required=True)
      doc_parser.add_argument('--template')

      # Validate subcommand
      validate_parser = subparsers.add_parser('validate')
      validate_parser.add_argument('--in', required=True)
      validate_parser.add_argument('--strict', action='store_true')

      # Schema subcommand
      schema_parser = subparsers.add_parser('schema')
      schema_parser.add_argument('--print', action='store_true')

      args = parser.parse_args()

      if args.command == 'parse':
          return handle_parse(args)
      elif args.command == 'diagram':
          return handle_diagram(args)
      # ...
  ```

#### 7.2: Implement Subcommand Handlers
- [ ] Create `python/xaml_parser/cli/parse_command.py`
  ```python
  def handle_parse(args):
      """Handle parse subcommand."""
      # 1. Load config file if exists
      config = load_config(args.config)

      # 2. Parse workflows
      parser = XamlParser(config.parser)
      if Path(args.in_path).is_dir():
          project_parser = ProjectParser(config.parser)
          project_result = project_parser.parse_project(args.in_path)
          parse_results = [w.parse_result for w in project_result.workflows]
      else:
          parse_results = [parser.parse_file(Path(args.in_path))]

      # 3. Normalize to DTOs
      normalizer = Normalizer(IdGenerator(), ControlFlowExtractor())
      workflows = [normalizer.normalize(pr) for pr in parse_results]

      # 4. Emit
      emitter_config = EmitterConfig(
          field_profile=args.fields,
          combine=args.combine,
          pretty=args.pretty
      )
      emitter = EmitterRegistry.get_emitter(args.format)
      result = emitter.emit(workflows, Path(args.out), emitter_config)

      # 5. Report
      if result.success:
          print(f"✓ Emitted {len(result.files_written)} files to {args.out}")
          return 0
      else:
          print(f"✗ Errors: {result.errors}", file=sys.stderr)
          return 1
  ```
- [ ] Create `python/xaml_parser/cli/diagram_command.py`
- [ ] Create `python/xaml_parser/cli/doc_command.py`
- [ ] Create `python/xaml_parser/cli/validate_command.py`
- [ ] Create `python/xaml_parser/cli/schema_command.py`

#### 7.3: Config File Support
- [ ] Create `python/xaml_parser/config.py`
- [ ] Implement config loading (YAML/TOML/JSON)
  ```python
  @dataclass
  class XamlParserConfig:
      """Complete configuration."""
      parser: ParserConfig
      emitters: dict[str, EmitterConfig]
      exclude: list[str] = field(default_factory=list)
      schema_version: str = "1.0.0"

      @classmethod
      def load(cls, path: Path) -> 'XamlParserConfig':
          """Load config from file."""
          if path.suffix == '.yaml' or path.suffix == '.yml':
              import yaml
              with open(path) as f:
                  data = yaml.safe_load(f)
          elif path.suffix == '.toml':
              import tomllib
              with open(path, 'rb') as f:
                  data = tomllib.load(f)
          elif path.suffix == '.json':
              with open(path) as f:
                  data = json.load(f)
          else:
              raise ValueError(f"Unsupported config format: {path.suffix}")

          return cls(**data)
  ```
- [ ] Example config: `xamlparser.yaml`
  ```yaml
  exclude:
    - "**/Tests/**"
    - "**/.local/**"

  schema_version: "1.0.0"

  parser:
    extract_expressions: true
    extract_viewstate: false
    strict_mode: false

  emitters:
    json:
      field_profile: "mcp"
      pretty: true
      exclude_none: true

    mermaid:
      max_depth: 5
      style: "default"

    doc:
      template: "default"
  ```

#### 7.4: Implement Validation
- [ ] Create `python/xaml_parser/validation.py`
- [ ] Implement `SchemaValidator`
  ```python
  class SchemaValidator:
      def __init__(self, schema_path: Path):
          with open(schema_path) as f:
              self.schema = json.load(f)

      def validate(self, workflow_dto: WorkflowDto) -> list[ValidationIssue]:
          """Validate DTO against JSON Schema."""
          import jsonschema

          data = dataclasses.asdict(workflow_dto)
          errors = []

          try:
              jsonschema.validate(data, self.schema)
          except jsonschema.ValidationError as e:
              errors.append(ValidationIssue(
                  level='error',
                  message=e.message,
                  path=e.json_path
              ))

          return errors
  ```
- [ ] Implement `ReferentialValidator`
  ```python
  class ReferentialValidator:
      def validate(self, workflows: list[WorkflowDto]) -> list[ValidationIssue]:
          """Validate referential integrity."""
          errors = []

          # Build ID index
          all_ids = set()
          for wf in workflows:
              all_ids.add(wf.id)
              for act in wf.activities:
                  all_ids.add(act.id)

          # Check edge references
          for wf in workflows:
              for edge in wf.edges:
                  if edge.from_id not in all_ids:
                      errors.append(ValidationIssue(
                          level='error',
                          message=f"Edge references unknown activity: {edge.from_id}"
                      ))
                  if edge.to_id not in all_ids:
                      errors.append(ValidationIssue(
                          level='error',
                          message=f"Edge references unknown activity: {edge.to_id}"
                      ))

          # Check invocations
          for wf in workflows:
              for inv in wf.invocations:
                  if inv.callee_id not in {w.id for w in workflows}:
                      errors.append(ValidationIssue(
                          level='warning',
                          message=f"Invocation to external workflow: {inv.callee_id}"
                      ))

          return errors
  ```

#### 7.5: Exit Codes
- [ ] Document exit codes
  - `0` - Success
  - `1` - Parse errors
  - `2` - Validation errors
  - `3` - Configuration errors
- [ ] Implement exit code logic

#### 7.6: Common Flags
- [ ] `--glob` - Glob pattern for file selection
- [ ] `--ignore` - Ignore patterns
- [ ] `--workers N` - Parallel processing (future)
- [ ] `--quiet` - Suppress output
- [ ] `--pretty` - Pretty print
- [ ] `--no-color` - Disable color output
- [ ] `--fail-on-warn` - Fail on warnings

#### 7.7: Testing
- [ ] Create `python/tests/test_cli.py`
- [ ] Test parse subcommand
- [ ] Test diagram subcommand
- [ ] Test doc subcommand
- [ ] Test validate subcommand
- [ ] Test schema subcommand
- [ ] Test config file loading
- [ ] Test exit codes
- [ ] Integration test: full pipeline

**Validation:**
- All subcommands work correctly
- Config file overrides CLI args
- Validation catches errors
- Exit codes are correct

---

### Phase 8: Testing & Documentation (Week 8-9)

**Goal:** Comprehensive testing and documentation

**Deliverables:**
- Full test suite (≥90% coverage)
- Golden tests
- Documentation complete

**Tasks:**

#### 8.1: Comprehensive Unit Tests
- [ ] Achieve ≥90% coverage across all modules
- [ ] Test all ID generation edge cases
- [ ] Test all control flow extraction patterns
- [ ] Test all emitters with various configs
- [ ] Test normalization with complex workflows
- [ ] Test validation with invalid data

#### 8.2: Golden Tests
- [ ] Create `python/tests/golden/` directory structure
  ```
  tests/golden/
    simple_sequence/
      input.xaml
      expected.json
      expected.mmd
      expected.md
    complex_workflow/
      input.xaml
      expected.json
      expected.mmd
      expected.md
  ```
- [ ] Implement golden test framework
  ```python
  def test_golden_simple_sequence():
      """Test against golden output."""
      input_path = GOLDEN_DIR / "simple_sequence" / "input.xaml"
      expected_json = GOLDEN_DIR / "simple_sequence" / "expected.json"

      # Parse and normalize
      parser = XamlParser()
      result = parser.parse_file(input_path)
      normalizer = Normalizer(IdGenerator(), ControlFlowExtractor())
      workflow = normalizer.normalize(result)

      # Emit JSON
      emitter = JsonEmitter()
      output = emitter.emit([workflow], tmp_path, EmitterConfig())

      # Compare
      with open(output.files_written[0]) as f:
          actual = json.load(f)
      with open(expected_json) as f:
          expected = json.load(f)

      assert actual == expected
  ```
- [ ] Add `--update-golden` flag to regenerate expectations

#### 8.3: Determinism Tests
- [ ] Test: parse same file 100x, verify identical IDs
- [ ] Test: parse on different machines, verify identical output
- [ ] Test: parse with different Python versions, verify identical output
- [ ] Test: sort stability across locales

#### 8.4: Performance Tests
- [ ] Benchmark parse time (target: <100ms per workflow)
- [ ] Benchmark normalization time (target: <50ms per workflow)
- [ ] Test large project (1000 workflows)
- [ ] Memory profiling
- [ ] Create `python/tests/performance/` directory

#### 8.5: Integration Tests
- [ ] Test full pipeline: parse → normalize → emit
- [ ] Test all emitter combinations
- [ ] Test CLI with real UiPath projects
- [ ] Test error handling and recovery

#### 8.6: Documentation
- [ ] Complete `docs/ARCHITECTURE.md`
- [ ] Complete `docs/API.md`
- [ ] Complete `docs/CLI.md`
- [ ] Complete `docs/EMITTERS.md`
- [ ] Complete `docs/DIAGRAMS.md`
- [ ] Complete `docs/TEMPLATES.md`
- [ ] Complete `docs/CONFIGURATION.md`
- [ ] Complete `docs/VALIDATION.md`
- [ ] Update `README.md` with quick start
- [ ] Create `CHANGELOG.md` for v1.0.0

#### 8.7: Example Workflows
- [ ] Create `examples/simple/` - Basic workflow
- [ ] Create `examples/complex/` - Complex with all features
- [ ] Create `examples/custom_emitter/` - Plugin example
- [ ] Create `examples/library_usage/` - API usage

**Validation:**
- Test coverage ≥90%
- All golden tests pass
- Performance targets met
- Documentation is complete

---

## Todo Checklist

### Phase 0: Foundation & Design
- [ ] Create `python/xaml_parser/dto.py` with all DTOs
- [ ] Create `python/schemas/xaml-workflow-1.0.0.json`
- [ ] Create `python/schemas/xaml-workflow-collection-1.0.0.json`
- [ ] Document DTO design in `docs/ADR-DTO-DESIGN.md`
- [ ] Update `docs/ARCHITECTURE.md`

### Phase 1: Stable ID Generation
- [ ] Create `python/xaml_parser/id_generation.py`
- [ ] Implement `IdGenerator` class
- [ ] Implement `generate_workflow_id()`
- [ ] Implement `generate_activity_id()`
- [ ] Implement `_hash_xml_span()`
- [ ] Implement `_normalize_xml()`
- [ ] Update `Activity` model with `xml_span` field
- [ ] Update `XamlParser` to capture XML spans
- [ ] Update `XamlParser` to generate stable IDs
- [ ] Create `python/xaml_parser/ordering.py`
- [ ] Implement `sort_by_id()`
- [ ] Create `python/tests/test_id_generation.py`
- [ ] Write ID generation tests
- [ ] Write determinism tests
- [ ] Run tests: `pytest python/tests/test_id_generation.py -v`

### Phase 2: Control Flow Extraction
- [ ] Define `EdgeDto` dataclass
- [ ] Document edge semantics in `docs/CONTROL-FLOW.md`
- [ ] Create `python/xaml_parser/control_flow.py`
- [ ] Implement `ControlFlowExtractor` class
- [ ] Implement `_extract_if_edges()`
- [ ] Implement `_extract_switch_edges()`
- [ ] Implement `_extract_flow_decision_edges()`
- [ ] Implement `_extract_try_catch_edges()`
- [ ] Implement `_extract_sequence_edges()`
- [ ] Extract branch conditions
- [ ] Create `InvocationDto` model
- [ ] Extract InvokeWorkflowFile references
- [ ] Create `python/tests/test_control_flow.py`
- [ ] Write control flow tests
- [ ] Run tests: `pytest python/tests/test_control_flow.py -v`

### Phase 3: DTO Layer & Normalization
- [ ] Create `python/xaml_parser/normalization.py`
- [ ] Implement `Normalizer` class
- [ ] Implement `_transform_activity()`
- [ ] Implement `_transform_argument()`
- [ ] Implement `_transform_variable()`
- [ ] Implement `_transform_dependency()`
- [ ] Add self-describing metadata
- [ ] Create `python/xaml_parser/field_profiles.py`
- [ ] Define field profiles (full, minimal, mcp, datalake)
- [ ] Implement `apply_profile()`
- [ ] Create `python/tests/test_normalization.py`
- [ ] Write normalization tests
- [ ] Run tests: `pytest python/tests/test_normalization.py -v`

### Phase 4: Emitter Architecture
- [ ] Create `python/xaml_parser/emitters/__init__.py`
- [ ] Define `Emitter` ABC
- [ ] Define `EmitterConfig` dataclass
- [ ] Define `EmitResult` dataclass
- [ ] Create `python/xaml_parser/emitters/registry.py`
- [ ] Implement `EmitterRegistry`
- [ ] Implement plugin discovery
- [ ] Create `python/xaml_parser/emitters/json_emitter.py`
- [ ] Implement `JsonEmitter`
- [ ] Implement combined mode
- [ ] Implement per-workflow mode
- [ ] ~~Create `python/xaml_parser/emitters/yaml_emitter.py`~~ (v1.1.0)
- [ ] ~~Implement `YamlEmitter`~~ (v1.1.0)
- [ ] Update `pyproject.toml` with entry points (JSON only)
- [ ] Update `pyproject.toml` with optional deps
- [ ] Create `python/tests/test_emitters.py`
- [ ] Write emitter tests
- [ ] Run tests: `pytest python/tests/test_emitters.py -v`

### Phase 5: Diagram Generation
- [ ] Document Mermaid format in `docs/DIAGRAMS.md`
- [ ] Create `python/xaml_parser/emitters/mermaid_emitter.py`
- [ ] Implement `MermaidEmitter`
- [ ] Implement `_generate_diagram()`
- [ ] Implement `_sanitize_id()`
- [ ] Implement `_format_label()`
- [ ] Implement subgraphs for containers
- [ ] Add node styling
- [ ] Add edge styling
- [ ] Create `python/tests/test_mermaid_emitter.py`
- [ ] Write Mermaid tests
- [ ] Run tests: `pytest python/tests/test_mermaid_emitter.py -v`

### Phase 6: Documentation Generation
- [ ] Document doc structure in `docs/DOCUMENTATION.md`
- [ ] Create `python/xaml_parser/templates/workflow.md.j2`
- [ ] Create `python/xaml_parser/templates/index.md.j2`
- [ ] Create `python/xaml_parser/emitters/doc_emitter.py`
- [ ] Implement `DocEmitter`
- [ ] Implement `_generate_workflow_doc()`
- [ ] Implement `_generate_index()`
- [ ] Support custom template directory
- [ ] Create `python/tests/test_doc_emitter.py`
- [ ] Write doc emitter tests
- [ ] Run tests: `pytest python/tests/test_doc_emitter.py -v`

### Phase 7: CLI & Validation
- [ ] Create `python/xaml_parser/cli/__init__.py`
- [ ] Design CLI structure with subcommands
- [ ] Create `python/xaml_parser/cli/parse_command.py`
- [ ] Create `python/xaml_parser/cli/diagram_command.py`
- [ ] Create `python/xaml_parser/cli/doc_command.py`
- [ ] Create `python/xaml_parser/cli/validate_command.py`
- [ ] Create `python/xaml_parser/cli/schema_command.py`
- [ ] Create `python/xaml_parser/config.py`
- [ ] Implement config loading (YAML/TOML/JSON)
- [ ] Create example `xamlparser.yaml`
- [ ] Create `python/xaml_parser/validation.py`
- [ ] Implement `SchemaValidator`
- [ ] Implement `ReferentialValidator`
- [ ] Implement exit codes
- [ ] Add common flags
- [ ] Create `python/tests/test_cli.py`
- [ ] Write CLI tests
- [ ] Run tests: `pytest python/tests/test_cli.py -v`

### Phase 8: Testing & Documentation
- [ ] Achieve ≥90% test coverage
- [ ] Create golden tests directory structure
- [ ] Implement golden test framework
- [ ] Create golden test fixtures
- [ ] Add `--update-golden` flag
- [ ] Write determinism tests
- [ ] Write performance benchmarks
- [ ] Write integration tests
- [ ] Complete `docs/ARCHITECTURE.md`
- [ ] Complete `docs/API.md`
- [ ] Complete `docs/CLI.md`
- [ ] Complete `docs/EMITTERS.md`
- [ ] Complete `docs/DIAGRAMS.md`
- [ ] Complete `docs/TEMPLATES.md`
- [ ] Complete `docs/CONFIGURATION.md`
- [ ] Complete `docs/VALIDATION.md`
- [ ] Update `README.md`
- [ ] Create `CHANGELOG.md` for v1.0.0
- [ ] Create example workflows
- [ ] Run full test suite: `pytest python/tests/ -v --cov`
- [ ] Verify coverage ≥90%

### Final: Release
- [ ] Verify `pyproject.toml` licensing (CC-BY-4.0)
- [ ] Verify LICENSE file (CC-BY-4.0)
- [ ] Run type checking: `mypy python/xaml_parser`
- [ ] Run linting: `ruff check python/`
- [ ] Fix remaining issues
- [ ] Update version to 1.0.0
- [ ] Tag release: `git tag v1.0.0`
- [ ] Build package: `python -m build`
- [ ] Test installation
- [ ] Deploy documentation

---

## Success Criteria

### Functional Requirements
- ✅ Stable deterministic IDs for all entities
- ✅ Control flow edges extracted and represented
- ✅ Self-describing DTOs with schema versioning
- ✅ Pluggable emitter system
- ✅ Data emitters: JSON (YAML deferred to v1.1.0)
- ✅ Diagram emitter: Mermaid (DOT/PlantUML deferred to v1.1.0)
- ✅ Doc emitter: Markdown via Jinja2
- ✅ CLI with subcommands
- ✅ Config file support
- ✅ Validation (schema + referential)

### Technical Requirements
- ✅ Test coverage ≥90%
- ✅ All tests pass
- ✅ Type checking passes (mypy strict)
- ✅ Linting passes (ruff)
- ✅ Golden tests for determinism
- ✅ Performance targets met

### Documentation Requirements
- ✅ Complete architecture documentation
- ✅ API reference
- ✅ CLI guide
- ✅ Emitter guide
- ✅ Template guide
- ✅ Examples

### Backward Compatibility
- ⚠️ BREAKING CHANGES (v1.0.0)
  - New CLI structure (old CLI deprecated)
  - New DTO format (not compatible with v0.x)
  - Migration guide provided

---

## Version Roadmap

### v1.0.0 (This Plan)
- Stable IDs
- Control flow edges
- Self-describing DTOs
- JSON emitter
- Mermaid diagram emitter
- Markdown doc emitter
- CLI with subcommands
- Config file support
- Validation

### v1.1.0 (Future)
- YAML emitter
- DOT diagram emitter
- PlantUML diagram emitter
- Enhanced templates (embedded diagrams)
- SQLite sink
- Parallel processing (`--workers`)

### v2.0.0 (Future)
- Go implementation
- Cross-language schema sharing
- Protobuf format
- Performance optimizations
- Streaming XML parsing

---

## Risks & Mitigations

| Risk                           | Impact | Probability | Mitigation                                                            |
| ------------------------------ | ------ | ----------- | --------------------------------------------------------------------- |
| Scope too large                | High   | Medium      | Phased approach, MVP first, defer YAML/DOT/PlantUML to v1.1.0         |
| Breaking changes               | High   | Certain     | v1.0.0, deprecation notices, migration guide                          |
| Performance regression         | Medium | Low         | Benchmark continuously, profile hotspots, target <100ms/workflow      |
| Complex ID generation          | Medium | Low         | Comprehensive tests, golden tests, W3C C14N for stability             |
| Hash collisions                | Low    | Low         | 64-bit hash space adequate for typical projects, full hash stored     |
| Plugin system complexity       | Medium | Medium      | Start simple, extend later, comprehensive plugin docs                 |
| Documentation debt             | Medium | Medium      | Write docs alongside code, API reference from docstrings              |
| Determinism issues             | Medium | Medium      | Explicit determinism rules, locale-independent sorting, golden tests  |
| XML canonicalization fragility | Medium | Medium      | Use W3C C14N standard, test with multiple XML serializers             |
| Mermaid syntax errors          | Low    | Medium      | Sanitize IDs, validate output, provide test rendering                 |
| Privacy/PII exposure           | High   | Low         | Warnings for sensitive patterns, documentation on user responsibility |
| Expression language ambiguity  | Medium | Low         | Support both VB.NET and C#, preserve raw expressions                  |
| Schema versioning conflicts    | Low    | Low         | Explicit schema version in DTOs, compatibility policy documented      |

---

## References

- **Analyst Requirements:** `docs/zweitmeinung.md`
- **Original Output Plan:** Previous `PLAN.md` (refactoring approach)
- **Original Implementation:** `D:\github.com\rpapub\rpax\src\xaml_parser\`
- **Current Implementation:** `python/xaml_parser/`
- **JSON Schema Reference:** `D:\github.com\rpapub\rpax\src\xaml_parser\schemas\workflow_content.schema.json`
- **UiPath XAML Spec:** [UiPath Documentation](https://docs.uipath.com/)

---

**Next Steps:**
1. Review and approve this plan
2. Begin Phase 0 (Foundation & Design)
3. Set up project tracking (GitHub issues/project board)
4. Establish weekly checkpoints
