# INSTRUCTIONS: Interprocedural Variable Ancestry Tracking

**Status**: Design Phase
**Author**: System Design based on CS 401 Analysis
**Date**: 2025-10-12
**Related**: ADR-DTO-DESIGN.md, ANALYSIS-xaml-metadata.md

---

## 1. Overview

### Objective

Implement **interprocedural variable ancestry tracking** to trace data flow across workflow boundaries, enabling:

- **Data lineage tracing**: "Where does this variable originate?"
- **Impact analysis**: "What's affected if I change variable X?"
- **Security auditing**: "Trace sensitive data flow across workflows"
- **Refactoring support**: "Can I safely rename this variable?"
- **Type flow analysis**: "How does this Dictionary value become a String?"

### Key Insight

We already capture **explicit argument bindings** in `InvocationDto.arguments_passed`, which provides the foundation for interprocedural analysis. Combined with:
- Stable variable/argument IDs (`var:sha256:...`, `arg:sha256:...`)
- Type annotations from XAML (`x:TypeArguments`)
- Activity parent relationships
- Expression text from Assign activities

We can build a complete **ancestry graph** tracking variables across workflows, including type transformations.

### Architecture Decision

**Parallel data structure**: Generate `ancestry_graph.json` as a separate output alongside `nested_view.json`

**Rationale**:
- Separation of concerns (parsing vs. expensive graph analysis)
- On-demand computation (only when needed)
- Graph-native format (nodes + edges)
- Export flexibility (JSON, GraphML, DOT)
- Performance (don't slow down default parsing)

---

## 2. Architecture Layers

### Layer 1: Data Collection (Already Implemented ✓)

**Source**: `XamlParser`, `Normalizer`, DTOs

**Provides**:
- `WorkflowDto` with variables, arguments, activities
- `InvocationDto` with `arguments_passed: dict[str, str]`
- Activity expressions in `properties`, `in_args`, `out_args`
- Type annotations from `VariableDto.type`, `ArgumentDto.type`
- Parent relationships via `ActivityDto.parent_id`

**Example data**:
```python
InvocationDto(
    callee_id="wf:sha256:WorkflowB",
    arguments_passed={
        "in_ConfigData": "[rawConfigDict]",  # Caller var → callee arg
        "out_Result": "[processedData]"
    }
)

VariableDto(
    id="var:sha256:abc123",
    name="rawConfigDict",
    type="System.Collections.Generic.Dictionary`2[System.String,System.Object]"
)
```

---

### Layer 2: Expression Analysis (NEW)

**Module**: `expression_parser.py`

**Purpose**: Parse VB/C# expressions to extract variable references and transformations

**Key Functions**:

```python
@dataclass
class Transformation:
    """Single transformation step in an expression."""
    operation: str  # 'dictionary_access' | 'method_call' | 'property_access' | 'array_index'
    details: dict[str, Any]  # Operation-specific data
    is_static: bool  # True if deterministic (static key, known method)

@dataclass
class ExpressionAnalysis:
    """Result of analyzing an expression."""
    source_variables: list[str]  # Variable names referenced
    transformations: list[Transformation]  # Transformation chain
    confidence: str  # 'definite' | 'possible' | 'unknown'

def analyze_expression(expr: str, workflow: WorkflowDto) -> ExpressionAnalysis:
    """Parse expression to extract variables and transformations.

    Examples:
        "[Config]" → {source: "Config", transformations: []}
        "[Config("Key").ToString()]" → {
            source: "Config",
            transformations: [
                Transformation(op='dictionary_access', details={'key': 'Key'}, is_static=True),
                Transformation(op='method_call', details={'method': 'ToString'}, is_static=True)
            ]
        }
        "[var1 + var2]" → {sources: ["var1", "var2"], transformations: [aggregate]}
    """
```

**Parsing Strategy** (Progressive Enhancement):

**Phase 1 - Regex-based** (MVP):
```python
# Pattern 1: Simple variable reference
SIMPLE_VAR = r'\[(\w+)\]'  # "[VarName]"

# Pattern 2: Dictionary/array access
DICT_ACCESS = r'(\w+)\((["\']?)([^"\'()]+)\2\)'  # VarName("key") or VarName(keyVar)

# Pattern 3: Method call
METHOD_CALL = r'\.(\w+)\(\)'  # .ToString()

# Pattern 4: Property access
PROPERTY_ACCESS = r'\.(\w+)(?![(\w])'  # .Name

