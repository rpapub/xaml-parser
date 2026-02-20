"""Base protocol for pure rendering functions.

Renderers transform DTOs/dicts into output formats (JSON, Mermaid, Markdown)
WITHOUT performing any I/O operations.

Key principles:
- Pure functions (no side effects)
- No file I/O (that's the Sink's job)
- No global state
- Deterministic output
"""

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class RenderResult:
    """Result of a pure render operation (no I/O).

    Attributes:
        success: Whether rendering succeeded
        content: Rendered output (str, bytes, or dict for multi-file)
        metadata: Renderer metadata (e.g., suggested_filename)
        errors: List of error messages
        warnings: List of warning messages
    """

    success: bool
    content: str | bytes | dict[str, Any]  # Rendered output
    metadata: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class Renderer(Protocol):
    """Protocol for pure rendering functions.

    All renderers must implement:
    - name: unique identifier
    - output_extension: file extension (e.g., ".json", ".mmd")
    - render_one(): render single workflow dict
    - render_many(): render multiple workflow dicts

    Renderers transform dicts into output format WITHOUT performing I/O.
    """

    @property
    def name(self) -> str:
        """Unique renderer identifier (e.g., 'json', 'mermaid', 'doc').

        Returns:
            Renderer name
        """
        ...

    @property
    def output_extension(self) -> str:
        """Suggested file extension (e.g., '.json', '.mmd', '.md').

        Returns:
            File extension with leading dot
        """
        ...

    def render_one(self, workflow_dict: dict[str, Any], config: Any) -> RenderResult:
        """Render single workflow dict to output format.

        Args:
            workflow_dict: Workflow data as dict (from dataclasses.asdict)
            config: Renderer configuration (format-specific)

        Returns:
            RenderResult with rendered content (no I/O performed)
        """
        ...

    def render_many(
        self, workflow_dicts: list[dict[str, Any]], config: Any
    ) -> RenderResult:
        """Render multiple workflows (combined or per-workflow).

        Args:
            workflow_dicts: List of workflow dicts
            config: Renderer configuration (config.combine determines behavior)

        Returns:
            RenderResult with:
            - Single str/bytes if config.combine=True
            - Dict of filename → content if config.combine=False
        """
        ...


__all__ = ["Renderer", "RenderResult"]
