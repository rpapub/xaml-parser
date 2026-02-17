"""Ancestry graph data structures for variable lineage tracking.

This module provides the graph representation for tracking variable relationships
across workflow boundaries, including interprocedural data flow and transformations.
"""

from dataclasses import asdict, dataclass, field
from typing import Any

try:
    import networkx as nx
except ImportError:
    nx = None  # Optional dependency

from ...stages.parsing.type_system import TypeInfo


@dataclass
class AncestryNode:
    """Node in ancestry graph representing a variable or argument.

    Attributes:
        id: Stable entity ID (var:sha256:... or arg:sha256:...)
        entity_type: 'variable' or 'argument'
        name: Entity name
        type: Full type information
        workflow_id: Parent workflow ID
        workflow_name: Parent workflow name
        scope: Scope identifier ('workflow' or activity_id)
        defined_at: Activity ID where this entity is defined/assigned (optional)
    """

    id: str
    entity_type: str  # 'variable' | 'argument'
    name: str
    type: TypeInfo
    workflow_id: str
    workflow_name: str
    scope: str = "workflow"
    defined_at: str | None = None


@dataclass
class TransformationInfo:
    """Details about a transformation between variables.

    Attributes:
        operation: Type of transformation operation
        details: Operation-specific details dictionary
        from_type: Type before transformation (optional)
        to_type: Type after transformation (optional)
    """

    operation: str  # 'dictionary_access' | 'method_call' | 'property_access' | 'cast' | 'aggregate'
    details: dict[str, Any] = field(default_factory=dict)
    from_type: TypeInfo | None = None
    to_type: TypeInfo | None = None


@dataclass
class AncestryEdge:
    """Edge representing variable relationship in ancestry graph.

    Attributes:
        id: Stable edge ID (edge:sha256:...)
        from_id: Source variable/argument ID
        to_id: Target variable/argument ID
        kind: Relationship type
        via_activity_id: Activity that creates this relationship
        transformation: Transformation details (optional)
        confidence: Analysis confidence level
    """

    id: str
    from_id: str
    to_id: str
    # 'arg_binding_in' | 'arg_binding_out' | 'assign' | 'cast' | 'extract' | 'transform' | 'aggregate'
    kind: str
    via_activity_id: str
    transformation: TransformationInfo | None = None
    confidence: str = "definite"  # 'definite' | 'possible' | 'unknown'


@dataclass
class AncestryPath:
    """A path from origin variable to target variable through edges.

    Attributes:
        origin_node: Starting variable/argument node
        target_node: Ending variable/argument node
        edges: List of edges in path (ordered from origin to target)
        transformations: List of transformations along path
        confidence: Overall confidence for this path
    """

    origin_node: AncestryNode
    target_node: AncestryNode
    edges: list[AncestryEdge] = field(default_factory=list)
    transformations: list[TransformationInfo] = field(default_factory=list)
    confidence: str = "definite"


@dataclass
class ValueFlowTrace:
    """Complete value flow trace for a variable with confidence levels.

    Attributes:
        variable: Target variable being traced
        definite_sources: Paths with definite confidence
        possible_sources: Paths with possible confidence
        unknown_sources: Paths with unknown confidence
    """

    variable: AncestryNode
    definite_sources: list[AncestryPath] = field(default_factory=list)
    possible_sources: list[AncestryPath] = field(default_factory=list)
    unknown_sources: list[AncestryPath] = field(default_factory=list)


@dataclass
class ImpactAnalysisResult:
    """Result of impact analysis for a variable.

    Attributes:
        source_variable: Variable being analyzed
        affected_variables: All variables that depend on source
        affected_workflows: Workflow IDs containing affected variables
        by_workflow: Affected variables grouped by workflow
    """

    source_variable: AncestryNode
    affected_variables: list[AncestryNode] = field(default_factory=list)
    affected_workflows: list[str] = field(default_factory=list)
    by_workflow: dict[str, list[AncestryNode]] = field(default_factory=dict)


