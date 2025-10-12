"""JSON emitter for workflow DTOs.

This module provides JSON output with support for:
- Combined mode (single file with all workflows)
- Per-workflow mode (one file per workflow)
- Field profile filtering
- Pretty printing
- None value exclusion

Design: ADR-DTO-DESIGN.md (JSON Emitter)
"""

import dataclasses
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..dto import WorkflowCollectionDto, WorkflowDto
from ..field_profiles import apply_profile_recursive
from . import EmitResult, Emitter, EmitterConfig


class JsonEmitter(Emitter):
    """JSON emitter for workflow DTOs.

    Emits workflow data in JSON format with configurable options.
    """

    @property
    def name(self) -> str:
        """Emitter name.

        Returns:
            'json'
        """
        return "json"

    @property
    def output_extension(self) -> str:
        """Output file extension.

        Returns:
            '.json'
        """
        return ".json"

    def emit(
        self, workflows: list[WorkflowDto], output_path: Path, config: EmitterConfig
    ) -> EmitResult:
        """Emit JSON output.

        Args:
            workflows: List of WorkflowDto objects to emit
            output_path: Output file path (file if combine=True, directory if combine=False)
            config: Emitter configuration

        Returns:
            EmitResult with success status and files written
        """
        try:
            if config.combine:
                return self._emit_combined(workflows, output_path, config)
            else:
                return self._emit_per_workflow(workflows, output_path, config)
        except Exception as e:
            return EmitResult(
                success=False,
                errors=[f"Failed to emit JSON: {e}"],
            )

    def _emit_combined(
        self, workflows: list[WorkflowDto], output_path: Path, config: EmitterConfig
    ) -> EmitResult:
        """Emit single combined JSON file.

        Args:
            workflows: Workflows to emit
            output_path: Output file path
            config: Emitter configuration

        Returns:
            EmitResult with success status
        """
        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Create collection DTO
        collection = WorkflowCollectionDto(
            schema_id="https://rpax.io/schemas/xaml-workflow-collection.json",
            schema_version="1.0.0",
            collected_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            project_info=None,  # TODO: Pass project info from context
            workflows=workflows,
            issues=[],
        )

        # Convert to dict
        data = self._to_dict(collection, config)

        # Write JSON file
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(
                data,
                f,
                indent=2 if config.pretty else None,
                ensure_ascii=False,
            )

        return EmitResult(
            success=True,
            files_written=[output_path],
        )

    def _emit_per_workflow(
        self, workflows: list[WorkflowDto], output_dir: Path, config: EmitterConfig
    ) -> EmitResult:
        """Emit one JSON file per workflow.

        Args:
            workflows: Workflows to emit
            output_dir: Output directory path
            config: Emitter configuration

        Returns:
            EmitResult with success status and files written
        """
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        files_written = []
        errors = []

        for workflow in workflows:
            try:
                # Generate filename from workflow name
                filename = self._sanitize_filename(workflow.name) + self.output_extension
                file_path = output_dir / filename

                # Convert to dict
                data = self._to_dict(workflow, config)

                # Write JSON file
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(
                        data,
                        f,
                        indent=2 if config.pretty else None,
                        ensure_ascii=False,
                    )

                files_written.append(file_path)

            except Exception as e:
                errors.append(f"Failed to emit {workflow.name}: {e}")

        return EmitResult(
            success=len(errors) == 0,
            files_written=files_written,
            errors=errors,
        )

    def _to_dict(self, dto: Any, config: EmitterConfig) -> dict[str, Any]:
        """Convert DTO to dict with field selection.

        Args:
            dto: DTO object (WorkflowDto or WorkflowCollectionDto)
            config: Emitter configuration

        Returns:
            Dictionary representation with field profile applied
        """
        # Convert to dict
        data = dataclasses.asdict(dto)

        # Apply field profile
        if config.field_profile != "full":
            # Detect DTO type
            if "workflows" in data and "project_info" in data:
                dto_type = "WorkflowCollectionDto"
            else:
                dto_type = "WorkflowDto"

            data = apply_profile_recursive(data, config.field_profile, dto_type)

        # Exclude None values if configured
        if config.exclude_none:
            data = self._exclude_none(data)

        return data

    def _exclude_none(self, data: Any) -> Any:
        """Recursively exclude None values from data.

        Args:
            data: Data to filter

        Returns:
            Filtered data without None values
        """
        if isinstance(data, dict):
            return {
                key: self._exclude_none(value) for key, value in data.items() if value is not None
            }
        elif isinstance(data, list):
            return [self._exclude_none(item) for item in data]
        else:
            return data

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize workflow name for use as filename.

        Args:
            name: Workflow name

        Returns:
            Sanitized filename (without extension)
        """
        # Replace invalid filename characters
        invalid_chars = '<>:"/\\|?*'
        sanitized = name
        for char in invalid_chars:
            sanitized = sanitized.replace(char, "_")

        # Remove leading/trailing whitespace and dots
        sanitized = sanitized.strip(". ")

        # Limit length to avoid filesystem issues
        max_length = 200
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]

        return sanitized or "Untitled"


__all__ = ["JsonEmitter"]
