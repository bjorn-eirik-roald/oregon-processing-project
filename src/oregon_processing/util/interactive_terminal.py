# -*- coding: utf-8 -*-
"""
Interactive Terminal for Oregon RFID Device

Provides a command-line interface for sending commands to the Oregon device
and receiving responses.
"""

import logging

# Support for history of readline on Windows via pyreadline3
try:
    import readline  # Linux / macOS
except ImportError:
    import pyreadline3 as readline  # Windows

class InteractiveTerminal:
    """Interactive terminal for sending commands to Oregon RFID device."""

    def __init__(self, communicator, command_manager):
        """
        Initialize the interactive terminal.

        Parameters
        ----------
        communicator : Communicator
            Communicator instance for device communication.
        command_manager : CommandManager
            CommandManager instance for sending commands to device.
        """
        self._communicator = communicator
        self._command_manager = command_manager
        self._logger = logging.getLogger('oregon_processing.interactive_terminal')

    def __enter__(self):
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Exit context manager."""
        pass

    def run(self):
        """
        Start the interactive terminal session.

        Allows user to enter commands, validates them, sends them to the device,
        and displays responses. Type 'exit' or 'quit' to exit the terminal.
        """
        logging_extra = {'process_name': 'Interactive Terminal'}

        self._logger.info("Entering interactive terminal. Type 'exit' to quit.", extra=logging_extra)

        try:
            while True:
                prompt = f"\n{self._command_manager.prompt_signature or ''}>> "
                cmd = input(prompt).strip()
                if not cmd:
                    continue

                # Exit on 'exit' or 'quit'
                if cmd.lower() in ("exit", "quit"):
                    self._logger.info("Exiting terminal.", extra=logging_extra)
                    break

                # Validate command format
                if not self._communicator._command_manager.validate_command(cmd):
                    self._logger.warning("Invalid command. Use a two-letter code followed by a space (e.g., 'SY ').", extra=logging_extra)
                    self._logger.info(f"Valid codes: {sorted(self._communicator._command_manager.VALID_MAIN_COMMANDS)}", extra=logging_extra)
                    continue

                # send command and get cleaned response
                lines = self._command_manager.send_command(cmd)
                if lines:
                    self._logger.info("\n".join(lines), extra=logging_extra)
                else:
                    self._logger.info("Command received without error", extra=logging_extra)

        except KeyboardInterrupt:
            self._logger.info("Terminal interrupted by user.", extra=logging_extra)