# Pattern 5: Multiple variables (aggregate)
MULTIPLE_VARS = r'\[([^]]+(?:\+|\&amp;|,)[^]]+)\]'  # "[var1 + var2]"
```

**Phase 2 - Tree-sitter** (Future):
- Full VB/C# parsing for complex expressions
- Handle nested method calls, LINQ, etc.

---

### Layer 3: Type System Modeling (NEW)

**Module**: `type_system.py`

**Purpose**: Model .NET types with generic parameters and provide type inference

```python
@dataclass
class TypeInfo:
    """Represents a .NET type with full fidelity."""

    full_name: str  # "System.Collections.Generic.Dictionary`2[System.String,System.Object]"
    namespace: str  # "System.Collections.Generic"
    name: str  # "Dictionary"
    generic_args: list[TypeInfo] | None = None  # For generic types
    is_array: bool = False
    array_rank: int = 0  # For multi-dimensional arrays

    @staticmethod
    def parse(type_str: str) -> TypeInfo:
        """Parse .NET type string to TypeInfo.

        Examples:
            "System.String" → TypeInfo(full_name="System.String", name="String", ...)
            "Dictionary`2[String,Object]" → TypeInfo(name="Dictionary",
                generic_args=[TypeInfo("String"), TypeInfo("Object")])
            "String[]" → TypeInfo(name="String", is_array=True, array_rank=1)
        """

    def get_element_type(self) -> TypeInfo | None:
        """Get element type for collections/arrays.

        Dictionary`2[K,V] → returns V (value type)
        List`1[T] → returns T
        T[] → returns T
        """
        if self.is_array:
            return TypeInfo(full_name=self.name, name=self.name)

        if self.name == "Dictionary" and self.generic_args and len(self.generic_args) >= 2:
            return self.generic_args[1]  # Value type

        if self.name in ["List", "IEnumerable", "ICollection"] and self.generic_args:
            return self.generic_args[0]

        return None

    def infer_method_return_type(self, method_name: str) -> TypeInfo | None:
        """Infer return type of method call.

        Examples:
            Object.ToString() → TypeInfo("System.String")
            String.ToUpper() → TypeInfo("System.String")
            Dictionary.ContainsKey() → TypeInfo("System.Boolean")
        """
        # Built-in method signatures
        KNOWN_METHODS = {
            'ToString': TypeInfo(full_name='System.String', name='String'),
            'ToUpper': TypeInfo(full_name='System.String', name='String'),
            'ToLower': TypeInfo(full_name='System.String', name='String'),
            'Trim': TypeInfo(full_name='System.String', name='String'),
            'ContainsKey': TypeInfo(full_name='System.Boolean', name='Boolean'),
            'Count': TypeInfo(full_name='System.Int32', name='Int32'),
        }

        return KNOWN_METHODS.get(method_name)
```

---

### Layer 4: Ancestry Graph Construction (NEW)

**Module**: `ancestry_graph.py`

**Purpose**: Build directed graph representing variable relationships

```python
@dataclass
class AncestryNode:
    """Node in ancestry graph."""
    id: str  # var:sha256:... or arg:sha256:...
    entity_type: str  # 'variable' | 'argument'
    name: str
    type: TypeInfo
    workflow_id: str
    workflow_name: str
    scope: str  # 'workflow' | activity_id
    defined_at: str | None = None  # activity_id where defined/assigned

@dataclass
class AncestryEdge:
    """Edge representing variable relationship."""
    id: str  # edge:sha256:...
    from_id: str  # Source variable/argument
    to_id: str  # Target variable/argument
    kind: str  # See edge types below
    via_activity_id: str  # Activity that creates this relationship
    transformation: TransformationInfo | None = None
    confidence: str = 'definite'  # 'definite' | 'possible' | 'unknown'

@dataclass
class TransformationInfo:
    """Details about a transformation between variables."""
    operation: str  # 'dictionary_access' | 'method_call' | 'property_access' | 'cast' | 'aggregate'
    details: dict[str, Any]  # Operation-specific details
    from_type: TypeInfo | None = None  # Type before transformation
    to_type: TypeInfo | None = None  # Type after transformation

    # For dictionary_access:
    #   details = {'key': 'ConnectionString', 'key_is_static': True}
    # For method_call:
    #   details = {'method': 'ToString', 'arguments': []}
    # For property_access:
    #   details = {'property': 'Name'}
```

**Edge Types**:

| Kind | Direction | Meaning | Confidence |
|------|-----------|---------|------------|
| `arg_binding_in` | Caller var → Callee arg | In/InOut argument binding | Definite |
| `arg_binding_out` | Callee arg → Caller var | Out/InOut argument binding | Definite |
| `assign` | Source var → Target var | Direct assignment (same type) | Definite |
| `cast` | Source var → Target var | Type conversion (ToString, CInt, etc.) | Definite |
| `extract` | Parent var → Child var | Dictionary/array/property access | Definite/Possible |
| `transform` | Source var → Target var | Arithmetic, string ops, complex expr | Possible |
| `aggregate` | Multiple sources → Target | Concatenation, arithmetic with 2+ vars | Possible |

**Graph Structure**:
```python
class AncestryGraph:
    """Directed graph of variable ancestry relationships."""

    def __init__(self):
        self.graph = nx.DiGraph()  # NetworkX directed graph
        self.nodes: dict[str, AncestryNode] = {}
        self.edges: dict[str, AncestryEdge] = {}

    def add_node(self, node: AncestryNode) -> None:
        """Add variable/argument node."""
        self.nodes[node.id] = node
        self.graph.add_node(node.id, **asdict(node))

    def add_edge(self, edge: AncestryEdge) -> None:
        """Add relationship edge."""
        self.edges[edge.id] = edge
        self.graph.add_edge(edge.from_id, edge.to_id, **asdict(edge))
