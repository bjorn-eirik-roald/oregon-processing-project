# -*- coding: utf-8 -*-
"""
Tee Stream - Duplicates output to both stdout and a log file.

Similar to Unix 'tee' command: redirects all prints to both console and file.
"""

import sys
from pathlib import Path


class TeeStream:
    """
    A file-like object that writes to both stdout and a log file simultaneously.

    All prints are duplicated to both the terminal and a log file without
    requiring any changes to existing print statements.
    """

    def __init__(self, log_file_path: Path):
        """
        Initialize TeeStream.

        Parameters
        ----------
        log_file_path : Path
            Path to the log file where output will be written.
        """
        self.terminal = sys.stdout
        self.log_file = open(log_file_path, 'w', encoding='utf-8')

    def write(self, message):
        """Write message to both terminal and log file."""
        self.terminal.write(message)
        self.log_file.write(message)
        self.flush()

    def flush(self):
        """Flush both output streams."""
        self.terminal.flush()
        self.log_file.flush()

    def isatty(self):
        """Check if stream is a tty (for compatibility)."""
        return self.terminal.isatty()

    def close(self):
        """Close the log file."""
        if self.log_file:
            self.log_file.close()

    def __enter__(self):
        """Enter context manager; redirect stdout to this stream."""
        self.old_stdout = sys.stdout
        sys.stdout = self
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager; restore original stdout and close log file."""
        sys.stdout = self.old_stdout
        self.close()
        return False
