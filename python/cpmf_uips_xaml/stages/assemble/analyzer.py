"""Project traversal and DTO management.

This module provides the ProjectAnalyzer class that builds the lean ProjectIndex
while also storing WorkflowDto and ActivityDto objects separately for retrieval.

This enables the separation of concerns:
- ProjectIndex stores ONLY IDs and adjacency lists (lightweight)
- ProjectAnalyzer stores full DTOs and provides access methods (heavy)

Design: docs/INSTRUCTIONS-nesting.md Part 4 (Refactored)
"""

from pathlib import Path

from ...shared.model.dto import ActivityDto, IssueDto, ProjectInfo, WorkflowDto
from .graph import Graph
from .index import ProjectIndex

__all__ = ["ProjectAnalyzer"]


class ProjectAnalyzer:
    """Builds lean ProjectIndex and stores DTOs separately.

    This is the "analysis phase" - it builds all graph structures needed for
    multi-view output while maintaining separate storage for full DTOs.

    The ProjectAnalyzer:
    - Builds a LEAN ProjectIndex (IDs and adjacency lists only)
    - Stores WorkflowDto and ActivityDto objects internally
    - Provides methods to retrieve DTOs by ID
    - Provides methods that require DTO access (e.g., slice_context)

    Attributes:
        _workflows: Internal storage for WorkflowDto objects (workflow_id → WorkflowDto)
        _activities: Internal storage for ActivityDto objects (activity_id → ActivityDto)
        _workflows_graph: Full workflow graph with DTO nodes (for legacy compatibility)
        _activities_graph: Full activity graph with DTO nodes (for legacy compatibility)
        _call_graph: Workflow-level call graph with DTO nodes (for legacy compatibility)
        _control_flow: Activity-level control flow with edge DTOs (for legacy compatibility)
    """

    def __init__(self) -> None:
        """Initialize ProjectAnalyzer with empty DTO storage."""
        self._workflows: dict[str, WorkflowDto] = {}
        self._activities: dict[str, ActivityDto] = {}

        # Legacy Graph objects (maintained for backward compatibility)
        self._workflows_graph: Graph[WorkflowDto] = Graph[WorkflowDto]()
        self._activities_graph: Graph[ActivityDto] = Graph[ActivityDto]()
        self._call_graph: Graph[WorkflowDto] = Graph[WorkflowDto]()
        self._control_flow: Graph[ActivityDto] = Graph[ActivityDto]()

    def analyze(
        self,
        workflows: list[WorkflowDto],
        project_dir: Path | None = None,
        project_info: ProjectInfo | None = None,
        collection_issues: list[IssueDto] | None = None,
    ) -> ProjectIndex:
        """Analyze workflows and build lean ProjectIndex with separate DTO storage.

        Args:
            workflows: List of WorkflowDto objects
            project_dir: Optional project directory
            project_info: Optional project information from project.json
            collection_issues: Optional collection-level issues

        Returns:
            ProjectIndex with ONLY IDs and adjacency lists (DTOs stored in analyzer)
        """
        # Clear previous storage
        self._workflows.clear()
        self._activities.clear()
        self._workflows_graph = Graph[WorkflowDto]()
        self._activities_graph = Graph[ActivityDto]()
        self._call_graph = Graph[WorkflowDto]()
        self._control_flow = Graph[ActivityDto]()

        # Initialize adjacency lists for lean index
        workflow_adjacency: dict[str, list[str]] = {}
        activity_adjacency: dict[str, list[str]] = {}
        call_graph_adjacency: dict[str, list[str]] = {}
        control_flow_adjacency: dict[str, tuple[str, str]] = {}

        # Lookups
        workflow_by_path: dict[str, str] = {}
        path_by_workflow: dict[str, str] = {}
        activity_to_workflow: dict[str, str] = {}
        entry_points: list[str] = []

        total_activities = 0

        # Build workflow nodes and activity nodes
        for workflow_dto in workflows:
            # Store DTO
            self._workflows[workflow_dto.id] = workflow_dto

            # Build legacy Graph objects
            self._workflows_graph.add_node(workflow_dto.id, workflow_dto)
            self._call_graph.add_node(workflow_dto.id, workflow_dto)

            # Initialize adjacency lists
            workflow_adjacency[workflow_dto.id] = []
            call_graph_adjacency[workflow_dto.id] = []

            # Track lookups
            if workflow_dto.source.path:
                workflow_by_path[workflow_dto.source.path] = workflow_dto.id
                path_by_workflow[workflow_dto.id] = workflow_dto.source.path

            # Add activity nodes and edges
            for activity in workflow_dto.activities:
                # Store DTO
                self._activities[activity.id] = activity

                # Build legacy Graph objects
                self._activities_graph.add_node(activity.id, activity)

                # Track lookups
                activity_to_workflow[activity.id] = workflow_dto.id
                total_activities += 1

                # Build activity adjacency list
                activity_adjacency[activity.id] = list(activity.children)

                # Add parent → child edges to legacy graph
                for child_id in activity.children:
                    self._activities_graph.add_edge(activity.id, child_id)

            # Add control flow edges
            for edge in workflow_dto.edges:
                control_flow_adjacency[edge.id] = (edge.from_id, edge.to_id)
                self._control_flow.add_edge(edge.from_id, edge.to_id)

        # Build call graph edges (workflow invocations)
        for workflow_dto in workflows:
            for invocation in workflow_dto.invocations:
                # Add to call graph adjacency list
                if workflow_dto.id not in call_graph_adjacency:
                    call_graph_adjacency[workflow_dto.id] = []
                call_graph_adjacency[workflow_dto.id].append(invocation.callee_id)

                # Add to workflow adjacency list (all edges)
                if workflow_dto.id not in workflow_adjacency:
                    workflow_adjacency[workflow_dto.id] = []
                workflow_adjacency[workflow_dto.id].append(invocation.callee_id)

                # Add to legacy graph
                self._call_graph.add_edge(workflow_dto.id, invocation.callee_id)

        # Build lean ProjectIndex (IDs only)
        return ProjectIndex(
            workflow_adjacency=workflow_adjacency,
            activity_adjacency=activity_adjacency,
            call_graph_adjacency=call_graph_adjacency,
            control_flow_adjacency=control_flow_adjacency,
            workflow_by_path=workflow_by_path,
            path_by_workflow=path_by_workflow,
            activity_to_workflow=activity_to_workflow,
            entry_point_ids=entry_points,
            project_dir=project_dir,
            project_info=project_info,
            collection_issues=collection_issues or [],
            total_workflows=len(workflows),
            total_activities=total_activities,
        )

    # DTO retrieval methods

    def get_workflow(self, workflow_id: str) -> WorkflowDto | None:
        """Get workflow DTO by ID.

        Args:
            workflow_id: The workflow ID to retrieve

        Returns:
            WorkflowDto if found, None otherwise
        """
        return self._workflows.get(workflow_id)

    def get_activity(self, activity_id: str) -> ActivityDto | None:
        """Get activity DTO by ID.

        Args:
            activity_id: The activity ID to retrieve

        Returns:
            ActivityDto if found, None otherwise
        """
        return self._activities.get(activity_id)

    def get_workflow_for_activity(
        self, activity_id: str, index: ProjectIndex
    ) -> WorkflowDto | None:
        """Get workflow containing an activity.

        Args:
            activity_id: The activity ID to query
            index: ProjectIndex containing the lookup map

        Returns:
            WorkflowDto if found, None otherwise
        """
        workflow_id = index.get_workflow_id_for_activity(activity_id)
        if workflow_id:
            return self.get_workflow(workflow_id)
        return None

    # Methods requiring DTO access

    def slice_context(
        self, activity_id: str, index: ProjectIndex, radius: int = 2
    ) -> dict[str, ActivityDto]:
        """Get context window around activity (for LLM consumption).

        Args:
            activity_id: The focal activity ID
            index: ProjectIndex containing the adjacency lists
            radius: Number of hops to traverse (default: 2)

        Returns:
            Dictionary mapping activity IDs to ActivityDto objects in context window
        """
        context: dict[str, ActivityDto] = {}

        # Get focal activity
        focal = self.get_activity(activity_id)
        if not focal:
            return context

        context[activity_id] = focal

        # Traverse upward (predecessors) - need to build reverse adjacency
        predecessors_map: dict[str, list[str]] = {}
        for parent_id, children_ids in index.activity_adjacency.items():
            for child_id in children_ids:
                if child_id not in predecessors_map:
                    predecessors_map[child_id] = []
                predecessors_map[child_id].append(parent_id)

        current_level = {activity_id}
        for _ in range(radius):
            next_level = set()
            for act_id in current_level:
                for pred_id in predecessors_map.get(act_id, []):
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
                for succ_id in index.get_activity_children(act_id):
                    if succ_id not in context:
                        succ = self.get_activity(succ_id)
                        if succ:
                            context[succ_id] = succ
                            next_level.add(succ_id)
            current_level = next_level

        return context

    # Legacy Graph access (for backward compatibility)

    @property
    def workflows_graph(self) -> Graph[WorkflowDto]:
        """Get legacy workflows graph.

        Returns:
            Graph containing WorkflowDto nodes
        """
        return self._workflows_graph

    @property
    def activities_graph(self) -> Graph[ActivityDto]:
        """Get legacy activities graph.

        Returns:
            Graph containing ActivityDto nodes
        """
        return self._activities_graph

    @property
    def call_graph(self) -> Graph[WorkflowDto]:
        """Get legacy call graph.

        Returns:
            Graph containing WorkflowDto nodes for call relationships
        """
        return self._call_graph

    @property
    def control_flow_graph(self) -> Graph[ActivityDto]:
        """Get legacy control flow graph.

        Returns:
            Graph containing ActivityDto nodes for control flow
        """
        return self._control_flow
