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
from oregon_processing.util.interactive_terminal import InteractiveTerminal
from oregon_processing.util.firmware_updater import FirmwareUpdater


class OregonCommunicator:
    """Class to communicate with Oregon device via serial port."""

    TIME_STATUSES_SYNCED = {'G':"GNSS Time", 'N':"Network time using CAT5 cable", 'U':"Uncalibrated (entered with DT command)", "E": "Ellapsed time since power-up"}
    CRITICAL_VOLTAGE_THRESHOLD = 14.0  # volts

    def __init__(self):
        self._connector = OregonConnector()
        self._connection = None
        self._port = None
        self._baudrate = None
        self._command_manager = None
        self._last_upload_date = None
        self._reader_name = None
        self._serial_number = None

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
            self.return_to_startup_mode()
        self.close()

    def connect(self):
        """Attempt to connect to Oregon RFID sensor using the OregonConnector."""
        result = self._connector.connect()

        if result:
            self._connection = result['connection']
            self._port = result['port']
            self._baudrate = result['baudrate']
            self._command_manager = CommandManager(self._connection)
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

    def return_to_startup_mode(self):
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
        """Send a quick SY command to verify connection and capture prompt signature. Store reader name"""

        if not self._connection:
            return

        self._get_reader_name()
        self._start_up_mode = self.mode


    def standby_mode(self) -> bool:
        """
        Check prompt code to see if device is in Sleep mode, Standby mode, or Run mode.

        Sends ST command to put device in standby mode if not already in that mode.

        Check the prompt code again to see if device is in standby mode.
        """
        if not self._connection:
            print("Not connected to device.")
            return False

        print("\n" + "=" * 70, flush=True)
        print("SETTING DEVICE TO STANDBY MODE")
        print("=" * 70, flush=True)

        if self.mode != 'Standby':
            print(f"\nDevice is in '{self.mode}' mode.", flush=True)
            print("\nSending ST command to device...", end="", flush=True)
            self.send_command("ST")
            print(" Done.", flush=True)
            print("Verifying device mode...", end="", flush=True)
            if self.mode == 'Standby':
                print(" SUCCESS! Device is now in 'Standby' mode.", flush=True)
            else:
                print(f" FAILED! Device is still in '{self.mode}' mode.", flush=True)
                return False
        else:
            print("\nDevice is already in 'Standby' mode.", flush=True)

        print("\n" + "=" * 70)
        print("DEVICE SET TO STANDBY MODE")
        print("=" * 70)

        return True

    def run_mode(self) -> bool:
        """
        Check prompt code to see if device is in Sleep mode, Standby mode, or Run mode.

        Sends ON command to put device in run mode if not already in that mode.

        Check the prompt code again to see if device is in run mode.
        """
        if not self._connection:
            print("Not connected to device.")
            return False

        print("\n" + "=" * 70, flush=True)
        print("SETTING DEVICE TO RUN MODE")
        print("=" * 70, flush=True)

        if self.mode != 'Run':
            print(f"\nDevice is in '{self.mode}' mode.", flush=True)
            print("\nSending ON command to device...", end="", flush=True)
            self.send_command("ON")
            print(" Done.", flush=True)
            print("Verifying device mode...", end="", flush=True)
            if self.mode == 'Run':
                print(" SUCCESS! Device is now in 'Run' mode.", flush=True)
            else:
                print(f" FAILED! Device is still in '{self.mode}' mode.", flush=True)
                return False
        else:
            print("\nDevice is already in 'Run' mode.", flush=True)

        print("\n" + "=" * 70)
        print("DEVICE SET TO RUN MODE")
        print("=" * 70)

        return True

    def sleep_mode(self) -> bool:
        """
        Check prompt code to see if device is in Sleep mode, Standby mode, or Run mode.

        Sends OF command to put device in sleep mode if not already in that mode.

        Check the prompt code again to see if device is in sleep mode.
        """
        if not self._connection:
            print("Not connected to device.")
            return False

        print("\n" + "=" * 70, flush=True)
        print("SETTING DEVICE TO SLEEP MODE")
        print("=" * 70, flush=True)

        if self.mode != 'Sleep':
            print(f"\nDevice is in '{self.mode}' mode.", flush=True)
            print("\nSending OF command to device...", end="", flush=True)
            self.send_command("OF")
            print(" Done.", flush=True)
            print("Verifying device mode...", end="", flush=True)
            if self.mode == 'Sleep':
                print(" SUCCESS! Device is now in 'Sleep' mode.", flush=True)
            else:
                print(f" FAILED! Device is still in '{self.mode}' mode.", flush=True)
                return False
        else:
            print("\nDevice is already in 'Sleep' mode.", flush=True)

        print("\n" + "=" * 70)
        print("DEVICE SET TO SLEEP MODE")
        print("=" * 70)

        return True


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

        updater = FirmwareUpdater(self._connection, self._command_manager)
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

        terminal = InteractiveTerminal(self._command_manager)
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
            'raw_output': status_lines,
            'warnings': []
        }

        # Parse first 3 lines by position (these are always in the same order)
        if len(status_lines) < 3:
            raise ValueError(f"Expected at least 3 lines in SY response, got {len(status_lines)}")

        # Line 0: device type
        status['device_type'] = status_lines[0].strip() or None

        # Line 1: version and serial number
        line = status_lines[1]
        if line.startswith('V'):
            parts = line.split()
            if parts:
                status['version'] = parts[0]
            if len(parts) > 1:
                status['serial_number'] = parts[1]
        else:
            raise ValueError(f"Unexpected version/serial line format at row 2: '{line}'")

        # Line 2: reader name
        status['reader_name'] = status_lines[2].strip()

        # Parse remaining lines by keyword matching (order may vary by firmware)
        for idx, line in enumerate(status_lines[3:], start=3):
            line_lower = line.lower().strip()

            # Mode line (contains "mode")
            if 'mode' in line_lower:
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

    def _parse_tz_response(self, tz_line: str) -> timezone:
        hours = 0
        minutes = 0
        sign = 1

        # Determine format and parse accordingly
        if tz_line.startswith("Hours:minutes to UT:"):
            # Format 1: "Hours:minutes to UT: -3h30m"
            offset_part = tz_line.split("Hours:minutes to UT:")[1].strip()

            # Determine sign
            if offset_part.startswith('-'):
                sign = -1
                offset_part = offset_part[1:]
            elif offset_part.startswith('+'):
                sign = 1
                offset_part = offset_part[1:]
            else:
                raise ValueError(f"Unrecognized timezone format: {tz_line}")

            # Parse "3h30m" format
            try:
                hours = int(offset_part.split('h')[0].strip())
                minutes = int(offset_part.split('h')[1].strip().split('m')[0].strip())
            except IndexError:
                raise ValueError(f"Unrecognized timezone format: {tz_line}")


        elif tz_line.startswith("Hours to UT:"):
            # Format 2: "Hours to UT: +0"
            offset_part = tz_line.split("Hours to UT:")[1].strip()

            # Determine sign
            if offset_part.startswith('-'):
                sign = -1
                offset_part = offset_part[1:]
            elif offset_part.startswith('+'):
                sign = 1
                offset_part = offset_part[1:]
            else:
                raise ValueError(f"Unrecognized timezone format: {tz_line}")

            # Parse hours only
            hours = int(offset_part)

        else:
            raise ValueError(f"Unrecognized timezone format: {tz_line}")

        # Calculate total offset and return timezone object
        total_seconds = sign * (hours * 3600 + minutes * 60)

        return timezone(timedelta(seconds=total_seconds))

    def _parse_dt_response(self, dt_line: str) -> dict:
        """
        Parse the DT command response line into its components.

        Parameters
        ----------
        dt_line : str
            The raw DT response line from the device.

        Returns
        -------
        dict
            Parsed DT response with keys:
            - 'date': Date string (YYYY-MM-DD)
            - 'time': Time string (HH:MM:SS)
            - 'milliseconds': Milliseconds component (int, 0-999)
            - 'sync_status': Synchronization status ('G', 'N', or 'U')
        """

        parts = dt_line.split()

        if len(parts) < 3:
            raise ValueError(f"Unrecognized DT response format: {dt_line}")

        date_str = parts[0]  # YYYY-MM-DD
        time_str = parts[1]  # HH:MM:SS.milliseconds
        sync_status = parts[2]  # G, N, or U

        # Parse time and milliseconds
        if '.' in time_str:
            time_part, milliseconds_str = time_str.split('.')
            milliseconds = int(milliseconds_str)
        else:
            time_part = time_str
            milliseconds = 0

        return {
            'datetime': datetime.strptime(f"{date_str} {time_part}", "%Y-%m-%d %H:%M:%S"),
            'milliseconds': milliseconds,
            'sync_status': sync_status
        }

    def get_device_datetime(self) -> dict:
        """
        Retrieve the device's current date and time using the DT and TZ commands.

        Returns a timezone-aware datetime object combining the device's time
        from the DT command with the timezone offset from the TZ command.

        Returns
        -------
        dict
            Parsed device datetime with keys:
            - 'datetime': Timezone-aware datetime object
            - 'milliseconds': Milliseconds component (int, 0-999)
            - 'sync_status': Synchronization status ('G', 'N', or 'U')
            - 'raw_output': Raw DT response line from device
            - 'error': Error message if parsing failed (None if successful)
        """

        if not self._connection:
            raise ConnectionError("Not connected to device.")

        try:
            # Send TZ command and get response
            lines = self.send_command("TZ")

        except Exception as e:
            raise Exception(f"Error sending TZ command: {e}")


        # First line contains timezone offset information
        # Format 1: "Hours:minutes to UT: -3h30m"
        # Format 2: "Hours to UT: +0"
        tz_line = lines[0].strip()
        device_tz = self._parse_tz_response(tz_line)


        # Send DT command and get response
        try:
            lines = self.send_command("DT")
        except Exception as e:
            raise Exception(f"Error sending DT command: {e}")

        parsed_dt = self._parse_dt_response(lines[0].strip())
        device_dt = parsed_dt['datetime']

        # Create timezone-aware datetime using the timezone from TZ command
        datetime_aware = device_dt.replace(tzinfo=device_tz)

        return {
            'datetime': datetime_aware,
            'milliseconds': parsed_dt['milliseconds'],
            'sync_status': self.TIME_STATUSES_SYNCED.get(parsed_dt['sync_status'], "Unknown"),
        }

    def control_device_datetime(self, tolerance_seconds: int = 15, attempt_sync: bool = True) -> dict:


        if not self._connection:
            raise ConnectionError("Not connected to device.")

        print("\n" + "=" * 70, flush=True)
        print("DEVICE DATE/TIME CHECK", flush=True)
        print("=" * 70, flush=True)

        device_result = self.get_device_datetime()
        device_datetime = device_result['datetime']
        sync_status = device_result['sync_status']

        # Get system datetime (PC time)
        system_datetime = datetime.now()
        system_datetime_utc = system_datetime.astimezone(timezone.utc)

        # Convert both to UTC for comparison
        device_datetime_utc = device_datetime.astimezone(timezone.utc)
        system_datetime_local = system_datetime.astimezone()  # Get local time with timezone

        # Calculate difference in UTC (negative means device is behind)
        time_diff = (device_datetime_utc - system_datetime_utc).total_seconds()

        # Check if within acceptable tolerance
        is_synced = abs(time_diff) <= tolerance_seconds

        # Display sync status and times (always, regardless of attempt_synch)
        device_offset_hours = device_datetime.utcoffset().total_seconds() / 3600
        system_offset_hours = system_datetime_local.utcoffset().total_seconds() / 3600
        device_tz_str = f"(UT{device_offset_hours:+.1f})"
        system_tz_str = f"(UT{system_offset_hours:+.1f})"

        print("\n" + "-" * 70)
        print("SYNC STATUS")
        print("-" * 70)
        print(f"Status: {'✓ IN SYNC' if is_synced else '⚠ OUT OF SYNC'}", flush=True)
        print(f"Device datetime: {device_datetime.strftime('%Y-%m-%d %H:%M:%S')} {device_tz_str} [Time source: {sync_status}]")
        print(f"System datetime: {system_datetime.strftime('%Y-%m-%d %H:%M:%S')} {system_tz_str}")
        if not is_synced:
            print(f"Time difference: {time_diff:+.1f} seconds ({abs(time_diff):.1f}s {'ahead' if time_diff > 0 else 'behind'})")

        report = {
            'synced': is_synced,
            'device_datetime': device_datetime,
            'system_datetime': system_datetime,
            'difference_seconds': time_diff,
            'was_updated': False,
            'update_command_sent': None,
            'update_response': None,
            'error': None
        }

        # If out of sync and attempt_sync enabled, prompt user and update device
        if not is_synced and attempt_sync:

            print("\n" + "-" * 70)
            print("CLOCK SYNC ACTION REQUIRED")
            print("-" * 70)

            # Ask for user confirmation
            confirm = None
            while confirm not in ['yes', 'y', 'no', 'n']:
                confirm = input("\nUpdate device time to match system time? (yes/no): ").strip().lower()

            if confirm in ['no', 'n']:
                print("Device time sync cancelled by user.")
                print("\n" + "=" * 70)
                print("CHECK COMPLETE")
                print("=" * 70)
                return report

            try:
                print("\n" + "-" * 70)
                print("UPDATING DEVICE TIME")
                print("-" * 70)
                print("Setting device timezone to UTC...", end="", flush=True)
                self.send_command("TZ 0")
                print("Done.")

                print("Sending device time..............", end="", flush=True)
                # Send UTC time to device (device interprets DT command as UTC)
                dt_command = system_datetime_utc.strftime("DT %Y-%m-%d %H:%M:%S")
                response_lines = self.send_command(dt_command)

                report['was_updated'] = True
                report['update_command_sent'] = dt_command
                report['update_response'] = response_lines
                report['synced'] = True

                print("Done.")

            except Exception as e:
                report['error'] = f'Failed to update device datetime: {e}'
                print("ERROR.")
                print(f"\nError updating device time: {e}")

        print("\n" + "=" * 70)
        print("CHECK COMPLETE")
        print("=" * 70)
        return report

    def export_system_status(self, output_dir: Path) -> bool:
        """
        Run the SY (system status) command and write the response to a text file.

        Parameters
        ----------
        output_dir : str or Path
            Directory where system status will be written.

        Returns
        -------
        bool
            True if successful, False otherwise.
        """

        if isinstance(output_dir, str):
            try:
                output_dir = Path(output_dir)
            except Exception as e:
                print(f"Error converting output directory string to Path object: {e}")
                return False

        if not self._connection:
            print("Not connected to device.")
            return False

        if not output_dir.exists():
            output_dir.mkdir(parents=True, exist_ok=True)

        output_filepath = output_dir / f"{self.reader_name}_system_status_{datetime.now().strftime('%Y_%m_%d_%H%M%S')}.txt"

        try:
            print(f"\nExporting system status to file...", end="")
            parsed_status = self.get_system_status()


            with open(output_filepath, 'w') as f:
                f.write("Oregon RFID System Status\n")
                f.write("Export Date/Time: " + time.strftime("%Y-%m-%d %H:%M:%S") + "\n")
                f.write("=========================\n\n")

                # Write system status
                f.write(f"Device Type: {parsed_status['device_type']}\n")
                f.write(f"Version: {parsed_status['version']}\n")
                f.write(f"Serial Number: {parsed_status['serial_number']}\n")
                f.write(f"Reader Name: {parsed_status['reader_name']}\n")
                f.write(f"Mode: {parsed_status['mode']}\n")
                f.write(f"Supply Voltage: {parsed_status['supply_voltage']}\n")
                f.write(f"Standby Amps: {parsed_status['standby_amps']}\n")
                f.write(f"Noise: {parsed_status['noise']}\n")
                f.write(f"Shutdown Supercap: {parsed_status['shutdown_supercap']}\n")
                f.write(f"Sleep Battery: {parsed_status['sleep_battery']}\n")
                f.write(f"Tags in Archive: {parsed_status['tags_in_archive']}\n\n")

                if parsed_status['warnings']:
                    f.write("Warnings:\n")
                    for warning in parsed_status['warnings']:
                        f.write(f"  - {warning}\n")
                    f.write("\n")
                else:
                    f.write("No warnings detected.\n\n")

            print("Done.")
            print(f"System status written to {output_filepath}")

            return True

        except Exception as e:
            print(f"Error writing system status to file: {e}")
            return False

    def export_upload_log(self, output_dir: Path) -> bool:
        """
        Run the UH (upload log) command and write the response to a text file.

        Parameters
        ----------
        output_dir : str or Path
            Directory where output file will be written.

        Returns
        -------
        bool
            True if successful, False otherwise.
        """

        if isinstance(output_dir, str):
            try:
                output_dir = Path(output_dir)
            except Exception as e:
                print(f"Error converting output directory string to Path object: {e}")
                return False

        if not self._connection:
            print("Not connected to device.")
            return False

        if not output_dir.exists():
            output_dir.mkdir(parents=True, exist_ok=True)

        output_filepath = output_dir / f"{self.reader_name}_upload_log_{datetime.now().strftime('%Y_%m_%d_%H%M%S')}.txt"

        try:
            print(f"\nExporting upload log to file:", flush=True)
            upload_history_lines = self.send_command("UH")

            with open(output_filepath, 'w') as f:
                f.write("Oregon RFID Upload Log\n")
                f.write("Export Date/Time: " + time.strftime("%Y-%m-%d %H:%M:%S") + "\n")
                f.write("=========================\n\n")

                # Write upload log
                f.write('\n'.join(upload_history_lines))

            print(f"  Upload log written to {output_filepath}")
            print(f"  Total lines written: {len(upload_history_lines)}")

            return True

        except Exception as e:
            print(f"Error writing upload log to file: {e}")
            return False

    def export_system_status_logs(self, first_date: date, last_date: Union[date, None] = None, output_dir: Path = Path("")) -> bool:
        """
        Export system status logs for all dates since specifed date

        This method retrieves the last upload date, then runs export_system_status_log()
        for each day in the range up to and including today.

        Parameters
        ----------
        first_date : date object
        output_dir : str or Path
            Directory where output files will be written (default: current directory)

        Returns
        -------
        bool
            True if all exports completed successfully, False if any failed.
        """

        if last_date is None:
            last_date = date.today()

        if isinstance(output_dir, str):
            try:
                output_dir = Path(output_dir)
            except Exception as e:
                print(f"Error converting output directory string to Path object: {e}")
                return False

        if not self._connection:
            print("Not connected to device.")
            return False


        try:

            if first_date > last_date:
                print(f"First date ({first_date}) is in the future. No logs to export.")
                return False

            # Header
            print("\n" + "=" * 70)
            print("EXPORTING SYSTEM STATUS LOGS")
            print("=" * 70)
            print(f"Date range: {first_date} to {last_date}")
            print(f"Output directory: {output_dir}")

            # Prepare ranges and formatting
            num_dates = (last_date - first_date).days + 1
            all_dates = [first_date + timedelta(days=i) for i in range(num_dates)]
            max_counter_width = len(f"({num_dates}/{num_dates})")
            max_line_width = len(str(1440))  # assume up to one line per minute per day

            print("\n" + "-" * 70)
            print("Exporting Logs")
            print("-" * 70)

            all_successful = True
            export_count = 0

            for date_num, current in enumerate(all_dates, start=1):

                output_filepath = f"{output_dir}/{self.reader_name}_system_log_{current.strftime('%Y_%m_%d')}.txt"

                counter = f"({date_num}/{num_dates})"
                spacing = " " * (max_counter_width - len(counter))
                print(f"  - {spacing}{counter} {current}. Exporting...", end="", flush=True)

                try:
                    success = True
                    # Send ER command with date
                    command = f"ER {current.strftime('%Y-%m-%d')}"
                    response = self.send_command(command)
                except Exception as e:
                    print(f"ERROR. {e}")
                    success = False
                    all_successful = False
                    response = []

                # Generate output filename with date
                with open(output_filepath, 'w') as f:
                    f.write("Oregon RFID Event Record\n")
                    f.write("Export Date/Time: " + time.strftime("%Y-%m-%d %H:%M:%S") + "\n")
                    f.write("Date of Record: " + current.strftime("%Y-%m-%d") + "\n")
                    f.write("=========================\n\n")

                    # Write event record
                    f.write('\n'.join(response))

                if success:
                    print(f"Done. Lines written: {len(response)}.")
                    export_count += 1

            failed_exports = num_dates - export_count

            print("\n" + "-" * 70)
            print("SUMMARY")
            print("-" * 70)
            print(f"Total dates processed: {num_dates}")
            print(f"Successful exports:    {export_count}")
            print(f"Failed exports:        {failed_exports}")

            print("\n" + "=" * 70)
            if all_successful:
                print("EXPORT COMPLETE")
            else:
                print("EXPORT COMPLETE WITH ERRORS")
            print("=" * 70)

            return True if all_successful else False

        except Exception as e:
            print(f"Error during batch export: {e}")
            print("\n" + "=" * 70)
            print("EXPORT FAILED")
            print("=" * 70)
            return False

    def export_records(self, first_date: date, last_date: Union[date, None] = None, output_dir: Path = Path("")) -> bool:
        """
        Export event records for a date range using the ER command.

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

        if last_date is None:
            last_date = date.today()

        if isinstance(output_dir, str):
            try:
                output_dir = Path(output_dir)
            except Exception as e:
                print(f"Error converting output directory string to Path object: {e}")
                return False

        if not self._connection:
            print("Not connected to device.")
            return False

        if not output_dir.exists():
            output_dir.mkdir(parents=True, exist_ok=True)

        if first_date > last_date:
            print(f"First date ({first_date}) is after last date ({last_date}). No records to export.")
            return False

        upload_history = self.get_upload_history()
        total_number_of_records = upload_history["total_records"]

        try:
            print("\n" + "=" * 70)
            print("EXPORTING EVENT RECORDS")
            print("=" * 70)
            print(f"Date range: {first_date} to {last_date}")
            print(f"Total records on device: {total_number_of_records}")
            print(f"Output directory: {output_dir}")

            print("\n" + "-" * 70)
            print("PHASE 1: Retrieving Records from Device")
            print("-" * 70)
            print("Requesting all records from device...", end="", flush=True)
            response = self.send_command("UP*")
            print("Done.")

            print("\n" + "-" * 70)
            print("PHASE 2: Processing Records")
            print("-" * 70)
            print("Filtering detection records in date range...", end="", flush=True)
            # Convert dates to strings for comparison (YYYY-MM-DD format sorts chronologically)
            first_date_str = first_date.strftime("%Y-%m-%d")
            last_date_str = last_date.strftime("%Y-%m-%d")

            # Filter records in date range - single pass with early termination
            filtered_records = []
            for line in response:
                if not line.startswith("S"):
                    continue
                record_date = line[3:13]  # Extract "YYYY-MM-DD" from "S  2021-09-25 05:14:56.400"
                if record_date > last_date_str:
                    break  # Early exit - records are chronological, no need to continue
                if record_date >= first_date_str:
                    filtered_records.append(line)
            print("Done.")

            print("Organizing records by date..................", end="", flush=True)
            records = {} # dict with date keys and list of records values
            all_dates = [first_date + timedelta(days=i) for i in range((last_date - first_date).days + 1)]
            num_dates = len(all_dates)

            current_date = None
            for record in filtered_records:
                record_date = datetime.strptime(record[3:13], "%Y-%m-%d").date()

                if record_date != current_date:
                    current_date = record_date
                    records[current_date] = []

                records[current_date].append(record)

            print("Done.")

            print("\n" + "-" * 70)
            print("SUMMARY")
            print("-" * 70)

            # Calculate max width for summary number alignment
            max_summary_width = max(
                len(str(len(filtered_records))),
                len(str(len(records))),
                len(str(num_dates - len(records)))
            )

            print(f"Total detection records in date range: {str(len(filtered_records)).rjust(max_summary_width)}")
            print(f"Number of dates with records:          {str(len(records)).rjust(max_summary_width)}")
            print(f"Number of dates without records:       {str(num_dates - len(records)).rjust(max_summary_width)}")

            print("\n" + "-" * 70)
            print("PHASE 3: Exporting Files")
            print("-" * 70)

            # Calculate max width for counter alignment
            max_counter_width = len(f"({num_dates}/{num_dates})")

            # Calculate max width for record count alignment
            max_record_count = max((len(recs) for recs in records.values()), default=0)
            max_count_width = len(str(max_record_count))

            for date_num, current_date in enumerate(all_dates):
                counter = f"({date_num + 1}/{num_dates})"
                spacing = " " * (max_counter_width - len(counter))
                print(f"  - {spacing}{counter} {current_date}. ", end="", flush=True)

                if current_date not in records:
                    count_str = "0".rjust(max_count_width)
                    print(f"Number of records: {count_str}. Exporting file...", end="", flush=True)
                else:
                    count_str = str(len(records[current_date])).rjust(max_count_width)
                    print(f"Number of records: {count_str}. Exporting file...", end="", flush=True)

                output_filepath = output_dir / f"{self.reader_name}_records_{current_date.strftime('%Y-%m-%d')}.txt"
                with open(output_filepath, 'w') as f:
                    f.write("Oregon RFID Event Records\n")
                    f.write("Export Date/Time: " + time.strftime("%Y-%m-%d %H:%M:%S") + "\n")
                    f.write("Date of Record: " + current_date.strftime("%Y-%m-%d") + "\n")
                    f.write("=========================\n\n")

                    # Write event records for the date
                    if current_date in records:
                        f.write('\n'.join(records[current_date]))

                print("Done.")

            print("\n" + "=" * 70, flush=True)
            print("EXPORT COMPLETE", flush=True)
            print("=" * 70, flush=True)
            return True

        except Exception as e:
            print(f"\nError during batch export: {e}")
            return False





