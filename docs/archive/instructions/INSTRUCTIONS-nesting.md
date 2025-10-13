# ARCHITECTURE: Graph-Based Call Graph Traversal & Multi-View Output

**Status:** Design Approved - Implementation Pending
**Target Audience:** Mid-level Python developers
**Estimated Time:** 40-60 hours full implementation
**Difficulty:** Advanced - Requires architectural refactoring
**Industry References:** NetworkX (graph API), Roslyn (view pattern), LLVM (IR design), Sourcegraph (code intelligence)

---

## Table of Contents

- [Part 1: Executive Summary & Current State](#part-1-executive-summary--current-state)
- [Part 2: Proposed Architecture](#part-2-proposed-architecture)
- [Part 3: Graph Module Implementation](#part-3-graph-module-implementation)
- [Part 4: Analysis & View Layer Implementation](#part-4-analysis--view-layer-implementation)
- [Part 5: Seven-Phase Refactoring Plan](#part-5-seven-phase-refactoring-plan)
- [Part 6: Code Examples & Usage Patterns](#part-6-code-examples--usage-patterns)
- [Part 7: Testing Strategy](#part-7-testing-strategy)
- [Part 8: Migration & Backward Compatibility](#part-8-migration--backward-compatibility)

---

# Part 1: Executive Summary & Current State

## 1.1 The Core Insight

The user's request for "nested activity output" initially appears to be a simple presentation change - converting flat lists to nested JSON. However, this reveals a **fundamental architectural need**:

**The parser needs to support multiple views of the same data:**
- **Flat View**: Current output - analytics-friendly, deterministic ordering, flat lists with ID references
- **Execution View**: Call graph traversal from entry point - shows "what actually runs", expands `InvokeWorkflowFile` with callee content
- **Slice View**: Context window around focal point - for LLM consumption (show me this activity + parent chain + siblings + immediate children)
- **Tree View**: Single-file hierarchical view - mirrors XAML structure within one workflow file

These aren't just different serialization formats - they're **different analytical perspectives** requiring:
1. **Graph data structures** to represent call graphs, control flow, and activity hierarchies
2. **Separation of concerns**: Parse → Analyze (build graphs) → Transform (views) → Serialize (formats)
3. **Industry-standard graph API** for maintainability and developer familiarity

## 1.2 Current Architecture Analysis

### What Exists and Works Well

```
XAML Files
    ↓
XamlParser (parser.py)
    ↓
ParseResult (models.py)
    ↓
Normalizer (normalization.py) + ControlFlowExtractor (control_flow.py)
    ↓
WorkflowDto / ActivityDto (dto.py)
    ↓
Emitters (json_emitter.py, mermaid_emitter.py, etc.)
    ↓
Output Files (JSON, Mermaid, etc.)
```

**Strengths:**
- Clean parsing: `XamlParser` converts XAML → `ParseResult` with no analysis mixed in ✓
- Comprehensive extraction: `ControlFlowExtractor` finds all edges (Next, Then, Else, Case, etc.) ✓
- Call graph data: `Normalizer._extract_invocations()` tracks `InvokeWorkflowFile` references ✓
- Stable IDs: Content-hash based IDs (`act:sha256:...`, `wf:sha256:...`) ✓
- Clean data models: `ActivityDto`, `WorkflowDto`, `EdgeDto`, `InvocationDto` well-defined ✓

### What's Missing (The Gap)

**Problem 1: No Graph Data Structure**

Currently, we extract graph data but store it as flat lists:
```python
# normalization.py lines 200-250
edges = self.flow_extractor.extract_edges(content.activities)  # Returns list[EdgeDto]
invocations = self._extract_invocations(content.activities, workflow_id_map)  # Returns list[InvocationDto]
```

**Result:** We have edge data but no graph structure to query:
- Cannot traverse: "What activities are reachable from entry point?"
- Cannot detect cycles: "Does workflow A eventually call itself?"
- Cannot slice context: "Show me 2 levels up/down from this activity"

**Problem 2: Analysis Mixed with Transformation**

`Normalizer` does TWO things simultaneously:
1. **Analysis**: Extract invocations, control flow edges, compute stable IDs
2. **Transformation**: Convert `ParseResult` → `WorkflowDto`

**Result:** Cannot analyze once, transform many ways. Every new output format must re-analyze.

**Problem 3: No View Layer Concept**

Emitters directly serialize DTOs:
```python
# json_emitter.py
def emit_combined(self, collection: WorkflowCollectionDto, output_path: Path, config: EmitterConfig) -> None:
    data = dataclasses.asdict(collection)  # Direct DTO serialization
    # ... write JSON
```

**Result:** Cannot support multiple views (flat vs execution vs slice) without duplicating logic.

**Problem 4: Project-Level Analysis Missing**

`ProjectParser.parse_project()` returns `ProjectResult` with:
- Flat list of `WorkflowResult` objects
- Simple `dependency_graph: dict[str, list[str]]` (path → list of paths)

**Result:** Cannot query across workflows efficiently. No unified graph structure.

### Where Key Data Is Currently Extracted

| Data Type | Where Extracted | Current Output | What's Missing |
|-----------|----------------|----------------|----------------|
| Activities | `parser.py` lines 100-400 | Flat list in `ParseResult.content.activities` | Graph structure |
| Parent/Child | `extractors.py` lines 50-150 | `parent_id` + `children: list[str]` | Graph with traversal |
| Control Flow | `control_flow.py` lines 100-600 | `list[EdgeDto]` | Graph with edge types |
| Invocations | `normalization.py` lines 230-290 | `list[InvocationDto]` | Call graph structure |
| Activity IDs | `id_generation.py` + `normalization.py` | Stable content-hash IDs | ✓ Good as-is |

**Key Observation:** All the data needed for graphs already exists - we just need to put it into graph structures!

## 1.3 Why Not Just Bolt On Nesting?

**Tempting but wrong approach:**
```python
# DON'T DO THIS - treats symptom, not cause
def emit_nested(collection):
    for workflow in collection.workflows:
        # Reconstruct tree ad-hoc at emission time
        tree = ad_hoc_nest_activities(workflow.activities)
        # Manually expand InvokeWorkflowFile
        for act in tree:
            if act.type == "InvokeWorkflowFile":
                callee = manually_find_callee(...)
                act.children = callee.activities  # Fragile!
```

**Why this fails:**
1. **Repeated work**: Every emitter re-implements tree building
2. **No reuse**: Cannot serve other use cases (cycle detection, reachability analysis, etc.)
3. **Fragile**: Manual graph traversal error-prone
4. **Not extensible**: Hard to add new views or query patterns
5. **Performance**: O(n²) lookups on every emission

**Correct approach:**
```python
# Parse once, analyze once, query many times
project_index = analyzer.analyze(project_result)  # Builds all graphs
flat_view = FlatView().render(project_index)
exec_view = ExecutionView(entry="Main.xaml").render(project_index)
slice_view = SliceView(focus="act:sha256:abc", radius=2).render(project_index)
```

## 1.4 Industry Precedents

### NetworkX (Python Graph Library)
- **API Pattern**: `add_node(id, data)`, `add_edge(from, to)`, `successors(id)`, `predecessors(id)`
- **Traversal**: DFS/BFS iterators with visitor pattern
- **Analysis**: `find_cycles()`, `reachable_from()`, `topological_sort()`
- **Why Reference It**: Industry-standard Python graph API - developers already know it
- **Our Approach**: Custom implementation (~200 lines, zero deps) with NetworkX-compatible API

### Roslyn (C# Compiler Platform)
- **Architecture**: Parse → Build SyntaxTree → Semantic Analysis → Multiple backends
- **View Pattern**: Single IR (Intermediate Representation), multiple transformations
- **Why Reference It**: Demonstrates view/transformation separation at production scale
- **Our Approach**: `ProjectIndex` (analyzed graph) + `View` protocol + multiple view implementations

### LLVM (Compiler Infrastructure)
- **Architecture**: Source → Parse → IR → Optimization passes → Multiple backends (x86, ARM, etc.)
- **Key Insight**: IR is queryable graph structure, backends are transformations
- **Why Reference It**: Shows how graph-based IR enables multiple output formats
- **Our Approach**: Similar separation - `ProjectIndex` is our IR, views are backends

### Sourcegraph / Kythe (Code Intelligence)
- **Architecture**: Index-once, query-many for code navigation
- **Graph Structure**: Files, symbols, references as nodes; relationships as edges
- **Why Reference It**: Shows how code analysis benefits from graph indexing
- **Our Approach**: Similar - analyze project once, support multiple query patterns

### Apache Airflow (Workflow Orchestration)
- **Architecture**: DAG definition (static) vs. execution graph (dynamic)
- **Key Insight**: Separation of declared structure from runtime traversal
- **Why Reference It**: Workflow = DAG, similar to our activity graphs
- **Our Approach**: Flat DTO = declared structure, ExecutionView = runtime traversal

## 1.5 Success Criteria

**Must-Have (Phase 1-4):**
- [ ] Custom Graph class (~200 lines, stdlib only, NetworkX-compatible API)
- [ ] ProjectIndex with queryable graphs (workflows, activities, call graph, control flow)
- [ ] FlatView producing current output (100% backward compatible)
- [ ] ExecutionView traversing call graph from entry point
- [ ] Zero new external dependencies

**Should-Have (Phase 5-6):**
- [ ] SliceView for LLM context windows
- [ ] CLI integration (`--view=execution`, `--entry=Main.xaml`)
- [ ] Cycle detection in call graphs
- [ ] Performance: analyze 100-workflow project in <5 seconds

**Nice-to-Have (Future):**
- [ ] TreeView (single-file hierarchy only, no call graph)
- [ ] CallGraphView (just the call graph, no activity details)
- [ ] Caching analyzed ProjectIndex for incremental updates
- [ ] Graph export to GraphML/DOT for visualization

---

# Part 2: Proposed Architecture

## 2.1 Architectural Principles

### Principle 1: Separation of Concerns
```
Parse → Analyze → Transform → Serialize
```

- **Parse** (existing): XAML → ParseResult ✓
- **Analyze** (NEW): ParseResult → ProjectIndex with graphs
- **Transform** (NEW): ProjectIndex → View-specific dicts
- **Serialize** (modify): dict → JSON/Mermaid/etc.

### Principle 2: Graph-First Analysis
All relationships modeled as graphs:
- Activity hierarchy: parent/child edges
- Control flow: Next, Then, Else, Case edges
- Call graph: InvokeWorkflowFile → callee edges
- Workflow dependencies: workflow → invoked workflow edges

### Principle 3: View Protocol
All views implement same interface:
```python
class View(Protocol):
    def render(self, index: ProjectIndex) -> dict[str, Any]: ...
```

This enables:
- Easy addition of new views
- Consistent interface for emitters
- Testing views in isolation

### Principle 4: Zero Dependencies
Custom Graph implementation to avoid:
- NetworkX dependency (heavyweight, 50+ deps)
- rustworkx/retworkx (Rust build complexity)
- igraph (C bindings, portability issues)

Trade-off: ~200 lines of custom code vs. dependency management

## 2.2 Component Overview

### New Components

#### 1. `graph.py` - Graph Data Structure
**Purpose:** Lightweight directed graph with NetworkX-compatible API

**Key Features:**
- Adjacency list representation (O(1) edge lookup)
- Reverse edges cached for predecessor queries
- Generic type support: `Graph[T]` where T is node data type
- DFS/BFS traversal with cycle detection
- Standard algorithms: topological sort, find_cycles, reachable_from

**Size:** ~200 lines
**Dependencies:** stdlib only (collections, dataclasses, typing)

#### 2. `analyzer.py` - Project Analysis
**Purpose:** Build graph structures from parsed workflows

**Key Responsibilities:**
- Convert flat lists (activities, edges, invocations) → Graph instances
- Build multiple graph layers (activity hierarchy, control flow, call graph)
- Compute derived properties (depth, reachability, cycle detection)
- Return `ProjectIndex` - unified queryable structure

**Size:** ~300 lines
**Dependencies:** graph.py, dto.py, models.py

#### 3. `views.py` - View Layer
**Purpose:** Transform ProjectIndex into different representations

**Key Classes:**
- `View` protocol: `render(index: ProjectIndex) -> dict`
- `FlatView`: Current flat output (backward compatible)
- `ExecutionView`: Call graph traversal from entry point
- `SliceView`: Context window around focal activity
- (Future) `TreeView`, `CallGraphView`, etc.

**Size:** ~400 lines
**Dependencies:** graph.py, analyzer.py, dto.py

### Modified Components

#### 4. `project.py` - Project Parser
**Changes:**
- Keep existing parsing logic
- Replace `project_result_to_dto()` with `analyze_project()`
- Return `ProjectIndex` instead of `WorkflowCollectionDto`
- Maintain `ProjectResult` for backward compatibility

#### 5. `emitters/*.py` - Output Emitters
**Changes:**
- Accept `ProjectIndex` + `View` instead of just DTO
- Apply view transformation before serialization
- Default view: `FlatView` (backward compatible)
- Add `view` parameter to `EmitterConfig`

#### 6. `cli.py` - Command Line Interface
**Changes:**
- Add `--view` flag (flat, execution, slice, tree)
- Add `--entry` flag for ExecutionView
- Add `--focus` and `--radius` flags for SliceView
- Maintain backward compatibility (default: flat view)

## 2.3 Data Flow Diagrams

### Current Flow (Flat Only)
```
XAML Files
    ↓
XamlParser.parse_file()
    ↓
ParseResult
    ↓
Normalizer.normalize()
    ↓ (extracts edges, invocations - then discards graph structure!)
WorkflowDto + list[EdgeDto] + list[InvocationDto]
    ↓
project_result_to_dto()
    ↓
WorkflowCollectionDto
    ↓
JsonEmitter.emit()
    ↓
Flat JSON output
```

### Proposed Flow (Multi-View)
```
XAML Files
    ↓
XamlParser.parse_file()
    ↓
ParseResult
    ↓
Normalizer.normalize()
    ↓ (still produces DTOs + edges + invocations)
WorkflowDto + list[EdgeDto] + list[InvocationDto]
    ↓
ProjectAnalyzer.analyze()  ← NEW
    ↓ (builds graph structures)
ProjectIndex {
    workflows: Graph[WorkflowDto]
    activities: Graph[ActivityDto]
    call_graph: Graph
    control_flow: Graph
}
    ↓
View.render(index)  ← NEW (multiple implementations)
    ↓
dict (view-specific structure)
    ↓
JsonEmitter.emit()
    ↓
JSON output (flat / execution / slice / tree)
```

**Key Difference:** Graphs built once, queried many times.

## 2.4 Module Dependencies

```
graph.py (stdlib only)
    ↓
analyzer.py (graph, dto, models)
    ↓
views.py (graph, analyzer, dto)
    ↓
project.py (analyzer, views, ...)
    ↓
emitters/*.py (views, ...)
    ↓
cli.py (project, emitters, views)
```

**Dependency Rules:**
- `graph.py` has ZERO internal dependencies (pure stdlib)
- `analyzer.py` depends on graph + existing DTO modules
- `views.py` depends on analyzer + graph
- Existing modules (parser, extractors, models, dto) UNCHANGED
- Only `project.py` and `emitters/*.py` need modifications

## 2.5 Type System Overview

### Core Types

```python
# graph.py
T = TypeVar('T')

@dataclass
class Graph(Generic[T]):
    """Directed graph with typed nodes."""
    _nodes: dict[str, T]
    _edges: dict[str, list[str]]  # adjacency list
    _reverse_edges: dict[str, list[str]]  # for predecessors

    def add_node(self, node_id: str, data: T) -> None: ...
    def add_edge(self, from_id: str, to_id: str) -> None: ...
    def successors(self, node_id: str) -> list[str]: ...
    def predecessors(self, node_id: str) -> list[str]: ...
    def traverse_dfs(self, start_id: str, visitor: Callable | None = None,
                     max_depth: int = 100) -> Iterator[tuple[str, T, int]]: ...
    def find_cycles(self) -> list[list[str]]: ...
    def reachable_from(self, start_id: str, max_depth: int = 100) -> set[str]: ...
    def topological_sort(self) -> list[str]: ...

# analyzer.py
@dataclass
class ProjectIndex:
    """Analyzed project with queryable graph structures."""

    # Graph structures
    workflows: Graph[WorkflowDto]
    activities: Graph[ActivityDto]  # All activities across all workflows
    call_graph: Graph  # Workflow invocations
    control_flow: Graph  # Activity control flow edges

    # Lookups
    workflow_by_path: dict[str, str]  # path → workflow ID
    activity_to_workflow: dict[str, str]  # activity ID → workflow ID
    entry_points: list[str]  # List of entry point workflow IDs

    # Methods
    def get_workflow(self, workflow_id: str) -> WorkflowDto | None: ...
    def get_activity(self, activity_id: str) -> ActivityDto | None: ...
    def traverse_from(self, entry_id: str, visitor: Callable, max_depth: int = 10) -> None: ...
    def slice_context(self, activity_id: str, radius: int = 2) -> dict[str, ActivityDto]: ...
    def find_call_cycles(self) -> list[list[str]]: ...

# views.py
class View(Protocol):
    """Protocol for view transformations."""
    def render(self, index: ProjectIndex) -> dict[str, Any]: ...

class FlatView(View):
    """Current flat output - backward compatible."""
    def render(self, index: ProjectIndex) -> dict[str, Any]: ...

class ExecutionView(View):
    """Traverse call graph from entry point."""
    def __init__(self, entry_point: str, max_depth: int = 10): ...
    def render(self, index: ProjectIndex) -> dict[str, Any]: ...

class SliceView(View):
    """Context window around focal activity."""
    def __init__(self, focus: str, radius: int = 2): ...
    def render(self, index: ProjectIndex) -> dict[str, Any]: ...
```

---

# Part 3: Graph Module Implementation

## 3.1 Design Decisions

### Why Adjacency List?
- **Time Complexity**: O(1) for adding edges, O(k) for iterating successors (where k = out-degree)
- **Space Complexity**: O(V + E) where V = nodes, E = edges
- **Trade-off**: Slightly slower than adjacency matrix for dense graphs, but our graphs are sparse

### Why Reverse Edges Cache?
- Predecessor queries needed for: context slicing, parent chain, breadcrumb navigation
- Without cache: O(V × E) to find predecessors
- With cache: O(1) lookup, O(E) space overhead (acceptable)

### Why Generic Types?
- Type safety: `Graph[WorkflowDto]` vs. `Graph[ActivityDto]`
- IDE support: autocomplete for node data
- Runtime: No performance penalty (type erasure)

## 3.2 Complete Implementation

**File:** `python/xaml_parser/graph.py`

```python
"""Lightweight directed graph for workflow analysis.

This module provides a NetworkX-compatible graph API with zero dependencies.
Designed for sparse graphs (workflows, activities, call graphs) with fast
traversal and common graph algorithms.

Industry Reference: NetworkX (https://networkx.org)
Design Philosophy: Adjacency list representation, stdlib only

Usage:
    >>> g = Graph[str]()
    >>> g.add_node("n1", "Node 1 data")
    >>> g.add_node("n2", "Node 2 data")
    >>> g.add_edge("n1", "n2")
    >>> list(g.successors("n1"))
    ['n2']
    >>> for node_id, data, depth in g.traverse_dfs("n1"):
    ...     print(f"{node_id} at depth {depth}: {data}")
"""

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Callable, Generic, Iterator, TypeVar

__all__ = ["Graph"]

T = TypeVar('T')


@dataclass
class Graph(Generic[T]):
    """Directed graph with typed nodes and fast traversal.

    NetworkX-compatible API for common operations.

    Attributes:
        _nodes: Node ID → node data mapping
        _edges: Adjacency list (node ID → list of successor IDs)
        _reverse_edges: Reverse adjacency list (node ID → list of predecessor IDs)

    Examples:
        >>> # Create graph of workflow DTOs
        >>> workflows = Graph[WorkflowDto]()
        >>> workflows.add_node("wf:main", main_dto)
        >>> workflows.add_node("wf:helper", helper_dto)
        >>> workflows.add_edge("wf:main", "wf:helper")  # main calls helper
        >>>
        >>> # Traverse from entry point
        >>> for wf_id, wf_dto, depth in workflows.traverse_dfs("wf:main"):
        ...     print(f"Workflow {wf_dto.name} at depth {depth}")
    """

    _nodes: dict[str, T] = field(default_factory=dict)
    _edges: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    _reverse_edges: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))

    def add_node(self, node_id: str, data: T) -> None:
        """Add node to graph.

        Args:
            node_id: Unique node identifier
            data: Node data (any type)

        Note:
            If node already exists, data is updated.
        """
        self._nodes[node_id] = data

    def add_edge(self, from_id: str, to_id: str) -> None:
        """Add directed edge from_id → to_id.

        Args:
            from_id: Source node ID
            to_id: Target node ID

        Note:
            Does not check if nodes exist (allows adding edges before nodes).
            Duplicate edges are added (use set if uniqueness needed).
        """
        self._edges[from_id].append(to_id)
        self._reverse_edges[to_id].append(from_id)

    def has_node(self, node_id: str) -> bool:
        """Check if node exists.

        Args:
            node_id: Node ID to check

        Returns:
            True if node exists
        """
        return node_id in self._nodes

    def has_edge(self, from_id: str, to_id: str) -> bool:
        """Check if edge exists.

        Args:
            from_id: Source node ID
            to_id: Target node ID

        Returns:
            True if edge from_id → to_id exists
        """
        return to_id in self._edges.get(from_id, [])

    def get_node(self, node_id: str) -> T | None:
        """Get node data.

        Args:
            node_id: Node ID

        Returns:
            Node data or None if not found
        """
        return self._nodes.get(node_id)

    def successors(self, node_id: str) -> list[str]:
        """Get successor node IDs (outgoing edges).

        Args:
            node_id: Node ID

        Returns:
            List of successor IDs (empty if node has no successors)

        Complexity:
            O(1) lookup, O(k) to return list where k = out-degree
        """
        return self._edges.get(node_id, [])

    def predecessors(self, node_id: str) -> list[str]:
        """Get predecessor node IDs (incoming edges).

        Args:
            node_id: Node ID

        Returns:
            List of predecessor IDs (empty if node has no predecessors)

        Complexity:
            O(1) lookup (uses cached reverse edges)
        """
        return self._reverse_edges.get(node_id, [])

    def nodes(self) -> list[str]:
        """Get all node IDs.

        Returns:
            List of all node IDs
        """
        return list(self._nodes.keys())

    def node_count(self) -> int:
        """Get number of nodes.

        Returns:
            Node count
        """
        return len(self._nodes)

    def edge_count(self) -> int:
        """Get number of edges.

        Returns:
            Edge count
        """
        return sum(len(successors) for successors in self._edges.values())

    def traverse_dfs(
        self,
        start_id: str,
        visitor: Callable[[str, T, int], bool] | None = None,
        max_depth: int = 100,
    ) -> Iterator[tuple[str, T, int]]:
        """Depth-first traversal with cycle detection.

        Args:
            start_id: Starting node ID
            visitor: Optional visitor function(node_id, data, depth) -> continue
                    Returns False to skip node's children
            max_depth: Maximum depth to traverse (cycle protection)

        Yields:
            Tuple of (node_id, node_data, depth) for each visited node

        Example:
            >>> # Visit all reachable nodes
            >>> for node_id, data, depth in graph.traverse_dfs("start"):
            ...     print(f"{'  ' * depth}{node_id}")
            >>>
            >>> # Custom visitor to stop at certain nodes
            >>> def visitor(node_id, data, depth):
            ...     if data.type == "StopHere":
            ...         return False  # Don't traverse children
            ...     return True
            >>> for node_id, data, depth in graph.traverse_dfs("start", visitor):
            ...     process(node_id, data)
        """
        if start_id not in self._nodes:
            return

        visited: set[str] = set()
        stack: list[tuple[str, int]] = [(start_id, 0)]

        while stack:
            node_id, depth = stack.pop()

            # Cycle detection
            if node_id in visited:
                continue

            # Depth limit
            if depth > max_depth:
                continue

            visited.add(node_id)

            # Get node data
            node_data = self._nodes.get(node_id)
            if node_data is None:
                continue

            # Apply visitor
            if visitor and not visitor(node_id, node_data, depth):
                # Visitor returned False - skip children
                continue

            # Yield current node
            yield (node_id, node_data, depth)

            # Add children to stack (reversed to maintain left-to-right order)
            children = self.successors(node_id)
            for child_id in reversed(children):
                if child_id not in visited:
                    stack.append((child_id, depth + 1))

    def traverse_bfs(
        self,
        start_id: str,
        visitor: Callable[[str, T, int], bool] | None = None,
        max_depth: int = 100,
    ) -> Iterator[tuple[str, T, int]]:
        """Breadth-first traversal with cycle detection.

        Args:
            start_id: Starting node ID
            visitor: Optional visitor function(node_id, data, depth) -> continue
            max_depth: Maximum depth to traverse

        Yields:
            Tuple of (node_id, node_data, depth) for each visited node

        Note:
            Similar to traverse_dfs but visits nodes level-by-level.
        """
        if start_id not in self._nodes:
            return

        visited: set[str] = set()
        queue: deque[tuple[str, int]] = deque([(start_id, 0)])

        while queue:
            node_id, depth = queue.popleft()

            if node_id in visited:
                continue

            if depth > max_depth:
                continue

            visited.add(node_id)

            node_data = self._nodes.get(node_id)
            if node_data is None:
                continue

            if visitor and not visitor(node_id, node_data, depth):
                continue

            yield (node_id, node_data, depth)

            for child_id in self.successors(node_id):
                if child_id not in visited:
                    queue.append((child_id, depth + 1))

    def reachable_from(self, start_id: str, max_depth: int = 100) -> set[str]:
        """Get all nodes reachable from start node.

        Args:
            start_id: Starting node ID
            max_depth: Maximum depth to search

        Returns:
            Set of reachable node IDs (including start_id)

        Example:
            >>> reachable = graph.reachable_from("wf:main")
            >>> print(f"Main workflow can call {len(reachable)} workflows")
        """
        reachable: set[str] = set()
        for node_id, _, _ in self.traverse_dfs(start_id, max_depth=max_depth):
            reachable.add(node_id)
        return reachable

    def find_cycles(self) -> list[list[str]]:
        """Detect all cycles in graph using DFS.

        Returns:
            List of cycles, where each cycle is a list of node IDs
            Empty list if no cycles found

        Example:
            >>> cycles = graph.find_cycles()
            >>> if cycles:
            ...     print(f"Found {len(cycles)} circular call chains:")
            ...     for cycle in cycles:
            ...         print(" -> ".join(cycle))

        Complexity:
            O(V + E) where V = nodes, E = edges
        """
        cycles: list[list[str]] = []
        visited: set[str] = set()
        rec_stack: list[str] = []
        rec_stack_set: set[str] = set()

        def dfs(node_id: str) -> None:
            visited.add(node_id)
            rec_stack.append(node_id)
            rec_stack_set.add(node_id)

            for child_id in self.successors(node_id):
                if child_id not in visited:
                    dfs(child_id)
                elif child_id in rec_stack_set:
                    # Found cycle - extract cycle from recursion stack
                    cycle_start = rec_stack.index(child_id)
                    cycle = rec_stack[cycle_start:] + [child_id]
                    cycles.append(cycle)

            rec_stack.pop()
            rec_stack_set.remove(node_id)

        for node_id in self._nodes:
            if node_id not in visited:
                dfs(node_id)

        return cycles

    def topological_sort(self) -> list[str]:
        """Topological sort using Kahn's algorithm.

        Returns:
            List of node IDs in topological order
            Empty list if graph has cycles

        Example:
            >>> # Get build order for workflows
            >>> build_order = graph.topological_sort()
            >>> if not build_order:
            ...     print("Cannot build - circular dependencies!")

        Complexity:
            O(V + E)
        """
        # Compute in-degrees
        in_degree: dict[str, int] = {node_id: 0 for node_id in self._nodes}
        for node_id in self._nodes:
            for child_id in self.successors(node_id):
                if child_id in in_degree:
                    in_degree[child_id] += 1

        # Find nodes with no incoming edges
        queue: deque[str] = deque([
            node_id for node_id, degree in in_degree.items() if degree == 0
        ])

        result: list[str] = []

        while queue:
            node_id = queue.popleft()
            result.append(node_id)

            for child_id in self.successors(node_id):
                if child_id in in_degree:
                    in_degree[child_id] -= 1
                    if in_degree[child_id] == 0:
                        queue.append(child_id)

        # If result doesn't include all nodes, graph has cycle
        if len(result) != len(self._nodes):
            return []

        return result

    def subgraph(self, node_ids: set[str]) -> 'Graph[T]':
        """Create subgraph containing only specified nodes.

        Args:
            node_ids: Set of node IDs to include

        Returns:
            New Graph instance with nodes and edges filtered

        Example:
            >>> # Get subgraph of reachable workflows
            >>> reachable = graph.reachable_from("wf:main")
            >>> subgraph = graph.subgraph(reachable)
        """
        sub = Graph[T]()

        # Add nodes
        for node_id in node_ids:
            if node_id in self._nodes:
                sub.add_node(node_id, self._nodes[node_id])

        # Add edges (only if both endpoints in subgraph)
        for from_id in node_ids:
            for to_id in self.successors(from_id):
                if to_id in node_ids:
                    sub.add_edge(from_id, to_id)

        return sub

    def __repr__(self) -> str:
        """String representation."""
        return f"Graph(nodes={self.node_count()}, edges={self.edge_count()})"
```

## 3.3 Usage Examples

### Example 1: Activity Hierarchy Graph
```python
from xaml_parser.graph import Graph
from xaml_parser.dto import ActivityDto

# Build activity graph
activities_graph = Graph[ActivityDto]()

for activity in workflow_dto.activities:
    activities_graph.add_node(activity.id, activity)

    # Add parent → child edges
    for child_id in activity.children:
        activities_graph.add_edge(activity.id, child_id)

# Query: Get all descendants of an activity
sequence_id = "act:sha256:abc123"
descendants = activities_graph.reachable_from(sequence_id)
print(f"Sequence has {len(descendants)} total activities")

# Query: Get parent chain (breadcrumbs)
log_activity_id = "act:sha256:def456"
parents = []
current = log_activity_id
while current:
    preds = activities_graph.predecessors(current)
    if not preds:
        break
    current = preds[0]  # Single parent
    parents.append(current)
print(" > ".join(parents[::-1]))  # Root to current
```

### Example 2: Call Graph with Cycle Detection
```python
from xaml_parser.graph import Graph

# Build call graph
call_graph = Graph()

for workflow_dto in collection.workflows:
    call_graph.add_node(workflow_dto.id, workflow_dto)

for invocation in collection.invocations:
    call_graph.add_edge(invocation.caller_workflow_id, invocation.callee_workflow_id)

# Detect circular dependencies
cycles = call_graph.find_cycles()
if cycles:
    print(f"WARNING: Found {len(cycles)} circular call chains:")
    for cycle in cycles:
        workflow_names = [call_graph.get_node(wf_id).name for wf_id in cycle]
        print(f"  {' -> '.join(workflow_names)}")
else:
    print("No circular dependencies detected")

# Topological sort for execution order
build_order = call_graph.topological_sort()
if build_order:
    print("Safe execution order:")
    for wf_id in build_order:
        wf = call_graph.get_node(wf_id)
        print(f"  - {wf.name}")
```

### Example 3: Control Flow Graph
```python
from xaml_parser.graph import Graph

# Build control flow graph from edges
control_flow = Graph()

for activity in workflow_dto.activities:
    control_flow.add_node(activity.id, activity)

for edge in workflow_dto.edges:
    control_flow.add_edge(edge.from_id, edge.to_id)

# Traverse execution paths
entry_activity_id = workflow_dto.activities[0].id

print("Execution paths:")
for act_id, act, depth in control_flow.traverse_dfs(entry_activity_id, max_depth=20):
    indent = "  " * depth
    print(f"{indent}{act.type_short}: {act.display_name}")
```

---

# Part 4: Analysis & View Layer Implementation

## 4.1 ProjectAnalyzer Design

**Purpose:** Transform flat lists (workflows, activities, edges, invocations) into queryable graph structures.

**Input:** `ProjectResult` from `ProjectParser.parse_project()`
**Output:** `ProjectIndex` with multiple graph layers

### 4.1.1 ProjectIndex Data Class

**File:** `python/xaml_parser/analyzer.py`

```python
"""Project analysis and graph construction.

This module builds queryable graph structures from parsed workflows,
enabling efficient traversal, cycle detection, and multi-view output.

Design: docs/INSTRUCTIONS-nesting.md Part 4
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .dto import ActivityDto, EdgeDto, InvocationDto, WorkflowDto
from .graph import Graph
from .models import ParseResult
from .project import ProjectResult

__all__ = ["ProjectIndex", "ProjectAnalyzer"]


@dataclass
class ProjectIndex:
    """Analyzed project with queryable graph structures.

    This is the "Intermediate Representation" (IR) of the parsed project.
    Like LLVM IR or Roslyn SyntaxTree, it's a queryable structure that
    supports multiple transformations (views).

    Attributes:
        workflows: Graph of all workflows (nodes = WorkflowDto, edges = invocations)
        activities: Graph of all activities across all workflows
        call_graph: Workflow-level call graph (workflow → workflow)
        control_flow: Activity-level control flow (activity → activity with edge types)

        workflow_by_path: Quick lookup: relative path → workflow ID
        activity_to_workflow: Quick lookup: activity ID → workflow ID
        entry_points: List of entry point workflow IDs

        project_dir: Original project directory
        total_workflows: Number of workflows
        total_activities: Number of activities across all workflows

    Usage:
        >>> index = analyzer.analyze(project_result)
        >>>
        >>> # Query entry points
        >>> for wf_id in index.entry_points:
        ...     wf = index.get_workflow(wf_id)
        ...     print(f"Entry point: {wf.name}")
        >>>
        >>> # Detect circular calls
        >>> cycles = index.find_call_cycles()
        >>>
        >>> # Traverse from entry point
        >>> index.traverse_from("wf:main", visitor_func, max_depth=10)
    """

    # Core graphs
    workflows: Graph[WorkflowDto]
    activities: Graph[ActivityDto]
    call_graph: Graph  # Workflow invocations (data = WorkflowDto)
    control_flow: Graph  # Activity edges (data = EdgeDto)

    # Lookups
    workflow_by_path: dict[str, str] = field(default_factory=dict)
    activity_to_workflow: dict[str, str] = field(default_factory=dict)
    entry_points: list[str] = field(default_factory=list)

    # Metadata
    project_dir: Path | None = None
    total_workflows: int = 0
    total_activities: int = 0

    def get_workflow(self, workflow_id: str) -> WorkflowDto | None:
        """Get workflow by ID.

        Args:
            workflow_id: Workflow ID (wf:sha256:...)

        Returns:
            WorkflowDto or None if not found
        """
        return self.workflows.get_node(workflow_id)

    def get_activity(self, activity_id: str) -> ActivityDto | None:
        """Get activity by ID.

        Args:
            activity_id: Activity ID (act:sha256:...)

        Returns:
            ActivityDto or None if not found
        """
        return self.activities.get_node(activity_id)

    def get_workflow_for_activity(self, activity_id: str) -> WorkflowDto | None:
        """Get workflow containing an activity.

        Args:
            activity_id: Activity ID

        Returns:
            WorkflowDto or None if not found
        """
        workflow_id = self.activity_to_workflow.get(activity_id)
        if workflow_id:
            return self.get_workflow(workflow_id)
        return None

    def traverse_from(
        self,
        entry_id: str,
        visitor: Callable[[str, WorkflowDto, int], bool],
        max_depth: int = 10,
    ) -> None:
        """Traverse call graph from entry point.

        Args:
            entry_id: Entry point workflow ID
            visitor: Visitor function(workflow_id, workflow_dto, depth) -> continue
            max_depth: Maximum call depth

        Example:
            >>> def visitor(wf_id, wf_dto, depth):
            ...     print(f"{'  ' * depth}{wf_dto.name}")
            ...     return True
            >>> index.traverse_from("wf:main", visitor, max_depth=5)
        """
        for wf_id, wf_dto, depth in self.call_graph.traverse_dfs(
            entry_id, visitor, max_depth
        ):
            pass  # Visitor called during traversal

    def slice_context(
        self, activity_id: str, radius: int = 2
    ) -> dict[str, ActivityDto]:
        """Get context window around activity (for LLM consumption).

        Returns activities within `radius` levels up and down from focal activity.

        Args:
            activity_id: Focal activity ID
            radius: Number of levels to include (up and down)

        Returns:
            Dict of activity_id → ActivityDto for context window

        Example:
            >>> # Get 2 levels up/down from focal activity
            >>> context = index.slice_context("act:sha256:abc123", radius=2)
            >>> print(f"Context includes {len(context)} activities")
        """
        context: dict[str, ActivityDto] = {}

        # Get focal activity
        focal = self.get_activity(activity_id)
        if not focal:
            return context

        context[activity_id] = focal

        # Traverse upward (predecessors)
        current_level = {activity_id}
        for _ in range(radius):
            next_level = set()
            for act_id in current_level:
                for pred_id in self.activities.predecessors(act_id):
                    if pred_id not in context:
                        pred = self.get_activity(pred_id)
                        if pred:
                            context[pred_id] = pred
                            next_level.add(pred_id)
            current_level = next_level

        # Traverse downward (successors)
        current_level = {activity_id}
        for _ in range(radius):
            next_level = set()
            for act_id in current_level:
                for succ_id in self.activities.successors(act_id):
                    if succ_id not in context:
                        succ = self.get_activity(succ_id)
                        if succ:
                            context[succ_id] = succ
                            next_level.add(succ_id)
            current_level = next_level

        return context

    def find_call_cycles(self) -> list[list[str]]:
        """Detect circular workflow calls.

        Returns:
            List of cycles (each cycle is list of workflow IDs)

        Example:
            >>> cycles = index.find_call_cycles()
            >>> if cycles:
            ...     for cycle in cycles:
            ...         names = [index.get_workflow(wf_id).name for wf_id in cycle]
            ...         print(f"Circular call: {' -> '.join(names)}")
        """
        return self.call_graph.find_cycles()

    def get_execution_order(self) -> list[str]:
        """Get safe workflow execution order (topological sort).

        Returns:
            List of workflow IDs in topological order
            Empty list if circular dependencies exist
        """
        return self.call_graph.topological_sort()
```

### 4.1.2 ProjectAnalyzer Implementation

```python
class ProjectAnalyzer:
    """Builds ProjectIndex from ProjectResult.

    This is the "analysis phase" - it builds all graph structures
    needed for multi-view output.

    Usage:
        >>> parser = ProjectParser()
        >>> project_result = parser.parse_project(project_dir)
        >>>
        >>> analyzer = ProjectAnalyzer()
        >>> index = analyzer.analyze(project_result)
        >>>
        >>> # Now index is queryable
        >>> cycles = index.find_call_cycles()
    """

    def analyze(self, project_result: ProjectResult) -> ProjectIndex:
        """Analyze parsed project and build graph structures.

        Args:
            project_result: Result from ProjectParser.parse_project()

        Returns:
            ProjectIndex with queryable graphs

        Steps:
            1. Build workflow graph (workflow nodes + invocation edges)
            2. Build activity graph (all activities across workflows)
            3. Build call graph (workflow-level)
            4. Build control flow graph (activity-level edges)
            5. Build lookup maps
        """
        # Initialize graphs
        workflows_graph = Graph[WorkflowDto]()
        activities_graph = Graph[ActivityDto]()
        call_graph = Graph()  # Workflow invocations
        control_flow_graph = Graph()  # Activity edges

        # Lookups
        workflow_by_path: dict[str, str] = {}
        activity_to_workflow: dict[str, str] = {}
        entry_points: list[str] = []

        total_activities = 0

        # Step 1: Build workflow nodes and activity nodes
        for wf_result in project_result.workflows:
            if not wf_result.parse_result.success:
                continue

            parse_result = wf_result.parse_result
            if not parse_result.content:
                continue

            # Derive WorkflowDto (simplified - in reality, use Normalizer)
            # For now, assume we have WorkflowDto from project_result
            workflow_dto = self._extract_workflow_dto(wf_result)

            # Add workflow node
            workflows_graph.add_node(workflow_dto.id, workflow_dto)
            call_graph.add_node(workflow_dto.id, workflow_dto)

            # Track lookups
            workflow_by_path[wf_result.relative_path] = workflow_dto.id
            if wf_result.is_entry_point:
                entry_points.append(workflow_dto.id)

            # Add activity nodes and edges
            for activity in workflow_dto.activities:
                activities_graph.add_node(activity.id, activity)
                activity_to_workflow[activity.id] = workflow_dto.id
                total_activities += 1

                # Add parent → child edges
                for child_id in activity.children:
                    activities_graph.add_edge(activity.id, child_id)

            # Add control flow edges
            for edge in workflow_dto.edges:
                control_flow_graph.add_node(edge.id, edge)
                control_flow_graph.add_edge(edge.from_id, edge.to_id)

        # Step 2: Build call graph edges (workflow invocations)
        for wf_result in project_result.workflows:
            if not wf_result.parse_result.success:
                continue

            workflow_dto = self._extract_workflow_dto(wf_result)

            # Add invocation edges
            for invocation in workflow_dto.invocations:
                # caller_workflow → callee_workflow edge
                call_graph.add_edge(
                    invocation.caller_workflow_id,
                    invocation.callee_workflow_id,
                )

        # Build ProjectIndex
        return ProjectIndex(
            workflows=workflows_graph,
            activities=activities_graph,
            call_graph=call_graph,
            control_flow=control_flow_graph,
            workflow_by_path=workflow_by_path,
            activity_to_workflow=activity_to_workflow,
            entry_points=entry_points,
            project_dir=project_result.project_dir,
            total_workflows=len(project_result.workflows),
            total_activities=total_activities,
        )

    def _extract_workflow_dto(self, wf_result) -> WorkflowDto:
        """Extract WorkflowDto from WorkflowResult.

        Note: In reality, this would use the existing Normalizer.
        For now, this is a placeholder.
        """
        # TODO: Integrate with existing Normalizer
        # For now, assume wf_result has a .dto attribute
        # In practice, we'd call normalizer.normalize() here
        raise NotImplementedError("Integrate with Normalizer")
```

## 4.2 View Layer Design

### 4.2.1 View Protocol

**File:** `python/xaml_parser/views.py`

```python
"""View layer for multi-representation output.

This module implements the "view pattern" inspired by Roslyn (C# compiler).
Each view transforms the ProjectIndex (IR) into a different representation.

Views:
- FlatView: Current flat output (backward compatible)
- ExecutionView: Call graph traversal from entry point
- SliceView: Context window around focal activity
- TreeView: Single-file hierarchical view (future)

Design: docs/INSTRUCTIONS-nesting.md Part 4.2
"""

from typing import Any, Protocol

from .analyzer import ProjectIndex
from .dto import ActivityDto

__all__ = ["View", "FlatView", "ExecutionView", "SliceView"]


class View(Protocol):
    """Protocol for view transformations.

    All views must implement render(index) -> dict.

    This enables:
    - Consistent interface for emitters
    - Easy addition of new views
    - Testing views in isolation

    Usage:
        >>> index = analyzer.analyze(project_result)
        >>>
        >>> # Apply different views
        >>> flat = FlatView().render(index)
        >>> exec_view = ExecutionView(entry="wf:main").render(index)
        >>> slice_view = SliceView(focus="act:123", radius=2).render(index)
    """

    def render(self, index: ProjectIndex) -> dict[str, Any]:
        """Transform ProjectIndex to view-specific dict.

        Args:
            index: Analyzed project with graph structures

        Returns:
            View-specific dictionary (ready for JSON serialization)
        """
        ...
```

### 4.2.2 FlatView (Backward Compatible)

```python
class FlatView:
    """Current flat output - 100% backward compatible.

    Produces same structure as current JSON emitter:
    - Flat list of workflows
    - Flat list of activities (with parent_id + children IDs)
    - Separate invocations list
    - Separate edges list

    This is the DEFAULT view to maintain backward compatibility.

    Example:
        >>> view = FlatView()
        >>> output = view.render(index)
        >>> # output has same structure as current WorkflowCollectionDto
    """

    def render(self, index: ProjectIndex) -> dict[str, Any]:
        """Render flat view (current output format).

        Args:
            index: ProjectIndex with graphs

        Returns:
            Dict with flat lists (backward compatible)
        """
        workflows = []

        for wf_id in index.workflows.nodes():
            wf_dto = index.get_workflow(wf_id)
            if not wf_dto:
                continue

            # Convert WorkflowDto to dict
            # (In practice, use dataclasses.asdict)
            wf_dict = {
                "id": wf_dto.id,
                "name": wf_dto.name,
                "file_path": wf_dto.file_path,
                "activities": [
                    {
                        "id": act.id,
                        "type": act.type,
                        "type_short": act.type_short,
                        "display_name": act.display_name,
                        "parent_id": act.parent_id,
                        "children": act.children,  # List of IDs
                        "depth": act.depth_level,
                        # ... other fields
                    }
                    for act in wf_dto.activities
                ],
                "edges": [
                    {
                        "id": edge.id,
                        "from_id": edge.from_id,
                        "to_id": edge.to_id,
                        "kind": edge.kind,
                    }
                    for edge in wf_dto.edges
                ],
                "invocations": [
                    {
                        "caller_activity_id": inv.caller_activity_id,
                        "caller_workflow_id": inv.caller_workflow_id,
                        "callee_workflow_id": inv.callee_workflow_id,
                        "callee_path": inv.callee_path,
                    }
                    for inv in wf_dto.invocations
                ],
                # ... metadata
            }
            workflows.append(wf_dict)

        return {
            "schema_id": "https://rpax.io/schemas/xaml-workflow-collection.json",
            "schema_version": "1.0.0",
            "workflows": workflows,
            # ... other fields
        }
```

### 4.2.3 ExecutionView (Call Graph Traversal)

```python
class ExecutionView:
    """Traverse call graph from entry point, showing execution flow.

    This view:
    1. Starts from specified entry point workflow
    2. Traverses call graph depth-first
    3. Expands InvokeWorkflowFile activities with callee content
    4. Shows "what actually runs" from entry to leaves

    Output structure:
    - Nested activities (mirrors XAML hierarchy)
    - InvokeWorkflowFile activities have children = callee's root activities
    - Call graph cycles detected and marked

    This is the view the user originally requested!

    Example:
        >>> view = ExecutionView(entry_point="wf:main", max_depth=10)
        >>> output = view.render(index)
        >>> # output["workflows"][0]["activities"] is nested with call graph expansion
    """

    def __init__(self, entry_point: str, max_depth: int = 10):
        """Initialize execution view.

        Args:
            entry_point: Entry point workflow ID or path
            max_depth: Maximum call depth (cycle protection)
        """
        self.entry_point = entry_point
        self.max_depth = max_depth

    def render(self, index: ProjectIndex) -> dict[str, Any]:
        """Render execution view (call graph traversal).

        Args:
            index: ProjectIndex with graphs

        Returns:
            Dict with nested activities and expanded call graph
        """
        # Resolve entry point (handle both ID and path)
        entry_wf_id = self._resolve_entry_point(index, self.entry_point)
        if not entry_wf_id:
            return {"error": f"Entry point not found: {self.entry_point}"}

        # Traverse call graph from entry point
        visited_workflows: set[str] = set()
        workflows = []

        for wf_id, wf_dto, depth in index.call_graph.traverse_dfs(
            entry_wf_id, max_depth=self.max_depth
        ):
            if wf_id in visited_workflows:
                continue
            visited_workflows.add(wf_id)

            # Build nested activity tree for this workflow
            nested_activities = self._build_nested_activities(
                wf_dto, index, visited_workflows, depth
            )

            wf_dict = {
                "id": wf_dto.id,
                "name": wf_dto.name,
                "file_path": wf_dto.file_path,
                "call_depth": depth,
                "activities": nested_activities,
                # ... other fields
            }
            workflows.append(wf_dict)

        return {
            "schema_id": "https://rpax.io/schemas/xaml-workflow-execution.json",
            "schema_version": "1.0.0",
            "entry_point": entry_wf_id,
            "max_depth": self.max_depth,
            "workflows": workflows,
        }

    def _resolve_entry_point(self, index: ProjectIndex, entry: str) -> str | None:
        """Resolve entry point to workflow ID.

        Args:
            index: ProjectIndex
            entry: Entry point (workflow ID or path)

        Returns:
            Workflow ID or None if not found
        """
        # Try as workflow ID
        if index.workflows.has_node(entry):
            return entry

        # Try as path
        return index.workflow_by_path.get(entry)

    def _build_nested_activities(
        self,
        workflow_dto,
        index: ProjectIndex,
        visited_workflows: set[str],
        depth: int,
    ) -> list[dict[str, Any]]:
        """Build nested activity tree with call graph expansion.

        Args:
            workflow_dto: WorkflowDto to nest
            index: ProjectIndex
            visited_workflows: Set of visited workflow IDs (cycle detection)
            depth: Current call depth

        Returns:
            List of root activity dicts (nested)
        """
        # Step 1: Build activity tree (parent/child nesting)
        activity_map = {act.id: act for act in workflow_dto.activities}
        nested_map: dict[str, dict[str, Any]] = {}

        for activity in workflow_dto.activities:
            act_dict = {
                "id": activity.id,
                "type": activity.type,
                "type_short": activity.type_short,
                "display_name": activity.display_name,
                "depth_level": activity.depth_level,
                "children": [],  # Will be filled
                # ... other fields
            }
            nested_map[activity.id] = act_dict

        # Step 2: Nest children (local hierarchy)
        for activity in workflow_dto.activities:
            act_dict = nested_map[activity.id]

            for child_id in activity.children:
                if child_id in nested_map:
                    child_dict = nested_map[child_id]
                    act_dict["children"].append(child_dict)

        # Step 3: Expand InvokeWorkflowFile activities
        if depth < self.max_depth:
            for activity in workflow_dto.activities:
                if "InvokeWorkflowFile" not in activity.type:
                    continue

                # Find callee workflow ID
                callee_wf_id = self._find_callee_for_activity(
                    activity.id, workflow_dto, index
                )

                if not callee_wf_id or callee_wf_id in visited_workflows:
                    continue

                # Get callee workflow
                callee_dto = index.get_workflow(callee_wf_id)
                if not callee_dto:
                    continue

                # Recursively build callee's nested activities
                new_visited = visited_workflows | {callee_wf_id}
                callee_nested = self._build_nested_activities(
                    callee_dto, index, new_visited, depth + 1
                )

                # Set as children of InvokeWorkflowFile
                act_dict = nested_map[activity.id]
                act_dict["children"] = callee_nested
                act_dict["expanded_from"] = callee_wf_id

        # Step 4: Return only root activities (no parent)
        roots = []
        for activity in workflow_dto.activities:
            if not activity.parent_id or activity.parent_id not in activity_map:
                roots.append(nested_map[activity.id])

        return roots

    def _find_callee_for_activity(
        self, activity_id: str, workflow_dto, index: ProjectIndex
    ) -> str | None:
        """Find callee workflow ID for InvokeWorkflowFile activity.

        Args:
            activity_id: InvokeWorkflowFile activity ID
            workflow_dto: Workflow containing the activity
            index: ProjectIndex

        Returns:
            Callee workflow ID or None
        """
        for invocation in workflow_dto.invocations:
            if invocation.caller_activity_id == activity_id:
                return invocation.callee_workflow_id
        return None
```

### 4.2.4 SliceView (Context Window)

```python
class SliceView:
    """Context window around focal activity (for LLM consumption).

    This view:
    1. Takes focal activity ID + radius
    2. Extracts activities within radius (up/down)
    3. Includes parent chain (breadcrumbs)
    4. Includes immediate children

    Output structure:
    - focal_activity: The activity of interest
    - parent_chain: List from root to focal activity
    - siblings: Activities at same level
    - children: Direct children of focal activity
    - context_activities: All activities within radius

    Use case: Give LLM just enough context about an activity without
    overwhelming it with entire workflow.

    Example:
        >>> view = SliceView(focus="act:sha256:abc123", radius=2)
        >>> output = view.render(index)
        >>> # output has focal activity + 2 levels up/down
    """

    def __init__(self, focus: str, radius: int = 2):
        """Initialize slice view.

        Args:
            focus: Focal activity ID
            radius: Number of levels to include (up and down)
        """
        self.focus = focus
        self.radius = radius

    def render(self, index: ProjectIndex) -> dict[str, Any]:
        """Render slice view (context window).

        Args:
            index: ProjectIndex with graphs

        Returns:
            Dict with focal activity and context
        """
        # Get context activities
        context = index.slice_context(self.focus, self.radius)

        if not context:
            return {"error": f"Activity not found: {self.focus}"}

        # Get focal activity
        focal = index.get_activity(self.focus)
        if not focal:
            return {"error": f"Activity not found: {self.focus}"}

        # Build parent chain (breadcrumbs)
        parent_chain = self._build_parent_chain(self.focus, index)

        # Get siblings
        siblings = self._get_siblings(self.focus, index)

        # Get workflow
        workflow = index.get_workflow_for_activity(self.focus)

        return {
            "schema_id": "https://rpax.io/schemas/xaml-activity-slice.json",
            "schema_version": "1.0.0",
            "focus": self.focus,
            "radius": self.radius,
            "workflow": {
                "id": workflow.id if workflow else None,
                "name": workflow.name if workflow else None,
            },
            "focal_activity": self._activity_to_dict(focal),
            "parent_chain": [self._activity_to_dict(act) for act in parent_chain],
            "siblings": [self._activity_to_dict(act) for act in siblings],
            "context_activities": [
                self._activity_to_dict(act) for act in context.values()
            ],
        }

    def _build_parent_chain(
        self, activity_id: str, index: ProjectIndex
    ) -> list[ActivityDto]:
        """Build parent chain from root to focal activity.

        Args:
            activity_id: Focal activity ID
            index: ProjectIndex

        Returns:
            List of activities from root to focal (excluding focal)
        """
        chain = []
        current_id = activity_id

        while True:
            preds = index.activities.predecessors(current_id)
            if not preds:
                break

            # Assume single parent (UiPath workflows are trees)
            parent_id = preds[0]
            parent = index.get_activity(parent_id)
            if not parent:
                break

            chain.append(parent)
            current_id = parent_id

        return list(reversed(chain))  # Root to focal

    def _get_siblings(
        self, activity_id: str, index: ProjectIndex
    ) -> list[ActivityDto]:
        """Get sibling activities (same parent).

        Args:
            activity_id: Focal activity ID
            index: ProjectIndex

        Returns:
            List of sibling activities (excluding focal)
        """
        siblings = []

        # Get parent
        preds = index.activities.predecessors(activity_id)
        if not preds:
            return siblings

        parent_id = preds[0]

        # Get all children of parent
        for child_id in index.activities.successors(parent_id):
            if child_id != activity_id:
                child = index.get_activity(child_id)
                if child:
                    siblings.append(child)

        return siblings

    def _activity_to_dict(self, activity: ActivityDto) -> dict[str, Any]:
        """Convert ActivityDto to dict.

        Args:
            activity: ActivityDto

        Returns:
            Activity dict (subset of fields for context)
        """
        return {
            "id": activity.id,
            "type": activity.type,
            "type_short": activity.type_short,
            "display_name": activity.display_name,
            "depth_level": activity.depth_level,
            # ... other relevant fields
        }
```

---

# Part 5: Seven-Phase Refactoring Plan

## Phase 1: Add Graph Module (2-4 hours)

### Goals
- Add `python/xaml_parser/graph.py` with complete implementation
- Write comprehensive unit tests
- Zero impact on existing code

### Tasks

**Task 1.1: Create graph.py**
- Copy complete implementation from Part 3.2
- File size: ~200 lines
- Dependencies: stdlib only

**Task 1.2: Write unit tests**
Create `python/tests/test_graph.py`:

```python
import pytest
from xaml_parser.graph import Graph

def test_add_node():
    g = Graph[str]()
    g.add_node("n1", "Node 1")
    assert g.has_node("n1")
    assert g.get_node("n1") == "Node 1"

def test_add_edge():
    g = Graph[str]()
    g.add_node("n1", "Node 1")
    g.add_node("n2", "Node 2")
    g.add_edge("n1", "n2")
    assert g.has_edge("n1", "n2")
    assert g.successors("n1") == ["n2"]
    assert g.predecessors("n2") == ["n1"]

def test_traverse_dfs():
    g = Graph[str]()
    g.add_node("root", "Root")
    g.add_node("child1", "Child 1")
    g.add_node("child2", "Child 2")
    g.add_edge("root", "child1")
    g.add_edge("root", "child2")

    visited = []
    for node_id, data, depth in g.traverse_dfs("root"):
        visited.append((node_id, depth))

    assert ("root", 0) in visited
    assert ("child1", 1) in visited
    assert ("child2", 1) in visited

def test_find_cycles():
    g = Graph[str]()
    g.add_node("n1", "N1")
    g.add_node("n2", "N2")
    g.add_node("n3", "N3")
    g.add_edge("n1", "n2")
    g.add_edge("n2", "n3")
    g.add_edge("n3", "n1")  # Creates cycle

    cycles = g.find_cycles()
    assert len(cycles) > 0
    assert "n1" in cycles[0]

def test_topological_sort():
    g = Graph[str]()
    g.add_node("n1", "N1")
    g.add_node("n2", "N2")
    g.add_node("n3", "N3")
    g.add_edge("n1", "n2")
    g.add_edge("n2", "n3")

    sorted_nodes = g.topological_sort()
    assert sorted_nodes.index("n1") < sorted_nodes.index("n2")
    assert sorted_nodes.index("n2") < sorted_nodes.index("n3")

def test_reachable_from():
    g = Graph[str]()
    g.add_node("root", "Root")
    g.add_node("child", "Child")
    g.add_node("grandchild", "Grandchild")
    g.add_node("isolated", "Isolated")
    g.add_edge("root", "child")
    g.add_edge("child", "grandchild")

    reachable = g.reachable_from("root")
    assert "root" in reachable
    assert "child" in reachable
    assert "grandchild" in reachable
    assert "isolated" not in reachable

def test_subgraph():
    g = Graph[str]()
    g.add_node("n1", "N1")
    g.add_node("n2", "N2")
    g.add_node("n3", "N3")
    g.add_edge("n1", "n2")
    g.add_edge("n2", "n3")

    sub = g.subgraph({"n1", "n2"})
    assert sub.has_node("n1")
    assert sub.has_node("n2")
    assert not sub.has_node("n3")
    assert sub.has_edge("n1", "n2")
```

**Task 1.3: Run tests**
```bash
cd python/
uv run pytest tests/test_graph.py -v
```

**Task 1.4: Update __init__.py**
Add to `python/xaml_parser/__init__.py`:
```python
from .graph import Graph

__all__ = [..., "Graph"]
```

### Success Criteria
- [ ] All unit tests pass
- [ ] ruff check passes
- [ ] mypy passes
- [ ] No changes to existing modules

---

## Phase 2: Add Analyzer Module (4-6 hours)

### Goals
- Add `python/xaml_parser/analyzer.py`
- Implement `ProjectIndex` and `ProjectAnalyzer`
- Integrate with existing `Normalizer`

### Tasks

**Task 2.1: Create analyzer.py skeleton**
Create `python/xaml_parser/analyzer.py`:
- Copy `ProjectIndex` dataclass from Part 4.1.1
- Copy `ProjectAnalyzer` class skeleton from Part 4.1.2

**Task 2.2: Integrate with Normalizer**
The challenge: `Normalizer` currently returns `WorkflowDto`, but `ProjectAnalyzer` needs to work with `ProjectResult`.

**Solution**: Modify `ProjectParser` to collect normalized DTOs:

```python
# In project.py
def parse_project(self, project_dir: Path, ...) -> ProjectResult:
    # ... existing parsing ...

    # NEW: Store normalized DTOs in ProjectResult
    normalized_workflows = []
    for wf_result in workflow_results:
        if wf_result.parse_result.success:
            workflow_dto = self.normalizer.normalize(...)
            normalized_workflows.append(workflow_dto)

    return ProjectResult(
        # ... existing fields ...
        normalized_workflows=normalized_workflows,  # NEW
    )
```

**Task 2.3: Implement analyzer.analyze()**
Complete the `ProjectAnalyzer.analyze()` method:

```python
def analyze(self, project_result: ProjectResult) -> ProjectIndex:
    # 1. Build workflow graph
    workflows_graph = Graph[WorkflowDto]()
    call_graph = Graph()

    for wf_dto in project_result.normalized_workflows:
        workflows_graph.add_node(wf_dto.id, wf_dto)
        call_graph.add_node(wf_dto.id, wf_dto)

    # 2. Build activity graph
    activities_graph = Graph[ActivityDto]()
    activity_to_workflow = {}

    for wf_dto in project_result.normalized_workflows:
        for activity in wf_dto.activities:
            activities_graph.add_node(activity.id, activity)
            activity_to_workflow[activity.id] = wf_dto.id

            # Add parent → child edges
            for child_id in activity.children:
                activities_graph.add_edge(activity.id, child_id)

    # 3. Build call graph edges
    for wf_dto in project_result.normalized_workflows:
        for invocation in wf_dto.invocations:
            call_graph.add_edge(
                invocation.caller_workflow_id,
                invocation.callee_workflow_id,
            )

    # 4. Build control flow graph
    control_flow_graph = Graph()
    for wf_dto in project_result.normalized_workflows:
        for edge in wf_dto.edges:
            control_flow_graph.add_node(edge.id, edge)
            control_flow_graph.add_edge(edge.from_id, edge.to_id)

    # 5. Build lookups
    workflow_by_path = {
        wf_result.relative_path: wf_dto.id
        for wf_result, wf_dto in zip(
            project_result.workflows, project_result.normalized_workflows
        )
    }

    entry_points = [
        wf_dto.id
        for wf_result, wf_dto in zip(
            project_result.workflows, project_result.normalized_workflows
        )
        if wf_result.is_entry_point
    ]

    # 6. Return ProjectIndex
    return ProjectIndex(
        workflows=workflows_graph,
        activities=activities_graph,
        call_graph=call_graph,
        control_flow=control_flow_graph,
        workflow_by_path=workflow_by_path,
        activity_to_workflow=activity_to_workflow,
        entry_points=entry_points,
        project_dir=project_result.project_dir,
        total_workflows=len(project_result.normalized_workflows),
        total_activities=sum(
            len(wf.activities) for wf in project_result.normalized_workflows
        ),
    )
```

**Task 2.4: Write unit tests**
Create `python/tests/test_analyzer.py`:

```python
import pytest
from pathlib import Path
from xaml_parser.analyzer import ProjectAnalyzer, ProjectIndex
from xaml_parser.project import ProjectParser

def test_analyze_simple_project(tmp_path):
    # Create minimal test project
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    (project_dir / "project.json").write_text('{"name": "Test", "main": "Main.xaml"}')
    (project_dir / "Main.xaml").write_text('<Activity x:Class="Main"></Activity>')

    # Parse
    parser = ProjectParser()
    project_result = parser.parse_project(project_dir)

    # Analyze
    analyzer = ProjectAnalyzer()
    index = analyzer.analyze(project_result)

    # Assert
    assert index.total_workflows > 0
    assert index.workflows.node_count() > 0
    assert len(index.entry_points) > 0

def test_call_graph_building(sample_project_result):
    analyzer = ProjectAnalyzer()
    index = analyzer.analyze(sample_project_result)

    # Check call graph has correct edges
    # (Assuming sample_project_result has Main → Helper invocation)
    assert index.call_graph.has_edge("wf:main", "wf:helper")

def test_activity_graph_building(sample_project_result):
    analyzer = ProjectAnalyzer()
    index = analyzer.analyze(sample_project_result)

    # Check activity hierarchy
    # (Assuming sample has Sequence → LogMessage)
    sequence_id = "act:sha256:seq123"
    log_id = "act:sha256:log456"
    assert index.activities.has_edge(sequence_id, log_id)

def test_cycle_detection(circular_project_result):
    analyzer = ProjectAnalyzer()
    index = analyzer.analyze(circular_project_result)

    # Check cycle detection
    cycles = index.find_call_cycles()
    assert len(cycles) > 0
```

**Task 2.5: Integration test with corpus**
```bash
cd python/
uv run pytest tests/test_analyzer.py -v
```

### Success Criteria
- [ ] All unit tests pass
- [ ] Integration with existing Normalizer works
- [ ] ProjectIndex correctly built from ProjectResult
- [ ] No breaking changes to existing code

---

## Phase 3: Add View Layer (6-8 hours)

### Goals
- Add `python/xaml_parser/views.py`
- Implement `FlatView`, `ExecutionView`, `SliceView`
- 100% backward compatible via FlatView

### Tasks

**Task 3.1: Create views.py**
- Copy `View` protocol from Part 4.2.1
- Copy `FlatView` from Part 4.2.2
- Copy `ExecutionView` from Part 4.2.3
- Copy `SliceView` from Part 4.2.4

**Task 3.2: Implement FlatView (backward compatible)**
Key requirement: FlatView must produce IDENTICAL output to current JSON emitter.

```python
class FlatView:
    def render(self, index: ProjectIndex) -> dict[str, Any]:
        # Convert ProjectIndex back to flat structure
        workflows = []

        for wf_id in index.workflows.nodes():
            wf_dto = index.get_workflow(wf_id)
            if not wf_dto:
                continue

            # Use dataclasses.asdict to maintain exact structure
            import dataclasses
            wf_dict = dataclasses.asdict(wf_dto)
            workflows.append(wf_dict)

        return {
            "schema_id": "https://rpax.io/schemas/xaml-workflow-collection.json",
            "schema_version": "1.0.0",
            "collected_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "workflows": workflows,
            "issues": [],
        }
```

**Task 3.3: Implement ExecutionView**
```python
class ExecutionView:
    def __init__(self, entry_point: str, max_depth: int = 10):
        self.entry_point = entry_point
        self.max_depth = max_depth

    def render(self, index: ProjectIndex) -> dict[str, Any]:
        # Implement call graph traversal with nesting
        # See Part 4.2.3 for complete implementation
        ...
```

**Task 3.4: Implement SliceView**
```python
class SliceView:
    def __init__(self, focus: str, radius: int = 2):
        self.focus = focus
        self.radius = radius

    def render(self, index: ProjectIndex) -> dict[str, Any]:
        # Implement context slicing
        # See Part 4.2.4 for complete implementation
        ...
```

**Task 3.5: Write unit tests**
Create `python/tests/test_views.py`:

```python
def test_flat_view_backward_compatible(sample_index, sample_collection_dto):
    """Test FlatView produces identical output to current format."""
    view = FlatView()
    output = view.render(sample_index)

    # Compare with current DTO output
    expected = dataclasses.asdict(sample_collection_dto)

    # Workflows should match
    assert len(output["workflows"]) == len(expected["workflows"])
    assert output["schema_id"] == expected["schema_id"]

def test_execution_view_nests_activities(sample_index):
    """Test ExecutionView produces nested structure."""
    view = ExecutionView(entry_point="wf:main", max_depth=10)
    output = view.render(sample_index)

    # Check nesting
    main_wf = output["workflows"][0]
    root_activities = main_wf["activities"]

    # Should have nested children (not just IDs)
    assert isinstance(root_activities[0]["children"], list)
    if root_activities[0]["children"]:
        assert isinstance(root_activities[0]["children"][0], dict)

def test_execution_view_expands_invoke(sample_index_with_invoke):
    """Test ExecutionView expands InvokeWorkflowFile."""
    view = ExecutionView(entry_point="wf:main", max_depth=10)
    output = view.render(sample_index_with_invoke)

    # Find InvokeWorkflowFile activity
    main_wf = output["workflows"][0]
    invoke_act = next(
        act for act in main_wf["activities"]
        if "InvokeWorkflowFile" in act["type"]
    )

    # Should have children from callee
    assert len(invoke_act["children"]) > 0
    assert "expanded_from" in invoke_act

def test_slice_view_context_window(sample_index):
    """Test SliceView extracts context window."""
    focal_activity_id = "act:sha256:abc123"
    view = SliceView(focus=focal_activity_id, radius=2)
    output = view.render(sample_index)

    # Check structure
    assert output["focus"] == focal_activity_id
    assert "focal_activity" in output
    assert "parent_chain" in output
    assert "context_activities" in output

    # Context should include activities within radius
    assert len(output["context_activities"]) > 1
```

### Success Criteria
- [ ] FlatView produces identical output to current format
- [ ] ExecutionView nests activities correctly
- [ ] ExecutionView expands InvokeWorkflowFile
- [ ] SliceView extracts context window
- [ ] All tests pass

---

## Phase 4: Modify Project Parser (3-4 hours)

### Goals
- Modify `project.py` to use analyzer
- Add option to return ProjectIndex or WorkflowCollectionDto
- Maintain backward compatibility

### Tasks

**Task 4.1: Add normalized_workflows to ProjectResult**
```python
# In project.py
@dataclass
class ProjectResult:
    # ... existing fields ...
    normalized_workflows: list[WorkflowDto] = field(default_factory=list)  # NEW
```

**Task 4.2: Modify ProjectParser to normalize during parsing**
```python
class ProjectParser:
    def __init__(self, parser_config: dict[str, Any] | None = None):
        self.parser_config = parser_config or {}
        self.xaml_parser = XamlParser(parser_config)
        self.normalizer = Normalizer()  # NEW

    def parse_project(self, project_dir: Path, ...) -> ProjectResult:
        # ... existing parsing ...

        # NEW: Normalize workflows
        normalized_workflows = []
        for wf_result in workflow_results:
            if wf_result.parse_result.success:
                workflow_name = Path(wf_result.file_path).stem
                workflow_dto = self.normalizer.normalize(
                    parse_result=wf_result.parse_result,
                    workflow_name=workflow_name,
                    workflow_id_map={},  # Build map first
                    sort_output=False,
                )
                normalized_workflows.append(workflow_dto)

        return ProjectResult(
            # ... existing fields ...
            normalized_workflows=normalized_workflows,  # NEW
        )
```

**Task 4.3: Add convenience method for analysis**
```python
# In project.py
def analyze_project(project_result: ProjectResult) -> ProjectIndex:
    """Analyze project and build graph structures.

    Args:
        project_result: Result from ProjectParser.parse_project()

    Returns:
        ProjectIndex with queryable graphs
    """
    from .analyzer import ProjectAnalyzer

    analyzer = ProjectAnalyzer()
    return analyzer.analyze(project_result)
```

**Task 4.4: Maintain backward compatibility**
Keep existing `project_result_to_dto()` function for backward compatibility:
```python
def project_result_to_dto(
    project_result: ProjectResult,
    normalizer: Normalizer | None = None,
    sort_output: bool = False,
) -> WorkflowCollectionDto:
    """Convert ProjectResult to WorkflowCollectionDto.

    DEPRECATED: Use analyze_project() + FlatView() instead.
    Maintained for backward compatibility.
    """
    # ... existing implementation ...
```

**Task 4.5: Update tests**
Ensure existing project tests still pass:
```bash
cd python/
uv run pytest tests/test_project.py -v
```

### Success Criteria
- [ ] ProjectParser still works as before
- [ ] New `analyze_project()` function available
- [ ] Backward compatibility maintained
- [ ] All existing tests pass

---

## Phase 5: Modify Emitters (4-6 hours)

### Goals
- Modify emitters to accept ProjectIndex + View
- Maintain backward compatibility with DTO input
- Add view parameter to EmitterConfig

### Tasks

**Task 5.1: Update EmitterConfig**
```python
# In emitters/__init__.py
@dataclass
class EmitterConfig:
    field_profile: str = "full"
    combine: bool = True
    pretty: bool = True
    exclude_none: bool = True
    view: str = "flat"  # NEW: flat, execution, slice, tree
    view_config: dict[str, Any] = field(default_factory=dict)  # NEW: View-specific config
```

**Task 5.2: Update JsonEmitter**
```python
# In emitters/json_emitter.py
class JsonEmitter:
    def emit_combined(
        self,
        data: WorkflowCollectionDto | ProjectIndex,  # Accept both!
        output_path: Path,
        config: EmitterConfig,
    ) -> None:
        """Emit combined JSON output.

        Args:
            data: WorkflowCollectionDto (legacy) or ProjectIndex (new)
            output_path: Output file path
            config: Emitter configuration
        """
        # Handle both types
        if isinstance(data, ProjectIndex):
            # New path: Apply view
            view = self._create_view(config)
            data_dict = view.render(data)
        else:
            # Legacy path: Direct DTO serialization
            data_dict = dataclasses.asdict(data)

        # Apply field profile, etc.
        # ... existing code ...

        # Write JSON
        self._write_json(data_dict, output_path, config.pretty)

    def _create_view(self, config: EmitterConfig) -> View:
        """Create view from config.

        Args:
            config: Emitter configuration

        Returns:
            View instance
        """
        from ..views import FlatView, ExecutionView, SliceView

        if config.view == "flat":
            return FlatView()
        elif config.view == "execution":
            entry_point = config.view_config.get("entry_point")
            max_depth = config.view_config.get("max_depth", 10)
            return ExecutionView(entry_point, max_depth)
        elif config.view == "slice":
            focus = config.view_config.get("focus")
            radius = config.view_config.get("radius", 2)
            return SliceView(focus, radius)
        else:
            raise ValueError(f"Unknown view: {config.view}")
```

**Task 5.3: Update MermaidEmitter**
Similar changes to MermaidEmitter:
```python
# In emitters/mermaid_emitter.py
class MermaidEmitter:
    def emit_combined(
        self,
        data: WorkflowCollectionDto | ProjectIndex,
        output_path: Path,
        config: EmitterConfig,
    ) -> None:
        # Apply view if ProjectIndex
        if isinstance(data, ProjectIndex):
            view = FlatView()  # Mermaid uses flat view
            workflows = view.render(data)["workflows"]
        else:
            workflows = data.workflows

        # ... existing Mermaid generation ...
```

**Task 5.4: Write tests**
```python
def test_json_emitter_with_project_index(sample_index, tmp_path):
    """Test JsonEmitter accepts ProjectIndex."""
    emitter = JsonEmitter()
    output_path = tmp_path / "output.json"
    config = EmitterConfig(view="flat")

    emitter.emit_combined(sample_index, output_path, config)

    assert output_path.exists()
    with open(output_path) as f:
        data = json.load(f)
    assert "workflows" in data

def test_json_emitter_execution_view(sample_index, tmp_path):
    """Test JsonEmitter with ExecutionView."""
    emitter = JsonEmitter()
    output_path = tmp_path / "output.json"
    config = EmitterConfig(
        view="execution",
        view_config={"entry_point": "wf:main", "max_depth": 10},
    )

    emitter.emit_combined(sample_index, output_path, config)

    # Check nested structure
    with open(output_path) as f:
        data = json.load(f)
    assert data["workflows"][0]["activities"][0]["children"]

def test_json_emitter_backward_compatible(sample_collection_dto, tmp_path):
    """Test JsonEmitter still accepts WorkflowCollectionDto."""
    emitter = JsonEmitter()
    output_path = tmp_path / "output.json"
    config = EmitterConfig(view="flat")

    emitter.emit_combined(sample_collection_dto, output_path, config)

    assert output_path.exists()
```

### Success Criteria
- [ ] Emitters accept both ProjectIndex and WorkflowCollectionDto
- [ ] FlatView produces identical output to current
- [ ] ExecutionView and SliceView work
- [ ] All tests pass
- [ ] Backward compatibility maintained

---

## Phase 6: CLI Integration (3-4 hours)

### Goals
- Add `--view` flag to CLI
- Add view-specific flags (`--entry`, `--focus`, `--radius`)
- Update CLI to use analyze_project() when view != flat

### Tasks

**Task 6.1: Add CLI flags**
```python
# In cli.py
parser.add_argument(
    "--view",
    choices=["flat", "execution", "slice"],
    default="flat",
    help=(
        "Output view: "
        "'flat' (default, current format), "
        "'execution' (call graph traversal from entry point), "
        "'slice' (context window around activity)"
    ),
)

parser.add_argument(
    "--entry",
    type=str,
    help="Entry point for execution view (workflow ID or path)",
)

parser.add_argument(
    "--focus",
    type=str,
    help="Focal activity ID for slice view",
)

parser.add_argument(
    "--radius",
    type=int,
    default=2,
    help="Radius for slice view (number of levels)",
)
```

**Task 6.2: Update CLI main logic**
```python
def main():
    args = parser.parse_args()

    # ... existing parsing ...

    # NEW: Handle view-based workflow
    if args.view != "flat":
        # Use ProjectParser + analyzer
        from xaml_parser.project import ProjectParser, analyze_project

        project_parser = ProjectParser(parser_config)
        project_result = project_parser.parse_project(project_dir)

        # Analyze
        project_index = analyze_project(project_result)

        # Create emitter config
        view_config = {}
        if args.view == "execution":
            if not args.entry:
                print("[ERROR] --entry required for execution view")
                return 1
            view_config = {"entry_point": args.entry, "max_depth": 10}
        elif args.view == "slice":
            if not args.focus:
                print("[ERROR] --focus required for slice view")
                return 1
            view_config = {"focus": args.focus, "radius": args.radius}

        emitter_config = EmitterConfig(
            field_profile=args.profile,
            combine=args.combine,
            pretty=args.pretty,
            exclude_none=not args.include_none,
            view=args.view,
            view_config=view_config,
        )

        # Emit
        emitter.emit_combined(project_index, output_path, emitter_config)
    else:
        # Legacy flat view path (backward compatible)
        # ... existing code ...
```

**Task 6.3: Update help text**
Update CLI help to document new flags:
```bash
xaml-parser --help
```

**Task 6.4: Manual testing**
```bash
cd python/

# Flat view (default, backward compatible)
uv run xaml-parser ../test-corpus/c25v001_CORE_00000001/ --json -o /tmp/flat.json

# Execution view
uv run xaml-parser ../test-corpus/c25v001_CORE_00000001/ --json --view=execution --entry=myEntrypointOne.xaml -o /tmp/execution.json

# Slice view
uv run xaml-parser ../test-corpus/c25v001_CORE_00000001/myEntrypointOne.xaml --json --view=slice --focus=act:sha256:abc123 --radius=2 -o /tmp/slice.json

# Verify outputs
cat /tmp/execution.json | jq '.workflows[0].activities[0]'
```

### Success Criteria
- [ ] CLI flags added
- [ ] Execution view works from CLI
- [ ] Slice view works from CLI
- [ ] Flat view still default (backward compatible)
- [ ] Help text updated

---

## Phase 7: Testing & Documentation (6-8 hours)

### Goals
- Comprehensive testing across all modules
- Update documentation
- Performance validation
- Corpus-based testing

### Tasks

**Task 7.1: Integration testing**
Create `python/tests/test_end_to_end.py`:
```python
def test_full_pipeline_flat_view(sample_project_dir):
    """Test complete pipeline: parse → analyze → flat view → emit."""
    # Parse
    parser = ProjectParser()
    project_result = parser.parse_project(sample_project_dir)

    # Analyze
    index = analyze_project(project_result)

    # Render flat view
    view = FlatView()
    output = view.render(index)

    # Validate
    assert "workflows" in output
    assert len(output["workflows"]) > 0

def test_full_pipeline_execution_view(sample_project_dir):
    """Test complete pipeline with execution view."""
    parser = ProjectParser()
    project_result = parser.parse_project(sample_project_dir)

    index = analyze_project(project_result)

    # Get entry point
    entry_wf_id = index.entry_points[0]

    # Render execution view
    view = ExecutionView(entry_point=entry_wf_id, max_depth=10)
    output = view.render(index)

    # Validate nesting
    main_wf = output["workflows"][0]
    assert isinstance(main_wf["activities"][0]["children"], list)

def test_backward_compatibility(sample_project_dir, tmp_path):
    """Test backward compatibility: old path vs new path produce same output."""
    # Old path
    parser = ProjectParser()
    project_result = parser.parse_project(sample_project_dir)
    old_dto = project_result_to_dto(project_result)
    old_output = dataclasses.asdict(old_dto)

    # New path
    index = analyze_project(project_result)
    view = FlatView()
    new_output = view.render(index)

    # Compare
    assert len(old_output["workflows"]) == len(new_output["workflows"])
    # ... detailed comparison ...
```

**Task 7.2: Corpus testing**
Update corpus tests to run with all views:
```python
@pytest.mark.corpus
def test_corpus_all_views(corpus_project_dir):
    """Test all corpus projects with all views."""
    parser = ProjectParser()
    project_result = parser.parse_project(corpus_project_dir)

    index = analyze_project(project_result)

    # Flat view
    flat = FlatView().render(index)
    assert flat

    # Execution view (if has entry points)
    if index.entry_points:
        exec_view = ExecutionView(index.entry_points[0]).render(index)
        assert exec_view
```

**Task 7.3: Performance testing**
```python
def test_performance_large_project(large_project_dir):
    """Test performance on large project (100+ workflows)."""
    import time

    parser = ProjectParser()

    start = time.time()
    project_result = parser.parse_project(large_project_dir)
    parse_time = time.time() - start

    start = time.time()
    index = analyze_project(project_result)
    analyze_time = time.time() - start

    print(f"Parse: {parse_time:.2f}s, Analyze: {analyze_time:.2f}s")

    # Assert reasonable performance
    assert analyze_time < 5.0  # Should be <5s for 100 workflows
```

**Task 7.4: Update documentation**

**Update docs/architecture.md:**
- Add section on graph-based analysis
- Document view layer pattern
- Add diagrams

**Update docs/ADR-DTO-DESIGN.md:**
- Add ADR for graph module
- Document view pattern decision
- Explain backward compatibility strategy

**Update CLAUDE.md:**
- Add examples of new views
- Document CLI usage
- Add performance notes

**Update README.md:**
- Add execution view example
- Add slice view example
- Update architecture diagram

**Task 7.5: Generate golden baselines**
```bash
cd python/

# Generate new golden baselines for execution view
uv run pytest tests/corpus/ -m corpus --update-golden

# Verify all corpus tests pass
uv run pytest tests/corpus/ -m corpus -v
```

### Success Criteria
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Corpus tests pass with all views
- [ ] Performance acceptable (<5s for 100 workflows)
- [ ] Documentation updated
- [ ] Golden baselines updated

---

# Part 6: Code Examples & Usage Patterns

## 6.1 Basic Usage

### Example 1: Parse and Analyze Project
```python
from xaml_parser.project import ProjectParser, analyze_project
from pathlib import Path

# Parse project
parser = ProjectParser()
project_result = parser.parse_project(Path("path/to/project"))

# Analyze (build graphs)
index = analyze_project(project_result)

# Query
print(f"Total workflows: {index.total_workflows}")
print(f"Total activities: {index.total_activities}")
print(f"Entry points: {len(index.entry_points)}")

# Detect cycles
cycles = index.find_call_cycles()
if cycles:
    print(f"WARNING: Found {len(cycles)} circular dependencies")
```

### Example 2: Flat View (Backward Compatible)
```python
from xaml_parser.views import FlatView
from xaml_parser.emitters import JsonEmitter, EmitterConfig

# Apply flat view
flat_view = FlatView()
output = flat_view.render(index)

# Emit JSON
emitter = JsonEmitter()
config = EmitterConfig(view="flat", pretty=True)
emitter.emit_combined(index, Path("output.json"), config)
```

### Example 3: Execution View (Call Graph Traversal)
```python
from xaml_parser.views import ExecutionView

# Get entry point
entry_wf_id = index.entry_points[0]

# Apply execution view
exec_view = ExecutionView(entry_point=entry_wf_id, max_depth=10)
output = exec_view.render(index)

# output["workflows"][0]["activities"] now has nested structure
# with InvokeWorkflowFile expanded
```

### Example 4: Slice View (Context Window)
```python
from xaml_parser.views import SliceView

# Get context around focal activity
focal_activity_id = "act:sha256:abc123..."
slice_view = SliceView(focus=focal_activity_id, radius=2)
output = slice_view.render(index)

# output has:
# - focal_activity
# - parent_chain (breadcrumbs)
# - siblings
# - context_activities
```

## 6.2 Advanced Queries

### Example 5: Find All Reachable Workflows
```python
# From entry point, what workflows can be called?
entry_wf_id = index.entry_points[0]
reachable = index.call_graph.reachable_from(entry_wf_id)

print(f"Entry point can call {len(reachable)} workflows")
for wf_id in reachable:
    wf = index.get_workflow(wf_id)
    print(f"  - {wf.name}")
```

### Example 6: Traverse Activity Hierarchy
```python
# Get all descendants of a Sequence activity
sequence_id = "act:sha256:abc123..."
descendants = index.activities.reachable_from(sequence_id)

print(f"Sequence contains {len(descendants)} activities:")
for act_id in descendants:
    act = index.get_activity(act_id)
    print(f"  {' ' * act.depth_level}{act.type_short}: {act.display_name}")
```

### Example 7: Find Parent Chain (Breadcrumbs)
```python
def get_parent_chain(activity_id: str, index: ProjectIndex) -> list[str]:
    """Get parent chain from root to activity."""
    chain = []
    current_id = activity_id

    while True:
        preds = index.activities.predecessors(current_id)
        if not preds:
            break

        parent_id = preds[0]
        chain.append(parent_id)
        current_id = parent_id

    return list(reversed(chain))

# Usage
activity_id = "act:sha256:def456..."
chain = get_parent_chain(activity_id, index)

print("Breadcrumbs:")
for act_id in chain:
    act = index.get_activity(act_id)
    print(f"{act.display_name} > ", end="")
print("(current)")
```

### Example 8: Custom Visitor for Traversal
```python
def print_execution_flow(index: ProjectIndex, entry_wf_id: str):
    """Print execution flow from entry point."""

    def visitor(wf_id: str, wf_dto, depth: int) -> bool:
        indent = "  " * depth
        print(f"{indent}[INFO] Workflow: {wf_dto.name}")

        # Print activities
        for activity in wf_dto.activities:
            act_indent = "  " * (depth + 1)
            print(f"{act_indent}- {activity.type_short}: {activity.display_name}")

        return True  # Continue traversal

    index.traverse_from(entry_wf_id, visitor, max_depth=5)

# Usage
entry_wf_id = index.entry_points[0]
print_execution_flow(index, entry_wf_id)
```

## 6.3 CLI Usage

### Flat View (Default)
```bash
# Same as before - backward compatible
xaml-parser path/to/project --json -o output.json

# Explicit flat view
xaml-parser path/to/project --json --view=flat -o output.json
```

### Execution View
```bash
# Traverse from entry point
xaml-parser path/to/project --json --view=execution --entry=Main.xaml -o execution.json

# View nested structure
cat execution.json | jq '.workflows[0].activities[0]'

# Output shows:
# {
#   "id": "act:...",
#   "type": "Sequence",
#   "children": [
#     { "id": "act:...", "type": "LogMessage", "children": [] },
#     {
#       "id": "act:...",
#       "type": "InvokeWorkflowFile",
#       "expanded_from": "wf:helper",
#       "children": [
#         { "id": "act:...", "type": "Sequence", ... }  # From helper workflow
#       ]
#     }
#   ]
# }
```

### Slice View
```bash
# Get context around specific activity
xaml-parser path/to/project/Main.xaml --json --view=slice --focus=act:sha256:abc123 --radius=2 -o slice.json

# View context
cat slice.json | jq '.focal_activity, .parent_chain, .siblings'
```

---

# Part 7: Testing Strategy

## 7.1 Unit Tests

### Graph Module (`test_graph.py`)
- [ ] Node add/remove/get
- [ ] Edge add/remove/has
- [ ] Successors/predecessors
- [ ] DFS traversal
- [ ] BFS traversal
- [ ] Cycle detection
- [ ] Topological sort
- [ ] Reachable nodes
- [ ] Subgraph extraction

### Analyzer Module (`test_analyzer.py`)
- [ ] ProjectIndex creation
- [ ] Workflow graph building
- [ ] Activity graph building
- [ ] Call graph building
- [ ] Control flow graph building
- [ ] Lookup maps
- [ ] Entry point detection

### Views Module (`test_views.py`)
- [ ] FlatView backward compatibility
- [ ] ExecutionView nesting
- [ ] ExecutionView call graph expansion
- [ ] ExecutionView cycle handling
- [ ] SliceView context extraction
- [ ] SliceView parent chain
- [ ] SliceView siblings

## 7.2 Integration Tests

### End-to-End (`test_end_to_end.py`)
- [ ] Full pipeline: parse → analyze → view → emit
- [ ] Backward compatibility: old path vs new path
- [ ] All views produce valid output
- [ ] Performance regression

### CLI Tests (`test_cli.py`)
- [ ] Flat view from CLI
- [ ] Execution view from CLI
- [ ] Slice view from CLI
- [ ] Error handling (missing --entry, --focus)

## 7.3 Corpus Tests

### Golden Baseline Tests (`test_corpus_golden.py`)
- [ ] All CORE projects parse successfully
- [ ] Flat view matches existing golden baselines
- [ ] Execution view generates valid output
- [ ] No regressions in existing projects

### Performance Tests (`test_corpus_performance.py`)
- [ ] Parse + analyze <5s for 100-workflow project
- [ ] Memory usage acceptable (<500MB for large project)
- [ ] No performance regression vs. baseline

## 7.4 Test Coverage Goals

- **Graph module**: >95% coverage (critical infrastructure)
- **Analyzer module**: >90% coverage
- **Views module**: >85% coverage
- **Overall project**: >80% coverage

---

# Part 8: Migration & Backward Compatibility

## 8.1 Backward Compatibility Strategy

### Principle: Zero Breaking Changes
- Current API must work exactly as before
- Flat output must be identical to current
- CLI without new flags behaves same as before

### Implementation

**1. Dual-Path Support**
```python
# Old path (still works)
from xaml_parser.project import ProjectParser, project_result_to_dto
parser = ProjectParser()
project_result = parser.parse_project(project_dir)
dto = project_result_to_dto(project_result)

# New path (optional)
from xaml_parser.project import ProjectParser, analyze_project
from xaml_parser.views import FlatView
parser = ProjectParser()
project_result = parser.parse_project(project_dir)
index = analyze_project(project_result)
flat = FlatView().render(index)
```

**2. Emitter Compatibility**
```python
# Emitters accept both types
def emit_combined(
    self,
    data: WorkflowCollectionDto | ProjectIndex,  # Both!
    output_path: Path,
    config: EmitterConfig,
) -> None:
    if isinstance(data, ProjectIndex):
        # New path
        view = self._create_view(config)
        data_dict = view.render(data)
    else:
        # Old path
        data_dict = dataclasses.asdict(data)

    # ... rest is same
```

**3. Default Behavior**
- CLI default: `--view=flat` (same as before)
- EmitterConfig default: `view="flat"` (same as before)
- FlatView output: identical to `dataclasses.asdict(WorkflowCollectionDto)`

## 8.2 Migration Guide

### For Library Users

**If you're using the Python API:**

**Before (still works):**
```python
from xaml_parser.project import ProjectParser, project_result_to_dto
from xaml_parser.emitters import JsonEmitter, EmitterConfig

parser = ProjectParser()
project_result = parser.parse_project(project_dir)
dto = project_result_to_dto(project_result)

emitter = JsonEmitter()
config = EmitterConfig(pretty=True)
emitter.emit_combined(dto, output_path, config)
```

**After (new, with execution view):**
```python
from xaml_parser.project import ProjectParser, analyze_project
from xaml_parser.views import ExecutionView
from xaml_parser.emitters import JsonEmitter, EmitterConfig

parser = ProjectParser()
project_result = parser.parse_project(project_dir)
index = analyze_project(project_result)

emitter = JsonEmitter()
config = EmitterConfig(
    pretty=True,
    view="execution",
    view_config={"entry_point": "Main.xaml", "max_depth": 10},
)
emitter.emit_combined(index, output_path, config)
```

### For CLI Users

**Before (still works):**
```bash
xaml-parser path/to/project --json -o output.json
```

**After (new, with execution view):**
```bash
xaml-parser path/to/project --json --view=execution --entry=Main.xaml -o output.json
```

### For Data Lake Consumers

**No changes needed!**
- Default flat view produces identical output
- Existing ETL pipelines work as-is
- Schema unchanged (unless using new views)

## 8.3 Deprecation Plan

### Phase 1 (Current): Full Backward Compatibility
- All old APIs work
- `project_result_to_dto()` marked as "legacy" in docs
- New users encouraged to use `analyze_project()`

### Phase 2 (Future, 6+ months): Soft Deprecation
- Add deprecation warnings to old APIs
- Documentation updated to show new patterns
- Migration examples provided

### Phase 3 (Future, 12+ months): Hard Deprecation
- Remove old APIs (optional - may keep forever)
- Only new graph-based API available

**Note:** Timeline flexible based on user feedback.

## 8.4 Version Compatibility

### Semantic Versioning
- Current: 0.x.x (pre-1.0)
- After this refactoring: Still 0.x.x (major changes, but backward compatible)
- Future 1.0: API stabilized, breaking changes require major version bump

### Schema Versioning
- Flat view: `schema_version: "1.0.0"` (unchanged)
- Execution view: `schema_version: "2.0.0"` (new schema)
- Slice view: `schema_version: "2.1.0"` (new schema)

---

## Summary

This comprehensive architecture refactoring transforms the xaml-parser from a flat-list parser to a graph-based code intelligence system. The changes:

**Enable:**
- ✓ Multiple views of same data (flat, execution, slice)
- ✓ Call graph traversal from entry point
- ✓ Context slicing for LLM consumption
- ✓ Cycle detection in workflow calls
- ✓ Reachability analysis
- ✓ Parent chain (breadcrumbs) navigation

**Maintain:**
- ✓ 100% backward compatibility
- ✓ Zero new external dependencies
- ✓ Existing data lake integration
- ✓ Current CLI behavior (with opt-in enhancements)

**Follow Industry Standards:**
- ✓ NetworkX-compatible graph API
- ✓ Roslyn-inspired view pattern
- ✓ LLVM-style IR (Intermediate Representation)
- ✓ Sourcegraph-style index-once, query-many

**Implementation Complexity:**
- ~200 lines: Graph module
- ~300 lines: Analyzer module
- ~400 lines: Views module
- ~100 lines: Modifications to existing modules
- **Total new code: ~1,000 lines**
- **Estimated time: 40-60 hours**

The result is a **production-grade, extensible architecture** that solves the user's original request ("show me execution flow with nested activities") while building a foundation for future enhancements (cycle detection, reachability, context windows, etc.).

**Next Steps:**
1. Review this document
2. Begin Phase 1: Graph module implementation
3. Test after each phase
4. Iterate based on feedback

Good luck with the implementation!