```

---

### Layer 5: Interprocedural Analyzer (NEW)

**Module**: `interprocedural_analysis.py`

**Purpose**: Orchestrate graph construction and provide query API

```python
class InterproceduralAliasAnalyzer:
    """Main analyzer for interprocedural variable ancestry."""

    def __init__(self, workflows: list[WorkflowDto]):
        self.workflows = {wf.id: wf for wf in workflows}
        self.graph = AncestryGraph()
        self.expression_parser = ExpressionParser()
        self.type_system = TypeSystem()

    def build_graph(self) -> AncestryGraph:
        """Build complete ancestry graph.

        Algorithm:
        1. Add all variables and arguments as nodes
        2. Add interprocedural edges (argument bindings)
        3. Add intraprocedural edges (assignments, transformations)
        4. Compute transitive relationships
        """
        self._add_nodes()
        self._add_interprocedural_edges()
        self._add_intraprocedural_edges()
        return self.graph

    def _add_nodes(self) -> None:
        """Phase 1: Add all variables and arguments as nodes."""
        for wf in self.workflows.values():
            for var in wf.variables:
                node = AncestryNode(
                    id=var.id,
                    entity_type='variable',
                    name=var.name,
                    type=TypeInfo.parse(var.type),
                    workflow_id=wf.id,
                    workflow_name=wf.name,
                    scope=var.scope
                )
                self.graph.add_node(node)

            for arg in wf.arguments:
                node = AncestryNode(
                    id=arg.id,
                    entity_type='argument',
                    name=arg.name,
                    type=TypeInfo.parse(arg.type),
                    workflow_id=wf.id,
                    workflow_name=wf.name,
                    scope='workflow'
                )
                self.graph.add_node(node)

    def _add_interprocedural_edges(self) -> None:
        """Phase 2: Add edges for InvokeWorkflowFile argument bindings."""
        for wf in self.workflows.values():
            for invocation in wf.invocations:
                callee = self.workflows.get(invocation.callee_id)
                if not callee:
                    continue  # Unresolved workflow

                for arg_name, caller_expr in invocation.arguments_passed.items():
                    # Parse caller expression
                    analysis = self.expression_parser.analyze(caller_expr, wf)

                    # Find callee argument
                    callee_arg = next((a for a in callee.arguments if a.name == arg_name), None)
                    if not callee_arg:
                        continue

                    # Find caller variable(s)
                    for caller_var_name in analysis.source_variables:
                        caller_var = next((v for v in wf.variables if v.name == caller_var_name), None)
                        if not caller_var:
                            continue

                        # Create edge based on argument direction
                        if callee_arg.direction in ['In', 'InOut']:
                            # Data flows: caller_var → callee_arg
                            edge = AncestryEdge(
                                id=self._generate_edge_id(caller_var.id, callee_arg.id, 'arg_binding_in'),
                                from_id=caller_var.id,
                                to_id=callee_arg.id,
                                kind='arg_binding_in',
                                via_activity_id=invocation.via_activity_id,
                                confidence='definite'
                            )
                            self.graph.add_edge(edge)

                        if callee_arg.direction in ['Out', 'InOut']:
                            # Data flows: callee_arg → caller_var
                            edge = AncestryEdge(
                                id=self._generate_edge_id(callee_arg.id, caller_var.id, 'arg_binding_out'),
                                from_id=callee_arg.id,
                                to_id=caller_var.id,
                                kind='arg_binding_out',
                                via_activity_id=invocation.via_activity_id,
                                confidence='definite'
                            )
                            self.graph.add_edge(edge)

    def _add_intraprocedural_edges(self) -> None:
        """Phase 3: Add edges for assignments and transformations within workflows."""
        for wf in self.workflows.values():
            for activity in wf.activities:
                if 'Assign' in activity.type_short:
                    self._process_assign(wf, activity)
                elif 'MultiAssign' in activity.type_short:
                    self._process_multiassign(wf, activity)
                # Add more activity types as needed

    def _process_assign(self, wf: WorkflowDto, activity: ActivityDto) -> None:
        """Process Assign activity to extract variable relationships."""
        # Extract To and Value
        to_expr = activity.in_args.get('To') or activity.properties.get('To')
        value_expr = activity.in_args.get('Value') or activity.properties.get('Value')

        if not to_expr or not value_expr:
            return

        # Parse target variable
        target_var_name = self._parse_simple_var_ref(to_expr)
        if not target_var_name:
            return

        target_var = next((v for v in wf.variables if v.name == target_var_name), None)
        if not target_var:
            return

        # Analyze value expression
        analysis = self.expression_parser.analyze(value_expr, wf)

        # Create edges for each source variable
        for source_var_name in analysis.source_variables:
            source_var = next((v for v in wf.variables if v.name == source_var_name), None)
            if not source_var:
                continue

            # Determine edge kind and transformation
            edge_kind, transformation = self._classify_relationship(
                source_var, target_var, analysis.transformations
            )

            edge = AncestryEdge(
                id=self._generate_edge_id(source_var.id, target_var.id, edge_kind),
                from_id=source_var.id,
                to_id=target_var.id,
                kind=edge_kind,
                via_activity_id=activity.id,
                transformation=transformation,
                confidence=analysis.confidence
            )
            self.graph.add_edge(edge)

    def _classify_relationship(
        self,
        source_var: VariableDto,
        target_var: VariableDto,
        transformations: list[Transformation]
    ) -> tuple[str, TransformationInfo | None]:
        """Classify relationship and build transformation info."""

        if not transformations:
            # Direct assignment
            return ('assign', None)

        # Build transformation chain with type flow
        current_type = TypeInfo.parse(source_var.type)

        for i, trans in enumerate(transformations):
            if trans.operation == 'dictionary_access':
                # Dict access: get element type
                element_type = current_type.get_element_type()

                return ('extract', TransformationInfo(
                    operation='dictionary_access',
                    details={
                        'key': trans.details.get('key'),
                        'key_is_static': trans.is_static
                    },
                    from_type=current_type,
                    to_type=element_type
                ))

            elif trans.operation == 'method_call':
                # Method call: infer return type
                method_name = trans.details.get('method')
                return_type = current_type.infer_method_return_type(method_name)

                return ('cast', TransformationInfo(
                    operation='method_call',
                    details={'method': method_name},
                    from_type=current_type,
                    to_type=return_type
                ))

        # Default: generic transformation
        return ('transform', TransformationInfo(
            operation='complex',
            details={'transformations': [t.operation for t in transformations]},
            from_type=TypeInfo.parse(source_var.type),
            to_type=TypeInfo.parse(target_var.type)
        ))

    # Query API

    def get_ancestry(self, var_id: str, max_depth: int = 10) -> list[AncestryPath]:
        """Get all ancestor paths for a variable.

        Returns list of paths from origin variables to target variable.
        """
        paths = []
        visited = set()

        def dfs(node_id: str, edge_path: list[AncestryEdge], depth: int):
            if depth > max_depth or node_id in visited:
                return

            visited.add(node_id)
            predecessors = list(self.graph.graph.predecessors(node_id))

            if not predecessors:
                # Found origin variable
                paths.append(AncestryPath(
                    origin_node=self.graph.nodes[node_id],
                    target_node=self.graph.nodes[var_id],
                    edges=list(reversed(edge_path)),
                    transformations=[e.transformation for e in edge_path if e.transformation],
                    confidence=self._compute_path_confidence(edge_path)
                ))
            else:
                for pred_id in predecessors:
                    edge = self.graph.edges[self.graph.graph[pred_id][node_id]['id']]
                    dfs(pred_id, edge_path + [edge], depth + 1)

        dfs(var_id, [], 0)
        return paths

    def trace_value_flow(self, var_id: str) -> ValueFlowTrace:
        """Trace complete value flow with confidence levels."""
        ancestry = self.get_ancestry(var_id)

        definite = []
        possible = []
        unknown = []

        for path in ancestry:
            if path.confidence == 'definite':
                definite.append(path)
            elif path.confidence == 'possible':
                possible.append(path)
            else:
                unknown.append(path)

        return ValueFlowTrace(
            variable=self.graph.nodes[var_id],
            definite_sources=definite,
            possible_sources=possible,
            unknown_sources=unknown
        )

    def get_descendants(self, var_id: str) -> list[AncestryNode]:
        """Get all variables that depend on this variable (forward slice)."""
        descendants = nx.descendants(self.graph.graph, var_id)
        return [self.graph.nodes[nid] for nid in descendants
                if self.graph.nodes[nid].entity_type == 'variable']

    def impact_analysis(self, var_id: str) -> ImpactAnalysisResult:
        """Analyze impact of changing a variable."""
        descendants = self.get_descendants(var_id)

        # Group by workflow
        by_workflow = {}
        for node in descendants:
            if node.workflow_id not in by_workflow:
                by_workflow[node.workflow_id] = []
            by_workflow[node.workflow_id].append(node)

        return ImpactAnalysisResult(
            source_variable=self.graph.nodes[var_id],
            affected_variables=descendants,
            affected_workflows=list(by_workflow.keys()),
            by_workflow=by_workflow
        )
