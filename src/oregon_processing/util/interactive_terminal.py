# -*- coding: utf-8 -*-
"""
Interactive Terminal for Oregon RFID Device

Provides a command-line interface for sending commands to the Oregon device
and receiving responses.
"""

# Support for history of readline on Windows via pyreadline3
try:
    import readline  # Linux / macOS
except ImportError:
    import pyreadline3 as readline  # Windows

class InteractiveTerminal:
    """Interactive terminal for sending commands to Oregon RFID device."""

    def __init__(self, communicator):
        """
        Initialize the interactive terminal.

        Parameters
        ----------
        communicator : OregonCommunicator
            OregonCommunicator instance for device communication.
        """
        self._communicator = communicator

    def run(self):
        """
        Start the interactive terminal session.

        Allows user to enter commands, validates them, sends them to the device,
        and displays responses. Type 'exit' or 'quit' to exit the terminal.
        """
        print("\nEntering interactive terminal. Type 'exit' to quit.")

        try:
            while True:
                prompt = f"\n{self._communicator.prompt_signature or ''}>> "
                cmd = input(prompt).strip()
                if not cmd:
                    continue

                # Exit on 'exit' or 'quit'
                if cmd.lower() in ("exit", "quit"):
                    print("Exiting terminal.")
                    break

                # Validate command format
                if not self._communicator._command_manager.validate_command(cmd):
                    print("Invalid command. Use a two-letter code followed by a space (e.g., 'SY ').")
                    print(f"Valid codes: {sorted(self._communicator._command_manager.VALID_MAIN_COMMANDS)}")
                    continue

                # send command and get cleaned response
                lines = self._communicator.send_command(cmd)
                if lines:
                    print("\n".join(lines))
                else:
                    print("Command received without error")

        except KeyboardInterrupt:
            print("\nTerminal interrupted by user.")
