# -*- coding: utf-8 -*-
"""
Logging Manager for Oregon RFID processing
"""

import sys
import logging
import logging.handlers
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
        self._memory_handler = None
        self._logger = None
        self._is_temp = temp  # Track whether current log file is temporary
        self._file_logging = file_logging  # Track whether file logging is enabled
        self._temp_log_paths = set()  # Track all temporary log files for cleanup
        self._console_formatter = None  # Will be initialized in _setup_logging
        self._file_formatter = None  # Will be initialized in _setup_logging

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

        # Console formatter (no timestamp)
        self._console_formatter = ProcessFormatter('%(levelname)s[%(process_display)s]: %(message)s')

        # File formatter (includes date and time)
        self._file_formatter = ProcessFormatter('%(levelname)s[%(asctime)s][%(process_display)s]: %(message)s')
        self._file_formatter.datefmt = '%Y-%m-%d %H:%M:%S'

        # Memory handler (stores WARNING and higher level logs)
        self._memory_handler = logging.handlers.MemoryHandler(capacity=1000, target=None, flushLevel=logging.CRITICAL + 1)
        self._memory_handler.setLevel(logging.WARNING)

        # Console handler
        self._console_handler = logging.StreamHandler(sys.stdout)
        self._console_handler.setFormatter(self._console_formatter)
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
            self._file_handler.setFormatter(self._file_formatter)
            self._file_handler.setLevel(logging.DEBUG)

        # Configure logger
        self._logger = logging.getLogger('oregon_processing')
        self._logger.setLevel(logging.DEBUG)
        self._logger.addHandler(self._console_handler)
        self._logger.addHandler(self._memory_handler)
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

        # Create and add new file handler with stored formatter
        self._file_handler = logging.FileHandler(new_log_path, mode='a', encoding='utf-8')
        self._file_handler.setFormatter(self._file_formatter)
        self._file_handler.setLevel(logging.DEBUG)
        self._logger.addHandler(self._file_handler)

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
        # Display recap of warnings and errors before closing
        if self._memory_handler:
            if self._memory_handler.buffer:
                recap_lines = []
                recap_lines.append("LOG RECAP - Warnings and Errors")

                # Sort records by level (WARNING < ERROR < CRITICAL)
                sorted_records = sorted(self._memory_handler.buffer, key=lambda r: r.levelno)

                for record in sorted_records:
                    level_name = record.levelname
                    process_name = getattr(record, 'process_name', record.name)
                    timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
                    message = record.getMessage()

                    # Format the message with level info and indent all lines
                    formatted_message = f"{level_name}[{timestamp}][{process_name}]: {message}"
                    lines = formatted_message.split("\n")
                    indented_message = f"  • {lines[0]}"
                    if len(lines) > 1:
                        indented_message += "\n" + "\n".join(f"    {line}" for line in lines[1:])
                    recap_lines.append(indented_message)

                recap_text = "\n".join(recap_lines)

                # Log to both file and console via logger
                if self._logger:
                    self._logger.info(recap_text, extra={'process_name': 'Logging Manager'})
            else:
                # No warnings or errors
                recap_message = "LOG RECAP - No warnings or errors detected."

                # Log to both file and console via logger
                if self._logger:
                    self._logger.info(recap_message, extra={'process_name': 'Logging Manager'})

        if self._logger:
            if self._console_handler:
                self._logger.removeHandler(self._console_handler)
                self._console_handler.close()
            if self._memory_handler:
                self._logger.removeHandler(self._memory_handler)
            if self._file_handler:
                self._logger.removeHandler(self._file_handler)
                self._file_handler.close()

        # Clean up temporary files that were replaced/transitioned
        # Keep the current log file as a crash log if it was never moved to final location
        for temp_path in self._temp_log_paths:
            if temp_path.exists() and temp_path != self._log_path:
                temp_path.unlink()
