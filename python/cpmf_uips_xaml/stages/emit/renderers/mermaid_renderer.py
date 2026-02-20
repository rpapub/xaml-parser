"""Mermaid renderer for pure dict → diagram string conversion.

Extracts diagram generation logic from MermaidEmitter.
"""

import re
from typing import Any

from ..utils import sanitize_filename
from .base import Renderer, RenderResult


class MermaidRenderer(Renderer):
    """Render workflow to Mermaid diagram string (pure, no I/O).

    Generates Mermaid flowchart syntax WITHOUT writing to files.
    All I/O is handled by sinks.
    """

    @property
    def name(self) -> str:
        """Renderer name.

        Returns:
            'mermaid'
        """
        return "mermaid"

    @property
    def output_extension(self) -> str:
        """Output file extension.

        Returns:
            '.mmd'
        """
        return ".mmd"

    def render_one(self, workflow_dict: dict[str, Any], config: Any) -> RenderResult:
        """Generate Mermaid diagram string.

        Args:
            workflow_dict: Workflow data as dict
            config: Renderer configuration (expects: extra dict with max_depth)

        Returns:
            RenderResult with Mermaid diagram string
        """
        try:
            diagram = self._generate_diagram(workflow_dict, config)

            workflow_name = workflow_dict.get("name", "workflow")
            suggested_filename = (
                sanitize_filename(workflow_name, fallback="Untitled") + ".mmd"
            )

            return RenderResult(
                success=True,
                content=diagram,
                metadata={"suggested_filename": suggested_filename},
                errors=[],
                warnings=[],
            )

        except Exception as e:
            workflow_name = workflow_dict.get("name", "unknown")
            return RenderResult(
                success=False,
                content="",
                metadata={},
                errors=[f"Failed to render Mermaid diagram for {workflow_name}: {e}"],
                warnings=[],
            )

    def render_many(
        self, workflow_dicts: list[dict[str, Any]], config: Any
    ) -> RenderResult:
        """Render multiple workflows as dict of filename → diagram.

        Args:
            workflow_dicts: List of workflow dicts
            config: Renderer configuration

        Returns:
            RenderResult with dict of filename → Mermaid diagram
        """
        content_map = {}
        errors = []

        for wf_dict in workflow_dicts:
            result = self.render_one(wf_dict, config)

            if result.success:
                filename = result.metadata["suggested_filename"]
                content_map[filename] = result.content
            else:
                errors.extend(result.errors)

        return RenderResult(
            success=len(errors) == 0,
            content=content_map,
            metadata={"count": len(content_map)},
            errors=errors,
            warnings=[],
        )

    def _generate_diagram(
        self, workflow_dict: dict[str, Any], config: Any
    ) -> str:
        """Generate Mermaid flowchart syntax.

        Extracted from MermaidEmitter._generate_diagram.

        Args:
            workflow_dict: Workflow data
            config: Renderer configuration

        Returns:
            Mermaid diagram string
        """
        lines = ["flowchart TD"]

        # Add title as comment
        workflow_name = workflow_dict.get("name", "Workflow")
        lines.append(f"    %% Workflow: {workflow_name}")

        metadata = workflow_dict.get("metadata", {})
        if metadata and isinstance(metadata, dict):
            annotation = metadata.get("annotation")
            if annotation:
                # Truncate long annotations
                if len(annotation) > 100:
                    annotation = annotation[:97] + "..."
                lines.append(f"    %% {annotation}")
        lines.append("")

        # Get max depth for filtering
        max_depth = (
            config.extra.get("max_depth", 5)
            if hasattr(config, "extra") and config.extra
            else 5
        )

        # Filter activities by depth
        all_activities = workflow_dict.get("activities", [])
        activities = [a for a in all_activities if a.get("depth", 0) <= max_depth]

        # Generate nodes
        for activity in activities:
            node_id = self._sanitize_id(activity.get("id", "unknown"))
            label = self._format_label(activity)
            shape = self._get_node_shape(activity)

            lines.append(f'    {node_id}{shape[0]}"{label}"{shape[1]}')

        # Add blank line before edges
        edges = workflow_dict.get("edges", [])
        if edges:
            lines.append("")

        # Generate edges
        for edge in edges:
            # Skip edges to/from activities beyond max depth
            from_id = edge.get("from_id")
            to_id = edge.get("to_id")

            from_act = next((a for a in all_activities if a.get("id") == from_id), None)
            to_act = next((a for a in all_activities if a.get("id") == to_id), None)

            if not from_act or not to_act:
                continue
            if (
                from_act.get("depth", 0) > max_depth
                or to_act.get("depth", 0) > max_depth
            ):
                continue

            from_id_clean = self._sanitize_id(from_id)
            to_id_clean = self._sanitize_id(to_id)

            # Format edge label
            edge_style = self._get_edge_style(edge)
            kind = edge.get("kind", "")
            label = f"|{kind}|" if kind else ""

            lines.append(f"    {from_id_clean} {edge_style[0]}{label}{edge_style[1]} {to_id_clean}")

        # Add styling
        lines.append("")
        lines.append("    %% Styling")
        lines.extend(self._generate_styling(activities))

        return "\n".join(lines)

    def _sanitize_id(self, id_str: str) -> str:
        """Sanitize ID for Mermaid (alphanumeric and underscores only).

        Args:
            id_str: Original ID string

        Returns:
            Sanitized ID suitable for Mermaid
        """
        # Replace non-alphanumeric chars with underscores
        sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", str(id_str))
        # Ensure it starts with a letter (Mermaid requirement)
        if sanitized and not sanitized[0].isalpha():
            sanitized = "n" + sanitized
        return sanitized or "node"

    def _format_label(self, activity: dict[str, Any]) -> str:
        """Format activity label for display.

        Args:
            activity: Activity dict

        Returns:
            Formatted label
        """
        # Use display name if available, otherwise type short
        name = activity.get("display_name") or activity.get("type_short", "Activity")

        # Escape special characters for Mermaid
        name = name.replace('"', '\\"')

        # Truncate long names
        if len(name) > 40:
            name = name[:37] + "..."

        # Add type annotation
        type_short = activity.get("type_short", "Unknown")
        return f"{name}\\n({type_short})"

    def _get_node_shape(self, activity: dict[str, Any]) -> tuple[str, str]:
        """Get Mermaid node shape based on activity type.

        Args:
            activity: Activity dict

        Returns:
            Tuple of (opening, closing) shape delimiters
        """
        activity_type = activity.get("type_short", "").lower()

        # Decision nodes (diamond)
        if activity_type in ["if", "switch", "flowdecision", "pick"]:
            return ("{", "}")

        # Container nodes (rounded rectangle)
        if activity_type in [
            "sequence",
            "flowchart",
            "statemachine",
            "parallel",
            "trycatch",
            "retryscope",
        ]:
            return ("([", "])")

        # Default: rectangle
        return ("[", "]")

    def _get_edge_style(self, edge: dict[str, Any]) -> tuple[str, str]:
        """Get Mermaid edge style based on edge kind.

        Args:
            edge: Edge dict

        Returns:
            Tuple of (arrow_start, arrow_end) style strings
        """
        kind = edge.get("kind", "").lower()

        # Error/exception paths (thick red)
        if kind in ["catch", "finally", "timeout"]:
            return ("==>", "")

        # Conditional branches (dotted)
        if kind in ["then", "else", "true", "false", "case", "default"]:
            return ("-.->", "")

        # Default: solid arrow
        return ("-->", "")

    def _generate_styling(self, activities: list[dict[str, Any]]) -> list[str]:
        """Generate CSS styling for nodes.

        Args:
            activities: List of activities

        Returns:
            List of Mermaid style statements
        """
        styles = []
        defined_classes = set()

        for activity in activities:
            node_id = self._sanitize_id(activity.get("id", "unknown"))
            activity_type = activity.get("type_short", "").lower()

            # Decision nodes (blue)
            if activity_type in ["if", "switch", "flowdecision", "pick"]:
                if "decisionStyle" not in defined_classes:
                    styles.append(
                        "    classDef decisionStyle fill:#6495ED,stroke:#4169E1"
                    )
                    defined_classes.add("decisionStyle")
                styles.append(f"    class {node_id} decisionStyle")

            # Container nodes (light green)
            elif activity_type in [
                "sequence",
                "flowchart",
                "statemachine",
                "parallel",
            ]:
                if "containerStyle" not in defined_classes:
                    styles.append(
                        "    classDef containerStyle fill:#90EE90,stroke:#228B22"
                    )
                    defined_classes.add("containerStyle")
                styles.append(f"    class {node_id} containerStyle")

            # Error handling (orange)
            elif activity_type in ["trycatch", "retryscope"]:
                if "errorStyle" not in defined_classes:
                    styles.append(
                        "    classDef errorStyle fill:#FFA500,stroke:#FF8C00"
                    )
                    defined_classes.add("errorStyle")
                styles.append(f"    class {node_id} errorStyle")

        return styles if styles else ["    %% No custom styling"]


__all__ = ["MermaidRenderer"]
