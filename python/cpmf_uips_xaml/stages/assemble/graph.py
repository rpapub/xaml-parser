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
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Generic, TypeVar

__all__ = ["Graph"]

T = TypeVar("T")


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
        queue: deque[str] = deque([node_id for node_id, degree in in_degree.items() if degree == 0])

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

    def subgraph(self, node_ids: set[str]) -> "Graph[T]":
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