class AncestryGraph:
    """Directed graph of variable ancestry relationships.

    This class wraps NetworkX (if available) or provides fallback graph implementation
    for tracking variable lineage across workflows.
    """

    def __init__(self) -> None:
        """Initialize ancestry graph."""
        self.nodes: dict[str, AncestryNode] = {}
        self.edges: dict[str, AncestryEdge] = {}

        # Use NetworkX if available, otherwise fall back to dict-based graph
        if nx:
            self.graph = nx.DiGraph()
            self.use_networkx = True
        else:
            # Simple adjacency list representation
            self.graph: dict[str, list[str]] = {}  # node_id → [successor_ids]
            self._predecessors: dict[str, list[str]] = {}  # node_id → [predecessor_ids]
            self.use_networkx = False

    def add_node(self, node: AncestryNode) -> None:
        """Add variable/argument node to graph.

        Args:
            node: AncestryNode to add
        """
        self.nodes[node.id] = node

        if self.use_networkx:
            self.graph.add_node(node.id, **asdict(node))
        else:
            if node.id not in self.graph:
                self.graph[node.id] = []
            if node.id not in self._predecessors:
                self._predecessors[node.id] = []

    def add_edge(self, edge: AncestryEdge) -> None:
        """Add relationship edge to graph.

        Args:
            edge: AncestryEdge to add
        """
        self.edges[edge.id] = edge

        if self.use_networkx:
            self.graph.add_edge(edge.from_id, edge.to_id, **asdict(edge))
        else:
            # Adjacency list
            if edge.from_id not in self.graph:
                self.graph[edge.from_id] = []
            if edge.to_id not in self.graph:
                self.graph[edge.to_id] = []

            self.graph[edge.from_id].append(edge.to_id)

            # Track predecessors for backward traversal
            if edge.to_id not in self._predecessors:
                self._predecessors[edge.to_id] = []
            self._predecessors[edge.to_id].append(edge.from_id)

    def get_successors(self, node_id: str) -> list[str]:
        """Get successor nodes (nodes that this node points to).

        Args:
            node_id: Node ID

        Returns:
            List of successor node IDs
        """
        if self.use_networkx:
            return list(self.graph.successors(node_id))
        else:
            return self.graph.get(node_id, [])

    def get_predecessors(self, node_id: str) -> list[str]:
        """Get predecessor nodes (nodes that point to this node).

        Args:
            node_id: Node ID

        Returns:
            List of predecessor node IDs
        """
        if self.use_networkx:
            return list(self.graph.predecessors(node_id))
        else:
            return self._predecessors.get(node_id, [])

    def get_descendants(self, node_id: str) -> set[str]:
        """Get all descendant nodes (forward reachability).

        Args:
            node_id: Starting node ID

        Returns:
            Set of all descendant node IDs
        """
        if self.use_networkx:
            return set(nx.descendants(self.graph, node_id))
        else:
            # BFS for descendants
            descendants = set()
            visited = set()
            queue = [node_id]

            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue
                visited.add(current)

                for successor in self.get_successors(current):
                    if successor not in visited:
                        descendants.add(successor)
                        queue.append(successor)

            return descendants

    def get_ancestors(self, node_id: str) -> set[str]:
        """Get all ancestor nodes (backward reachability).

        Args:
            node_id: Target node ID

        Returns:
            Set of all ancestor node IDs
        """
        if self.use_networkx:
            return set(nx.ancestors(self.graph, node_id))
        else:
            # BFS for ancestors
            ancestors = set()
            visited = set()
            queue = [node_id]

            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue
                visited.add(current)

                for predecessor in self.get_predecessors(current):
                    if predecessor not in visited:
                        ancestors.add(predecessor)
                        queue.append(predecessor)

            return ancestors

    def find_edge(self, from_id: str, to_id: str) -> AncestryEdge | None:
        """Find edge between two nodes.

        Args:
            from_id: Source node ID
            to_id: Target node ID

        Returns:
            AncestryEdge if found, None otherwise
        """
        for edge in self.edges.values():
            if edge.from_id == from_id and edge.to_id == to_id:
                return edge
        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert graph to dictionary for JSON serialization.

        Returns:
            Dictionary representation of graph
        """
        return {
            "nodes": [self._node_to_dict(node) for node in self.nodes.values()],
            "edges": [self._edge_to_dict(edge) for edge in self.edges.values()],
        }

    def _node_to_dict(self, node: AncestryNode) -> dict[str, Any]:
        """Convert AncestryNode to dictionary.

        Args:
            node: Node to convert

        Returns:
            Dictionary representation
        """
        return {
            "id": node.id,
            "entity_type": node.entity_type,
            "name": node.name,
            "type": {
                "full_name": node.type.full_name,
                "namespace": node.type.namespace,
                "name": node.type.name,
                "generic_args": (
                    [self._type_to_dict(arg) for arg in node.type.generic_args]
                    if node.type.generic_args
                    else None
                ),
                "is_array": node.type.is_array,
                "array_rank": node.type.array_rank,
            },
            "workflow_id": node.workflow_id,
            "workflow_name": node.workflow_name,
            "scope": node.scope,
            "defined_at": node.defined_at,
        }

    def _type_to_dict(self, type_info: TypeInfo) -> dict[str, Any]:
        """Convert TypeInfo to dictionary recursively.

        Args:
            type_info: Type to convert

        Returns:
            Dictionary representation
        """
        return {
            "full_name": type_info.full_name,
            "namespace": type_info.namespace,
            "name": type_info.name,
            "generic_args": (
                [self._type_to_dict(arg) for arg in type_info.generic_args]
                if type_info.generic_args
                else None
            ),
            "is_array": type_info.is_array,
            "array_rank": type_info.array_rank,
        }

    def _edge_to_dict(self, edge: AncestryEdge) -> dict[str, Any]:
        """Convert AncestryEdge to dictionary.

        Args:
            edge: Edge to convert

        Returns:
            Dictionary representation
        """
        result = {
            "id": edge.id,
            "from_id": edge.from_id,
            "to_id": edge.to_id,
            "kind": edge.kind,
            "via_activity_id": edge.via_activity_id,
            "confidence": edge.confidence,
        }

        if edge.transformation:
            result["transformation"] = {
                "operation": edge.transformation.operation,
                "details": edge.transformation.details,
                "from_type": (
                    self._type_to_dict(edge.transformation.from_type)
                    if edge.transformation.from_type
                    else None
                ),
                "to_type": (
                    self._type_to_dict(edge.transformation.to_type)
                    if edge.transformation.to_type
                    else None
                ),
            }

        return result