```

---

### Layer 6: Output Formats (NEW)

**Module**: `emitters/ancestry_emitter.py`

**Purpose**: Export ancestry graph to various formats

#### JSON Format (`ancestry_graph.json`)

```json
{
  "$schema": "https://rpax.io/schemas/xaml-ancestry-graph.json",
  "schema_version": "1.0.0",
  "collected_at": "2025-10-12T10:30:00Z",
  "project_id": "proj:sha256:abc123",

  "nodes": [
    {
      "id": "var:sha256:abc123",
      "entity_type": "variable",
      "name": "configString",
      "type": {
        "full_name": "System.String",
        "namespace": "System",
        "name": "String"
      },
      "workflow_id": "wf:sha256:WorkflowB",
      "workflow_name": "ProcessConfig",
      "scope": "workflow"
    }
  ],

  "edges": [
    {
      "id": "edge:sha256:def456",
      "from_id": "var:sha256:rawDict",
      "to_id": "var:sha256:configString",
      "kind": "extract",
      "via_activity_id": "act:sha256:Assign_1",
      "transformation": {
        "operation": "dictionary_access",
        "details": {
          "key": "ConnectionString",
          "key_is_static": true
        },
        "from_type": {"name": "Dictionary", "generic_args": [...]},
        "to_type": {"name": "Object"}
      },
      "confidence": "definite"
    }
  ],

  "query_cache": {
    "ancestry": {
      "var:sha256:configString": {
        "definite_sources": [
          {
            "origin_var_id": "var:sha256:rawDict",
            "origin_workflow": "wf:sha256:WorkflowA",
            "transformation_chain": [
              "arg_binding → in_Data",
              "extract → dictionary[ConnectionString]",
              "cast → ToString()"
            ]
          }
        ]
      }
    }
  }
}
```

#### GraphML Format (for Gephi/Cytoscape)

```python
def export_graphml(graph: AncestryGraph, output_path: Path) -> None:
    """Export to GraphML for visualization tools."""
    nx.write_graphml(graph.graph, output_path)
