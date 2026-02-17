"""Field profile filter for selective field output.

Extracts logic from shared/model/field_profiles.py to apply
field profiles (full, minimal, mcp, datalake) to workflow data.
"""

from typing import Any

from ....shared.model.field_profiles import PROFILES, apply_profile_recursive
from .base import Filter, FilterResult


class FieldFilter(Filter):
    """Apply field profile filtering to remove unwanted fields.

    Uses existing apply_profile_recursive logic from field_profiles.py.

    Profiles:
    - full: All fields included (no filtering)
    - minimal: Bare essentials (id, name, activities, edges)
    - mcp: MCP-optimized fields (metadata, arguments, variables)
    - datalake: Full fields (same as full currently)
    """

    def __init__(self, profile: str = "full"):
        """Initialize field filter.

        Args:
            profile: Field profile name (full, minimal, mcp, datalake)

        Raises:
            ValueError: If profile is unknown
        """
        if profile not in PROFILES:
            raise ValueError(
                f"Unknown profile: {profile}. "
                f"Valid profiles: {', '.join(PROFILES.keys())}"
            )
        self.profile = profile

    @property
    def name(self) -> str:
        """Filter name including profile.

        Returns:
            Filter name with profile (e.g., 'field_filter_minimal')
        """
        return f"field_filter_{self.profile}"

    def apply(
        self, data: Any, config: dict[str, Any] | None = None
    ) -> FilterResult:
        """Apply field profile to data structure.

        Args:
            data: Data to filter (dict/list structure from dataclasses.asdict())
            config: Optional override for profile name

        Returns:
            FilterResult with filtered data

        Example:
            filter = FieldFilter("minimal")
            result = filter.apply(workflow_dict)
            # result.data has only minimal fields
        """
        # Allow config override
        profile = config.get("profile", self.profile) if config else self.profile

        # "full" profile means no filtering
        if profile == "full":
            return FilterResult(data=data, modified=False, metadata={"profile": "full"})

        # Use existing apply_profile_recursive logic
        filtered = apply_profile_recursive(data, profile)

        # Check if data was modified
        modified = filtered != data

        return FilterResult(
            data=filtered,
            modified=modified,
            metadata={
                "profile": profile,
                "modified": modified,
            },
        )

    def can_handle(self, data: Any) -> bool:
        """Check if data is a dict (DTO structure).

        Args:
            data: Data to check

        Returns:
            True if data is dict, False otherwise
        """
        return isinstance(data, dict)


__all__ = ["FieldFilter"]
