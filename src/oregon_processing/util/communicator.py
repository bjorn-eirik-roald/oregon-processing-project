# -*- coding: utf-8 -*-
"""
Oregon RFID Communicator
"""

from contextlib import ExitStack

from datetime import datetime
from pathlib import Path

from oregon_processing.util.connector import Connector
from oregon_processing.util.command_manager import CommandManager
from oregon_processing.util.clock_manager import ClockManager
from oregon_processing.util.device_mode_manager import DeviceModeManager
from oregon_processing.util.interactive_terminal import InteractiveTerminal
from oregon_processing.util.firmware_updater import FirmwareUpdater
from oregon_processing.util.format_manager import FormatManager
from oregon_processing.util.data_exporter import DataExporter
from oregon_processing.util.device_health_checker import DeviceHealthChecker
from oregon_processing.util.logging_manager import get_logger
from src.oregon_processing.util.exceptions import ConnectionFailedError, UnexpectedResponseError, UnexpectedResponseError



class Communicator:
    """Class to communicate with Oregon device via serial port."""

    def __init__(self):
        self._connector = Connector()
        self._connection = None
        self._port = None
        self._baudrate = None

        self._exit_stack = None

        self._command_manager: CommandManager = None
        self._mode_manager: DeviceModeManager = None
        self._clock_manager: ClockManager = None
        self._format_manager: FormatManager = None
        self._data_exporter: DataExporter = None
        self._health_manager: DeviceHealthChecker = None

        self._last_upload_date = None
        self._reader_name = None
        self._serial_number = None
        self._device_type = None
        self._detection_record_format = None
        self._mode = None

        self._logger = get_logger(__name__)

    def __enter__(self):
        """Allow use in 'with' statement."""


        self._exit_stack = ExitStack()

        try:
            connector =  Connector()
            result = connector.connect()

            if result and 'connection' in result and result['connection']:
                self._connection = result['connection']
                self._port = result['port']
                self._baudrate = result['baudrate']

                # Enter all managers via ExitStack (they are context managers)
                # Register in reverse order so they exit in LIFO order
                self._command_manager = CommandManager(self)

                self._post_connect_handshake()

                self._mode_manager = self._exit_stack.enter_context(DeviceModeManager(self, self._command_manager))
                self._format_manager = self._exit_stack.enter_context(FormatManager(self, self._command_manager))
                self._data_exporter = DataExporter(self, self._format_manager, self._command_manager)
                self._clock_manager = ClockManager(self, self._command_manager)
                self._health_checker = DeviceHealthChecker(self)

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
        if self._mode_manager:
            self._mode =  self._mode_manager._get_current_mode()
            return self._mode

        error_message = "Mode manager not initialized; cannot retrieve current mode."
        self._logger.error(error_message)
        raise RuntimeError(error_message)

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
        return self._mode_manager.change_mode(mode_name)

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
        return self._health_checker.check_device_health()

    def update_firmware(self, firmware_file_path: Path, new_version: str) -> bool:
        """
        Update the firmware on the Oregon RFID reader.

        Parameters
        ----------
        firmware_file_path : str or Path
            Path to the firmware update file
        new_version : str
            Version string of the new firmware (e.g., "V2.2A")

        Returns
        -------
        bool
            True if update completed successfully, False otherwise.
        """



        if isinstance(firmware_file_path, str):
            try:
                firmware_file_path = Path(firmware_file_path)
            except Exception as e:
                error_message = f"Firmware file path must be a valid string or Path object. Error converting '{firmware_file_path}' to Path: {e}"
                self._logger.error(error_message)
                raise ValueError(error_message)

        if not self._connection:
            error_message = "Not connected to device. Cannot update firmware."
            self._logger.error(error_message)
            raise ConnectionError(error_message)

        updater = FirmwareUpdater(self, self._command_manager)
        return updater.update(firmware_file_path, new_version)

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

        terminal = InteractiveTerminal(self, self._command_manager)
        terminal.run()

        self._logger.info("Interactive terminal session ended.")
        self._logger.info("As a safety measure, reconnecting to device to refresh state.")
        self._post_connect_handshake()

    def get_system_status(self):
        """
        Parse system status output into a structured dictionary.

        The SY output has a fixed structure for the first 3 lines (device type, version/serial, reader name),
        but subsequent lines may vary by firmware version. This parser uses position for the first 3 lines
        and keyword matching for the remaining fields.
        """

        status_lines = self._command_manager.send_command("SY")

        status = {
            'device_type': None,
            'version': None,
            'serial_number': None,
            'reader_name': None,
            'mode': None,
            'supply_voltage': None,
            'standby_amps': None,
            'noise': None,
            'antenna_1': None,
            'antenna_2': None,
            'antenna_3': None,
            'antenna_4': None,
            'shutdown_supercap': None,
            'sleep_battery': None,
            'tags_in_archive': None,
            'bluetooth_status': None,
            'gnss_log_interval_minutes': False,
            'raw_output': status_lines,
            'warnings': []
        }

        # Parse first 3 lines by position (these are always in the same order)
        if len(status_lines) < 3:
            error_message = f"Expected at least 3 lines in SY response, got {len(status_lines)}"
            self._logger.error(error_message)
            raise UnexpectedResponseError(error_message)

        for line_num, line in enumerate(status_lines):
            if not line.strip():
                error_message = f"Empty line encountered in SY response at row {line_num + 1} of SY response."
                self._logger.error(error_message)
                raise UnexpectedResponseError(error_message)

            line = line.strip()
            line_lower = line.lower()

            # Line 0: device type
            if line_num == 0:
                # Line 0: device type
                if not "oregon rfid" in line_lower:
                    error_message = f"Unexpected device type line format at row 1 of SY response: '{line}'"
                    self._logger.error(error_message)
                    raise UnexpectedResponseError(error_message)

                if 'single antenna' in line_lower:
                    status['device_type'] = 'ORSR'
                elif 'multiple antenna' in line_lower:
                    status['device_type'] = 'ORMR'
                else:
                    error_message = f"Could not determine device type from line 1 of SY response: '{line}'"
                    self._logger.error(error_message)
                    raise UnexpectedResponseError(error_message)


            # Line 1: version and serial number
            elif line_num == 1:
                line_splits = line.split()
                if len(line_splits) != 2:
                    error_message = f"Unexpected version/serial line format at row 2 of SY response: '{line}'"
                    self._logger.error(error_message)
                    raise UnexpectedResponseError(error_message)

                version = line_splits[0]
                version_valid = True
                if status['device_type']=='ORSR':
                    if len(version) != 6: version_valid = False
                    if version[0].upper() != 'V': version_valid = False
                    if version[-1].upper() not in ['M', 'N', 'F']: version_valid = False
                elif status['device_type']  == 'ORMR':
                    if len(version) != 5: version_valid = False
                    if version[0].upper() != 'V': version_valid = False
                else:
                    error_message = f"Unknown device type '{status['device_type']}' for version/serial parsing."
                    self._logger.error(error_message)
                    raise UnexpectedResponseError(error_message)

                if not version_valid:
                    error_message = f"Unexpected version format in row 2 of SY response: '{line}'"
                    self._logger.error(error_message)
                    raise UnexpectedResponseError(error_message)

                serial_number = line_splits[1].strip()
                # Validate serial number format: hex digits separated by hyphens (e.g., 0011-000C-0C36-3039-3455-37)
                if not all(c in '0123456789ABCDEFabcdef-' for c in serial_number):
                    error_message = f"Unexpected serial number in row 2 of SY response: '{line}'"
                    self._logger.error(error_message)
                    raise UnexpectedResponseError(error_message)
                if not serial_number or serial_number.startswith('-') or serial_number.endswith('-'):
                    error_message = f"Unexpected serial number in row 2 of SY response: '{line}'"
                    self._logger.error(error_message)
                    raise UnexpectedResponseError(error_message)

                status['version'] = version
                status['serial_number'] = serial_number

            # Line 2: reader name
            elif line_num == 2:
                status['reader_name'] = line

            # Mode line (contains "mode")
            elif 'mode' in line_lower:
                mode = line.strip().split(' mode')[0].strip() or None

                # valdate mode is one of expected values
                if not DeviceModeManager.is_valid_mode(mode):
                    error_message = f"Unexpected mode value parsed from SY response: '{mode}' in line: '{line}'"
                    self._logger.error(error_message)
                    raise UnexpectedResponseError(error_message)

                status['mode'] = mode

            # Supply voltage
            elif 'supply voltage' in line_lower:
                parts = line.split()
                status['supply_voltage'] = parts[-1] if parts else None

            # Standby/Sleep amps (could be "standby amps" or "sleep amps")
            elif ('standby amps' in line_lower or 'sleep amps' in line_lower) and 'amps' in line_lower:
                parts = line.split()
                status['standby_amps'] = parts[-1] if parts else None

            # Noise
            elif line_lower.startswith('noise'):
                parts = line.split()
                status['noise'] = parts[-1] if parts else None

            # Antenna readings (Antenna #1, #2, #3, #4)
            elif 'antenna' in line_lower and '#' in line:
                parts = line.split()
                try:
                    antenna_num = line.split('#')[1].strip().split()[0]
                    antenna_value = parts[-1]
                    if antenna_num == '1':
                        status['antenna_1'] = antenna_value
                    elif antenna_num == '2':
                        status['antenna_2'] = antenna_value
                    elif antenna_num == '3':
                        status['antenna_3'] = antenna_value
                    elif antenna_num == '4':
                        status['antenna_4'] = antenna_value
                except (IndexError, ValueError):
                    pass

            # Shutdown supercap/supply
            elif 'shutdown' in line_lower and ('supercap' in line_lower or 'supply' in line_lower):
                parts = line.split()
                status['shutdown_supercap'] = parts[-1] if parts else None

            # Sleep battery
            elif 'sleep battery' in line_lower or (line_lower.startswith('battery') and 'sleep' not in line_lower):
                parts = line.split()
                status['sleep_battery'] = parts[-1] if parts else None

            # Tags in archive
            elif 'tags in archive' in line_lower:
                parts = line.split()
                status['tags_in_archive'] = parts[-1] if parts else None

            # Bluetooth status
            elif 'bluetooth' in line_lower:
                status['bluetooth_status'] = line.strip()

            elif "gnss logged every " in line_lower or 'gnss log is off' in line_lower:
                status['gnss_log_interval_minutes'] = True
            else:
                error_message = f"Unrecognized line format in system status at row {line_num + 1} of SY response: '{line}'"
                self._logger.error(error_message)
                raise UnexpectedResponseError(error_message)

        must_have_fields = ['device_type', 'version', 'serial_number', 'reader_name', 'mode']
        for field in must_have_fields:
            if not status[field]:
                error_message = f"Missing expected field '{field}' in system status. Parsed value: '{status[field]}'"
                self._logger.error(error_message)
                raise UnexpectedResponseError(error_message)

        return status

    def get_upload_history(self):
        """
        Parse upload history output from UH command.

        Returns
        -------
        dict
            Parsed upload history with upload records and metadata.
        """


        self.get_mode() # update mode property
        old_mode = None
        if self._mode.lower() != 'standby':
            old_mode = self._mode
            self.change_mode('Standby')

        upload_history_lines = self._command_manager.send_command("UH")

        if old_mode:
            self.change_mode(old_mode)

        history = {
            'reader_name': None,
            'site': None,
            'upload_count': None,
            'uploads': [],
            'new_records': None,
            'total_records': None,
            'raw_output': upload_history_lines
        }

        for i, line in enumerate(upload_history_lines):
            line_stripped = line.strip()

            # Parse header line: "Reader: <name>  Site: <site>"
            if line_stripped.startswith('Reader:'):
                parts = line_stripped.split('Site:')
                if len(parts) == 2:
                    reader_part = parts[0].replace('Reader:', '').strip()
                    site_part = parts[1].strip()
                    history['reader_name'] = reader_part
                    history['site'] = site_part

            # Parse upload histories count
            elif 'Upload Histories:' in line:
                parts = line_stripped.split('Upload Histories:')
                if len(parts) == 2:
                    try:
                        history['upload_count'] = int(parts[1].strip())
                    except ValueError:
                        pass

            # Skip header row (Num   UP Date    Time    Records)
            elif line_stripped.startswith('Num'):
                continue

            # Parse upload record lines (numbered entries)
            elif line_stripped and line_stripped[0].isdigit():
                parts = line_stripped.split()
                if len(parts) >= 4:
                    try:
                        upload_record = {
                            'num': int(parts[0]),
                            'date': parts[1],
                            'time': parts[2],
                            'records': int(parts[3])
                        }
                        history['uploads'].append(upload_record)
                    except (ValueError, IndexError):
                        error_message = f"Unrecognized line format in upload history at row {i + 1}: '{line}'"
                        self._logger.error(error_message)
                        raise UnexpectedResponseError(error_message)

            # Parse NEW records line
            elif line_stripped.startswith('NEW'):
                parts = line_stripped.split()
                if len(parts) >= 2:
                    try:
                        history['new_records'] = int(parts[-1])
                    except ValueError:
                        error_message = f"Unrecognized line format in upload history at row {i + 1}: '{line}'"
                        self._logger.error(error_message)
                        raise UnexpectedResponseError(error_message)

            # Parse Total line
            elif line_stripped.startswith('Total'):
                parts = line_stripped.split()
                if len(parts) >= 2:
                    try:
                        history['total_records'] = int(parts[-1])
                    except ValueError:
                        error_message = f"Unrecognized line format in upload history at row {i + 1}: '{line}'"
                        self._logger.error(error_message)
                        raise UnexpectedResponseError(error_message)

            else:
                error_message = f"Unrecognized line format in upload history at row {i + 1}: '{line}'"
                self._logger.error(error_message)
                raise UnexpectedResponseError(error_message)


        # Store the most recent upload date (last entry in uploads list)
        if history['uploads']:
            last_upload = history['uploads'][-1]

            upload_datetime = datetime.strptime(f"{last_upload['date']} {last_upload['time']}", "%Y-%m-%d %H:%M:%S")
            self._last_upload_date = upload_datetime.date()

        return history

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

    def export_system_status(self, output_dir: Path) -> bool:
        """
        Export system status to a file.

        Delegates to DataExporter.export_system_status().

        Parameters
        ----------
        output_dir : str or Path
            Directory where system status will be written.

        Returns
        -------
        bool
            True if successful, False otherwise.
        """
        return self._data_exporter.export_system_status(output_dir)

    def export_upload_log(self, output_dir: Path) -> bool:
        """
        Export upload log to a file.

        Delegates to DataExporter.export_upload_log().

        Parameters
        ----------
        output_dir : str or Path
            Directory where upload log will be written.

        Returns
        -------
        bool
            True if successful, False otherwise.
        """
        return self._data_exporter.export_upload_log(output_dir)

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
        return self._data_exporter.export_event_records(dates, output_dir)

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
        return self._data_exporter.export_detection_records(dates, output_dir, sep)

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
            self._logger.error("Not connected to device.")
            return False

        try:
            parsed_status = self.get_system_status()
            self._reader_name = parsed_status["reader_name"]
            return True

        except Exception as e:
            self._logger.error(f"Error retrieving reader name: {e}")
            return False

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
            parsed_status = self.get_system_status()
            self._serial_number = parsed_status["serial_number"]
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
            parsed_status = self.get_system_status()
            self._device_type = parsed_status["device_type"]
            return True

        except Exception as e:
            error_message = f"Error retrieving device type: {e}"
            self._logger.error(error_message)
            raise RuntimeError(error_message)


