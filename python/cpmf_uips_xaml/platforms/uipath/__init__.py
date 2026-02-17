"""UiPath platform integration.

Provides UiPath-specific constants, utilities, and dialect configuration.
"""

from .activities import ActivityUtils
from .constants import (
    ARGUMENT_DIRECTIONS,
    CORE_VISUAL_ACTIVITIES,
    DEFAULT_CONFIG,
    EXPRESSION_PATTERNS,
    INVISIBLE_ATTRIBUTE_PATTERNS,
    PLATFORM_NAMESPACE,
    SKIP_ELEMENTS,
    STANDARD_NAMESPACES,
    VIEWSTATE_PROPERTIES,
)
from .dialect import create_uipath_dialect

__all__ = [
    "create_uipath_dialect",
    "ActivityUtils",
    "ARGUMENT_DIRECTIONS",
    "CORE_VISUAL_ACTIVITIES",
    "DEFAULT_CONFIG",
    "EXPRESSION_PATTERNS",
    "INVISIBLE_ATTRIBUTE_PATTERNS",
    "PLATFORM_NAMESPACE",
    "SKIP_ELEMENTS",
    "STANDARD_NAMESPACES",
    "VIEWSTATE_PROPERTIES",
]
