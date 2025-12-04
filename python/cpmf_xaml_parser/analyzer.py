"""Project analysis and graph construction.

This module builds queryable graph structures from parsed workflows,
enabling efficient traversal, cycle detection, and multi-view output.

Design: docs/INSTRUCTIONS-nesting.md Part 4
"""

from dataclasses import dataclass, field
from pathlib import Path

from .dto import ActivityDto, EdgeDto, IssueDto, ProjectInfo, WorkflowDto
from .graph import Graph

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
    """

    # Core graphs
    workflows: Graph[WorkflowDto]
    activities: Graph[ActivityDto]
    call_graph: Graph[WorkflowDto]  # Workflow invocations (data = WorkflowDto)
    control_flow: Graph[EdgeDto]  # Activity edges (data = EdgeDto)

    # Lookups
    workflow_by_path: dict[str, str] = field(default_factory=dict)
    activity_to_workflow: dict[str, str] = field(default_factory=dict)
    entry_points: list[str] = field(default_factory=list)

    # Metadata
    project_dir: Path | None = None
    project_info: ProjectInfo | None = None
    collection_issues: list[IssueDto] = field(default_factory=list)
    total_workflows: int = 0
    total_activities: int = 0

    def get_workflow(self, workflow_id: str) -> WorkflowDto | None:
        """Get workflow by ID."""
        return self.workflows.get_node(workflow_id)

    def get_activity(self, activity_id: str) -> ActivityDto | None:
        """Get activity by ID."""
        return self.activities.get_node(activity_id)

    def get_workflow_for_activity(self, activity_id: str) -> WorkflowDto | None:
        """Get workflow containing an activity."""
        workflow_id = self.activity_to_workflow.get(activity_id)
        if workflow_id:
            return self.get_workflow(workflow_id)
        return None

    def slice_context(self, activity_id: str, radius: int = 2) -> dict[str, ActivityDto]:
        """Get context window around activity (for LLM consumption)."""
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
        """Detect circular workflow calls."""
        return self.call_graph.find_cycles()

    def get_execution_order(self) -> list[str]:
        """Get safe workflow execution order (topological sort)."""
        return self.call_graph.topological_sort()


class ProjectAnalyzer:
    """Builds ProjectIndex from workflow DTOs.

    This is the "analysis phase" - it builds all graph structures
    needed for multi-view output.
    """

    def analyze(
        self,
        workflows: list[WorkflowDto],
        project_dir: Path | None = None,
        project_info: ProjectInfo | None = None,
        collection_issues: list[IssueDto] | None = None,
    ) -> ProjectIndex:
        """Analyze workflows and build graph structures.

        Args:
            workflows: List of WorkflowDto objects
            project_dir: Optional project directory
            project_info: Optional project information from project.json
            collection_issues: Optional collection-level issues

        Returns:
            ProjectIndex with queryable graphs
        """
        # Initialize graphs
        workflows_graph = Graph[WorkflowDto]()
        activities_graph = Graph[ActivityDto]()
        call_graph: Graph[WorkflowDto] = Graph[WorkflowDto]()
        control_flow_graph: Graph[EdgeDto] = Graph[EdgeDto]()

        # Lookups
        workflow_by_path: dict[str, str] = {}
        activity_to_workflow: dict[str, str] = {}
        entry_points: list[str] = []

        total_activities = 0

        # Build workflow nodes and activity nodes
        for workflow_dto in workflows:
            workflows_graph.add_node(workflow_dto.id, workflow_dto)
            call_graph.add_node(workflow_dto.id, workflow_dto)

            # Track lookups
            if workflow_dto.source.path:
                workflow_by_path[workflow_dto.source.path] = workflow_dto.id

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

        # Build call graph edges (workflow invocations)
        for workflow_dto in workflows:
            for invocation in workflow_dto.invocations:
                # Caller is the workflow containing the invocation
                call_graph.add_edge(
                    workflow_dto.id,
                    invocation.callee_id,
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
            project_dir=project_dir,
            project_info=project_info,
            collection_issues=collection_issues or [],
            total_workflows=len(workflows),
            total_activities=total_activities,
        )
