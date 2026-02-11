# -*- coding: utf-8 -*-
"""
Managed Log Stream - Handles temporary-to-final log file transition.

Manages the lifecycle of a log file that starts as a temporary file and later
transitions to a final location once the proper filename is known.
"""

import logging
import shutil
from pathlib import Path
from contextlib import ExitStack
from datetime import datetime

from oregon_processing.util.tee_stream import TeeStream
from oregon_processing.util.input_logger import InputLogger


class ManagedLogStream:
    """
    A managed logging stream that starts with a temporary file and transitions to a final location.

    This solves the problem of needing to log early output before knowing the final filename
    (e.g., when the filename depends on a serial number obtained during connection).
    """

    def __init__(self, base_filename: str = "export_protocol", crash_logs_dir: Path = None):
        """
        Initialize ManagedLogStream with a temporary file.

        Parameters
        ----------
        base_filename : str
            Base name for the log file (without extension or timestamp).
        crash_logs_dir : Path, optional
            Directory where crash logs should be saved if transition to final never occurs.
            If None, defaults to AppData/Roaming/oregon_communicator/crash_logs
        """
        self._base_filename = base_filename
        self._tee_stream = None
        self._temp_log_path = None
        self._final_log_path = None
        self._input_logger = None
        self._logger = logging.getLogger('oregon_processing.managed_log_stream')

        # Set crash log directory
        if crash_logs_dir is None:
            self._crash_logs_dir = Path.home() / "AppData" / "Roaming" / "oregon_communicator" / "crash_logs"
        else:
            self._crash_logs_dir = crash_logs_dir
        self._crash_logs_dir.mkdir(parents=True, exist_ok=True)

        # Create temp log immediately
        temp_log_filename = f"{base_filename}_temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        self._temp_log_path = Path.home() / "AppData" / "Roaming" / "oregon_communicator" / temp_log_filename
        self._temp_log_path.parent.mkdir(parents=True, exist_ok=True)

    def __enter__(self):
        """Enter context manager; start logging to temporary file."""
        self._exit_stack = ExitStack()

        try:
            self._tee_stream = self._exit_stack.enter_context(TeeStream(self._temp_log_path))

            # Capture user input() values in the log file
            self._input_logger = self._exit_stack.enter_context(InputLogger(self._tee_stream.log_file))
        except Exception:
            self._exit_stack.close()
            raise
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager; close log and move to crash folder if not yet transitioned."""
        # Close the exit stack FIRST to ensure TeeStream and file are closed
        if self._exit_stack:
            self._exit_stack.__exit__(exc_type, exc_val, exc_tb)

        # If we never transitioned to final location, this is a crash - save to crash log folder
        if self._final_log_path is None and self._temp_log_path and self._temp_log_path.exists():
            logging_extra = {'process_name': 'Log Stream'}
            crash_log_filename = f"{self._base_filename}_crash_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            crash_log_path = self._crash_logs_dir / crash_log_filename
            shutil.move(str(self._temp_log_path), str(crash_log_path))
            self._logger.info(f"Log saved to crash log: {crash_log_path}", extra=logging_extra)

        return False

    def temp_to_final(self, final_log_dir: Path):
        """
        Transition from temporary log file to final location.

        This method closes the temporary log, moves it to the final directory,
        and reopens logging to the final file.

        Parameters
        ----------
        final_log_dir : Path
            Directory where the final log file should be placed.
        """
        if self._tee_stream is None:
            raise RuntimeError("ManagedLogStream not yet entered as context manager.")

        # Close *only the current phase*
        self._exit_stack.close()

        final_log_filename = f"{self._base_filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        self._final_log_path = final_log_dir / final_log_filename

        shutil.move(self._temp_log_path, self._final_log_path)

        # Start a NEW scope
        self._exit_stack = ExitStack()
        self._tee_stream = self._exit_stack.enter_context(
            TeeStream(self._final_log_path, mode="a")
        )

    @property
    def final_log_path(self) -> Path:
        """Get the final log file path (None if not yet transitioned)."""
        return self._final_log_path

    @property
    def temp_log_path(self) -> Path:
        """Get the temporary log file path."""
        return self._temp_log_path
