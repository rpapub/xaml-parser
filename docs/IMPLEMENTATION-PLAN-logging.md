# Logging Implementation Plan for xaml-parser

## Overview
Implement Python best-practice logging with rotating log files and sensible stdout output, using only Python stdlib to maintain zero-dependency philosophy.

## Goals
1. **File logging**: Rotating logs by day OR 10MB (whichever comes first)
2. **Console logging**: INFO+ to stdout, ERROR+ to stderr
3. **Configurable**: Via CLI args, environment variables, and config file
4. **Zero dependencies**: Use only Python stdlib
5. **Non-invasive**: Preserve existing user-facing output, add diagnostic logging

## Architecture

### 1. New Module: `xaml_parser/logging_config.py`
Central logging configuration with:
- `setup_logging()` - Initialize all handlers and formatters
- `get_logger()` - Get module-specific logger
- Log directory management (default: `~/.xaml-parser/logs/`)
- Support for both time-based (daily) AND size-based (10MB) rotation

### 2. Handler Strategy
**Three handlers:**
1. **TimedRotatingFileHandler** - Daily rotation (midnight), keep 7 days
2. **RotatingFileHandler** - 10MB limit, 10 backup files (safety net)
3. **StreamHandler** - Console output (INFO+ to stdout via print, keep current UX)

**Key insight**: We'll use BOTH time and size handlers writing to different files, then merge them for analysis if needed.

### 3. Log Format Design
**File logs** (detailed for debugging):
```
2025-10-12 23:45:12,345 [INFO] parser:parse_file:127 - Parsing workflow.xaml (size: 45KB)
```

**Console** (minimal, preserve UX):
- Current `print()` statements stay as-is for user output
- Add optional `--verbose` logging to stderr for diagnostics
- ERROR+ always goes to stderr

### 4. Logger Hierarchy
```python
xaml_parser              # Root logger (WARNING)
├── xaml_parser.parser   # DEBUG
├── xaml_parser.extractors  # DEBUG
├── xaml_parser.cli      # INFO
├── xaml_parser.project  # DEBUG
└── ...
```

## Implementation Steps

### Step 1: Create `xaml_parser/logging_config.py`
```python
import logging
import logging.handlers
from pathlib import Path
import os

def setup_logging(
    log_level: str = "INFO",
    log_dir: Path | None = None,
    enable_file_logging: bool = True,
    verbose: bool = False
) -> None:
    """Configure application-wide logging."""
    # Creates log directory, handlers, formatters
    # Sets up both time and size rotation
    # Configures console output based on verbose flag
```

### Step 2: Update `xaml_parser/__init__.py`
- Add lazy logging initialization
- Export logging config functions

### Step 3: Add CLI Arguments in `cli.py`
```python
parser.add_argument("--verbose", "-v", action="store_true")
parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
parser.add_argument("--log-dir", type=Path, help="Log file directory")
parser.add_argument("--no-log-file", action="store_true", help="Disable file logging")
```

### Step 4: Add Logging to Key Modules
**Priority modules:**
- `parser.py` - File parsing start/end, errors, timing
- `project.py` - Project discovery, workflow counts
- `extractors.py` - Extraction progress, element counts
- `cli.py` - Command execution, argument validation
- `normalization.py` - DTO generation, ID assignment

### Step 5: Environment Variable Support
```python
# Check environment for config
LOG_LEVEL = os.getenv("XAML_PARSER_LOG_LEVEL", "INFO")
LOG_DIR = os.getenv("XAML_PARSER_LOG_DIR", "~/.xaml-parser/logs")
```

### Step 6: Config File Integration
Update `.xaml-parser.json` support:
```json
{
  "logging": {
    "level": "INFO",
    "log_dir": "~/.xaml-parser/logs",
    "enable_file_logging": true,
    "max_file_size_mb": 10,
    "keep_days": 7
  }
}
```

