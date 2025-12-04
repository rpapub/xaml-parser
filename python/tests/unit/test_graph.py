"""Tests for graph module."""

from cpmf_xaml_parser.graph import Graph


def test_add_node():
    """Test adding nodes to graph."""
    g = Graph[str]()
    g.add_node("n1", "Node 1")
    assert g.has_node("n1")
    assert g.get_node("n1") == "Node 1"


def test_add_edge():
    """Test adding edges to graph."""
    g = Graph[str]()
    g.add_node("n1", "Node 1")
    g.add_node("n2", "Node 2")
    g.add_edge("n1", "n2")
    assert g.has_edge("n1", "n2")
    assert g.successors("n1") == ["n2"]
    assert g.predecessors("n2") == ["n1"]


def test_traverse_dfs():
    """Test depth-first traversal."""
    g = Graph[str]()
    g.add_node("root", "Root")
    g.add_node("child1", "Child 1")
    g.add_node("child2", "Child 2")
    g.add_edge("root", "child1")
    g.add_edge("root", "child2")

    visited = []
    for node_id, _data, depth in g.traverse_dfs("root"):
        visited.append((node_id, depth))

    assert ("root", 0) in visited
    assert ("child1", 1) in visited
    assert ("child2", 1) in visited


def test_traverse_dfs_with_visitor():
    """Test DFS traversal with visitor function."""
    g = Graph[str]()
    g.add_node("root", "Root")
    g.add_node("child1", "Child 1")
    g.add_node("child2", "Child 2")
    g.add_node("grandchild", "Grandchild")
    g.add_edge("root", "child1")
    g.add_edge("root", "child2")
    g.add_edge("child1", "grandchild")

    visited = []

    def visitor(node_id: str, data: str, depth: int) -> bool:
        visited.append(node_id)
        # Stop at child1
        if node_id == "child1":
            return False
        return True

    for _ in g.traverse_dfs("root", visitor):
        pass

    assert "root" in visited
    assert "child1" in visited
    assert "child2" in visited
    assert "grandchild" not in visited  # Should be skipped


def test_traverse_bfs():
    """Test breadth-first traversal."""
    g = Graph[str]()
    g.add_node("root", "Root")
    g.add_node("child1", "Child 1")
    g.add_node("child2", "Child 2")
    g.add_node("grandchild1", "Grandchild 1")
    g.add_node("grandchild2", "Grandchild 2")
    g.add_edge("root", "child1")
    g.add_edge("root", "child2")
    g.add_edge("child1", "grandchild1")
    g.add_edge("child2", "grandchild2")

    visited = []
    for node_id, _data, depth in g.traverse_bfs("root"):
        visited.append((node_id, depth))

    # BFS should visit all children before grandchildren
    root_idx = next(i for i, (nid, _) in enumerate(visited) if nid == "root")
    child1_idx = next(i for i, (nid, _) in enumerate(visited) if nid == "child1")
    child2_idx = next(i for i, (nid, _) in enumerate(visited) if nid == "child2")
    grandchild1_idx = next(i for i, (nid, _) in enumerate(visited) if nid == "grandchild1")

    assert root_idx < child1_idx < grandchild1_idx
    assert root_idx < child2_idx < grandchild1_idx


def test_find_cycles():
    """Test cycle detection."""
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


def test_find_cycles_no_cycle():
    """Test cycle detection on acyclic graph."""
    g = Graph[str]()
    g.add_node("n1", "N1")
    g.add_node("n2", "N2")
    g.add_node("n3", "N3")
    g.add_edge("n1", "n2")
    g.add_edge("n2", "n3")

    cycles = g.find_cycles()
    assert len(cycles) == 0


def test_topological_sort():
    """Test topological sort."""
    g = Graph[str]()
    g.add_node("n1", "N1")
    g.add_node("n2", "N2")
    g.add_node("n3", "N3")
    g.add_edge("n1", "n2")
    g.add_edge("n2", "n3")

    sorted_nodes = g.topological_sort()
    assert len(sorted_nodes) == 3
    assert sorted_nodes.index("n1") < sorted_nodes.index("n2")
    assert sorted_nodes.index("n2") < sorted_nodes.index("n3")


def test_topological_sort_with_cycle():
    """Test topological sort on cyclic graph."""
    g = Graph[str]()
    g.add_node("n1", "N1")
    g.add_node("n2", "N2")
    g.add_edge("n1", "n2")
    g.add_edge("n2", "n1")  # Cycle

    sorted_nodes = g.topological_sort()
    assert len(sorted_nodes) == 0  # Cannot sort cyclic graph


def test_reachable_from():
    """Test reachable nodes query."""
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
    """Test subgraph extraction."""
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


def test_node_count():
    """Test node count."""
    g = Graph[str]()
    assert g.node_count() == 0
    g.add_node("n1", "N1")
    assert g.node_count() == 1
    g.add_node("n2", "N2")
    assert g.node_count() == 2


def test_edge_count():
    """Test edge count."""
    g = Graph[str]()
    g.add_node("n1", "N1")
    g.add_node("n2", "N2")
    assert g.edge_count() == 0
    g.add_edge("n1", "n2")
    assert g.edge_count() == 1


def test_nodes():
    """Test getting all node IDs."""
    g = Graph[str]()
    g.add_node("n1", "N1")
    g.add_node("n2", "N2")
    nodes = g.nodes()
    assert len(nodes) == 2
    assert "n1" in nodes
    assert "n2" in nodes


def test_max_depth_traversal():
    """Test max depth limit in traversal."""
    g = Graph[str]()
    for i in range(10):
        g.add_node(f"n{i}", f"N{i}")
        if i > 0:
            g.add_edge(f"n{i-1}", f"n{i}")

    visited = []
    for node_id, _, _depth in g.traverse_dfs("n0", max_depth=3):
        visited.append(node_id)

    # Should only visit up to depth 3
    assert len(visited) == 4  # n0, n1, n2, n3


def test_repr():
    """Test string representation."""
    g = Graph[str]()
    g.add_node("n1", "N1")
    g.add_node("n2", "N2")
    g.add_edge("n1", "n2")

    repr_str = repr(g)
    assert "nodes=2" in repr_str
    assert "edges=1" in repr_str


def test_empty_graph_traversal():
    """Test traversal on empty graph."""
    g = Graph[str]()
    visited = list(g.traverse_dfs("nonexistent"))
    assert len(visited) == 0


def test_multiple_edges_same_pair():
    """Test adding multiple edges between same nodes."""
    g = Graph[str]()
    g.add_node("n1", "N1")
    g.add_node("n2", "N2")
    g.add_edge("n1", "n2")
    g.add_edge("n1", "n2")  # Duplicate

    # Both edges should be stored
    successors = g.successors("n1")
    assert len(successors) == 2


def test_update_node_data():
    """Test updating node data."""
    g = Graph[str]()
    g.add_node("n1", "Original")
    assert g.get_node("n1") == "Original"
    g.add_node("n1", "Updated")
    assert g.get_node("n1") == "Updated"
