"""Tests for logging configuration."""

import logging

from xaml_parser.logging_config import setup_logging


def test_setup_logging_default(tmp_path):
    """Test setup_logging with default configuration."""
    log_dir = tmp_path / "logs"

    setup_logging(log_dir=log_dir)

    # Check log directory created
    assert log_dir.exists()
    assert log_dir.is_dir()

    # Check log files created
    assert (log_dir / "xaml_parser.log").exists()
    assert (log_dir / "xaml_parser_size.log").exists()


def test_setup_logging_no_file_logging(tmp_path):
    """Test setup_logging with file logging disabled."""
    log_dir = tmp_path / "logs"

    setup_logging(log_dir=log_dir, enable_file_logging=False)

    # Check log directory NOT created when file logging is disabled
    assert not log_dir.exists()


def test_setup_logging_levels(tmp_path):
    """Test that log levels are set correctly."""
    log_dir = tmp_path / "logs"

    # Test DEBUG level
    setup_logging(log_level="DEBUG", log_dir=log_dir)
    root_logger = logging.getLogger("xaml_parser")
    assert root_logger.level == logging.DEBUG

    # Test WARNING level
    setup_logging(log_level="WARNING", log_dir=log_dir)
    root_logger = logging.getLogger("xaml_parser")
    assert root_logger.level == logging.WARNING


def test_logging_writes_to_file(tmp_path):
    """Test that logging actually writes to files."""
    log_dir = tmp_path / "logs"

    setup_logging(log_level="INFO", log_dir=log_dir)

    # Get logger and write test message
    logger = logging.getLogger("xaml_parser.test")
    logger.info("Test message")

    # Check file contains message
    log_file = log_dir / "xaml_parser.log"
    content = log_file.read_text()
    assert "Test message" in content


def test_logging_level_filtering(tmp_path):
    """Test that log levels filter messages correctly."""
    log_dir = tmp_path / "logs"

    setup_logging(log_level="WARNING", log_dir=log_dir)

    logger = logging.getLogger("xaml_parser.test")
    logger.debug("debug message")  # Should not appear
    logger.info("info message")  # Should not appear
    logger.warning("warning message")  # Should appear

    log_file = log_dir / "xaml_parser.log"
    content = log_file.read_text()

    assert "warning message" in content
    assert "debug message" not in content
    assert "info message" not in content


def test_verbose_console_logging(tmp_path, capfd):
    """Test verbose mode enables console logging."""
    log_dir = tmp_path / "logs"

    setup_logging(log_level="INFO", log_dir=log_dir, verbose=True)

    logger = logging.getLogger("xaml_parser.test")
    logger.info("Test console message")

    # Capture stderr (where console logging goes)
    captured = capfd.readouterr()

    # Check message appears in stderr
    assert "Test console message" in captured.err


def test_error_always_to_stderr(tmp_path, capfd):
    """Test that ERROR messages always go to stderr even without verbose."""
    log_dir = tmp_path / "logs"

    setup_logging(log_level="INFO", log_dir=log_dir, verbose=False)

    logger = logging.getLogger("xaml_parser.test")
    logger.error("Error message")

    # Capture stderr
    captured = capfd.readouterr()

    # Check error appears in stderr even without verbose
    assert "Error message" in captured.err


def test_config_dict_override(tmp_path):
    """Test that config_dict overrides default values."""
    log_dir = tmp_path / "logs"

    config_dict = {"level": "DEBUG", "enable_file_logging": True}

    setup_logging(log_dir=log_dir, config_dict=config_dict)

    root_logger = logging.getLogger("xaml_parser")
    assert root_logger.level == logging.DEBUG
