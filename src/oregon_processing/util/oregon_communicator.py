# -*- coding: utf-8 -*-
"""
Oregon RFID Communicator
"""

from inspect import signature
import time
import os

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Union



from oregon_processing.util.oregon_connector import OregonConnector
from oregon_processing.util.command_manager import CommandManager
from oregon_processing.util.clock_manager import ClockManager
from oregon_processing.util.interactive_terminal import InteractiveTerminal
from oregon_processing.util.firmware_updater import FirmwareUpdater
from oregon_processing.util.data_exporter import DataExporter


class OregonCommunicator:
    """Class to communicate with Oregon device via serial port."""

    CRITICAL_VOLTAGE_THRESHOLD = 14.0  # volts

    def __init__(self):
        self._connector = OregonConnector()
        self._connection = None
        self._port = None
        self._baudrate = None

        self._command_manager = None
        self._clock_manager = None
        self._data_exporter = None

        self._last_upload_date = None
        self._reader_name = None
        self._serial_number = None
        self._event_record_format = None

    @property
    def port(self):
        """Get the connected port name."""
        return self._port

    @property
    def baudrate(self):
        """Get the connected baud rate."""
        return self._baudrate

    @property
    def reader_name(self):
        """Get the reader name if known."""

        if not self._reader_name:
            self._get_reader_name()
        return self._reader_name

    @property
    def serial_number(self):
        """Get the serial number if known."""

        if not self._serial_number:
            self._get_serial_number()
        return self._serial_number

    @property
    def is_connected(self):
        """Check if there is an active connection."""
        return self._connection is not None

    @property
    def prompt_signature(self):
        """Get the last received prompt signature from the command manager."""
        if self._command_manager:
            return self._command_manager.prompt_signature
        return None

    @property
    def mode(self):
        """Get the current operating mode from the system status."""
        status = self.get_system_status()
        return status['mode']

    def __enter__(self):
        """Allow use in 'with' statement."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Ensure the connection is closed when leaving context."""
        if self._connection:
            self._return_to_startup_mode()
            if self._data_exporter:
                self._data_exporter.restore_startup_format()
        self.close()

    def connect(self):
        """Attempt to connect to Oregon RFID sensor using the OregonConnector."""
        result = self._connector.connect()

        if result:
            self._connection = result['connection']
            self._port = result['port']
            self._baudrate = result['baudrate']


            self._command_manager = CommandManager(self)
            self._data_exporter = DataExporter(self)
            self._clock_manager = ClockManager(self)

            self._post_connect_handshake()

        return False

    def close(self):
        """Close serial connection."""
        if self._connection:
            try:
                self._connection.close()
                print(f"\nConnection to {self._port} closed.")
            except Exception as e:
                print(f"\nError closing connection: {e}")
            finally:
                self._connection = None
                self._port = None
                self._baudrate = None
                self._command_manager = None
                self._clock_manager = None

    def _return_to_startup_mode(self):
        """Return the Oregon RFID device to its start-up mode."""
        if self._connection is None:
            return

        if self._start_up_mode.lower() == "standby":
            self.standby_mode()
        elif self._start_up_mode.lower() == "run":
            self.run_mode()
        elif self._start_up_mode.lower() == "sleep":
            self.sleep_mode()
        else:
            self.sleep_mode()
            print("WARNING: Unknown start-up mode. Reader has been set to Sleep mode to be safe.")

    def _post_connect_handshake(self):
        """Send a quick SY command to verify connection and capture prompt signature. Store reader name and FM format"""

        if not self._connection:
            return

        self._get_reader_name()
        self._start_up_mode = self.mode


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

        if not self._connection:
            print("Not connected to device.")
            return False

        command = mode_commands[mode_name]

        print("\n" + "=" * 70, flush=True)
        print(f"SETTING DEVICE TO {mode_name.upper()} MODE")
        print("=" * 70, flush=True)

        if self.mode != mode_name:
            print(f"\nDevice is in '{self.mode}' mode.", flush=True)
            print(f"\nSending {command} command to device...", end="", flush=True)
            self.send_command(command)
            print(" Done.", flush=True)
            print("Verifying device mode...", end="", flush=True)
            if self.mode == mode_name:
                print(f" SUCCESS! Device is now in '{mode_name}' mode.", flush=True)
            else:
                print(f" FAILED! Device is still in '{self.mode}' mode.", flush=True)
                return False
        else:
            print(f"\nDevice is already in '{mode_name}' mode.", flush=True)

        print("\n" + "=" * 70)
        print(f"DEVICE SET TO {mode_name.upper()} MODE")
        print("=" * 70)

        return True

    def standby_mode(self) -> bool:
        """Set device to standby mode."""
        return self.change_mode('Standby')

    def run_mode(self) -> bool:
        """Set device to run mode."""
        return self.change_mode('Run')

    def sleep_mode(self) -> bool:
        """Set device to sleep mode."""
        return self.change_mode('Sleep')

    def check_system_status_health(self):
        """
        Calls for system status and checks parsed system status for potential issues.

        Returns
        -------
        dict
            Dictionary with 'healthy' (bool) and 'warnings' (list of str) keys.
        """

        print("\n" + "=" * 70, flush=True)
        print("SYSTEM STATUS HEALTH CHECK", flush=True)
        print("=" * 70, flush=True)

        print("\n" + "-" * 70)
        print("Retrieving System Status")
        print("-" * 70)
        print("Requesting system status from device...", end="", flush=True)

        warnings = []
        parsed_status = self.get_system_status()

        print("Done.")

        # Check supply voltage
        print("\n" + "-" * 70)
        print("Health Analysis")
        print("-" * 70)

        if parsed_status['supply_voltage']:
            try:
                voltage = float(parsed_status['supply_voltage'])
                if voltage < self.CRITICAL_VOLTAGE_THRESHOLD:
                    warnings.append(f"Low supply voltage: {voltage}V (should be >= {self.CRITICAL_VOLTAGE_THRESHOLD}V)")
            except (ValueError, TypeError):
                warnings.append(f"Could not parse supply voltage: {parsed_status['supply_voltage']}")

        health_report = {
            'healthy': len(warnings) == 0,
            'warnings': warnings
        }

        # Report health status
        if not health_report['healthy']:
            print(f"\n⚠ WARNING: {len(health_report['warnings'])} issue(s) detected:")
            for warning in health_report['warnings']:
                print(f"  - {warning}")
        else:
            print("\n✓ System status check: All parameters within normal range")

        print("\n" + "=" * 70)
        print("CHECK COMPLETE")
        print("=" * 70)

        return health_report

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
                print(f"Error converting firmware path string to Path object: {e}")
                return False

        if not self._connection:
            print("Not connected to device.")
            return False

        updater = FirmwareUpdater(self)
        return updater.update(firmware_file_path, new_version)

    def start_interactive_terminal(self):
        """
        Start an interactive terminal session for sending commands to the device.

        Opens a command-line interface where commands can be entered, validated,
        sent to the device, and responses displayed. Type 'exit' or 'quit' to exit.
        """
        if not self._connection:
            print("Not connected to device.")
            return

        terminal = InteractiveTerminal(self)
        terminal.run()

    def send_command(self, command: str):
        return self._command_manager.send_command_and_receive_response(command)

    def get_system_status(self):
        """
        Parse system status output into a structured dictionary.

        The SY output has a fixed structure for the first 3 lines (device type, version/serial, reader name),
        but subsequent lines may vary by firmware version. This parser uses position for the first 3 lines
        and keyword matching for the remaining fields.
        """

        status_lines = self.send_command("SY")

        status = {
            'device_type': None,
            'version': None,
            'serial_number': None,
            'reader_name': None,
            'mode': None,
            'supply_voltage': None,
            'standby_amps': None,
            'noise': None,
            'shutdown_supercap': None,
            'sleep_battery': None,
            'tags_in_archive': None,
            'gnss_log_interval_minutes': False,
            'raw_output': status_lines,
            'warnings': []
        }

        # Parse first 3 lines by position (these are always in the same order)
        if len(status_lines) < 3:
            raise ValueError(f"Expected at least 3 lines in SY response, got {len(status_lines)}")

        for line_num, line in enumerate(status_lines):
            if not line.strip():
                raise ValueError(f"Empty line encountered in SY response at row {line_num + 1}")

            line = line.strip()
            line_lower = line.lower()

            # Line 0: device type
            if line_num == 0:
                # Line 0: device type
                if not "oregon rfid" in line_lower:
                    raise ValueError(f"Unexpected device type line format at row 1: '{line}'")

                status['device_type'] = line

            # Line 1: version and serial number
            elif line_num == 1:
                line_splits = line.split()
                if len(line_splits) != 2:
                    raise ValueError(f"Unexpected version/serial line format at row 2: '{line}'")

                version = line_splits[0]
                # Validate version format: Vx.xxM/N/F (e.g., V2.74M)
                if not (len(version) >= 3 and
                        version[0].upper() == 'V' and
                        version[-1].upper() in ['M', 'N', 'F']):
                    raise ValueError(f"Unexpected version/serial line format at row 2: '{line}'")

                # Validate that the middle part is numerical (digits and decimal point)
                version_number = version[1:-1]
                if not all(c.isdigit() or c == '.' for c in version_number):
                    raise ValueError(f"Unexpected version/serial line format at row 2: '{line}'")

                serial_number = line_splits[1].strip()
                # Validate serial number format: hex digits separated by hyphens (e.g., 0011-000C-0C36-3039-3455-37)
                if not all(c in '0123456789ABCDEFabcdef-' for c in serial_number):
                    raise ValueError(f"Unexpected version/serial line format at row 2: '{line}'")
                if not serial_number or serial_number.startswith('-') or serial_number.endswith('-'):
                    raise ValueError(f"Unexpected version/serial line format at row 2: '{line}'")

                status['version'] = version
                status['serial_number'] = serial_number

            # Line 2: reader name
            elif line_num == 2:
                # No validation possible here yet
                # TODO add validfation by restricting to allowed names. Only possible once we have changed all names.
                status['reader_name'] = line

            # Mode line (contains "mode")
            elif 'mode' in line_lower:
                status['mode'] = line.strip().split(' mode')[0].strip() or None

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
            elif "gnss logged every / minutes" in line_lower:
                status['gnss_log_interval_minutes'] = True
            else:
                raise ValueError(f"Unrecognized line format in system status at row {line_num + 1}: '{line}'")

        return status

    def get_upload_history(self):
        """
        Parse upload history output from UH command.

        Returns
        -------
        dict
            Parsed upload history with upload records and metadata.
        """

        upload_history_lines = self.send_command("UH")

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
                        pass

            # Parse NEW records line
            elif line_stripped.startswith('NEW'):
                parts = line_stripped.split()
                if len(parts) >= 2:
                    try:
                        history['new_records'] = int(parts[-1])
                    except ValueError:
                        pass

            # Parse Total line
            elif line_stripped.startswith('Total'):
                parts = line_stripped.split()
                if len(parts) >= 2:
                    try:
                        history['total_records'] = int(parts[-1])
                    except ValueError:
                        pass

            else:
                raise ValueError(f"Unrecognized line format in upload history: '{line}'")


        # Store the most recent upload date (last entry in uploads list)
        if history['uploads']:
            last_upload = history['uploads'][-1]

            upload_datetime = datetime.strptime(f"{last_upload['date']} {last_upload['time']}", "%Y-%m-%d %H:%M:%S")
            self._last_upload_date = upload_datetime.date()

        return history

    def _get_reader_name(self) -> str:
        """
        Retrieve the reader name from the device using the SY command.

        Returns
        -------
        str
            The reader name, or None if not set or an error occurs.
        """

        if not self._connection:
            print("Not connected to device.")
            return None

        try:
            parsed_status = self.get_system_status()
            self._reader_name = parsed_status["reader_name"]
            return self._reader_name

        except Exception as e:
            print(f"Error retrieving reader name: {e}")
            return None

    def _get_serial_number(self) -> str:
        """
        Retrieve the serial number from the device using the SY command.

        Returns
        -------
        str
            The serial number, or None if not set or an error occurs.
        """

        if not self._connection:
            print("Not connected to device.")
            return None

        try:
            parsed_status = self.get_system_status()
            serial_number = parsed_status["serial_number"]
            return serial_number

        except Exception as e:
            print(f"Error retrieving serial number: {e}")
            return None

    def get_device_datetime(self) -> dict:
        """
        Retrieve the device's current date and time using the DT and TZ commands.

        Delegates to ClockManager. Returns parsed device datetime with timezone awareness.

        Returns
        -------
        dict
            Device datetime with keys: datetime, elapsed_time, milliseconds, sync_status
        """
        if not self._connection:
            raise ConnectionError("Not connected to device.")

        return self._clock_manager.get_device_datetime()

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
            raise ConnectionError("Not connected to device.")

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

    def export_system_status_logs(self, first_date: date, last_date: Union[date, None] = None, output_dir: Path = Path("")) -> bool:
        """
        Export system status logs for a date range.

        Delegates to DataExporter.export_system_status_logs().

        Parameters
        ----------
        first_date : date object
            Start date for export (inclusive)
        last_date : date object, optional
            End date for export (inclusive). If None, defaults to current date.
        output_dir : str or Path
            Directory where output files will be written (default: current directory)

        Returns
        -------
        bool
            True if all exports completed successfully, False if any failed.
        """
        return self._data_exporter.export_system_status_logs(first_date, last_date, output_dir)

    def export_records(self, first_date: date, last_date: Union[date, None] = None, output_dir: Path = Path(""), sep=',') -> bool:
        """
        Export event records for a date range.

        Delegates to DataExporter.export_records().

        Parameters
        ----------
        first_date : date object
            Start date for export (inclusive)
        last_date : date object, optional
            End date for export (inclusive). If None, defaults to current date.
        output_dir : str or Path
            Directory where output files will be written (default: current directory)
        sep : str, optional
            Separator to use in the output file (default: ',')

        Returns
        -------
        bool
            True if all exports completed successfully, False if any failed.
        """
        return self._data_exporter.export_records(first_date, last_date, output_dir, sep)

