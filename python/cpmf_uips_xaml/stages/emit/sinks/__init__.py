"""I/O sinks for writing rendered content."""

from .base import Sink, SinkResult
from .file_sink import FileSink
from .stdout_sink import StdoutSink

__all__ = [
    "Sink",
    "SinkResult",
    "FileSink",
    "StdoutSink",
]