```

#### DOT Format (for Graphviz)

```python
def export_dot(graph: AncestryGraph, output_path: Path) -> None:
    """Export to DOT format for Graphviz."""
    # Color by entity type
    # Shape by confidence
    # Edges labeled with transformation
```

---

## 3. Implementation Phases

### Phase 1: Foundation (Week 1)

**Goal**: Basic graph construction with interprocedural edges

**Tasks**:
1. Create `type_system.py` with `TypeInfo` class
   - `parse()` method for .NET type strings
   - `get_element_type()` for collections
   - Test with common UiPath types

2. Create `ancestry_graph.py` with graph data structure
   - `AncestryNode`, `AncestryEdge` dataclasses
   - `AncestryGraph` wrapper around NetworkX
   - Basic add_node/add_edge methods

3. Create `interprocedural_analysis.py` with basic analyzer
   - Load workflows from `WorkflowCollectionDto`
   - Add nodes for all variables/arguments
   - Add interprocedural edges from `InvocationDto.arguments_passed`

4. Write unit tests
   - Test type parsing
   - Test graph construction with 2-workflow scenario
   - Verify edges created correctly

**Deliverable**: Can build graph with interprocedural argument bindings

---

### Phase 2: Expression Analysis (Week 2)

**Goal**: Parse expressions and extract transformations

**Tasks**:
1. Create `expression_parser.py` with regex-based parsing
   - `analyze_expression()` main function
   - Patterns for: variable ref, dict access, method call, property
   - Return `ExpressionAnalysis` with sources and transformations

2. Add intraprocedural edge creation
   - `_process_assign()` in analyzer
   - Extract To/Value from Assign activities
   - Parse expressions and create edges

3. Implement transformation classification
   - `_classify_relationship()` method
   - Determine edge kind (assign/cast/extract/transform)
   - Build `TransformationInfo` with type flow

4. Write tests
   - Expression parsing test cases
   - Assign activity processing
   - Type flow through transformations

**Deliverable**: Can trace variables through Assign activities with transformations

---

### Phase 3: Type Flow (Week 3)

**Goal**: Complete type inference through transformations

**Tasks**:
1. Enhance `TypeInfo` with method signatures
   - `infer_method_return_type()` for common methods
   - Dictionary for known .NET methods (ToString, ToUpper, etc.)

2. Implement full type flow in `_classify_relationship()`
   - Track type changes through transformation chain
   - Dictionary access → element type
   - Method call → return type
   - Store intermediate types in `TransformationInfo`

3. Add confidence scoring
   - Definite: static keys, known methods
   - Possible: dynamic keys but traceable
   - Unknown: complex expressions

4. Write tests
   - Type inference for dictionary access
   - Method return type inference
   - Confidence level assignment

**Deliverable**: Full type lineage with confidence levels

---

### Phase 4: Query API (Week 4)

**Goal**: Provide powerful query capabilities

**Tasks**:
1. Implement `get_ancestry()` with DFS
   - Find all ancestor paths
   - Respect max_depth limit
   - Return `AncestryPath` objects with full details

2. Implement `trace_value_flow()`
   - Group ancestors by confidence
   - Return structured `ValueFlowTrace`

3. Implement `get_descendants()` and `impact_analysis()`
   - Forward slice through graph
   - Group by workflow
   - Return impact summary

4. Write comprehensive query tests
   - Multi-hop ancestry across 3+ workflows
   - Type transformations in chain
   - Impact analysis scenarios

**Deliverable**: Complete query API for ancestry analysis

---

### Phase 5: Output Formats (Week 5)

**Goal**: Export to multiple formats

**Tasks**:
1. Create `emitters/ancestry_emitter.py`
   - JSON emitter with schema
   - Include query cache for common queries
   - Pretty printing with indentation

2. Add GraphML export
   - Use NetworkX built-in writer
   - Add node/edge attributes

3. Add DOT export for Graphviz
   - Custom formatting with colors
   - Edge labels with transformations
   - Cluster by workflow

4. CLI integration
   - `xaml-parser --ancestry` flag
   - `xaml-ancestry` separate command
   - Output format selection

**Deliverable**: Multi-format export with CLI integration

---

### Phase 6: Optimization & Advanced Features (Week 6)

**Goal**: Performance and advanced analysis

**Tasks**:
1. Caching and incremental updates
   - Cache ancestry queries
   - Incremental graph updates on file changes

2. Advanced expression parsing (optional)
   - Tree-sitter integration for full VB/C# parsing
   - Handle complex nested expressions
   - LINQ query support

3. Security/compliance features
   - Tag sensitive variables
   - Trace PII data flow
   - Generate compliance reports

4. Documentation
   - User guide for ancestry queries
   - API documentation
   - Example use cases

**Deliverable**: Production-ready ancestry analysis system

---

## 4. File Structure

```
python/xaml_parser/
├── interprocedural_analysis.py     # Main analyzer class
│   └── class InterproceduralAliasAnalyzer
│
├── expression_parser.py            # VB/C# expression parsing
│   ├── class ExpressionParser
│   ├── dataclass Transformation
│   └── dataclass ExpressionAnalysis
│
├── type_system.py                  # .NET type modeling
│   ├── class TypeInfo
│   └── KNOWN_METHOD_SIGNATURES
│
├── ancestry_graph.py               # Graph data structure
│   ├── class AncestryGraph
│   ├── dataclass AncestryNode
│   ├── dataclass AncestryEdge
│   └── dataclass TransformationInfo
│
├── emitters/
│   └── ancestry_emitter.py         # Export formats
│       ├── class AncestryJsonEmitter
│       ├── export_graphml()
│       └── export_dot()
│
└── cli.py                          # CLI integration
    └── ancestry_command()

