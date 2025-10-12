"""View layer for multi-representation output.

This module implements the "view pattern" inspired by Roslyn (C# compiler).
Each view transforms the ProjectIndex (IR) into a different representation.

Views:
- FlatView: Current flat output (backward compatible)
- ExecutionView: Call graph traversal from entry point
- SliceView: Context window around focal activity

Design: docs/INSTRUCTIONS-nesting.md Part 4.2
"""

import dataclasses
from datetime import UTC, datetime
from typing import Any, Protocol

from .analyzer import ProjectIndex
from .dto import ActivityDto

__all__ = ["View", "FlatView", "ExecutionView", "SliceView"]


class View(Protocol):
    """Protocol for view transformations.

    All views must implement render(index) -> dict.
    """

    def render(self, index: ProjectIndex) -> dict[str, Any]:
        """Transform ProjectIndex to view-specific dict."""
        ...


class FlatView:
    """Current flat output - 100% backward compatible.

    Produces same structure as current JSON emitter.
    This is the DEFAULT view to maintain backward compatibility.
    """

    def render(self, index: ProjectIndex) -> dict[str, Any]:
        """Render flat view (current output format)."""
        workflows = []

        for wf_id in index.workflows.nodes():
            wf_dto = index.get_workflow(wf_id)
            if not wf_dto:
                continue

            # Convert WorkflowDto to dict
            wf_dict = dataclasses.asdict(wf_dto)
            workflows.append(wf_dict)

        return {
            "schema_id": "https://rpax.io/schemas/xaml-workflow-collection.json",
            "schema_version": "1.0.0",
            "collected_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "workflows": workflows,
            "issues": [],
        }


class ExecutionView:
    """Traverse call graph from entry point, showing execution flow.

    This view expands InvokeWorkflowFile activities with callee content,
    showing "what actually runs" from entry to leaves.
    """

    def __init__(self, entry_point: str, max_depth: int = 10) -> None:
        """Initialize execution view.

        Args:
            entry_point: Entry point workflow ID or path
            max_depth: Maximum call depth (cycle protection)
        """
        self.entry_point = entry_point
        self.max_depth = max_depth

    def render(self, index: ProjectIndex) -> dict[str, Any]:
        """Render execution view (call graph traversal)."""
        # Resolve entry point
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

            # Build nested activity tree
            nested_activities = self._build_nested_activities(
                wf_dto, index, visited_workflows, depth
            )

            wf_dict = dataclasses.asdict(wf_dto)
            wf_dict["activities"] = nested_activities
            wf_dict["call_depth"] = depth
            workflows.append(wf_dict)

        return {
            "schema_id": "https://rpax.io/schemas/xaml-workflow-execution.json",
            "schema_version": "2.0.0",
            "entry_point": entry_wf_id,
            "max_depth": self.max_depth,
            "workflows": workflows,
        }

    def _resolve_entry_point(self, index: ProjectIndex, entry: str) -> str | None:
        """Resolve entry point to workflow ID."""
        if index.workflows.has_node(entry):
            return entry
        return index.workflow_by_path.get(entry)

    def _build_nested_activities(
        self,
        workflow_dto: Any,
        index: ProjectIndex,
        visited_workflows: set[str],
        depth: int,
    ) -> list[dict[str, Any]]:
        """Build nested activity tree with call graph expansion."""
        # Build activity tree
        activity_map = {act.id: act for act in workflow_dto.activities}
        nested_map: dict[str, dict[str, Any]] = {}

        for activity in workflow_dto.activities:
            act_dict = dataclasses.asdict(activity)
            act_dict["children"] = []  # Will be filled with nested dicts
            nested_map[activity.id] = act_dict

        # Nest children (local hierarchy)
        for activity in workflow_dto.activities:
            act_dict = nested_map[activity.id]
            for child_id in activity.children:
                if child_id in nested_map:
                    act_dict["children"].append(nested_map[child_id])

        # Expand InvokeWorkflowFile activities
        if depth < self.max_depth:
            for activity in workflow_dto.activities:
                if "InvokeWorkflowFile" not in activity.type:
                    continue

                # Find callee workflow ID
                callee_wf_id = self._find_callee_for_activity(activity.id, workflow_dto)

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

        # Remove parent_id field (redundant in nested structure)
        for act_dict in nested_map.values():
            act_dict.pop("parent_id", None)

        # Return only root activities (no parent)
        roots = []
        for activity in workflow_dto.activities:
            if not activity.parent_id or activity.parent_id not in activity_map:
                roots.append(nested_map[activity.id])

        return roots

    def _find_callee_for_activity(self, activity_id: str, workflow_dto: Any) -> str | None:
        """Find callee workflow ID for InvokeWorkflowFile activity."""
        for invocation in workflow_dto.invocations:
            if invocation.via_activity_id == activity_id:
                return invocation.callee_id
        return None


class SliceView:
    """Context window around focal activity (for LLM consumption).

    Extracts activities within radius (up/down) including parent chain.
    """

    def __init__(self, focus: str, radius: int = 2) -> None:
        """Initialize slice view.

        Args:
            focus: Focal activity ID
            radius: Number of levels to include (up and down)
        """
        self.focus = focus
        self.radius = radius

    def render(self, index: ProjectIndex) -> dict[str, Any]:
        """Render slice view (context window)."""
        # Get context activities
        context = index.slice_context(self.focus, self.radius)

        if not context:
            return {"error": f"Activity not found: {self.focus}"}

        # Get focal activity
        focal = index.get_activity(self.focus)
        if not focal:
            return {"error": f"Activity not found: {self.focus}"}

        # Build parent chain
        parent_chain = self._build_parent_chain(self.focus, index)

        # Get siblings
        siblings = self._get_siblings(self.focus, index)

        # Get workflow
        workflow = index.get_workflow_for_activity(self.focus)

        return {
            "schema_id": "https://rpax.io/schemas/xaml-activity-slice.json",
            "schema_version": "2.1.0",
            "focus": self.focus,
            "radius": self.radius,
            "workflow": {
                "id": workflow.id if workflow else None,
                "name": workflow.name if workflow else None,
            },
            "focal_activity": dataclasses.asdict(focal),
            "parent_chain": [dataclasses.asdict(act) for act in parent_chain],
            "siblings": [dataclasses.asdict(act) for act in siblings],
            "context_activities": [dataclasses.asdict(act) for act in context.values()],
        }

    def _build_parent_chain(self, activity_id: str, index: ProjectIndex) -> list[ActivityDto]:
        """Build parent chain from root to focal activity."""
        chain = []
        current_id = activity_id

        while True:
            preds = index.activities.predecessors(current_id)
            if not preds:
                break

            parent_id = preds[0]
            parent = index.get_activity(parent_id)
            if not parent:
                break

            chain.append(parent)
            current_id = parent_id

        return list(reversed(chain))

    def _get_siblings(self, activity_id: str, index: ProjectIndex) -> list[ActivityDto]:
        """Get sibling activities (same parent)."""
        siblings = []

        preds = index.activities.predecessors(activity_id)
        if not preds:
            return siblings

        parent_id = preds[0]

        for child_id in index.activities.successors(parent_id):
            if child_id != activity_id:
                child = index.get_activity(child_id)
                if child:
                    siblings.append(child)

        return siblings
