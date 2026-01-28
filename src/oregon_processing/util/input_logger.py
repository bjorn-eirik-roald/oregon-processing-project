# -*- coding: utf-8 -*-
"""
Input Logger - Captures user input() and writes it to a log file.

Wraps builtins.input so typed values are written to the log file while
preserving normal prompt behavior.
"""

import builtins


class InputLogger:
    """Context manager that logs user input() values to a file-like object."""

    def __init__(self, log_file):
        self._log_file = log_file
        self._original_input = None

    def __enter__(self):
        self._original_input = builtins.input

        def _logged_input(prompt=""):
            user_input = self._original_input(prompt)
            try:
                if self._log_file:
                    self._log_file.write(f"{user_input}\n")
                    self._log_file.flush()
            except Exception:
                pass
            return user_input

        builtins.input = _logged_input
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._original_input is not None:
            builtins.input = self._original_input
            self._original_input = None
        return False
