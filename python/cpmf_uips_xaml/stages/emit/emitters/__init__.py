"""Emitter base classes and configuration."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ....shared.model.dto import WorkflowDto
from ....config.models import EmitterConfig

__all__ = ["Emitter", "EmitResult", "EmitterConfig"]


@dataclass
class EmitResult:
    """Result of an emit operation."""

    success: bool
    files_written: list[Path]
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class Emitter(ABC):
    """Base emitter protocol.

    All emitters must implement:
    - name: unique identifier
    - output_extension: file extension (e.g., ".json", ".md")
    - emit(): core emission logic
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique emitter identifier."""
        ...

    @property
    @abstractmethod
    def output_extension(self) -> str:
        """Output file extension (e.g., '.json', '.md')."""
        ...

    @abstractmethod
    def emit(
        self,
        workflows: list[WorkflowDto],
        output_dir: Path,
        config: EmitterConfig,
    ) -> EmitResult:
        """Emit workflows to output directory.

        Args:
            workflows: Workflows to emit
            output_dir: Target directory
            config: Emitter configuration

        Returns:
            EmitResult with success status and files written
        """
        ...
