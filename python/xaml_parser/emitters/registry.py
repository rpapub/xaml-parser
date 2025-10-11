"""Emitter registry for plugin discovery and management.

This module provides a registry for discovering and loading emitters,
both built-in and from third-party plugins via entry points.

Design: ADR-DTO-DESIGN.md (Emitter Registry)
"""

from . import Emitter


class EmitterRegistry:
    """Registry for discovering and loading emitters.

    The registry maintains a mapping of emitter names to emitter classes,
    and supports plugin discovery via entry points.
    """

    _emitters: dict[str, type[Emitter]] = {}

    @classmethod
    def register(cls, emitter_class: type[Emitter]) -> None:
        """Register an emitter.

        Args:
            emitter_class: Emitter class to register

        Raises:
            ValueError: If emitter name is already registered
        """
        # Create temporary instance to get name
        instance = emitter_class()
        name = instance.name

        if name in cls._emitters:
            raise ValueError(f"Emitter already registered: {name}")

        cls._emitters[name] = emitter_class

    @classmethod
    def get_emitter(cls, name: str) -> Emitter:
        """Get emitter by name.

        Args:
            name: Emitter name

        Returns:
            Emitter instance

        Raises:
            ValueError: If emitter name is unknown
        """
        if name not in cls._emitters:
            raise ValueError(
                f"Unknown emitter: {name}. " f"Available emitters: {', '.join(cls.list_emitters())}"
            )

        emitter_class = cls._emitters[name]
        return emitter_class()

    @classmethod
    def discover_plugins(cls) -> None:
        """Discover emitters via entry points.

        Loads emitter plugins from the 'xamlparser.emitters' entry point group.
        This allows third-party packages to provide custom emitters.
        """
        try:
            import importlib.metadata

            for entry_point in importlib.metadata.entry_points(group="xamlparser.emitters"):
                try:
                    emitter_class = entry_point.load()
                    cls.register(emitter_class)
                except Exception as e:
                    # Log warning but continue - don't fail if plugin broken
                    print(f"Warning: Failed to load emitter plugin {entry_point.name}: {e}")
        except ImportError:
            # importlib.metadata not available (Python < 3.8)
            pass

    @classmethod
    def list_emitters(cls) -> list[str]:
        """List all registered emitters.

        Returns:
            List of emitter names
        """
        return sorted(cls._emitters.keys())

    @classmethod
    def clear(cls) -> None:
        """Clear all registered emitters.

        Useful for testing.
        """
        cls._emitters.clear()


__all__ = ["EmitterRegistry"]
