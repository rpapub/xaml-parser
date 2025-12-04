"""Anti-pattern detector for workflow code smells (v0.2.10).

This module detects common anti-patterns and code smells in XAML workflows,
enabling automated quality checks and code reviews.
"""

import re

from .models import Activity, AntiPattern, WorkflowVariable


class AntiPatternDetector:
    """Detects anti-patterns and code smells in workflows."""

    # Hardcoded value patterns (pre-compiled regex for performance - v0.2.11)
    HARDCODED_PATTERNS = [
        (re.compile(r"[A-Z]:\\", re.IGNORECASE), "Windows file path", "warning"),
        (re.compile(r"/(?:home|usr|var|tmp)/", re.IGNORECASE), "Unix file path", "warning"),
        (re.compile(r"https?://", re.IGNORECASE), "Hardcoded URL", "info"),
        (
            re.compile(
                r"(?:password|pwd|pass|secret|key|token)\s*[=:]\s*[\"'][^\"']+[\"']",
                re.IGNORECASE,
            ),
            "Potential hardcoded credential",
            "error",
        ),
        (re.compile(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", re.IGNORECASE), "IP address", "info"),
    ]

    # Activities that terminate workflow
    TERMINATING_ACTIVITIES = {"Throw", "TerminateWorkflow", "Return"}

    def detect(
        self, activities: list[Activity], variables: list[WorkflowVariable] | None = None
    ) -> list[AntiPattern]:
        """Detect all anti-patterns in workflow.

        Args:
            activities: List of workflow activities
            variables: Optional list of workflow variables

        Returns:
            List of detected anti-patterns
        """
        patterns = []

        if not activities:
            return patterns

        # Empty catch blocks
        patterns.extend(self._detect_empty_catch_blocks(activities))

        # Hardcoded values
        patterns.extend(self._detect_hardcoded_values(activities))

        # Unreachable code
        patterns.extend(self._detect_unreachable_code(activities))

        # Missing error handling
        if not self._has_error_handling(activities):
            patterns.append(
                AntiPattern(
                    pattern_type="missing_error_handling",
                    severity="warning",
                    message="Workflow has no error handling (TryCatch)",
                    suggestion="Add TryCatch activities to handle potential errors",
                )
            )

        # Unused variables
        if variables:
            patterns.extend(self._detect_unused_variables(variables, activities))

        return patterns

    def _detect_empty_catch_blocks(self, activities: list[Activity]) -> list[AntiPattern]:
        """Detect TryCatch activities with empty Catch blocks.

        Args:
            activities: List of activities

        Returns:
            List of detected patterns
        """
        patterns = []

        for activity in activities:
            if "TryCatch" not in activity.activity_type:
                continue

            # Check Catches property
            catches = activity.properties.get("Catches", [])
            if not isinstance(catches, list):
                continue

            for i, catch in enumerate(catches):
                # Check if catch block has no activities or only logging
                is_empty = False

                if not catch:
                    is_empty = True
                elif isinstance(catch, dict):
                    catch_activities = catch.get("activities", [])
                    if not catch_activities:
                        is_empty = True
                    elif len(catch_activities) == 1:
                        # Only has LogMessage - considered empty
                        if "Log" in catch_activities[0].get("type", ""):
                            is_empty = True

                if is_empty:
                    patterns.append(
                        AntiPattern(
                            pattern_type="empty_catch",
                            severity="error",
                            activity_id=activity.activity_id,
                            message=f"Empty catch block in TryCatch (catch block #{i + 1})",
                            suggestion="Add proper error handling or logging in catch block",
                            location=f"TryCatch.Catches[{i}]",
                        )
                    )

        return patterns

    def _detect_hardcoded_values(self, activities: list[Activity]) -> list[AntiPattern]:
        """Detect hardcoded file paths, URLs, credentials, etc.

        Args:
            activities: List of activities

        Returns:
            List of detected patterns
        """
        patterns = []

        for activity in activities:
            # Check visible attributes for hardcoded values
            for key, value in activity.visible_attributes.items():
                if not isinstance(value, str):
                    continue

                # Check against hardcoded patterns (now pre-compiled)
                for pattern_regex, description, severity in self.HARDCODED_PATTERNS:
                    if pattern_regex.search(value):
                        patterns.append(
                            AntiPattern(
                                pattern_type="hardcoded_value",
                                severity=severity,
                                activity_id=activity.activity_id,
                                message=f"{description} found in {activity.activity_type}.{key}",
                                suggestion="Use Config or Orchestrator assets instead of hardcoding values",
                                location=f"{activity.activity_type}.{key}",
                            )
                        )
                        # Only report first match per attribute
                        break

        return patterns

    def _detect_unreachable_code(self, activities: list[Activity]) -> list[AntiPattern]:
        """Detect code after Throw/TerminateWorkflow/Return.

        Args:
            activities: List of activities

        Returns:
            List of detected patterns
        """
        patterns = []

        # Build parent-child relationships
        parent_map = {}
        for activity in activities:
            if activity.parent_activity_id:
                if activity.parent_activity_id not in parent_map:
                    parent_map[activity.parent_activity_id] = []
                parent_map[activity.parent_activity_id].append(activity)

        # Check for terminating activities
        for activity in activities:
            # Check if this activity terminates execution
            is_terminating = any(
                term in activity.activity_type for term in self.TERMINATING_ACTIVITIES
            )

            if not is_terminating:
                continue

            # Check if there are siblings after this activity
            if activity.parent_activity_id:
                siblings = parent_map.get(activity.parent_activity_id, [])
                # Sort by activity_id to get execution order (approximation)
                siblings_sorted = sorted(siblings, key=lambda a: a.activity_id)

                # Find this activity's position
                try:
                    current_idx = siblings_sorted.index(activity)
                    # Check if there are activities after this one
                    if current_idx < len(siblings_sorted) - 1:
                        unreachable_count = len(siblings_sorted) - current_idx - 1
                        patterns.append(
                            AntiPattern(
                                pattern_type="unreachable_code",
                                severity="warning",
                                activity_id=activity.activity_id,
                                message=f"{unreachable_count} activities after {activity.activity_type} are unreachable",
                                suggestion="Remove or restructure unreachable activities",
                                location=f"After {activity.activity_type}",
                            )
                        )
                except ValueError:
                    pass

        return patterns

    def _detect_unused_variables(
        self, variables: list[WorkflowVariable], activities: list[Activity]
    ) -> list[AntiPattern]:
        """Detect variables that are declared but never used.

        Args:
            variables: List of workflow variables
            activities: List of activities

        Returns:
            List of detected patterns
        """
        patterns = []

        # Collect all variable references from activities
        referenced_vars = set()
        for activity in activities:
            referenced_vars.update(activity.variables_referenced)

            # Also check expressions
            for expr in activity.expression_objects:
                if hasattr(expr, "contains_variables"):
                    referenced_vars.update(expr.contains_variables)

        # Find unused variables
        for variable in variables:
            if variable.name not in referenced_vars:
                patterns.append(
                    AntiPattern(
                        pattern_type="unused_variable",
                        severity="info",
                        message=f"Variable '{variable.name}' is declared but never used",
                        suggestion="Remove unused variable or ensure it's referenced",
                        location="Variables",
                    )
                )

        return patterns

    def _has_error_handling(self, activities: list[Activity]) -> bool:
        """Check if workflow has any error handling.

        Args:
            activities: List of activities

        Returns:
            True if TryCatch found
        """
        return any("TryCatch" in activity.activity_type for activity in activities)
