"""Pluggable emitter system for XAML parser output.

This module provides a pluggable architecture for emitting parsed workflows
in different formats (JSON, YAML, Mermaid diagrams, Markdown docs).

Design: ADR-DTO-DESIGN.md (Emitter Architecture)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..dto import WorkflowDto


@dataclass
class EmitterConfig:
    """Configuration for emitter.

    Attributes:
        field_profile: Field selection profile (full, minimal, mcp, datalake)
        combine: Single file vs. one-per-workflow
        pretty: Pretty print output
        exclude_none: Exclude None values from output
        extra: Emitter-specific configuration
    """

    field_profile: str = "full"
    combine: bool = False
    pretty: bool = True
    exclude_none: bool = True
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class EmitResult:
    """Result of emission.

    Attributes:
        success: Whether emission succeeded
        files_written: List of files written
        errors: List of error messages
        warnings: List of warning messages
    """

    success: bool
    files_written: list[Path] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class Emitter(ABC):
    """Base class for all emitters.

    Emitters transform WorkflowDto objects into various output formats.
    Each emitter is responsible for:
    - Validating configuration
    - Transforming DTOs to output format
    - Writing output files
    - Reporting success/errors
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Emitter name (e.g., 'json', 'mermaid').

        Returns:
            Emitter name for registration and CLI usage
        """
        pass

    @property
    @abstractmethod
    def output_extension(self) -> str:
        """Output file extension (e.g., '.json', '.mmd').

        Returns:
            File extension including leading dot
        """
        pass

    @abstractmethod
    def emit(
        self, workflows: list[WorkflowDto], output_path: Path, config: EmitterConfig
    ) -> EmitResult:
        """Emit output files.

        Args:
            workflows: List of WorkflowDto objects to emit
            output_path: Output file path (file if combine=True, directory if combine=False)
            config: Emitter configuration

        Returns:
            EmitResult with success status and files written
        """
        pass

    def validate_config(self, config: EmitterConfig) -> list[str]:
        """Validate emitter configuration.

        Args:
            config: Emitter configuration to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        return []  # Base implementation accepts all configs


__all__ = [
    "Emitter",
    "EmitterConfig",
    "EmitResult",
]
