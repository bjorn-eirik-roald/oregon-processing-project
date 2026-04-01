# -*- coding: utf-8 -*-
"""
Oregon RFID Communicator
"""

from contextlib import ExitStack

from datetime import datetime
from pathlib import Path

from oregon_processing.util.connector import ConnectionResult, Connector
from oregon_processing.util.command_manager import CommandManager
from oregon_processing.util.clock_manager import ClockManager
from oregon_processing.util.device_mode_manager import DeviceModeManager
from oregon_processing.util.interactive_terminal import InteractiveTerminal
from oregon_processing.util.format_manager import FormatManager
from oregon_processing.util.data_exporter import DataExporter
from oregon_processing.util.device_health_checker import DeviceHealthChecker, DeviceHealthReport
from oregon_processing.util.logging_manager import get_logger
from src.oregon_processing.util.exceptions import ConnectionFailedError, UnexpectedResponseError, UnexpectedResponseError
from src.oregon_processing.util.system_status import SystemStatusChecker, SystemStatus
from src.oregon_processing.util.upload_history import UploadHistory



class Communicator:
    """Class to communicate with Oregon device via serial port."""

    def __init__(self):

        self._connection = None

        self._exit_stack = None

        self._command_manager: CommandManager = None
        self._mode_manager: DeviceModeManager = None
        self._system_status_checker: SystemStatusChecker = None
        self._clock_manager: ClockManager = None
        self._format_manager: FormatManager = None
        self._data_exporter: DataExporter = None
        self._health_manager: DeviceHealthChecker = None

        self._last_upload_date = None
        self._reader_name = None
        self._serial_number = None
        self._device_type = None
        self._mode = None

        self._logger = get_logger(__name__)

    def __enter__(self):

        self._exit_stack = ExitStack()

        connection_result = None
        try:
            connector = Connector()
            connection_result: ConnectionResult = connector.connect()

            if connection_result and connection_result.success:
                self._connection = connection_result.connection

                # Command manager needed already in post-connect handshake
                self._command_manager = CommandManager(self)

                self._post_connect_handshake()

                self._mode_manager = self._exit_stack.enter_context(DeviceModeManager(self, self._command_manager))
                self._format_manager = self._exit_stack.enter_context(FormatManager(self, self._command_manager))
                self._data_exporter = DataExporter(self, self._format_manager, self._command_manager)
                self._clock_manager = ClockManager(self, self._command_manager)
                self._health_checker = DeviceHealthChecker(self)
                self._system_status_checker = SystemStatusChecker(self._command_manager)

            else:
                error_message = f"Failed to connect to Oregon device."
                self._logger.error(error_message)
                raise ConnectionFailedError(error_message)

        except ConnectionFailedError as e:
            self._exit_stack.close()
            raise
        except Exception as e:
            self._logger.exception("Failed to initialize Communicator")
            self._exit_stack.close()
            raise

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Ensure all managers and connection are properly cleaned up."""
        if self._exit_stack:
            return self._exit_stack.__exit__(exc_type, exc_value, traceback)
        return False

    @property
    def reader_name(self):
        """Get the reader name if known."""
        if not self._reader_name:
            self._update_reader_name()

        return self._reader_name

    @property
    def serial_number(self):
        """Get the serial number if known."""
        if not self._serial_number:
            self._update_serial_number()

        return self._serial_number

    @property
    def device_type(self):
        """Get the device type from system status."""
        if not self._device_type:
            self._update_device_type()

        return self._device_type

    @property
    def is_connected(self):
        """Check if there is an active connection."""
        return self._connection is not None

    @property
    def prompt_signature(self):
        if not self._command_manager:
            error_message = "Command manager not initialized; cannot retrieve prompt signature."
            self._logger.error(error_message)
            raise RuntimeError(error_message)

        return self._command_manager.prompt_signature

    def get_mode(self):
        """Get the current operating mode from the system status."""
        if not self._mode_manager:
            error_message = "Mode manager not initialized. Cannot retrieve current mode."
            self._logger.error(error_message)
            raise RuntimeError(error_message)

        self._mode =  self._mode_manager.get_current_mode()
        return self._mode

    def change_mode(self, mode_name: str) -> bool:
        """
        Change the device operating mode.

        Delegates to DeviceModeManager.

        Parameters
        ----------
        mode_name : str
            Target mode: "Standby", "Run", or "Sleep"

        Returns
        -------
        bool
            True if mode change successful, False otherwise.
        """


        if not self._mode_manager:
            error_message = "Mode manager not initialized. Cannot change mode."
            self._logger.error(error_message)
            raise RuntimeError(error_message)

        success: bool = self._mode_manager.change_mode(mode_name)
        return success

    def check_device_health(self):
        """
        Check system status and health.

        Delegates to DeviceHealthChecker.check_device_health().
        Returns
        -------
        dict
            Dictionary with 'healthy' (bool) and 'warnings' (list of str) keys.
        """


        if not self._health_checker:
            error_message = "Health checker not initialized. Cannot check device health."
            self._logger.error(error_message)
            raise RuntimeError(error_message)

        health_report: DeviceHealthReport = self._health_checker.check_device_health()
        return health_report

    def start_interactive_terminal(self):
        """
        Start an interactive terminal session for sending commands to the device.

        Opens a command-line interface where commands can be entered, validated,
        sent to the device, and responses displayed. Type 'exit' or 'quit' to exit.
        """


        if not self._connection:
            error_message = "Not connected to device. Cannot start interactive terminal."
            self._logger.error(error_message)
            raise ConnectionError(error_message)

        terminal = InteractiveTerminal(self._command_manager)
        terminal.run()

        self._logger.info("Interactive terminal session ended.")
        self._logger.info("As a safety measure, reconnecting to device to refresh state.")
        self._post_connect_handshake()

    def get_system_status(self) -> SystemStatus:

        if not self._system_status_checker:
            error_message = "System status checker not initialized. Cannot get system status."
            self._logger.error(error_message)
            raise RuntimeError(error_message)

        return self._system_status_checker.get_system_status()

    def get_upload_history(self) -> UploadHistory:
        """
        Parse upload history output from UH command.

        Returns
        -------
        UploadHistory
            Parsed upload history with upload records and metadata.
        """

        if not self._command_manager:
            error_message = "Command manager not initialized. Cannot retrieve upload history."
            self._logger.error(error_message)
            raise RuntimeError(error_message)

        if not self._connection:
            error_message = "Not connected to device. Cannot retrieve upload history."
            self._logger.error(error_message)
            raise ConnectionError(error_message)

        if not self._mode_manager:
            error_message = "Mode manager not initialized. Cannot retrieve upload history."
            self._logger.error(error_message)
            raise RuntimeError(error_message)

        upload_history: UploadHistory = self._mode_manager.get_upload_history()
        return upload_history

    def control_device_datetime(self, tolerance_seconds: int = 15, attempt_sync: bool = True) -> dict:
        """
        Check if device datetime is synchronized with system time and optionally update it.

        Delegates to ClockManager. When device has elapsed time only (not synchronized),
        displays uptime and returns with error. When device has absolute datetime, compares
        with system time and prompts for sync if needed.

        Parameters
        ----------
        tolerance_seconds : int
            Acceptable difference in seconds before device is considered out of sync. Default: 15
        attempt_sync : bool
            If True and out of sync, prompt user to update device time. Default: True

        Returns
        -------
        dict
            Report with keys: synced, device_datetime, elapsed_time, system_datetime,
            difference_seconds, was_updated, update_command_sent, update_response, error
        """
        if not self._connection:
            error_message = f"Not connected to device. Cannot check or control device datetime."
            self._logger.error(error_message)
            raise ConnectionError(error_message)

        return self._clock_manager.control_device_datetime(tolerance_seconds, attempt_sync)

    def export_event_records(self, dates: list, output_dir: Path = Path("")) -> bool:
        """
        Export event records for specified dates.

        Delegates to DataExporter.export_event_records().

        Parameters
        ----------
        dates : list
            List of date objects to export
        output_dir : str or Path
            Directory where output files will be written (default: current directory)

        Returns
        -------
        bool
            True if all exports completed successfully, False if any failed.
        """
        success: bool = self._data_exporter.export_event_records(dates, output_dir)
        return success

    def export_detection_records(self, dates: list, output_dir: Path = Path(""), sep=',') -> bool:
        """
        Export detection records for specified dates.

        Delegates to DataExporter.export_detection_records().

        Parameters
        ----------
        dates : list
            List of date objects to export
        output_dir : str or Path
            Directory where output files will be written (default: current directory)
        sep : str, optional
            Separator to use in the output file (default: ',')

        Returns
        -------
        bool
            True if all exports completed successfully, False if any failed.
        """
        success: bool = self._data_exporter.export_detection_records(dates, output_dir, sep)
        return success

    def _post_connect_handshake(self):
        """Send a quick SY command to verify connection and capture prompt signature. Store reader name and FM format"""

        if not self._connection:
            return



        self._logger.debug("Starting post-connection handshake.")

        self._update_reader_name()
        self._update_device_type()

        self._logger.info(f"Connected to device '{self.reader_name}' of type '{self.device_type}' with serial number '{self.serial_number}'.")

    def _update_reader_name(self) -> str:
        """
        Retrieve the reader name from the device using the SY command.

        Returns
        -------
        str
            The reader name, or None if not set or an error occurs.
        """



        if not self._connection:
            error_message = "Not connected to device. Cannot retrieve reader name."
            self._logger.error(error_message)
            raise ConnectionError(error_message)

        try:
            system_status: SystemStatus = self.get_system_status()
            self._reader_name = system_status.reader_name
            return True

        except Exception as e:
            error_message = f"Error retrieving reader name: {e}"
            self._logger.error(error_message)
            raise RuntimeError(error_message)

    def _update_serial_number(self) -> str:
        """
        Retrieve the serial number from the device using the SY command.

        Returns
        -------
        str
            The serial number, or None if not set or an error occurs.
        """



        if not self._connection:
            error_message = "Not connected to device. Cannot retrieve serial number."
            self._logger.error(error_message)
            raise ConnectionError(error_message)

        try:
            system_status: SystemStatus = self.get_system_status()
            self._serial_number = system_status.serial_number
            return True

        except Exception as e:
            error_message = f"Error retrieving serial number: {e}"
            self._logger.error(error_message)
            raise RuntimeError(error_message)

    def _update_device_type(self) -> str:
        """
        Retrieve the device type from the device using the SY command.

        Returns
        -------
        str
            The device type, or None if not set or an error occurs.
        """



        if not self._connection:
            error_message = f"Not connected to device. Cannot retrieve device type."
            self._logger.error(error_message)
            raise ConnectionError(error_message)

        try:
            system_status: SystemStatus = self.get_system_status()
            self._device_type = system_status.device_type
            return True

        except Exception as e:
            error_message = f"Error retrieving device type: {e}"
            self._logger.error(error_message)
            raise RuntimeError(error_message)


