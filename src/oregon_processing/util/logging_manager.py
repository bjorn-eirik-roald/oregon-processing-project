# -*- coding: utf-8 -*-
"""
Logging Manager for Oregon RFID processing
"""

import sys
import logging
from pathlib import Path
from datetime import datetime


class LoggingManager:
    """Manages logging configuration with console and file output."""

    def __init__(self, log_name: str, log_dir: Path = None):
        """
        Initialize the LoggingManager.

        Parameters
        ----------
        log_name : str
            Name for the log file (without extension)
        log_dir : Path, optional
            Directory where log files will be written. If None, uses a temporary location
            until set_log_directory is called.
        """
        self._log_name = log_name
        self._log_dir = log_dir
        self._file_handler = None
        self._console_handler = None
        self._logger = None
        self._temp_log_path = None

    def __enter__(self):
        """Enter context manager."""
        self._setup_logging()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        self._cleanup_logging()

    def _setup_logging(self):
        """Configure logging with console and file handlers."""
        # Create custom formatter with process name support
        class ProcessFormatter(logging.Formatter):
            def format(self, record):
                # Use process_name from extra if provided, otherwise use logger name
                process = getattr(record, 'process_name', record.name)
                record.process_display = process
                return super().format(record)

        formatter = ProcessFormatter('%(levelname)s[%(process_display)s]: %(message)s')

        # Console handler
        self._console_handler = logging.StreamHandler(sys.stdout)
        self._console_handler.setFormatter(formatter)
        self._console_handler.setLevel(logging.INFO)

        # File handler
        if self._log_dir:
            log_path = self._get_log_path(self._log_dir)
        else:
            # Use temporary location
            self._temp_log_path = Path.cwd() / f"{self._log_name}_temp.log"
            log_path = self._temp_log_path

        self._file_handler = logging.FileHandler(log_path, mode='a', encoding='utf-8')
        self._file_handler.setFormatter(formatter)
        self._file_handler.setLevel(logging.DEBUG)

        # Configure logger
        self._logger = logging.getLogger('oregon_processing')
        self._logger.setLevel(logging.DEBUG)
        self._logger.addHandler(self._console_handler)
        self._logger.addHandler(self._file_handler)

        # Prevent propagation to root logger to avoid duplicate output
        self._logger.propagate = False

    def _get_log_path(self, log_dir: Path) -> Path:
        """
        Generate log file path with timestamp.

        Parameters
        ----------
        log_dir : Path
            Directory for log file

        Returns
        -------
        Path
            Full path to log file
        """
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"{self._log_name}_{timestamp}.log"
        return log_dir / log_filename

    def set_log_directory(self, log_dir: Path):
        """
        Set or update the log directory, moving from temp location if needed.

        Parameters
        ----------
        log_dir : Path
            New directory for log files
        """
        if not self._file_handler:
            return

        # Create new file handler with final location
        new_log_path = self._get_log_path(log_dir)

        # If we were using a temp file, copy its contents
        if self._temp_log_path and self._temp_log_path.exists():
            with open(self._temp_log_path, 'r', encoding='utf-8') as temp_file:
                temp_contents = temp_file.read()

            # Write temp contents to new file
            with open(new_log_path, 'a', encoding='utf-8') as new_file:
                new_file.write(temp_contents)

            # Remove old temp file
            self._temp_log_path.unlink()
            self._temp_log_path = None

        # Remove old file handler
        self._logger.removeHandler(self._file_handler)
        self._file_handler.close()

        # Create and add new file handler
        formatter = self._file_handler.formatter
        self._file_handler = logging.FileHandler(new_log_path, mode='a', encoding='utf-8')
        self._file_handler.setFormatter(formatter)
        self._file_handler.setLevel(logging.DEBUG)
        self._logger.addHandler(self._file_handler)

        self._log_dir = log_dir

    def get_logger(self, name: str = None) -> logging.Logger:
        """
        Get a logger instance.

        Parameters
        ----------
        name : str, optional
            Logger name. If None, returns the root oregon_processing logger.

        Returns
        -------
        logging.Logger
            Logger instance
        """
        if name:
            return logging.getLogger(f'oregon_processing.{name}')
        return self._logger

    def _cleanup_logging(self):
        """Clean up logging handlers."""
        if self._logger:
            if self._console_handler:
                self._logger.removeHandler(self._console_handler)
                self._console_handler.close()
            if self._file_handler:
                self._logger.removeHandler(self._file_handler)
                self._file_handler.close()

        # Clean up temp file if it still exists
        if self._temp_log_path and self._temp_log_path.exists():
            self._temp_log_path.unlink()
