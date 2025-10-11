"""Deterministic ordering utilities for stable, reproducible output.

This module provides locale-independent sorting functions to ensure
deterministic output across different systems and environments.

All sorting uses UTF-8 binary collation (byte-wise comparison) to avoid
locale-dependent behavior that could cause output differences between systems.

Design: ADR-DTO-DESIGN.md (Deterministic Serialization)
"""

from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")


def sort_by_id(items: list[T]) -> list[T]:
    """Sort items by their 'id' attribute using binary collation.

    Args:
        items: List of objects with 'id' attribute (ActivityDto, EdgeDto, etc.)

    Returns:
        Sorted list (new list, input not modified)

    Example:
        >>> activities = [ActivityDto(id="act:sha256:def"), ActivityDto(id="act:sha256:abc")]
        >>> sorted_acts = sort_by_id(activities)
        >>> sorted_acts[0].id
        'act:sha256:abc'
    """
    return sorted(items, key=lambda item: item.id)


def sort_by_name(items: list[T]) -> list[T]:
    """Sort items by their 'name' attribute using binary collation.

    Args:
        items: List of objects with 'name' attribute (ArgumentDto, VariableDto, etc.)

    Returns:
        Sorted list (new list, input not modified)

    Example:
        >>> args = [ArgumentDto(name="out_Result"), ArgumentDto(name="in_FilePath")]
        >>> sorted_args = sort_by_name(args)
        >>> sorted_args[0].name
        'in_FilePath'
    """
    return sorted(items, key=lambda item: item.name)


def sort_dict_by_key(d: dict[str, Any]) -> dict[str, Any]:
    """Sort dictionary by keys using binary collation.

    Args:
        d: Dictionary to sort

    Returns:
        New dictionary with keys sorted

    Example:
        >>> props = {"Value": "x", "DisplayName": "Test", "To": "y"}
        >>> sorted_props = sort_dict_by_key(props)
        >>> list(sorted_props.keys())
        ['DisplayName', 'To', 'Value']
    """
    return dict(sorted(d.items(), key=lambda item: item[0]))


def sort_by_key(items: list[T], key_func: Callable[[T], str]) -> list[T]:
    """Sort items using custom key function with binary collation.

    Args:
        items: List of items to sort
        key_func: Function to extract sort key from item

    Returns:
        Sorted list (new list, input not modified)

    Example:
        >>> edges = [
        ...     EdgeDto(from_id="act:2", to_id="act:1"),
        ...     EdgeDto(from_id="act:1", to_id="act:2"),
        ... ]
        >>> sorted_edges = sort_by_key(edges, lambda e: f"{e.from_id}:{e.to_id}")
    """
    return sorted(items, key=key_func)


def sort_edges(edges: list[T]) -> list[T]:
    """Sort edges by (from_id, to_id, kind) tuple for deterministic output.

    Args:
        edges: List of EdgeDto objects

    Returns:
        Sorted list (new list, input not modified)

    Example:
        >>> edges = [
        ...     EdgeDto(from_id="act:2", to_id="act:3", kind="Then"),
        ...     EdgeDto(from_id="act:1", to_id="act:2", kind="Next"),
        ... ]
        >>> sorted_edges = sort_edges(edges)
    """
    return sorted(
        edges,
        key=lambda e: (
            e.from_id,
            e.to_id,
            e.kind,
        ),
    )


def ensure_deterministic_order(workflow_dto: Any) -> None:
    """Ensure all collections in WorkflowDto are deterministically sorted.

    This function modifies the workflow DTO in-place to sort all collections
    using locale-independent binary collation.

    Args:
        workflow_dto: WorkflowDto instance to sort (modified in-place)

    Note:
        This is called by the Normalizer after DTO transformation to ensure
        deterministic output.
    """
    # Sort activities by ID
    if hasattr(workflow_dto, "activities") and workflow_dto.activities:
        workflow_dto.activities = sort_by_id(workflow_dto.activities)

    # Sort arguments by name
    if hasattr(workflow_dto, "arguments") and workflow_dto.arguments:
        workflow_dto.arguments = sort_by_name(workflow_dto.arguments)

    # Sort variables by name
    if hasattr(workflow_dto, "variables") and workflow_dto.variables:
        workflow_dto.variables = sort_by_name(workflow_dto.variables)

    # Sort dependencies by package name
    if hasattr(workflow_dto, "dependencies") and workflow_dto.dependencies:
        workflow_dto.dependencies = sort_by_name(workflow_dto.dependencies)

    # Sort edges by (from_id, to_id, kind)
    if hasattr(workflow_dto, "edges") and workflow_dto.edges:
        workflow_dto.edges = sort_edges(workflow_dto.edges)

    # Sort invocations by callee_id
    if hasattr(workflow_dto, "invocations") and workflow_dto.invocations:
        workflow_dto.invocations = sorted(
            workflow_dto.invocations,
            key=lambda inv: inv.callee_id,
        )

    # Sort issues by (level, message)
    if hasattr(workflow_dto, "issues") and workflow_dto.issues:
        workflow_dto.issues = sorted(
            workflow_dto.issues,
            key=lambda issue: (
                issue.level,
                issue.message,
            ),
        )

    # Sort properties within activities
    for activity in getattr(workflow_dto, "activities", []):
        if hasattr(activity, "properties") and isinstance(activity.properties, dict):
            activity.properties = sort_dict_by_key(activity.properties)

        if hasattr(activity, "in_args") and isinstance(activity.in_args, dict):
            activity.in_args = sort_dict_by_key(activity.in_args)

        if hasattr(activity, "out_args") and isinstance(activity.out_args, dict):
            activity.out_args = sort_dict_by_key(activity.out_args)

        if hasattr(activity, "selectors") and isinstance(activity.selectors, dict):
            activity.selectors = sort_dict_by_key(activity.selectors)

        # Sort lists within activities
        if hasattr(activity, "expressions") and activity.expressions:
            activity.expressions = sorted(activity.expressions)

        if hasattr(activity, "variables_referenced") and activity.variables_referenced:
            activity.variables_referenced = sorted(activity.variables_referenced)

        if hasattr(activity, "children") and activity.children:
            activity.children = sorted(activity.children)


def verify_deterministic_order(workflow_dto: Any) -> list[str]:
    """Verify that all collections in WorkflowDto are deterministically sorted.

    Args:
        workflow_dto: WorkflowDto instance to check

    Returns:
        List of warnings about non-deterministic ordering (empty if all good)

    Example:
        >>> warnings = verify_deterministic_order(workflow)
        >>> if warnings:
        ...     print("Warning: Non-deterministic ordering detected")
    """
    warnings = []

    # Check activities sorted by ID
    if hasattr(workflow_dto, "activities") and workflow_dto.activities:
        ids = [a.id for a in workflow_dto.activities]
        sorted_ids = sorted(ids)
        if ids != sorted_ids:
            warnings.append("Activities not sorted by ID")

    # Check arguments sorted by name
    if hasattr(workflow_dto, "arguments") and workflow_dto.arguments:
        names = [a.name for a in workflow_dto.arguments]
        sorted_names = sorted(names)
        if names != sorted_names:
            warnings.append("Arguments not sorted by name")

    # Check variables sorted by name
    if hasattr(workflow_dto, "variables") and workflow_dto.variables:
        names = [v.name for v in workflow_dto.variables]
        sorted_names = sorted(names)
        if names != sorted_names:
            warnings.append("Variables not sorted by name")

    return warnings