tests/
├── test_type_system.py
├── test_expression_parser.py
├── test_ancestry_graph.py
├── test_interprocedural_analysis.py
└── test_ancestry_emitter.py

docs/
└── INSTRUCTIONS-ancestry.md        # This file
```

---

## 5. Testing Strategy

### Unit Tests

**Type System** (`test_type_system.py`):
```python
def test_parse_simple_type():
    t = TypeInfo.parse("System.String")
    assert t.name == "String"
    assert t.namespace == "System"

def test_parse_generic_type():
    t = TypeInfo.parse("Dictionary`2[System.String,System.Object]")
    assert t.name == "Dictionary"
    assert len(t.generic_args) == 2
    assert t.generic_args[1].name == "Object"

def test_get_element_type_dictionary():
    t = TypeInfo.parse("Dictionary`2[String,Object]")
    elem = t.get_element_type()
    assert elem.name == "Object"

def test_infer_method_return_type():
    t = TypeInfo.parse("System.Object")
    ret = t.infer_method_return_type("ToString")
    assert ret.name == "String"
```

**Expression Parser** (`test_expression_parser.py`):
```python
def test_parse_simple_variable():
    analysis = analyze_expression("[myVar]", workflow)
    assert analysis.source_variables == ["myVar"]
    assert len(analysis.transformations) == 0

def test_parse_dictionary_access():
    analysis = analyze_expression('[Config("Key").ToString()]', workflow)
    assert analysis.source_variables == ["Config"]
    assert len(analysis.transformations) == 2
    assert analysis.transformations[0].operation == "dictionary_access"
    assert analysis.transformations[0].details['key'] == "Key"
    assert analysis.transformations[1].operation == "method_call"

def test_parse_multiple_variables():
    analysis = analyze_expression("[var1 + var2]", workflow)
    assert len(analysis.source_variables) == 2
    assert "var1" in analysis.source_variables
    assert "var2" in analysis.source_variables
```

**Ancestry Graph** (`test_ancestry_graph.py`):
```python
def test_add_node():
    graph = AncestryGraph()
    node = AncestryNode(id="var:sha256:abc", entity_type="variable", ...)
    graph.add_node(node)
    assert "var:sha256:abc" in graph.nodes

def test_add_edge():
    graph = AncestryGraph()
    # Add nodes first
    edge = AncestryEdge(from_id="var1", to_id="var2", kind="assign", ...)
    graph.add_edge(edge)
    assert graph.graph.has_edge("var1", "var2")
```

### Integration Tests

**Two-Workflow Scenario** (`test_interprocedural_analysis.py`):
```python
def test_cross_workflow_ancestry():
    """Test ancestry across InvokeWorkflowFile."""
    # Workflow A: rawDict variable
    # Workflow B: receives as in_Data arg, assigns to configString

    analyzer = InterproceduralAliasAnalyzer([workflow_a, workflow_b])
    graph = analyzer.build_graph()

    # Query ancestry of configString
    paths = analyzer.get_ancestry("var:sha256:configString")

    assert len(paths) == 1
    assert paths[0].origin_node.name == "rawDict"
    assert paths[0].origin_node.workflow_id == workflow_a.id

    # Check transformation chain
    assert len(paths[0].edges) == 3
    assert paths[0].edges[0].kind == "arg_binding_in"
    assert paths[0].edges[1].kind == "assign"
    assert paths[0].edges[2].kind == "extract"
```

**Type Flow Test**:
```python
def test_type_flow_through_dict_access():
    """Test type inference through dictionary access and cast."""
    # Config: Dictionary<String,Object>
    # configString = Config("Key").ToString()

    analyzer = InterproceduralAliasAnalyzer([workflow])
    graph = analyzer.build_graph()

    # Find edge from Config to configString
    edge = find_edge(graph, "var:Config", "var:configString")

    assert edge.transformation.operation == "dictionary_access"
    assert edge.transformation.from_type.name == "Dictionary"
    assert edge.transformation.to_type.name == "Object"  # Intermediate

    # Check final type is String (from ToString)
    target_node = graph.nodes["var:configString"]
    assert target_node.type.name == "String"
