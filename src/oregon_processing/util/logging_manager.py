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

    def __init__(self, log_name: str, log_dir: Path = None, temp: bool = False, file_logging: bool = True):
        """
        Initialize the LoggingManager.

        Parameters
        ----------
        log_name : str
            Name for the log file (without extension)
        log_dir : Path, optional
            Directory where log files will be written. If None and file_logging is True,
            uses a temporary location in the current working directory until set_log_directory
            is called. Ignored if file_logging is False.
        temp : bool, optional
            If True, marks the current log location as temporary and schedules it for
            cleanup on exit. Default is False. Note: if log_dir is None, the log is
            always treated as temporary regardless of this parameter. Ignored if file_logging
            is False.
        file_logging : bool, optional
            If True, enables file logging in addition to console logging. If False,
            only console logging is enabled. Default is True.
        """
        self._log_name = log_name
        self._log_dir = log_dir
        self._log_path = None
        self._file_handler = None
        self._console_handler = None
        self._logger = None
        self._is_temp = temp  # Track whether current log file is temporary
        self._file_logging = file_logging  # Track whether file logging is enabled
        self._temp_log_paths = set()  # Track all temporary log files for cleanup

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

        # File handler - only create if file_logging is enabled
        if self._file_logging:
            # File handler - if log_dir is provided, use it; otherwise, use a temp file
            if self._log_dir:
                self._log_path = self._get_log_path(self._log_dir)
            else:
                # Use temporary location in current working directory
                self._log_path = self._get_log_path(Path.cwd())
                # Override: if no log_dir provided, file is always temporary
                self._is_temp = True

            # Track temporary files for cleanup
            if self._is_temp:
                self._temp_log_paths.add(self._log_path)

            self._file_handler = logging.FileHandler(self._log_path, mode='a', encoding='utf-8')
            self._file_handler.setFormatter(formatter)
            self._file_handler.setLevel(logging.DEBUG)

        # Configure logger
        self._logger = logging.getLogger('oregon_processing')
        self._logger.setLevel(logging.DEBUG)
        self._logger.addHandler(self._console_handler)
        if self._file_logging and self._file_handler:
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

    def set_log_directory(self, log_dir: Path, temp: bool = False):
        """
        Set or update the log directory, moving the current log file if needed.

        Transitions the log file from its current location to a new directory,
        preserving all logged content. Supports moving from temporary locations
        to permanent ones or between any two locations.

        Only valid when file_logging is enabled. Does nothing if file_logging
        is False.

        Parameters
        ----------
        log_dir : Path
            New directory for log files. Can be a string or Path object.
        temp : bool, optional
            If True, marks the new log file as temporary for cleanup on exit.
            Default is False.
        """
        if not self._file_logging or not self._file_handler:
            return

        if isinstance(log_dir, str):
            log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)

        # Create new log path - reuse old filename if exists, otherwise generate new
        if self._log_path and self._log_path.exists():
            new_log_path = log_dir / self._log_path.name
        else:
            new_log_path = self._get_log_path(log_dir)

        # Copy contents from old file if it exists
        if self._log_path and self._log_path.exists():
            with open(self._log_path, 'r', encoding='utf-8') as old_file:
                old_contents = old_file.read()

            with open(new_log_path, 'a', encoding='utf-8') as new_file:
                new_file.write(old_contents)

            # If old file was marked as temporary, schedule it for cleanup
            if self._is_temp:
                self._temp_log_paths.add(self._log_path)

        self._log_path = new_log_path

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

        # Track new temp file if applicable
        if temp:
            self._temp_log_paths.add(new_log_path)

        self._is_temp = temp  # Update temp status based on new location

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
        """Clean up logging handlers and temporary log files."""
        if self._logger:
            if self._console_handler:
                self._logger.removeHandler(self._console_handler)
                self._console_handler.close()
            if self._file_handler:
                self._logger.removeHandler(self._file_handler)
                self._file_handler.close()

        # Clean up all temporary files that were ever created
        for temp_path in self._temp_log_paths:
            if temp_path.exists():
                temp_path.unlink()
