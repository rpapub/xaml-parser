"""UiPath platform dialect factory.

Creates XamlDialect configured for UiPath automation platform.
"""

from typing import TYPE_CHECKING

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

if TYPE_CHECKING:
    from ...stages.parsing.parser import XamlDialect


def create_uipath_dialect() -> "XamlDialect":
    """Create XamlDialect configured for UiPath platform.

    Returns:
        XamlDialect with UiPath-specific configuration and utilities
    """
    # Import here to avoid circular dependency
    from ...stages.parsing.parser import XamlDialect

    return XamlDialect(
        standard_namespaces=dict(STANDARD_NAMESPACES),
        platform_namespace=PLATFORM_NAMESPACE,
        activity_utils=ActivityUtils,
        core_visual_activities=set(CORE_VISUAL_ACTIVITIES),
        skip_elements=set(SKIP_ELEMENTS),
        argument_directions=dict(ARGUMENT_DIRECTIONS),
        invisible_attribute_patterns=list(INVISIBLE_ATTRIBUTE_PATTERNS),
        viewstate_properties=set(VIEWSTATE_PROPERTIES),
        expression_patterns=list(EXPRESSION_PATTERNS),
        default_parser_config=dict(DEFAULT_CONFIG),
    )
