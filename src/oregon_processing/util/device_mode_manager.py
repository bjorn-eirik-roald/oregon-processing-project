# -*- coding: utf-8 -*-
"""
Device Mode Manager for Oregon RFID
"""

import logging


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from oregon_processing.util.oregon_communicator import Communicator
    from oregon_processing.util.command_manager import CommandManager


class DeviceModeManager:
    """Manages device operating modes (Standby, Run, Sleep)."""

    def __init__(self, communicator: "Communicator", command_manager: "CommandManager"):
        """
        Initialize DeviceModeManager with communicator and command manager.

        Parameters
        ----------
        communicator : Communicator
            Connected Communicator instance to use for device operations.
        command_manager : CommandManager
            Command manager instance for sending commands to device.
        """
        self._communicator = communicator
        self._command_manager = command_manager
        self._startup_mode = None
        self._logger = logging.getLogger('oregon_processing.device_mode_manager')

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

        logging_extra = {'process_name': 'Device Mode Change'}

        # Map mode names to commands
        mode_commands = {
            'Standby': 'ST',
            'Run': 'ON',
            'Sleep': 'OF'
        }

        if mode_name not in mode_commands:
            self._logger.error(f"Invalid mode: {mode_name}. Valid modes are: Standby, Run, Sleep", extra=logging_extra)
            return False

        if not self._communicator._connection:
            self._logger.error("Not connected to device.", extra=logging_extra)
            return False

        command = mode_commands[mode_name]

        current_mode = self._get_current_mode()
        if current_mode != mode_name:
            self._logger.info(f"Changing device mode from '{current_mode}' to '{mode_name}' (sending {command} command).", extra=logging_extra)
            self._command_manager.send_command(command)
            if self._get_current_mode() == mode_name:
                self._logger.info(f"Device mode change successful.", extra=logging_extra)
            else:
                self._logger.error(f"Device mode change failed! Device is still in '{self._get_current_mode()}' mode.", extra=logging_extra)
                return False

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

        logging_extra = {'process_name': 'Device Mode Change'}

        startup_mode_lower = self._startup_mode.lower()
        target_mode = mode_map.get(startup_mode_lower)

        if target_mode is None:
            self._logger.warning("WARNING: Unknown start-up mode. Reader has been set to Sleep mode to be safe.", extra=logging_extra)
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


