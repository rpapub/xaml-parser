"""Variable flow analysis for tracking read/write patterns across activities.

This module provides data flow analysis capabilities for UiPath workflows,
detecting uninitialized variables, unused variables, and tracking variable usage patterns.
"""

from ...shared.model.dto import VariableFlowDto
from ...stages.parsing.expression_parser import ParsedExpression
from ...shared.model.models import Activity


class VariableFlowAnalyzer:
    """Analyzes variable data flow across workflow activities."""

    def __init__(self) -> None:
        """Initialize flow analyzer."""
        self.variable_flows: dict[str, VariableFlowDto] = {}

    def analyze_workflow(self, activities: list[Activity]) -> list[VariableFlowDto]:
        """Analyze variable flow across all activities in a workflow.

        Args:
            activities: List of activities with parsed expressions

        Returns:
            List of VariableFlowDto objects with flow analysis
        """
        self.variable_flows = {}

        # Process activities in order (assuming depth-first traversal order)
        for activity in activities:
            self._process_activity(activity)

        # Post-process to detect patterns
        self._detect_patterns()

        # Return sorted by variable name for determinism
        return sorted(self.variable_flows.values(), key=lambda x: x.variable_name)

    def _process_activity(self, activity: Activity) -> None:
        """Process a single activity to extract variable accesses.

        Args:
            activity: Activity with expressions to analyze
        """
        activity_id = activity.activity_id

        # Process expression_objects if they contain ParsedExpression data
        for expr in activity.expression_objects:
            # Check if this is a ParsedExpression or if we have parsed data
            if hasattr(expr, "variables"):
                # This is a parsed expression with VariableAccess objects
                for var_access in expr.variables:
                    self._record_access(
                        var_access.name, activity_id, var_access.access_type, var_access.context
                    )

        # Also process variables_referenced (legacy) for backward compatibility
        for var_name in activity.variables_referenced:
            # Assume read access for legacy data (conservative)
            self._record_access(var_name, activity_id, "read", "legacy")

    def _record_access(
        self, var_name: str, activity_id: str, access_type: str, context: str
    ) -> None:
        """Record a variable access.

        Args:
            var_name: Variable name
            activity_id: Activity performing the access
            access_type: 'read', 'write', or 'readwrite'
            context: Access context (LHS, RHS, argument, etc.)
        """
        # Create flow record if not exists
        if var_name not in self.variable_flows:
            self.variable_flows[var_name] = VariableFlowDto(variable_name=var_name)

        flow = self.variable_flows[var_name]

        # Record read access
        if access_type in ("read", "readwrite"):
            flow.read_count += 1
            if activity_id not in flow.read_locations:
                flow.read_locations.append(activity_id)
            if flow.first_read is None:
                flow.first_read = activity_id

        # Record write access
        if access_type in ("write", "readwrite"):
            flow.write_count += 1
            if activity_id not in flow.write_locations:
                flow.write_locations.append(activity_id)
            if flow.first_write is None:
                flow.first_write = activity_id

    def _detect_patterns(self) -> None:
        """Detect common patterns like uninitialized reads and unused variables."""
        for _var_name, flow in self.variable_flows.items():
            # Detect uninitialized: read before write
            if flow.first_read is not None and flow.first_write is None:
                # Variable read but never written (might be argument or uninitialized)
                flow.is_uninitialized = True
            elif (
                flow.first_read is not None
                and flow.first_write is not None
                and flow.read_locations
                and flow.write_locations
            ):
                # Check if first read comes before first write
                # (approximation: check if first_read appears earlier in location lists)
                # This is a heuristic since we don't have full execution order
                pass

            # Detect unused: written but never read
            if flow.write_count > 0 and flow.read_count == 0:
                flow.is_unused = True

    @staticmethod
    def analyze_expressions(
        expressions: list[ParsedExpression], activity_id: str
    ) -> dict[str, list[str]]:
        """Analyze expressions and return variable usage summary.

        Helper method for quick analysis without full workflow context.

        Args:
            expressions: List of parsed expressions
            activity_id: Activity ID for reference

        Returns:
            Dictionary with 'reads' and 'writes' lists
        """
        reads = []
        writes = []

        for expr in expressions:
            for var_access in expr.variables:
                if var_access.access_type in ("read", "readwrite"):
                    reads.append(var_access.name)
                if var_access.access_type in ("write", "readwrite"):
                    writes.append(var_access.name)

        return {"reads": list(set(reads)), "writes": list(set(writes))}


def analyze_variable_flow(activities: list[Activity]) -> list[VariableFlowDto]:
    """Convenience function to analyze variable flow in a workflow.

    Args:
        activities: List of activities to analyze

    Returns:
        List of VariableFlowDto objects with analysis results
    """
    analyzer = VariableFlowAnalyzer()
    return analyzer.analyze_workflow(activities)
