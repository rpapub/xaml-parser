"""Lean project index storing ONLY IDs and adjacency lists.

This module provides the lightweight ProjectIndex class that stores graph topology
and lookup maps WITHOUT storing any DTOs. This enables efficient memory usage
for large projects and clear separation between index (ID-only) and traversal
(DTO management) concerns.

Design: docs/INSTRUCTIONS-nesting.md Part 4 (Refactored)
"""

from dataclasses import dataclass, field
from pathlib import Path

from ...shared.model.dto import IssueDto, ProjectInfo

__all__ = ["ProjectIndex"]


@dataclass
class ProjectIndex:
    """Lean index storing ONLY IDs and adjacency lists - NO DTOs.

    This is the lightweight "Intermediate Representation" (IR) of the parsed project.
    It stores ONLY graph topology (adjacency lists of IDs) and lookup maps,
    without storing any WorkflowDto or ActivityDto objects.

    OWNS:
    - Graph topology (workflow_id → [called_workflow_ids], activity_id → [child_activity_ids])
    - Lookup maps (path → workflow_id, activity_id → workflow_id)
    - Scalar metadata (counts, entry point IDs, project_dir)

    DOES NOT OWN:
    - Workflow DTOs (stored separately by ProjectAnalyzer)
    - Activity DTOs (stored separately by ProjectAnalyzer)
    - Full Graph[WorkflowDto] or Graph[ActivityDto] objects

    Attributes:
        workflow_adjacency: workflow_id → list of child workflow IDs (all edges)
        activity_adjacency: activity_id → list of child activity IDs (nesting hierarchy)
        call_graph_adjacency: workflow_id → list of called workflow IDs (invocations only)
        control_flow_adjacency: edge_id → [from_id, to_id] for control flow edges
        workflow_by_path: relative path → workflow ID lookup
        path_by_workflow: workflow ID → relative path reverse lookup
        activity_to_workflow: activity ID → workflow ID lookup
        entry_point_ids: List of entry point workflow IDs
        project_dir: Original project directory
        project_info: Project metadata from project.json
        collection_issues: Issues encountered during collection phase
        total_workflows: Number of workflows
        total_activities: Number of activities across all workflows
    """

    # Graph topology (adjacency lists of IDs ONLY)
    workflow_adjacency: dict[str, list[str]] = field(default_factory=dict)
    activity_adjacency: dict[str, list[str]] = field(default_factory=dict)
    call_graph_adjacency: dict[str, list[str]] = field(default_factory=dict)
    control_flow_adjacency: dict[str, tuple[str, str]] = field(default_factory=dict)

    # Lookup dictionaries (ID/path mappings ONLY)
    workflow_by_path: dict[str, str] = field(default_factory=dict)
    path_by_workflow: dict[str, str] = field(default_factory=dict)
    activity_to_workflow: dict[str, str] = field(default_factory=dict)

    # Scalar metadata ONLY
    project_dir: Path | None = None
    project_info: ProjectInfo | None = None
    collection_issues: list[IssueDto] = field(default_factory=list)
    entry_point_ids: list[str] = field(default_factory=list)
    total_workflows: int = 0
    total_activities: int = 0

    # ID-only query methods (no DTO access)

    def get_workflow_children(self, workflow_id: str) -> list[str]:
        """Get child workflow IDs (callees) for a workflow.

        Args:
            workflow_id: The workflow ID to query

        Returns:
            List of called workflow IDs (from call graph adjacency)
        """
        return self.call_graph_adjacency.get(workflow_id, [])

    def get_activity_children(self, activity_id: str) -> list[str]:
        """Get child activity IDs for an activity.

        Args:
            activity_id: The activity ID to query

        Returns:
            List of child activity IDs (from nesting hierarchy)
        """
        return self.activity_adjacency.get(activity_id, [])

    def get_workflow_id_by_path(self, path: str) -> str | None:
        """Get workflow ID by relative path.

        Args:
            path: Relative path to workflow file

        Returns:
            Workflow ID if found, None otherwise
        """
        return self.workflow_by_path.get(path)

    def get_workflow_path(self, workflow_id: str) -> str | None:
        """Get relative path for workflow ID.

        Args:
            workflow_id: The workflow ID to query

        Returns:
            Relative path if found, None otherwise
        """
        return self.path_by_workflow.get(workflow_id)

    def get_workflow_id_for_activity(self, activity_id: str) -> str | None:
        """Get workflow ID containing an activity.

        Args:
            activity_id: The activity ID to query

        Returns:
            Workflow ID if found, None otherwise
        """
        return self.activity_to_workflow.get(activity_id)

    def find_call_cycles(self) -> list[list[str]]:
        """Detect circular workflow calls using Tarjan's algorithm.

        Returns:
            List of cycles, where each cycle is a list of workflow IDs
        """
        # Tarjan's strongly connected components algorithm
        index_counter = [0]
        stack: list[str] = []
        lowlinks: dict[str, int] = {}
        index: dict[str, int] = {}
        on_stack: dict[str, bool] = {}
        cycles: list[list[str]] = []

        def strongconnect(node: str) -> None:
            index[node] = index_counter[0]
            lowlinks[node] = index_counter[0]
            index_counter[0] += 1
            stack.append(node)
            on_stack[node] = True

            # Consider successors
            for successor in self.call_graph_adjacency.get(node, []):
                if successor not in index:
                    strongconnect(successor)
                    lowlinks[node] = min(lowlinks[node], lowlinks[successor])
                elif on_stack.get(successor, False):
                    lowlinks[node] = min(lowlinks[node], index[successor])

            # If node is a root node, pop the stack and record SCC
            if lowlinks[node] == index[node]:
                connected_component: list[str] = []
                while True:
                    successor = stack.pop()
                    on_stack[successor] = False
                    connected_component.append(successor)
                    if successor == node:
                        break
                # Only record if it's an actual cycle (size > 1)
                if len(connected_component) > 1:
                    cycles.append(connected_component)

        # Run algorithm on all nodes
        for node in self.call_graph_adjacency:
            if node not in index:
                strongconnect(node)

        return cycles

    def get_execution_order(self) -> list[str]:
        """Get safe workflow execution order using topological sort.

        Returns:
            List of workflow IDs in topological order (safe execution order)
            Returns empty list if cycles exist
        """
        # Calculate in-degrees
        in_degree: dict[str, int] = {wf_id: 0 for wf_id in self.call_graph_adjacency}

        for wf_id, callees in self.call_graph_adjacency.items():
            for callee_id in callees:
                in_degree[callee_id] = in_degree.get(callee_id, 0) + 1

        # Find all nodes with in-degree 0
        queue = [wf_id for wf_id, degree in in_degree.items() if degree == 0]
        result: list[str] = []

        while queue:
            # Remove node from queue
            node = queue.pop(0)
            result.append(node)

            # Decrease in-degree for neighbors
            for neighbor in self.call_graph_adjacency.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # If result doesn't contain all nodes, there's a cycle
        if len(result) != len(self.call_graph_adjacency):
            return []

        return result
