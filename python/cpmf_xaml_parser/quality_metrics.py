"""Quality metrics calculator for workflow analysis (v0.2.10).

This module calculates complexity and quality metrics for XAML workflows,
enabling data lake analytics and quality dashboards.
"""

from .models import Activity, QualityMetrics, WorkflowVariable


class QualityMetricsCalculator:
    """Calculates quality and complexity metrics for workflows."""

    # Decision point activity types (contribute to cyclomatic complexity)
    DECISION_ACTIVITIES = {
        "If",
        "Switch",
        "While",
        "DoWhile",
        "ForEach",
        "ParallelForEach",
        "Pick",
        "PickBranch",
        "TryCatch",
        "Catch",
    }

    # Control flow activity types
    CONTROL_FLOW_TYPES = {
        "If",
        "Switch",
        "While",
        "DoWhile",
        "ForEach",
        "ParallelForEach",
        "Sequence",
        "Flowchart",
        "StateMachine",
        "TryCatch",
        "Parallel",
        "Pick",
    }

    # UI automation activity types (based on common patterns)
    UI_AUTOMATION_PATTERNS = [
        "click",
        "type",
        "get",
        "find",
        "wait",
        "hover",
        "drag",
        "select",
        "attach",
        "element",
        "window",
        "application",
    ]

    # Data processing activity types
    DATA_ACTIVITY_PATTERNS = [
        "assign",
        "invoke",
        "read",
        "write",
        "build",
        "filter",
        "append",
        "add",
        "remove",
        "contains",
    ]

    def calculate(
        self,
        activities: list[Activity],
        variables: list[WorkflowVariable],
        expressions: list[str] | None = None,
    ) -> QualityMetrics:
        """Calculate all quality metrics for a workflow.

        Args:
            activities: List of workflow activities
            variables: List of workflow variables
            expressions: Optional list of expressions (for complexity)

        Returns:
            QualityMetrics with all calculated metrics
        """
        metrics = QualityMetrics()

        # Always calculate quality score, even for empty workflows
        if not activities:
            # Still count variables and expressions
            metrics.total_variables = len(variables)
            if expressions:
                metrics.total_expressions = len(expressions)
                metrics.complex_expressions = sum(1 for expr in expressions if len(expr) > 100)
            metrics.quality_score = self._calculate_quality_score(metrics)
            return metrics

        # Complexity metrics
        metrics.cyclomatic_complexity = self._calculate_cyclomatic_complexity(activities)
        metrics.cognitive_complexity = self._calculate_cognitive_complexity(activities)
        metrics.max_nesting_depth = self._calculate_max_nesting_depth(activities)

        # Size metrics
        metrics.total_activities = len(activities)
        metrics.control_flow_activities = self._count_control_flow(activities)
        metrics.ui_automation_activities = self._count_ui_automation(activities)
        metrics.data_activities = self._count_data_activities(activities)
        metrics.total_variables = len(variables)

        if expressions:
            metrics.total_expressions = len(expressions)
            metrics.complex_expressions = sum(1 for expr in expressions if len(expr) > 100)

        # Quality indicators
        metrics.has_error_handling = self._has_error_handling(activities)
        metrics.empty_catch_blocks = self._count_empty_catch_blocks(activities)

        # Overall quality score
        metrics.quality_score = self._calculate_quality_score(metrics)

        return metrics

    def _calculate_cyclomatic_complexity(self, activities: list[Activity]) -> int:
        """Calculate cyclomatic complexity.

        Formula: Number of decision points + 1
        Decision points: If, Switch, While, ForEach, TryCatch (per Catch block)

        Args:
            activities: List of activities

        Returns:
            Cyclomatic complexity value
        """
        decision_points = 0

        for activity in activities:
            activity_type = activity.activity_type

            # Check if it's a decision activity
            if any(decision in activity_type for decision in self.DECISION_ACTIVITIES):
                decision_points += 1

                # TryCatch adds complexity for each Catch block
                if "TryCatch" in activity_type or "Catch" in activity_type:
                    # Count catch blocks from properties
                    catches = activity.properties.get("Catches", [])
                    if isinstance(catches, list):
                        decision_points += len(catches)

        return decision_points + 1

    def _calculate_cognitive_complexity(self, activities: list[Activity]) -> int:
        """Calculate cognitive complexity with nesting penalties.

        Cognitive complexity adds +1 for each nesting level of decision points.

        Args:
            activities: List of activities

        Returns:
            Cognitive complexity value
        """
        cognitive_score = 0

        for activity in activities:
            activity_type = activity.activity_type

            # Check if it's a decision activity
            if any(decision in activity_type for decision in self.DECISION_ACTIVITIES):
                # Base complexity: +1
                # Nesting penalty: +1 per level beyond 0
                nesting_level = activity.depth
                cognitive_score += 1 + max(0, nesting_level)

        return cognitive_score

    def _calculate_max_nesting_depth(self, activities: list[Activity]) -> int:
        """Calculate maximum nesting depth.

        Args:
            activities: List of activities

        Returns:
            Maximum depth value
        """
        if not activities:
            return 0

        return max(activity.depth for activity in activities)

    def _count_control_flow(self, activities: list[Activity]) -> int:
        """Count control flow activities.

        Args:
            activities: List of activities

        Returns:
            Count of control flow activities
        """
        count = 0
        for activity in activities:
            if any(cf_type in activity.activity_type for cf_type in self.CONTROL_FLOW_TYPES):
                count += 1
        return count

    def _count_ui_automation(self, activities: list[Activity]) -> int:
        """Count UI automation activities.

        Args:
            activities: List of activities

        Returns:
            Count of UI automation activities
        """
        count = 0
        for activity in activities:
            activity_type_lower = activity.activity_type.lower()
            if any(pattern in activity_type_lower for pattern in self.UI_AUTOMATION_PATTERNS):
                count += 1
        return count

    def _count_data_activities(self, activities: list[Activity]) -> int:
        """Count data processing activities.

        Args:
            activities: List of activities

        Returns:
            Count of data activities
        """
        count = 0
        for activity in activities:
            activity_type_lower = activity.activity_type.lower()
            if any(pattern in activity_type_lower for pattern in self.DATA_ACTIVITY_PATTERNS):
                count += 1
        return count

    def _has_error_handling(self, activities: list[Activity]) -> bool:
        """Check if workflow has error handling.

        Args:
            activities: List of activities

        Returns:
            True if TryCatch found
        """
        return any("TryCatch" in activity.activity_type for activity in activities)

    def _count_empty_catch_blocks(self, activities: list[Activity]) -> int:
        """Count TryCatch activities with empty Catch blocks.

        Args:
            activities: List of activities

        Returns:
            Count of empty catch blocks
        """
        empty_count = 0

        for activity in activities:
            if "TryCatch" in activity.activity_type:
                # Check if Catches property exists and has children
                catches = activity.properties.get("Catches", [])
                if isinstance(catches, list):
                    for catch in catches:
                        # Empty if no child activities
                        if not catch or (isinstance(catch, dict) and not catch.get("activities")):
                            empty_count += 1

        return empty_count

    def _calculate_quality_score(self, metrics: QualityMetrics) -> float:
        """Calculate overall quality score (0-100).

        Scoring algorithm:
        - Start with 100 points
        - Deduct for high complexity
        - Deduct for anti-patterns
        - Bonus for error handling

        Args:
            metrics: Calculated metrics

        Returns:
            Quality score 0-100
        """
        score = 100.0

        # Complexity penalties
        if metrics.cyclomatic_complexity > 20:
            score -= 20
        elif metrics.cyclomatic_complexity > 10:
            score -= 10

        if metrics.cognitive_complexity > 30:
            score -= 20
        elif metrics.cognitive_complexity > 15:
            score -= 10

        if metrics.max_nesting_depth > 5:
            score -= 15
        elif metrics.max_nesting_depth > 3:
            score -= 5

        # Anti-pattern penalties
        score -= metrics.empty_catch_blocks * 5
        score -= metrics.hardcoded_strings * 2
        score -= metrics.unreachable_activities * 10
        score -= metrics.unused_variables * 1

        # Error handling bonus
        if metrics.has_error_handling:
            score += 10

        # Ensure score stays in bounds
        return max(0.0, min(100.0, score))