### Step 7: Testing
Create `tests/unit/test_logging.py`:
- Test handler configuration
- Test log rotation behavior
- Test log level filtering
- Test concurrent logging (thread-safe)
- Mock-based tests (don't create actual log files in tests)

## Key Design Decisions

### 1. Dual Rotation Strategy
```python
# Daily rotation
time_handler = TimedRotatingFileHandler(
    filename=log_dir / "xaml_parser.log",
    when="midnight",
    interval=1,
    backupCount=7
)

# Size-based safety net
size_handler = RotatingFileHandler(
    filename=log_dir / "xaml_parser_size.log",
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=10
)
```

### 2. User Output vs Logging
- **Keep**: All existing `print()` for user-facing output (results, summaries)
- **Add**: Logger calls for diagnostics/debugging
- **Stderr**: Use for errors and --verbose diagnostics

### 3. Log Directory Structure
```
~/.xaml-parser/logs/
├── xaml_parser.log              # Current daily log
├── xaml_parser.log.2025-10-11   # Previous day
├── xaml_parser.log.2025-10-10
├── xaml_parser_size.log         # Current size-based log
├── xaml_parser_size.log.1       # Rollover backup
└── xaml_parser_size.log.2
```

### 4. Performance Considerations
- Use lazy formatting: `logger.debug("Found %d activities", count)` not f-strings
- Guard expensive operations: `if logger.isEnabledFor(logging.DEBUG):`
- Disable file logging in performance-critical scenarios with `--no-log-file`

## What Gets Logged

### DEBUG Level
- XML element processing
- Extractor details (each argument/variable found)
- ID generation
- Namespace resolution

### INFO Level
- File/project parsing started/completed
- Workflow counts and statistics
- Phase transitions (parsing → extraction → normalization)
- Performance metrics

### WARNING Level
- Unknown activity types
- Missing expected attributes
- Fallback to defaults
- Deprecation notices

### ERROR Level
- Parse failures
- File not found
- Invalid configuration
- Unexpected exceptions (with full traceback to file)

## Files to Modify

1. **New**: `xaml_parser/logging_config.py` (~200 lines)
2. **Update**: `xaml_parser/__init__.py` (add imports, setup call)
3. **Update**: `xaml_parser/cli.py` (add args, call setup_logging())
4. **Update**: `xaml_parser/parser.py` (add logger, log parse events)
5. **Update**: `xaml_parser/extractors.py` (add logger, log extraction)
6. **Update**: `xaml_parser/project.py` (add logger, log project ops)
7. **Update**: `xaml_parser/normalization.py` (add logger)
8. **New**: `tests/unit/test_logging.py` (~150 lines)
9. **Update**: `README.md` (document logging configuration)

## Migration Strategy

### Phase 1: Foundation (Steps 1-3)
- Create logging_config.py
- Add CLI arguments
- Basic setup, no disruption to current behavior

### Phase 2: Instrumentation (Step 4)
- Add loggers to modules one by one
- Start with parser.py (most critical)
- Verify no regression in tests

### Phase 3: Configuration (Steps 5-6)
- Environment variable support
- Config file integration
- Default behavior testing

### Phase 4: Testing & Documentation (Step 7)
- Unit tests for logging
- Update README with examples
- Document log format and location

## Backward Compatibility
- **Default**: File logging enabled, INFO level, user sees same output
- **Opt-in verbosity**: `--verbose` shows diagnostic logs to stderr
- **No breakage**: Existing print() output unchanged
- **Config optional**: Works without .xaml-parser.json

## Example Usage

```bash
# Default (file logging, INFO level, same UX)
xaml-parser workflow.xaml

# Verbose diagnostics to stderr
xaml-parser workflow.xaml --verbose

# Custom log level and directory
xaml-parser workflow.xaml --log-level DEBUG --log-dir ./logs

# Disable file logging (performance mode)
xaml-parser workflow.xaml --no-log-file

# Environment variable control
export XAML_PARSER_LOG_LEVEL=DEBUG
xaml-parser workflow.xaml
```

## Success Criteria
- ✅ Logs rotate by day (midnight) with 7-day retention
- ✅ Logs rotate by size (10MB) with 10-file retention
- ✅ No dependencies added (stdlib only)
- ✅ User-facing output unchanged
- ✅ All tests pass
- ✅ Type checking passes (mypy)
- ✅ Configurable via CLI, env vars, config file
- ✅ Thread-safe logging (concurrent workflow parsing)

## Code Examples

### Example 1: Basic Logger Usage in Modules
```python
# In xaml_parser/parser.py
import logging

logger = logging.getLogger(__name__)

class XamlParser:
    def parse_file(self, file_path: Path) -> ParseResult:
        logger.info("Parsing file: %s (size: %d bytes)", file_path, file_path.stat().st_size)

        try:
            content = file_path.read_text(encoding="utf-8")
            logger.debug("Read %d characters from %s", len(content), file_path)

            result = self.parse_content(content, str(file_path))

            if result.success:
                logger.info("Successfully parsed %s: %d activities, %d arguments",
                           file_path.name, len(result.content.activities),
                           len(result.content.arguments))
            else:
                logger.error("Failed to parse %s: %s", file_path, ", ".join(result.errors))

            return result

        except Exception as e:
            logger.exception("Unexpected error parsing %s", file_path)
            raise
```

### Example 2: Logging Configuration Module
```python
# xaml_parser/logging_config.py
import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Any

def setup_logging(
    log_level: str = "INFO",
    log_dir: Path | None = None,
    enable_file_logging: bool = True,
    verbose: bool = False,
    config_dict: dict[str, Any] | None = None,
) -> None:
    """Configure application-wide logging.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files (default: ~/.xaml-parser/logs)
        enable_file_logging: Whether to write logs to files
        verbose: Enable verbose console output to stderr
        config_dict: Optional logging config from .xaml-parser.json
    """
    # Override with config file settings if provided
    if config_dict:
        log_level = config_dict.get("level", log_level)
        log_dir_str = config_dict.get("log_dir")
        if log_dir_str:
            log_dir = Path(log_dir_str).expanduser()
        enable_file_logging = config_dict.get("enable_file_logging", enable_file_logging)

    # Check environment variables
    env_level = os.getenv("XAML_PARSER_LOG_LEVEL")
    if env_level:
        log_level = env_level

    env_log_dir = os.getenv("XAML_PARSER_LOG_DIR")
    if env_log_dir:
        log_dir = Path(env_log_dir).expanduser()

    # Set default log directory
    if log_dir is None:
        log_dir = Path.home() / ".xaml-parser" / "logs"

    # Create log directory
    if enable_file_logging:
        log_dir.mkdir(parents=True, exist_ok=True)

    # Get root logger
    root_logger = logging.getLogger("xaml_parser")
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Clear any existing handlers
    root_logger.handlers.clear()

    # File format (detailed)
    file_formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s:%(funcName)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console format (simpler)
    console_formatter = logging.Formatter(
        fmt="[%(levelname)s] %(name)s - %(message)s"
    )

    # Add file handlers if enabled
    if enable_file_logging:
        # Time-based rotation (daily at midnight)
        time_handler = logging.handlers.TimedRotatingFileHandler(
            filename=log_dir / "xaml_parser.log",
            when="midnight",
            interval=1,
            backupCount=7,
            encoding="utf-8"
        )
        time_handler.setLevel(logging.DEBUG)
        time_handler.setFormatter(file_formatter)
        root_logger.addHandler(time_handler)

        # Size-based rotation (10MB safety net)
        size_handler = logging.handlers.RotatingFileHandler(
            filename=log_dir / "xaml_parser_size.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=10,
            encoding="utf-8"
        )
        size_handler.setLevel(logging.DEBUG)
        size_handler.setFormatter(file_formatter)
        root_logger.addHandler(size_handler)

    # Add console handler if verbose
    if verbose:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

    # Add error handler (always to stderr)
    error_handler = logging.StreamHandler(sys.stderr)
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(console_formatter)
    root_logger.addHandler(error_handler)

    # Log initial message
    root_logger.debug("Logging configured: level=%s, log_dir=%s, file_logging=%s",
                     log_level, log_dir if enable_file_logging else "disabled",
                     enable_file_logging)


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific module.

    Args:
        name: Module name (usually __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
```

### Example 3: CLI Integration
```python
# In xaml_parser/cli.py main() function

def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(...)

    # Add logging arguments
    logging_group = parser.add_argument_group("logging options")
    logging_group.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose diagnostic logging to stderr"
    )
    logging_group.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set logging level (default: INFO, or from config/env)"
    )
    logging_group.add_argument(
        "--log-dir",
        type=Path,
        help="Directory for log files (default: ~/.xaml-parser/logs)"
    )
    logging_group.add_argument(
        "--no-log-file",
        action="store_true",
        help="Disable file logging (performance mode)"
    )

    args = parser.parse_args()

    # Load config file if it exists
    from .provenance import load_config
    config_file = load_config()
    logging_config = config_file.get("logging", {}) if config_file else {}

    # Setup logging
    from .logging_config import setup_logging
    setup_logging(
        log_level=args.log_level or logging_config.get("level", "INFO"),
        log_dir=args.log_dir,
        enable_file_logging=not args.no_log_file,
        verbose=args.verbose,
        config_dict=logging_config
    )

    # Rest of CLI logic...
```

## Implementation Notes

### Thread Safety
Python's logging module is thread-safe by default. The handlers use locks internally to prevent race conditions during concurrent writes. This is important for:
- Parsing multiple files in parallel
- Concurrent project workflow parsing
- Background tasks

### Performance Impact
Expected performance impact:
- **File logging**: ~1-5ms per log call (buffered I/O)
- **Console logging**: ~0.1-1ms per log call
- **Total overhead**: <1% for typical workloads (INFO level)
- **Debug level**: 5-10% overhead (many more log calls)

Mitigation strategies:
- Use `--no-log-file` for performance-critical batch operations
- Use lazy formatting with `%` style instead of f-strings
- Guard expensive computations with `if logger.isEnabledFor(logging.DEBUG)`

### Log Rotation Details
**Daily rotation:**
- Rotates at midnight (local time)
- Keeps 7 days of logs
- Naming: `xaml_parser.log.2025-10-11`

**Size rotation:**
- Rotates when file reaches 10MB
- Keeps 10 backup files (total: 110MB max)
- Naming: `xaml_parser_size.log.1`, `.2`, etc.

**Why both?**
- Time-based: Good for regular auditing and debugging recent issues
- Size-based: Safety net for verbose logging or high-volume operations
- Analysis: Can merge logs by timestamp if needed

### Testing Strategy
```python
# tests/unit/test_logging.py
import logging
import tempfile
from pathlib import Path
from unittest.mock import patch

def test_setup_logging_creates_log_directory(tmp_path):
    """Test that setup_logging creates log directory."""
    log_dir = tmp_path / "logs"
    setup_logging(log_dir=log_dir)
    assert log_dir.exists()
    assert log_dir.is_dir()

def test_logging_levels_filter_correctly(tmp_path):
    """Test that log levels filter messages correctly."""
    log_dir = tmp_path / "logs"
    setup_logging(log_level="WARNING", log_dir=log_dir)

    logger = get_logger("xaml_parser.test")
    logger.debug("debug message")  # Should not appear
    logger.info("info message")    # Should not appear
    logger.warning("warning message")  # Should appear

    log_file = log_dir / "xaml_parser.log"
    content = log_file.read_text()
    assert "warning message" in content
    assert "debug message" not in content
    assert "info message" not in content

def test_log_rotation_by_size(tmp_path):
    """Test that size-based rotation works."""
    log_dir = tmp_path / "logs"

    # Create handler with small max size for testing
    handler = RotatingFileHandler(
        filename=log_dir / "test.log",
        maxBytes=1024,  # 1KB for testing
        backupCount=3
    )

    logger = logging.getLogger("test_rotation")
    logger.addHandler(handler)

    # Write enough data to trigger rotation
    for i in range(100):
        logger.info("Test message number %d with some padding text", i)

    # Check that backup files were created
    assert (log_dir / "test.log.1").exists()
```

## Rollout Plan

### Week 1: Foundation
- [ ] Create `logging_config.py` module
- [ ] Add CLI arguments
- [ ] Write unit tests for logging setup
- [ ] Verify no disruption to existing tests

### Week 2: Instrumentation
- [ ] Add logging to `parser.py`
- [ ] Add logging to `extractors.py`
- [ ] Add logging to `project.py`
- [ ] Verify log output is useful and not excessive

### Week 3: Configuration & Testing
- [ ] Add environment variable support
- [ ] Add config file integration
- [ ] Write integration tests
- [ ] Performance testing with --no-log-file

### Week 4: Documentation & Polish
- [ ] Update README.md
- [ ] Add troubleshooting guide
- [ ] Review log messages for clarity
- [ ] Final testing and validation

## Future Enhancements (Out of Scope)
- Structured logging (JSON format for machine parsing)
- Log aggregation (send logs to external service)
- Async logging handlers (for very high-volume scenarios)
- Per-file log level configuration
- Log viewer CLI tool (`xaml-parser logs --tail --follow`)
