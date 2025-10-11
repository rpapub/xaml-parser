"""Control flow extraction for XAML workflows.

This module extracts explicit control flow edges from the activity tree structure,
making implicit control flow (If/Then/Else, Switch/Case, etc.) explicit for
analysis and visualization.

Design: ADR-DTO-DESIGN.md (Control Flow Modeling)
"""

from typing import Any

from .dto import EdgeDto
from .id_generation import IdGenerator
from .models import Activity


class ControlFlowExtractor:
    """Extract control flow edges from activities.

    This class analyzes the activity tree and extracts explicit EdgeDto objects
    representing control flow between activities. It handles:
    - Sequential flow (Sequence activities)
    - Conditional branches (If, FlowDecision)
    - Multi-way branches (Switch, FlowSwitch)
    - Exception handling (TryCatch)
    - Flowchart connections (Link elements)
    - State machines (Transitions)
    - Parallel execution (Parallel, ParallelForEach)
    """

    def __init__(self, id_generator: IdGenerator | None = None) -> None:
        """Initialize control flow extractor.

        Args:
            id_generator: ID generator for edge IDs (creates new if None)
        """
        self.id_generator = id_generator or IdGenerator()

    def extract_edges(self, activities: list[Activity]) -> list[EdgeDto]:
        """Extract all control flow edges from activities.

        Args:
            activities: List of Activity objects from parser

        Returns:
            List of EdgeDto objects representing control flow
        """
        edges: list[EdgeDto] = []

        # Build activity lookup for efficient access
        activity_map = {act.activity_id: act for act in activities}

        # Extract edges from each activity based on type
        for activity in activities:
            activity_edges = self._extract_from_activity(activity, activity_map)
            edges.extend(activity_edges)

        return edges

    def _extract_from_activity(
        self, activity: Activity, activity_map: dict[str, Activity]
    ) -> list[EdgeDto]:
        """Extract edges from a single activity based on its type.

        Args:
            activity: Activity to analyze
            activity_map: Map of activity_id → Activity for lookups

        Returns:
            List of EdgeDto objects for this activity
        """
        activity_type = activity.activity_type

        # Dispatch to specific handler based on activity type
        if activity_type == "Sequence":
            return self._extract_sequence_edges(activity, activity_map)
        elif activity_type == "If":
            return self._extract_if_edges(activity, activity_map)
        elif activity_type in ["Switch", "FlowSwitch"]:
            return self._extract_switch_edges(activity, activity_map)
        elif activity_type == "FlowDecision":
            return self._extract_flow_decision_edges(activity, activity_map)
        elif activity_type == "TryCatch":
            return self._extract_try_catch_edges(activity, activity_map)
        elif activity_type == "Flowchart":
            return self._extract_flowchart_edges(activity, activity_map)
        elif activity_type in ["Parallel", "ParallelForEach"]:
            return self._extract_parallel_edges(activity, activity_map)
        elif activity_type in ["Pick", "PickBranch"]:
            return self._extract_pick_edges(activity, activity_map)
        elif activity_type == "StateMachine":
            return self._extract_state_machine_edges(activity, activity_map)
        elif activity_type == "RetryScope":
            return self._extract_retry_scope_edges(activity, activity_map)
        else:
            # No special control flow for this activity type
            return []

    def _extract_sequence_edges(
        self, activity: Activity, activity_map: dict[str, Activity]
    ) -> list[EdgeDto]:
        """Extract sequential 'Next' edges from Sequence activity.

        Args:
            activity: Sequence activity
            activity_map: Activity lookup map

        Returns:
            List of 'Next' edges between sequential children
        """
        edges: list[EdgeDto] = []

        # Get children in order
        children = activity.child_activities

        # Create Next edges between consecutive children
        for i in range(len(children) - 1):
            from_id = children[i]
            to_id = children[i + 1]

            # Generate stable edge ID
            edge_id = self.id_generator.generate_edge_id(from_id, to_id, "Next")

            edge = EdgeDto(
                id=edge_id,
                from_id=from_id,
                to_id=to_id,
                kind="Next",
                condition=None,
                label=None,
            )
            edges.append(edge)

        return edges

    def _extract_if_edges(
        self, activity: Activity, activity_map: dict[str, Activity]
    ) -> list[EdgeDto]:
        """Extract 'Then' and 'Else' edges from If activity.

        Args:
            activity: If activity
            activity_map: Activity lookup map

        Returns:
            List of Then/Else edges
        """
        edges: list[EdgeDto] = []

        # Extract condition from properties
        condition = activity.properties.get("Condition") or activity.properties.get(
            "Condition.Expression"
        )

        # Get Then and Else branches from configuration or child activities
        then_activity = self._find_child_by_name(activity, "Then", activity_map)
        else_activity = self._find_child_by_name(activity, "Else", activity_map)

        # Create Then edge
        if then_activity:
            edge_id = self.id_generator.generate_edge_id(
                activity.activity_id, then_activity, "Then"
            )
            edges.append(
                EdgeDto(
                    id=edge_id,
                    from_id=activity.activity_id,
                    to_id=then_activity,
                    kind="Then",
                    condition=str(condition) if condition else None,
                    label="Then",
                )
            )

        # Create Else edge
        if else_activity:
            edge_id = self.id_generator.generate_edge_id(
                activity.activity_id, else_activity, "Else"
            )
            edges.append(
                EdgeDto(
                    id=edge_id,
                    from_id=activity.activity_id,
                    to_id=else_activity,
                    kind="Else",
                    condition=None,
                    label="Else",
                )
            )

        return edges

    def _extract_switch_edges(
        self, activity: Activity, activity_map: dict[str, Activity]
    ) -> list[EdgeDto]:
        """Extract 'Case' edges from Switch activity.

        Args:
            activity: Switch or FlowSwitch activity
            activity_map: Activity lookup map

        Returns:
            List of Case/Default edges
        """
        edges: list[EdgeDto] = []

        # Extract expression being switched on
        expression = activity.properties.get("Expression")

        # Get cases from configuration
        # In XAML, cases are typically stored in the configuration
        cases = activity.configuration.get("Cases", {})

        # Handle different case representations
        if isinstance(cases, dict):
            for case_value, case_config in cases.items():
                # Find the activity for this case
                case_activity_id = self._extract_activity_id_from_config(case_config)
                if case_activity_id:
                    edge_id = self.id_generator.generate_edge_id(
                        activity.activity_id, case_activity_id, f"Case:{case_value}"
                    )
                    edges.append(
                        EdgeDto(
                            id=edge_id,
                            from_id=activity.activity_id,
                            to_id=case_activity_id,
                            kind="Case",
                            condition=f"{expression} == {case_value}" if expression else None,
                            label=str(case_value),
                        )
                    )

        # Extract default case
        default_config = activity.configuration.get("Default")
        if default_config:
            default_activity_id = self._extract_activity_id_from_config(default_config)
            if default_activity_id:
                edge_id = self.id_generator.generate_edge_id(
                    activity.activity_id, default_activity_id, "Default"
                )
                edges.append(
                    EdgeDto(
                        id=edge_id,
                        from_id=activity.activity_id,
                        to_id=default_activity_id,
                        kind="Default",
                        condition=None,
                        label="Default",
                    )
                )

        return edges

    def _extract_flow_decision_edges(
        self, activity: Activity, activity_map: dict[str, Activity]
    ) -> list[EdgeDto]:
        """Extract 'True' and 'False' edges from FlowDecision activity.

        Args:
            activity: FlowDecision activity
            activity_map: Activity lookup map

        Returns:
            List of True/False edges
        """
        edges: list[EdgeDto] = []

        # Extract condition
        condition = activity.properties.get("Condition")

        # Get True and False branches
        true_activity = self._find_child_by_name(activity, "True", activity_map)
        false_activity = self._find_child_by_name(activity, "False", activity_map)

        # Create True edge
        if true_activity:
            edge_id = self.id_generator.generate_edge_id(
                activity.activity_id, true_activity, "True"
            )
            edges.append(
                EdgeDto(
                    id=edge_id,
                    from_id=activity.activity_id,
                    to_id=true_activity,
                    kind="True",
                    condition=str(condition) if condition else None,
                    label="True",
                )
            )

        # Create False edge
        if false_activity:
            edge_id = self.id_generator.generate_edge_id(
                activity.activity_id, false_activity, "False"
            )
            edges.append(
                EdgeDto(
                    id=edge_id,
                    from_id=activity.activity_id,
                    to_id=false_activity,
                    kind="False",
                    condition=None,
                    label="False",
                )
            )

        return edges

    def _extract_try_catch_edges(
        self, activity: Activity, activity_map: dict[str, Activity]
    ) -> list[EdgeDto]:
        """Extract Try/Catch/Finally edges from TryCatch activity.

        Args:
            activity: TryCatch activity
            activity_map: Activity lookup map

        Returns:
            List of Try/Catch/Finally edges
        """
        edges: list[EdgeDto] = []

        # Get Try block
        try_activity = self._find_child_by_name(activity, "Try", activity_map)
        if try_activity:
            edge_id = self.id_generator.generate_edge_id(activity.activity_id, try_activity, "Try")
            edges.append(
                EdgeDto(
                    id=edge_id,
                    from_id=activity.activity_id,
                    to_id=try_activity,
                    kind="Try",
                    condition=None,
                    label="Try",
                )
            )

        # Get Catch blocks (can be multiple)
        catches = activity.configuration.get("Catches", [])
        if isinstance(catches, list):
            for catch_config in catches:
                catch_activity_id = self._extract_activity_id_from_config(catch_config)
                if catch_activity_id:
                    # Extract exception type if available
                    exception_type = catch_config.get("ExceptionType", "Exception")
                    edge_id = self.id_generator.generate_edge_id(
                        activity.activity_id,
                        catch_activity_id,
                        f"Catch:{exception_type}",
                    )
                    edges.append(
                        EdgeDto(
                            id=edge_id,
                            from_id=activity.activity_id,
                            to_id=catch_activity_id,
                            kind="Catch",
                            condition=None,
                            label=f"Catch ({exception_type})",
                        )
                    )

        # Get Finally block
        finally_activity = self._find_child_by_name(activity, "Finally", activity_map)
        if finally_activity:
            edge_id = self.id_generator.generate_edge_id(
                activity.activity_id, finally_activity, "Finally"
            )
            edges.append(
                EdgeDto(
                    id=edge_id,
                    from_id=activity.activity_id,
                    to_id=finally_activity,
                    kind="Finally",
                    condition=None,
                    label="Finally",
                )
            )

        return edges

    def _extract_flowchart_edges(
        self, activity: Activity, activity_map: dict[str, Activity]
    ) -> list[EdgeDto]:
        """Extract 'Link' edges from Flowchart activity.

        Args:
            activity: Flowchart activity
            activity_map: Activity lookup map

        Returns:
            List of Link edges between flowchart nodes
        """
        edges: list[EdgeDto] = []

        # Flowcharts use explicit FlowStep/FlowDecision/FlowSwitch nodes
        # connected by Next properties

        # For now, create sequential links between children
        # TODO: Parse actual FlowStep.Next connections from configuration
        children = activity.child_activities
        for i in range(len(children) - 1):
            from_id = children[i]
            to_id = children[i + 1]

            edge_id = self.id_generator.generate_edge_id(from_id, to_id, "Link")
            edges.append(
                EdgeDto(
                    id=edge_id,
                    from_id=from_id,
                    to_id=to_id,
                    kind="Link",
                    condition=None,
                    label=None,
                )
            )

        return edges

    def _extract_parallel_edges(
        self, activity: Activity, activity_map: dict[str, Activity]
    ) -> list[EdgeDto]:
        """Extract 'Branch' edges from Parallel activity.

        Args:
            activity: Parallel or ParallelForEach activity
            activity_map: Activity lookup map

        Returns:
            List of Branch edges for parallel execution
        """
        edges: list[EdgeDto] = []

        # Each child is a parallel branch
        for child_id in activity.child_activities:
            edge_id = self.id_generator.generate_edge_id(activity.activity_id, child_id, "Branch")
            edges.append(
                EdgeDto(
                    id=edge_id,
                    from_id=activity.activity_id,
                    to_id=child_id,
                    kind="Branch",
                    condition=None,
                    label="Parallel Branch",
                )
            )

        return edges

    def _extract_pick_edges(
        self, activity: Activity, activity_map: dict[str, Activity]
    ) -> list[EdgeDto]:
        """Extract 'Trigger' edges from Pick activity.

        Args:
            activity: Pick or PickBranch activity
            activity_map: Activity lookup map

        Returns:
            List of Trigger edges
        """
        edges: list[EdgeDto] = []

        # Each PickBranch is triggered by an event
        for child_id in activity.child_activities:
            edge_id = self.id_generator.generate_edge_id(activity.activity_id, child_id, "Trigger")
            edges.append(
                EdgeDto(
                    id=edge_id,
                    from_id=activity.activity_id,
                    to_id=child_id,
                    kind="Trigger",
                    condition=None,
                    label="Event Trigger",
                )
            )

        return edges

    def _extract_state_machine_edges(
        self, activity: Activity, activity_map: dict[str, Activity]
    ) -> list[EdgeDto]:
        """Extract 'Transition' edges from StateMachine activity.

        Args:
            activity: StateMachine activity
            activity_map: Activity lookup map

        Returns:
            List of Transition edges between states
        """
        edges: list[EdgeDto] = []

        # State machines have explicit Transition elements
        # TODO: Parse Transition configuration from State activities
        # For now, create transitions between consecutive states
        children = activity.child_activities
        for i in range(len(children) - 1):
            from_id = children[i]
            to_id = children[i + 1]

            edge_id = self.id_generator.generate_edge_id(from_id, to_id, "Transition")
            edges.append(
                EdgeDto(
                    id=edge_id,
                    from_id=from_id,
                    to_id=to_id,
                    kind="Transition",
                    condition=None,
                    label=None,
                )
            )

        return edges

    def _extract_retry_scope_edges(
        self, activity: Activity, activity_map: dict[str, Activity]
    ) -> list[EdgeDto]:
        """Extract Retry/Timeout/Done edges from RetryScope activity.

        Args:
            activity: RetryScope activity
            activity_map: Activity lookup map

        Returns:
            List of Retry/Timeout/Done edges
        """
        edges: list[EdgeDto] = []

        # Get the action being retried
        action_activity = self._find_child_by_name(activity, "Action", activity_map)
        if action_activity:
            edge_id = self.id_generator.generate_edge_id(
                activity.activity_id, action_activity, "Retry"
            )
            edges.append(
                EdgeDto(
                    id=edge_id,
                    from_id=activity.activity_id,
                    to_id=action_activity,
                    kind="Retry",
                    condition=None,
                    label="Retry Action",
                )
            )

        return edges

    def _find_child_by_name(
        self, activity: Activity, name: str, activity_map: dict[str, Activity]
    ) -> str | None:
        """Find child activity by configuration name.

        Args:
            activity: Parent activity
            name: Configuration key name (e.g., "Then", "Else")
            activity_map: Activity lookup map

        Returns:
            Activity ID if found, None otherwise
        """
        # Check configuration for nested activity
        config_value = activity.configuration.get(name)
        if config_value:
            # Extract activity ID from configuration
            activity_id = self._extract_activity_id_from_config(config_value)
            if activity_id:
                return activity_id

        # Fallback: search child activities for matching type/name
        for child_id in activity.child_activities:
            child = activity_map.get(child_id)
            if child and child.display_name == name:
                return child_id

        return None

    def _extract_activity_id_from_config(self, config: Any) -> str | None:
        """Extract activity ID from configuration object.

        Args:
            config: Configuration value (dict, string, or other)

        Returns:
            Activity ID if found, None otherwise
        """
        if isinstance(config, str):
            # Could be an activity ID
            if config.startswith("act:"):
                return config

        elif isinstance(config, dict):
            # Check for IdRef or other ID fields
            if "IdRef" in config:
                return config["IdRef"]
            # Check for nested activity
            if "Activity" in config:
                return self._extract_activity_id_from_config(config["Activity"])

        return None
