"""Mermaid diagram emitter for workflow visualization."""

import re
from pathlib import Path

from ..dto import ActivityDto, EdgeDto, WorkflowDto
from . import EmitResult, Emitter, EmitterConfig


class MermaidEmitter(Emitter):
    """Generate Mermaid flowchart diagrams from workflows."""

    @property
    def name(self) -> str:
        """Emitter name."""
        return "mermaid"

    @property
    def output_extension(self) -> str:
        """Output file extension."""
        return ".mmd"

    def emit(
        self, workflows: list[WorkflowDto], output_path: Path, config: EmitterConfig
    ) -> EmitResult:
        """Generate Mermaid diagrams for workflows.

        Args:
            workflows: List of workflow DTOs
            output_path: Output directory or file path
            config: Emitter configuration

        Returns:
            EmitResult with success status and files written
        """
        try:
            # Ensure output directory exists
            if output_path.suffix == ".mmd":
                # Single workflow to specific file
                output_dir = output_path.parent
                output_dir.mkdir(parents=True, exist_ok=True)
                files_written = [self._emit_single(workflows[0], output_path, config)]
            else:
                # Multiple workflows to directory
                output_path.mkdir(parents=True, exist_ok=True)
                files_written = []
                for workflow in workflows:
                    filename = self._sanitize_filename(workflow.name) + ".mmd"
                    file_path = output_path / filename
                    files_written.append(self._emit_single(workflow, file_path, config))

            return EmitResult(
                success=True,
                files_written=files_written,
                errors=[],
                warnings=[],
            )
        except Exception as e:
            return EmitResult(success=False, files_written=[], errors=[str(e)], warnings=[])

    def _emit_single(self, workflow: WorkflowDto, output_path: Path, config: EmitterConfig) -> Path:
        """Emit a single Mermaid diagram."""
        diagram = self._generate_diagram(workflow, config)
        output_path.write_text(diagram, encoding="utf-8")
        return output_path

    def _generate_diagram(self, workflow: WorkflowDto, config: EmitterConfig) -> str:
        """Generate Mermaid flowchart from workflow.

        Args:
            workflow: Workflow DTO
            config: Emitter configuration

        Returns:
            Mermaid diagram as string
        """
        lines = ["flowchart TD"]

        # Add title as comment
        lines.append(f"    %% Workflow: {workflow.name}")
        if (
            workflow.metadata
            and hasattr(workflow.metadata, "annotation")
            and workflow.metadata.annotation
        ):
            annotation = workflow.metadata.annotation
            # Truncate long annotations
            if len(annotation) > 100:
                annotation = annotation[:97] + "..."
            lines.append(f"    %% {annotation}")
        lines.append("")

        # Get max depth for filtering
        max_depth = config.extra.get("max_depth", 5)

        # Filter activities by depth
        activities = [a for a in workflow.activities if a.depth <= max_depth]

        # Generate nodes
        for activity in activities:
            node_id = self._sanitize_id(activity.id)
            label = self._format_label(activity)
            shape = self._get_node_shape(activity)

            lines.append(f'    {node_id}{shape[0]}"{label}"{shape[1]}')

        # Add blank line before edges
        if workflow.edges:
            lines.append("")

        # Generate edges
        for edge in workflow.edges:
            # Skip edges to/from activities beyond max depth
            from_act = next((a for a in workflow.activities if a.id == edge.from_id), None)
            to_act = next((a for a in workflow.activities if a.id == edge.to_id), None)

            if not from_act or not to_act:
                continue
            if from_act.depth > max_depth or to_act.depth > max_depth:
                continue

            from_id = self._sanitize_id(edge.from_id)
            to_id = self._sanitize_id(edge.to_id)

            # Format edge label
            edge_style = self._get_edge_style(edge)
            label = f"|{edge.kind}|" if edge.kind else ""

            lines.append(f"    {from_id} {edge_style[0]}{label}{edge_style[1]} {to_id}")

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
        sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", id_str)
        # Ensure it starts with a letter (Mermaid requirement)
        if sanitized and not sanitized[0].isalpha():
            sanitized = "n" + sanitized
        return sanitized or "node"

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize workflow name for use as filename.

        Args:
            name: Workflow name

        Returns:
            Safe filename (without extension)
        """
        # Replace non-alphanumeric chars with underscores, preserve spaces
        safe = re.sub(r'[<>:"/\\|?*]', "_", name)
        # Trim whitespace
        safe = safe.strip()
        return safe or "workflow"

    def _format_label(self, activity: ActivityDto) -> str:
        """Format activity label for display.

        Args:
            activity: Activity DTO

        Returns:
            Formatted label
        """
        # Use display name if available, otherwise type short
        name = activity.display_name or activity.type_short

        # Escape special characters for Mermaid
        name = name.replace('"', '\\"')

        # Truncate long names
        if len(name) > 40:
            name = name[:37] + "..."

        # Add type annotation
        return f"{name}\\n({activity.type_short})"

    def _get_node_shape(self, activity: ActivityDto) -> tuple[str, str]:
        """Get Mermaid node shape based on activity type.

        Args:
            activity: Activity DTO

        Returns:
            Tuple of (opening, closing) shape delimiters
        """
        activity_type = activity.type_short.lower()

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

    def _get_edge_style(self, edge: EdgeDto) -> tuple[str, str]:
        """Get Mermaid edge style based on edge kind.

        Args:
            edge: Edge DTO

        Returns:
            Tuple of (arrow_start, arrow_end) style strings
        """
        kind = edge.kind.lower() if edge.kind else "next"

        # Error/exception paths (thick red)
        if kind in ["catch", "finally", "timeout"]:
            return ("==>", "")

        # Conditional branches (dotted)
        if kind in ["then", "else", "true", "false", "case", "default"]:
            return ("-.->", "")

        # Default: solid arrow
        return ("-->", "")

    def _generate_styling(self, activities: list[ActivityDto]) -> list[str]:
        """Generate CSS styling for nodes.

        Args:
            activities: List of activities

        Returns:
            List of Mermaid style statements
        """
        styles = []

        for activity in activities:
            node_id = self._sanitize_id(activity.id)
            activity_type = activity.type_short.lower()

            # Decision nodes (blue)
            if activity_type in ["if", "switch", "flowdecision", "pick"]:
                styles.append("    classDef decisionStyle fill:#6495ED,stroke:#4169E1")
                styles.append(f"    class {node_id} decisionStyle")

            # Container nodes (light green)
            elif activity_type in [
                "sequence",
                "flowchart",
                "statemachine",
                "parallel",
            ]:
                styles.append("    classDef containerStyle fill:#90EE90,stroke:#228B22")
                styles.append(f"    class {node_id} containerStyle")

            # Error handling (orange)
            elif activity_type in ["trycatch", "retryscope"]:
                styles.append("    classDef errorStyle fill:#FFA500,stroke:#FF8C00")
                styles.append(f"    class {node_id} errorStyle")

        return styles if styles else ["    %% No custom styling"]