```

### Corpus Tests

**Real UiPath Projects** (mark with `@pytest.mark.corpus`):
```python
@pytest.mark.corpus
def test_ancestry_on_core_project():
    """Test ancestry analysis on CORE reference project."""
    project_path = Path("test-corpus/c25v001_CORE_00000001")

    # Parse project
    parser = ProjectParser()
    project_result = parser.parse_project(project_path)

    # Build ancestry graph
    analyzer = InterproceduralAliasAnalyzer(project_result.workflows)
    graph = analyzer.build_graph()

    # Verify graph metrics
    assert len(graph.nodes) > 50  # Expect many variables
    assert len(graph.edges) > 30  # Expect many relationships

    # Test specific ancestry
    config_var = find_variable_by_name(graph, "Config")
    if config_var:
        ancestry = analyzer.get_ancestry(config_var.id)
        # Should trace back to InitAllSettings workflow
```

---

## 6. Example Use Cases

### Use Case 1: Security Audit

**Question**: "Where does the password variable originate and where is it used?"

```python
# Find password variable
password_var = find_variable_by_name(graph, "password")

# Trace origins
flow = analyzer.trace_value_flow(password_var.id)
for source in flow.definite_sources:
    print(f"Origin: {source.origin_node.name} in {source.origin_node.workflow_name}")
    print(f"Path: {' → '.join(source.transformation_chain)}")

# Trace usage
impact = analyzer.impact_analysis(password_var.id)
print(f"Used in {len(impact.affected_workflows)} workflows:")
for wf_id, vars in impact.by_workflow.items():
    print(f"  - {wf_id}: {[v.name for v in vars]}")
```

**Output**:
```
Origin: userCredentials in Login workflow
Path: dictionary_access["password"] → arg_binding → cast:ToString()

Used in 3 workflows:
  - wf:ProcessPayment: [encryptedPassword, apiCredentials]
  - wf:LogTransaction: [maskedPassword]
  - wf:SendEmail: [*** SECURITY ALERT: password in plaintext email ***]
```

### Use Case 2: Debugging Type Mismatch

**Question**: "Why is configString giving me a type error?"

```python
config_string_var = find_variable_by_name(graph, "configString")
paths = analyzer.get_ancestry(config_string_var.id)

for path in paths:
    print(f"Origin: {path.origin_node.name} ({path.origin_node.type.name})")

    current_type = path.origin_node.type
    for edge in path.edges:
        if edge.transformation:
            print(f"  {edge.kind}: {edge.transformation.operation}")
            print(f"    {edge.transformation.from_type.name} → {edge.transformation.to_type.name}")
            current_type = edge.transformation.to_type

    print(f"Final type: {current_type.name}")
```

**Output**:
```
Origin: rawConfigDict (Dictionary<String,Object>)
  extract: dictionary_access
    Dictionary → Object
  cast: method_call (ToString)
    Object → String
Final type: String

Issue: Dictionary value was Object, but key "ConnectionString" might not exist!
Recommendation: Add null check or use TryGetValue
```

### Use Case 3: Refactoring Impact

**Question**: "If I change the structure of appSettings dictionary, what breaks?"

```python
settings_var = find_variable_by_name(graph, "appSettings")
impact = analyzer.impact_analysis(settings_var.id)

print(f"Changing appSettings affects {len(impact.affected_variables)} variables:")

for var in impact.affected_variables:
    # Find how it's used
    edge = find_edge_to(graph, settings_var.id, var.id)
    if edge and edge.transformation:
        details = edge.transformation.details
        if 'key' in details:
            print(f"  - {var.name} in {var.workflow_name}")
            print(f"    Uses key: '{details['key']}'")
```

**Output**:
```
Changing appSettings affects 8 variables:
  - dbConnectionString in ProcessOrder
    Uses key: 'DatabaseConnection'
  - apiEndpoint in CallExternalService
    Uses key: 'ApiBaseUrl'
  - logLevel in InitializeLogger
    Uses key: 'LogLevel'
...

Recommendation: If changing dictionary structure, update these 8 access points
```

---

## 7. CLI Integration

### New Commands

```bash
# Generate ancestry graph alongside normal parsing
xaml-parser project.json --dto --ancestry

# Output:
#   nested_view.json          (workflow structure)
#   ancestry_graph.json       (lineage graph)

# Generate ancestry from existing output
xaml-ancestry nested_view.json -o ancestry_graph.json

# Export to different format
xaml-ancestry nested_view.json --format graphml -o ancestry.graphml
xaml-ancestry nested_view.json --format dot -o ancestry.dot

# Query ancestry (interactive)
xaml-query ancestry ancestry_graph.json

# Query specific variable
xaml-query ancestry ancestry_graph.json --var "var:sha256:abc123" --operation ancestors
xaml-query ancestry ancestry_graph.json --var "var:sha256:abc123" --operation descendants
xaml-query ancestry ancestry_graph.json --var "var:sha256:abc123" --operation impact

# Security scan
xaml-query ancestry ancestry_graph.json --scan-sensitive --keywords "password,secret,apikey"
```

### CLI Implementation

```python
# cli.py

