"""Logging configuration for xaml-parser.

This module provides centralized logging configuration with:
- Time-based log rotation (daily at midnight, 7-day retention)
- Size-based log rotation (10MB limit, 10 backup files)
- Console output (ERROR+ to stderr, optional --verbose for all levels)
- Configuration via CLI args, environment variables, and config file

Zero dependencies - uses only Python stdlib.
"""

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

    Example:
        >>> setup_logging(log_level="DEBUG", verbose=True)
        >>> logger = logging.getLogger("xaml_parser.parser")
        >>> logger.info("Parsing started")
    """
    # Override with config file settings if provided
    if config_dict:
        log_level = config_dict.get("level", log_level)
        log_dir_str = config_dict.get("log_dir")
        if log_dir_str:
            log_dir = Path(log_dir_str).expanduser()
        enable_file_logging = config_dict.get("enable_file_logging", enable_file_logging)

    # Check environment variables (highest priority)
    env_level = os.getenv("XAML_PARSER_LOG_LEVEL")
    if env_level:
        log_level = env_level.upper()

    env_log_dir = os.getenv("XAML_PARSER_LOG_DIR")
    if env_log_dir:
        log_dir = Path(env_log_dir).expanduser()

    # Set default log directory
    if log_dir is None:
        log_dir = Path.home() / ".xaml-parser" / "logs"

    # Create log directory
    if enable_file_logging:
        log_dir.mkdir(parents=True, exist_ok=True)

    # Get root logger for xaml_parser package
    root_logger = logging.getLogger("xaml_parser")
    root_logger.setLevel(getattr(logging, log_level))

    # Clear any existing handlers (important for testing)
    root_logger.handlers.clear()

    # Prevent propagation to Python root logger (avoid duplicate messages)
    root_logger.propagate = False

    # File format (detailed for debugging)
    file_formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s:%(funcName)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console format (simpler for readability)
    console_formatter = logging.Formatter(fmt="[%(levelname)s] %(name)s - %(message)s")

    # Add file handlers if enabled
    if enable_file_logging:
        # Time-based rotation (daily at midnight, keep 7 days)
        time_handler = logging.handlers.TimedRotatingFileHandler(
            filename=log_dir / "xaml_parser.log",
            when="midnight",
            interval=1,
            backupCount=7,
            encoding="utf-8",
        )
        time_handler.setLevel(logging.DEBUG)
        time_handler.setFormatter(file_formatter)
        root_logger.addHandler(time_handler)

        # Size-based rotation (10MB safety net, keep 10 backups)
        size_handler = logging.handlers.RotatingFileHandler(
            filename=log_dir / "xaml_parser_size.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=10,
            encoding="utf-8",
        )
        size_handler.setLevel(logging.DEBUG)
        size_handler.setFormatter(file_formatter)
        root_logger.addHandler(size_handler)

    # Add console handler if verbose (all levels to stderr)
    if verbose:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

    # Always add error handler (ERROR+ to stderr, even without --verbose)
    error_handler = logging.StreamHandler(sys.stderr)
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(console_formatter)
    root_logger.addHandler(error_handler)

    # Log initial configuration message
    root_logger.debug(
        "Logging configured: level=%s, log_dir=%s, file_logging=%s, verbose=%s",
        log_level,
        log_dir if enable_file_logging else "disabled",
        enable_file_logging,
        verbose,
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific module.

    Args:
        name: Module name (typically __name__)

    Returns:
        Logger instance for the specified module

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Module initialized")
    """
    return logging.getLogger(name)
