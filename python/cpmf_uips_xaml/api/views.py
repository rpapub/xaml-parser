"""View rendering functions.

Provides transformations for rendering project data in different views
(nested/hierarchical, execution flow, context slices).
"""

from typing import Any, Literal, TYPE_CHECKING

if TYPE_CHECKING:
    from ..stages.assemble.analyzer import ProjectAnalyzer
    from ..stages.assemble.index import ProjectIndex


def render_project_view(
    analyzer: "ProjectAnalyzer",
    index: "ProjectIndex",
    view_type: Literal["nested", "execution", "slice"] = "nested",
    **view_options
) -> dict[str, Any]:
    """Render project using specified view transformation.

    Orchestrates view selection and rendering:
    - nested: Hierarchical call graph (default)
    - execution: Call graph traversal from entry point
    - slice: Context window around focal activity

    Args:
        analyzer: ProjectAnalyzer with graph data
        index: ProjectIndex with workflow/activity lookups
        view_type: View transformation to apply
        **view_options: View-specific options (entry_point, focus, radius, max_depth, etc.)

    Returns:
        JSON-serializable dict with view output

    Example:
        view_output = render_project_view(
            analyzer, index,
            view_type="execution",
            entry_point="Main.xaml",
            max_depth=10
        )
    """
    from ..stages.emit.views import ExecutionView, NestedView, SliceView

    if view_type == "nested":
        view = NestedView(**view_options)
    elif view_type == "execution":
        view = ExecutionView(**view_options)
    elif view_type == "slice":
        view = SliceView(**view_options)
    else:
        raise ValueError(f"Unknown view type: {view_type}")

    return view.render(analyzer, index)


__all__ = ["render_project_view"]