@click.command()
@click.argument('nested_view_json', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output path')
@click.option('--format', type=click.Choice(['json', 'graphml', 'dot']), default='json')
def ancestry_command(nested_view_json: str, output: str, format: str):
    """Generate ancestry graph from workflow collection."""

    # Load workflows
    with open(nested_view_json) as f:
        collection = WorkflowCollectionDto.from_dict(json.load(f))

    # Build ancestry graph
    analyzer = InterproceduralAliasAnalyzer(collection.workflows)
    graph = analyzer.build_graph()

    # Export
    if format == 'json':
        emitter = AncestryJsonEmitter()
        emitter.emit(graph, output)
    elif format == 'graphml':
        export_graphml(graph, output)
    elif format == 'dot':
        export_dot(graph, output)

    click.echo(f"Ancestry graph written to {output}")
    click.echo(f"  Nodes: {len(graph.nodes)}")
    click.echo(f"  Edges: {len(graph.edges)}")
```

---

## 8. Performance Considerations

### Expected Complexity

**Graph Construction**:
- Nodes: O(V + A) where V = variables, A = arguments
- Interprocedural edges: O(W × I × P) where W = workflows, I = invocations, P = arguments per invocation
- Intraprocedural edges: O(W × A × E) where A = activities, E = expressions per activity
- **Total**: O(V + W×I×P + W×A×E) ≈ O(n) for typical projects

**Ancestry Query**:
- BFS/DFS: O(V + E) per query
- With memoization: O(1) for cached queries

**Typical Project**:
- 50 workflows × 20 variables = 1,000 variable nodes
- 50 workflows × 5 invocations = 250 interprocedural edges
- 50 workflows × 100 activities × 0.3 assigns = 1,500 intraprocedural edges
- **Total graph size**: ~1,000 nodes, ~2,000 edges
- **Build time**: <1 second
- **Query time**: <10ms

### Optimization Strategies

1. **Lazy Loading**: Only build graph when ancestry analysis requested
2. **Incremental Updates**: When one workflow changes, only update affected subgraph
3. **Query Caching**: Cache common ancestry queries in JSON output
4. **Parallel Processing**: Build graph for each workflow in parallel, merge afterward
5. **Sparse Graph Storage**: Use adjacency lists, not matrices

---

## 9. Future Enhancements

### Phase 7+ (Beyond Initial Implementation)

1. **Control-Flow Sensitivity**
   - Track which branch assigns which value
   - If/Else path-specific ancestry
   - Loop iteration tracking

2. **State Machine Analysis**
   - Track variable values across state transitions
   - Detect state-dependent transformations

3. **Collection Element Tracking**
   - Track individual array/list elements
   - Detect when element is extracted vs. collection passed as-is

4. **UI Selector Ancestry**
   - Track how selector variables are constructed
   - Trace selector components across workflows

5. **Machine Learning Integration**
   - Learn common transformation patterns
   - Suggest missing type annotations
   - Predict likely ancestry when static analysis fails

6. **Visualization**
   - Interactive web UI for ancestry exploration
   - D3.js graph visualization
   - Zoom/filter by workflow or confidence level

---

## 10. Success Criteria

The implementation is successful when:

✅ **Correctness**:
- [ ] Accurately tracks variables across InvokeWorkflowFile boundaries
- [ ] Correctly identifies transformations (dictionary access, casts, etc.)
- [ ] Properly infers types through transformation chains
- [ ] Handles all edge cases in test suite

✅ **Performance**:
- [ ] Builds graph for 100-workflow project in <5 seconds
- [ ] Query response time <50ms for ancestry lookup
- [ ] Memory usage <500MB for large projects

✅ **Usability**:
- [ ] CLI commands are intuitive
- [ ] JSON output is well-documented and self-describing
- [ ] Error messages are helpful
- [ ] Documentation includes examples

✅ **Robustness**:
- [ ] Handles unresolved workflows gracefully
- [ ] Deals with dynamic expressions conservatively
- [ ] Provides confidence levels for uncertain analysis
- [ ] Passes all corpus tests

✅ **Value**:
- [ ] Enables security auditing use cases
- [ ] Supports debugging type mismatches
- [ ] Facilitates refactoring with impact analysis
- [ ] Provides foundation for advanced analysis tools

---

## 11. References

### Computer Science Literature

1. **Interprocedural Data Flow Analysis**
   - Aho, Sethi, Ullman: "Compilers: Principles, Techniques, and Tools" (Dragon Book)
   - Chapter 10: Interprocedural Analysis

2. **Alias Analysis**
   - Hind, M.: "Pointer Analysis: Haven't We Solved This Problem Yet?" (2001)
   - Landi, W.: "Undecidability of Static Analysis" (1992)

3. **SSA Form and φ-functions**
   - Cytron et al.: "Efficiently Computing Static Single Assignment Form" (1991)
   - Braun et al.: "Simple and Efficient Construction of SSA Form" (2013)

4. **Program Slicing**
   - Weiser, M.: "Program Slicing" (1981)
   - Tip, F.: "A Survey of Program Slicing Techniques" (1995)

### UiPath Documentation

- UiPath Studio: Variable Scope and Lifetime
- InvokeWorkflowFile Activity Reference
- VB.NET Expression Syntax
- XAML Workflow Foundation Structure

### Internal Documentation

- `docs/ADR-DTO-DESIGN.md` - DTO architecture
- `docs/ANALYSIS-xaml-metadata.md` - XAML metadata analysis
- `docs/INSTRUCTIONS-nesting.md` - Call graph traversal
- `python/xaml_parser/dto.py` - DTO definitions
- `python/xaml_parser/normalization.py` - DTO transformation

---

**END OF INSTRUCTIONS**
