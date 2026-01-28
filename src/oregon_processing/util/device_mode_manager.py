# -*- coding: utf-8 -*-
"""
Device Mode Manager for Oregon RFID
"""

from oregon_processing.util.display_constants import display

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from oregon_processing.util.oregon_communicator import OregonCommunicator
    from oregon_processing.util.command_manager import CommandManager


class DeviceModeManager:
    """Manages device operating modes (Standby, Run, Sleep)."""

    def __init__(self, communicator: "OregonCommunicator", command_manager: "CommandManager"):
        """
        Initialize DeviceModeManager with communicator and command manager.

        Parameters
        ----------
        communicator : OregonCommunicator
            Connected OregonCommunicator instance to use for device operations.
        command_manager : CommandManager
            Command manager instance for sending commands to device.
        """
        self._communicator = communicator
        self._command_manager = command_manager
        self._startup_mode = None

    def __enter__(self):
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager; return to startup mode."""
        self._return_to_startup_mode()

    @property
    def startup_mode(self) -> str:
        """Get the stored startup mode."""
        return self._startup_mode

    @startup_mode.setter
    def startup_mode(self, mode: str):
        """Set the startup mode."""
        self._startup_mode = mode

    def change_mode(self, mode_name: str) -> bool:
        """
        Change the device operating mode.

        Parameters
        ----------
        mode_name : str
            Target mode: "Standby", "Run", or "Sleep"

        Returns
        -------
        bool
            True if mode change successful, False otherwise.
        """
        # Map mode names to commands
        mode_commands = {
            'Standby': 'ST',
            'Run': 'ON',
            'Sleep': 'OF'
        }

        if mode_name not in mode_commands:
            print(f"Invalid mode: {mode_name}. Valid modes are: Standby, Run, Sleep")
            return False

        if not self._communicator._connection:
            print("Not connected to device.")
            return False

        command = mode_commands[mode_name]

        print("\n" + display.SECTION_SEPARATOR * display.SECTION_LINE_LENGTH, flush=True)
        print(f"SETTING DEVICE TO {mode_name.upper()} MODE")
        print(display.SECTION_SEPARATOR * display.SECTION_LINE_LENGTH, flush=True)

        current_mode = self._get_current_mode()
        if current_mode != mode_name:
            print(f"\nDevice is in '{current_mode}' mode.", flush=True)
            print(f"\nSending {command} command to device...", end="", flush=True)
            self._command_manager.send_command(command)
            print(" Done.", flush=True)
            print("Verifying device mode...", end="", flush=True)
            if self._get_current_mode() == mode_name:
                print(f" SUCCESS! Device is now in '{mode_name}' mode.", flush=True)
            else:
                print(f" FAILED! Device is still in '{self._get_current_mode()}' mode.", flush=True)
                return False
        else:
            print(f"\nDevice is already in '{mode_name}' mode.", flush=True)

        print("\n" + display.SECTION_SEPARATOR * display.SECTION_LINE_LENGTH)
        print(f"DEVICE SET TO {mode_name.upper()} MODE")
        print(display.SECTION_SEPARATOR * display.SECTION_LINE_LENGTH)

        return True

    def _return_to_startup_mode(self) -> None:
        """Return the Oregon RFID device to its start-up mode."""
        if not self._communicator._connection:
            return

        if not self._startup_mode:
            return

        # Map startup mode to mode names used by change_mode()
        mode_map = {
            'standby': 'Standby',
            'run': 'Run',
            'sleep': 'Sleep'
        }

        startup_mode_lower = self._startup_mode.lower()
        target_mode = mode_map.get(startup_mode_lower)

        if target_mode is None:
            print("WARNING: Unknown start-up mode. Reader has been set to Sleep mode to be safe.")
            target_mode = 'Sleep'

        self.change_mode(target_mode)

    def _get_current_mode(self) -> str:
        """
        Get the current operating mode from the system status.

        Returns
        -------
        str
            Current mode: "Standby", "Run", or "Sleep"
        """
        status = self._communicator.get_system_status()
        return status.get('mode', 'Unknown')


