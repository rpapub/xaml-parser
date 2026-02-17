"""Field profiles for configurable DTO output.

This module defines field selection profiles that allow users to control
which fields are included in the output DTOs. This is useful for:
- Reducing output size
- Focusing on specific use cases (MCP, data lake, minimal)
- Excluding sensitive/unnecessary fields

Design: ADR-DTO-DESIGN.md (Field Profiles)
"""

from typing import Any

# Field profiles define which fields to include in output
# None means "all fields"
# List of strings means "only these fields"

PROFILES = {
    "full": None,  # All fields included
    "minimal": {
        "WorkflowDto": [
            "schema_id",
            "schema_version",
            "id",
            "name",
            "activities",
            "edges",
        ],
        "ActivityDto": [
            "id",
            "type",
            "type_short",
            "display_name",
            "depth",
            "children",
        ],
        "EdgeDto": ["id", "from_id", "to_id", "kind"],
    },
    "mcp": {
        "WorkflowDto": [
            "schema_id",
            "schema_version",
            "id",
            "name",
            "metadata",
            "arguments",
            "variables",
            "activities",
            "edges",
        ],
        "ActivityDto": [
            "id",
            "type",
            "type_short",
            "display_name",
            "parent_id",
            "children",
            "depth",
            "properties",
            "in_args",
            "out_args",
            "annotation",
            "annotation_block",
            "expressions",
            "variables_referenced",
        ],
        "EdgeDto": ["id", "from_id", "to_id", "kind", "condition", "label"],
        "ArgumentDto": ["id", "name", "type", "direction", "annotation", "annotation_block"],
        "VariableDto": ["id", "name", "type", "scope", "default_value"],
    },
    "datalake": None,  # Full but exclude ViewState (handled elsewhere)
}


def apply_profile(data: dict[str, Any], profile_name: str, dto_type: str) -> dict[str, Any]:
    """Apply field profile to DTO data.

    Args:
        data: Dictionary representation of DTO
        profile_name: Profile name (full, minimal, mcp, datalake)
        dto_type: DTO type name (e.g., "WorkflowDto", "ActivityDto")

    Returns:
        Filtered dictionary with only allowed fields

    Raises:
        ValueError: If profile name is unknown
    """
    if profile_name not in PROFILES:
        raise ValueError(
            f"Unknown profile: {profile_name}. Valid profiles: {', '.join(PROFILES.keys())}"
        )

    profile = PROFILES[profile_name]

    # If profile is None (full), return all fields
    if profile is None:
        return data

    # If profile doesn't specify this DTO type, return all fields
    if dto_type not in profile:
        return data

    # Get allowed fields for this DTO type
    allowed_fields = profile[dto_type]

    # Filter data to only include allowed fields
    return {key: value for key, value in data.items() if key in allowed_fields}


def apply_profile_recursive(data: Any, profile_name: str, dto_type: str | None = None) -> Any:
    """Apply field profile recursively to nested data structures.

    Args:
        data: Data to filter (can be dict, list, or primitive)
        profile_name: Profile name
        dto_type: Current DTO type (detected from data if None)

    Returns:
        Filtered data structure
    """
    # Handle None
    if data is None:
        return None

    # Handle primitives
    if isinstance(data, str | int | float | bool):
        return data

    # Handle lists
    if isinstance(data, list):
        return [apply_profile_recursive(item, profile_name, dto_type) for item in data]

    # Handle dicts (DTOs)
    if isinstance(data, dict):
        # Detect DTO type from schema_id or type field
        if dto_type is None:
            dto_type = _detect_dto_type(data)

        # Apply profile to current level
        filtered = apply_profile(data, profile_name, dto_type)

        # Recursively apply to nested structures
        result = {}
        for key, value in filtered.items():
            # Detect nested DTO types based on field name
            nested_type = _get_nested_dto_type(key)
            result[key] = apply_profile_recursive(value, profile_name, nested_type)

        return result

    # Unknown type, return as-is
    return data


def _detect_dto_type(data: dict[str, Any]) -> str:
    """Detect DTO type from data.

    Args:
        data: Dictionary data

    Returns:
        DTO type name (e.g., "WorkflowDto", "ActivityDto")
    """
    # Check for schema_id field
    if "schema_id" in data:
        schema_id = data["schema_id"]
        if "workflow-collection" in schema_id:
            return "WorkflowCollectionDto"
        elif "workflow" in schema_id:
            return "WorkflowDto"

    # Check for field patterns
    if "activities" in data and "edges" in data:
        return "WorkflowDto"
    elif "type_short" in data and "depth" in data:
        return "ActivityDto"
    elif "from_id" in data and "to_id" in data and "kind" in data:
        return "EdgeDto"
    elif "direction" in data and "name" in data:
        return "ArgumentDto"
    elif "scope" in data and "name" in data:
        return "VariableDto"

    return "Unknown"


def _get_nested_dto_type(field_name: str) -> str | None:
    """Get DTO type for nested field.

    Args:
        field_name: Field name

    Returns:
        DTO type name or None
    """
    field_type_map = {
        "activities": "ActivityDto",
        "edges": "EdgeDto",
        "arguments": "ArgumentDto",
        "variables": "VariableDto",
        "dependencies": "DependencyDto",
        "invocations": "InvocationDto",
        "issues": "IssueDto",
        "workflows": "WorkflowDto",
    }

    return field_type_map.get(field_name)


def list_profiles() -> list[str]:
    """List all available profile names.

    Returns:
        List of profile names
    """
    return list(PROFILES.keys())


def get_profile_fields(profile_name: str, dto_type: str) -> list[str] | None:
    """Get field list for a profile and DTO type.

    Args:
        profile_name: Profile name
        dto_type: DTO type name

    Returns:
        List of field names, or None if all fields included

    Raises:
        ValueError: If profile name is unknown
    """
    if profile_name not in PROFILES:
        raise ValueError(
            f"Unknown profile: {profile_name}. Valid profiles: {', '.join(PROFILES.keys())}"
        )

    profile = PROFILES[profile_name]

    # If profile is None (full), all fields included
    if profile is None:
        return None

    # If profile doesn't specify this DTO type, all fields included
    if dto_type not in profile:
        return None

    return profile[dto_type]
