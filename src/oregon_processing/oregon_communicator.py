# -*- coding: utf-8 -*-
"""
Oregon RFID Communicator
"""

from inspect import signature
import time
import os

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

# Support for history of readline on Windows via pyreadline3
try:
    import readline  # Linux / macOS
except ImportError:
    import pyreadline3 as readline  # Windows

from oregon_processing.oregon_connector import OregonConnector
from oregon_processing.command_manager import CommandManager
from oregon_processing.interactive_terminal import InteractiveTerminal





class OregonCommunicator:
    """Class to communicate with Oregon device via serial port."""

    TIME_STATUSES_SYNCED = {'G':"GNSS Time", 'N':"Network time using CAT5 cable", 'U':"Uncalibrated (entered with DT command)", "E": "Ellapsed time since power-up"}
    CRITICAL_VOLTAGE_THRESHOLD = 12.0  # volts

    def __init__(self):
        self._connector = OregonConnector()
        self._connection = None
        self._port = None
        self._baudrate = None
        self._command_manager = None
        self._last_upload_date = None
        self._reader_name = None

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
        return self._reader_name

    def __enter__(self):
        """Allow use in 'with' statement."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Ensure the connection is closed when leaving context."""
        self.close()

    def _post_connect_handshake(self):
        """Send a quick SY command to verify connection and capture prompt signature. Store reader name"""

        if not self._connection:
            return

        self.check_system_status_health()
        self.get_reader_name()

    def connect(self):
        """Attempt to connect to Oregon RFID sensor using the OregonConnector."""
        result = self._connector.connect()

        if result:
            self._connection = result['connection']
            self._port = result['port']
            self._baudrate = result['baudrate']
            self._command_manager = CommandManager(self._connection)
            self._post_connect_handshake()
            return True

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

    def send_command(self, command: str):
        return self._command_manager.send_command_and_receive_response(command)

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

    def _parse_system_status(self):
        """
        Parse system status output into a structured dictionary.

        The SY output is order-specific and some fields (e.g., reader name) may
        not include a label. This parser uses the expected row positions and
        validates prefixes for the labeled rows to guard against misalignment.
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

        # Expected order (0-indexed):
        # 0: device type line (free text)
        # 1: version/serial line (starts with V)
        # 2: reader name (free text, label may vary)
        # 3: mode line (contains "mode")
        # 4: supply voltage (prefix "supply voltage")
        # 5: standby amps (prefix "standby amps")
        # 6: noise (prefix "noise")
        # 7: shutdown supercap (prefix "shutdown supercap")
        # 8: sleep battery (prefix "sleep battery")
        # 9: tags in archive (prefix "tags in archive")

        def warn(msg):
            status['warnings'].append(msg)


        for idx, line in enumerate(status_lines):
            line_lower = line.lower().strip()

            # Device type
            if idx == 0:
                status['device_type'] = line.strip() or None

            # Version and serial number
            elif idx == 1:
                if line.startswith('V'):
                    parts = line.split()
                    if parts:
                        status['version'] = parts[0]
                    if len(parts) > 1:
                        status['serial_number'] = parts[1]
                else:
                    warn(f"Unexpected version/serial line format at row {idx+1}: '{line}'")

            # Reader name (no reliable label, trust position)
            elif idx == 2:
                status['reader_name'] = line.strip()

            # Mode line
            elif idx == 3:
                if 'mode' in line_lower:
                    status['mode'] = line.strip()
                else:
                    status['mode'] = line.strip() or None
                    warn(f"Expected mode line at row {idx+1} but got: '{line}'")

            # Supply voltage
            elif idx == 4:
                if line_lower.startswith('supply voltage'):
                    parts = line.split()
                    status['supply_voltage'] = parts[-1] if parts else None
                else:
                    warn(f"Expected 'Supply voltage' at row {idx+1} but got: '{line}'")

            # Standby amps
            elif idx == 5:
                if line_lower.startswith('standby amps'):
                    parts = line.split()
                    status['standby_amps'] = parts[-1] if parts else None
                else:
                    warn(f"Expected 'Standby amps' at row {idx+1} but got: '{line}'")

            # Noise
            elif idx == 6:
                if line_lower.startswith('noise'):
                    parts = line.split()
                    status['noise'] = parts[-1] if parts else None
                else:
                    warn(f"Expected 'Noise' at row {idx+1} but got: '{line}'")

            # Shutdown supercap
            elif idx == 7:
                if line_lower.startswith('shutdown supercap'):
                    parts = line.split()
                    status['shutdown_supercap'] = parts[-1] if parts else None
                else:
                    warn(f"Expected 'Shutdown supercap' at row {idx+1} but got: '{line}'")

            # Sleep battery
            elif idx == 8:
                if line_lower.startswith('sleep battery'):
                    parts = line.split()
                    status['sleep_battery'] = parts[-1] if parts else None
                else:
                    warn(f"Expected 'Sleep battery' at row {idx+1} but got: '{line}'")

            # Tags in archive
            elif idx == 9:
                if line_lower.startswith('tags in archive'):
                    parts = line.split()
                    status['tags_in_archive'] = parts[-1] if parts else None
                else:
                    warn(f"Expected 'Tags in archive' at row {idx+1} but got: '{line}'")

        return status

    def _parse_upload_history(self):
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

    def get_reader_name(self) -> str:
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
            parsed_status = self._parse_system_status()
            self._reader_name = parsed_status["reader_name"]
            return self._reader_name

        except Exception as e:
            print(f"Error retrieving reader name: {e}")
            return None

    def get_device_timezone(self) -> timezone:
        """
        Retrieve the device's timezone offset using the TZ command.

        The TZ command returns timezone information in two possible formats:
        Format 1 (hours and minutes): "Hours:minutes to UT: -3h30m"
        Format 2 (hours only): "Hours to UT: +0"

        Returns
        -------
        timezone
            Python timezone object representing the device's UTC offset,
            or None if an error occurs.
        """
        if not self._connection:
            raise ConnectionError("Not connected to device.")

        try:
            # Send TZ command and get response
            lines = self.send_command("TZ")

        except Exception as e:
            print(f"Error sending TZ command: {e}")


        # First line contains timezone offset information
        # Format 1: "Hours:minutes to UT: -3h30m"
        # Format 2: "Hours to UT: +0"
        tz_line = lines[0].strip()

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

        device_tz = self.get_device_timezone()


        # Send DT command and get response
        try:
            lines = self.send_command("DT")
        except Exception as e:
            raise Exception(f"Error sending DT command: {e}")

        # Parse the DT response: "2025-01-19 09:18:02.304 U (UT+0)"
        response_line = lines[0].strip()
        parts = response_line.split()

        if len(parts) < 3:
            raise ValueError(f"Unrecognized DT response format: {response_line}")

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

        # Create timezone-aware datetime
        datetime_obj = datetime.strptime(f"{date_str} {time_part}", "%Y-%m-%d %H:%M:%S")
        datetime_aware = datetime_obj.replace(tzinfo=device_tz)

        return {
            'datetime': datetime_aware,
            'milliseconds': milliseconds,
            'sync_status': self.TIME_STATUSES_SYNCED.get(sync_status, "Unknown"),
            'raw_output': response_line,
            'error': None
        }


    def control_device_datetime(self, tolerance_seconds: int = 15, attempt_sync: bool = False) -> dict:


        if not self._connection:
            raise ConnectionError("Not connected to device.")

        print("\n" + "=" * 70)
        print("Device Date/Time Check")


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


        print(f"Sync Status: {'✓ IN SYNC' if is_synced else '⚠ OUT OF SYNC'}")
        print("-" * 70)
        print(f"Device datetime: {device_datetime.strftime('%Y-%m-%d %H:%M:%S')} {device_tz_str} [Time source: {sync_status}]")
        print(f"System datetime: {system_datetime.strftime('%Y-%m-%d %H:%M:%S')} {system_tz_str}")
        if not is_synced:
            print(f"Time difference: {time_diff:+.1f} seconds ({abs(time_diff):.1f}s {'ahead' if time_diff > 0 else 'behind'})")
        print("=" * 70)

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
            # Ask for user confirmation
            confirm = None
            while confirm not in ['yes', 'y', 'no', 'n']:
                confirm = input("\nUpdate device time to match system time? (yes/no): ").strip().lower()

            if confirm in ['no', 'n']:
                print("Device time sync cancelled by user.")
                return report

            try:
                # Update device time: first set timezone to UTC, then send the time
                print("Updating device time...", end="", flush=True)
                print("\n  Setting device timezone to UTC...", end="", flush=True)
                self.send_command("TZ 0")
                print("Done.")

                print("  Sending device time...", end="", flush=True)
                # Send UTC time to device (device interprets DT command as UTC)
                dt_command = system_datetime_utc.strftime("DT %Y-%m-%d %H:%M:%S")
                response_lines = self.send_command(dt_command)

                report['was_updated'] = True
                report['update_command_sent'] = dt_command
                report['update_response'] = response_lines
                report['synced'] = True

                print("Done.")
                print("Device datetime updated successfully.")

            except Exception as e:
                report['error'] = f'Failed to update device datetime: {e}'
                print("ERROR.")
                print(f"Error updating device time: {e}")

        return report



    def check_system_status_health(self):
        """
        Calls for system status and checks parsed system status for potential issues.

        Returns
        -------
        dict
            Dictionary with 'healthy' (bool) and 'warnings' (list of str) keys.
        """

        print("\nChecking system status health...", end="")
        warnings = []

        parsed_status = self._parse_system_status()

        # Check supply voltage
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

        print("Done")

        # Report health status
        if not health_report['healthy']:
            print(f"\n⚠ WARNING: {len(health_report['warnings'])} issue(s) detected:")
            for warning in health_report['warnings']:
                print(f"  - {warning}")
        else:
                print("✓ System status check: All parameters within normal range")

    def export_system_status(self, output_filepath: str) -> bool:
        """
        Run the SY (system status) command and write the response to a text file.

        Parameters
        ----------
        filepath : str
            Path to the output text file where system status will be written.

        Returns
        -------
        bool
            True if successful, False otherwise.
        """

        if not self._connection:
            print("Not connected to device.")
            return False

        try:
            print(f"\nExporting system status to file...", end="")
            parsed_status = self._parse_system_status()


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

    def export_upload_log(self, output_filepath: str) -> bool:
        """
        Run the UH (upload log) command and write the response to a text file.

        Parameters
        ----------
        filepath : str
            Path to the output text file where upload log will be written.

        Returns
        -------
        bool
            True if successful, False otherwise.
        """

        if not self._connection:
            print("Not connected to device.")
            return False

        try:
            print(f"\nExporting upload log to file...", end="")
            upload_history_lines = self.send_command("UH")

            with open(output_filepath, 'w') as f:
                f.write("Oregon RFID Upload Log\n")
                f.write("Export Date/Time: " + time.strftime("%Y-%m-%d %H:%M:%S") + "\n")
                f.write("=========================\n\n")

                # Write upload log
                f.write('\n'.join(upload_history_lines))

            print("Done.")
            print(f"Upload log written to {output_filepath}")
            print(f"Total lines written: {len(upload_history_lines)}")

            return True

        except Exception as e:
            print(f"Error writing upload log to file: {e}")
            return False

    def export_system_status_log(self, date: date, output_dir:Path = Path("")) -> bool:
        """
        Run the ER command for a specific date and write to file.

        The event record shows system status every minute for the specified date.

        Parameters
        ----------
        date : date
            Date in format YYYY-MM-DD (e.g., "2026-01-08")
        output_dir : Path
            Directory where output file will be written (default: current directory)

        Returns
        -------
        bool
            True if successful, False otherwise.
        """

        if not self._connection:
            print("Not connected to device.")
            return False


        print(f"\nExporting system status log for {date.strftime('%Y-%m-%d')}...", end="")

        output_filepath = f"{output_dir}/system_log_{date.strftime('%Y_%m_%d')}.txt"

        if not output_dir.exists():
            output_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Send ER command with date
            command = f"ER {date.strftime('%Y-%m-%d')}"
            lines = self.send_command(command)

            # Generate output filename with date
            with open(output_filepath, 'w') as f:
                f.write("Oregon RFID Event Record\n")
                f.write("Export Date/Time: " + time.strftime("%Y-%m-%d %H:%M:%S") + "\n")
                f.write("Date of Record: " + date.strftime("%Y-%m-%d") + "\n")
                f.write("=========================\n\n")

                # Write event record
                f.write('\n'.join(lines))

            print("Done.")
            print(f"System status log written to {output_filepath}")
            print(f"Total lines written: {len(lines)}")

            return True

        except Exception as e:
            print("ERROR.")
            print(f"Error exporting system status log: {e}")
            return False

    def export_system_status_logs_from_last_upload(self, output_dir: Path = Path("")) -> bool:
        """
        Export system status logs for all dates from last upload date to current date (inclusive).

        This method retrieves the last upload date, then runs export_system_status_log()
        for each day in the range up to and including today.

        Parameters
        ----------
        output_dir : Path
            Directory where output files will be written (default: current directory)

        Returns
        -------
        bool
            True if all exports completed successfully, False if any failed.
        """

        if not self._connection:
            print("Not connected to device.")
            return False

        if not self._last_upload_date:
            try:
                print("Retrieving last upload date from device...", end="", flush=True)
                self._parse_upload_history()
                print("Done.")
            except Exception as e:
                print("ERROR")
                print(f"Error parsing upload history: {e}")
                print("Failed to retrieve last upload date. Cannot proceed with batch export.")
                return False

        try:
            last_upload = self._last_upload_date
            current_date = date.today()


            last_upload = date(2025,11,25) # TODO: remove after testing

            if last_upload > current_date:
                print(f"Last upload date ({last_upload}) is in the future. No logs to export.")
                return False

            print(f"\nExporting system status logs from {last_upload} to {current_date}...")

            # Generate date range
            current = last_upload
            all_successful = True
            export_count = 0

            while current <= current_date:
                success = self.export_system_status_log(current, output_dir)
                if not success:
                    all_successful = False
                else:
                    export_count += 1
                current += timedelta(days=1)

            print(f"\nBatch export complete: {export_count} system log(s) exported.")
            return all_successful

        except Exception as e:
            print(f"Error during batch export: {e}")
            return False

    def update_firmware(self, firmware_file_path: str, new_version: str) -> bool:
        """
        Update the firmware on the Oregon RFID reader.

        Process:
        1. Get current firmware version
        2. Confirm with user
        3. Turn off reader with OF command
        4. Run FW command
        5. Wait for prompt and confirm with Y
        6. Wait for "Start" prompt
        7. Send firmware file content

        Parameters
        ----------
        firmware_file_path : str
            Path to the firmware update file
        new_version : str
            Version string of the new firmware (e.g., "V2.2A")

        Returns
        -------
        bool
            True if update completed successfully, False otherwise.
        """

        if not self._connection:
            print("Not connected to device.")
            return False

        # Verify firmware file exists before starting
        try:
            with open(firmware_file_path, 'r') as f:
                firmware_content = f.read()
        except FileNotFoundError:
            print(f"\nError: Firmware file not found: {firmware_file_path}")
            return False
        except Exception as e:
            print(f"\nError reading firmware file: {e}")
            return False

        # Get current firmware version
        print("Retrieving current firmware version...", end="")
        parsed_status = self._parse_system_status()
        current_version = parsed_status.get('version', 'Unknown')
        print(f"Done. Current version: {current_version}")

        # Initial confirmation
        print("\n" + "="*60)
        print("FIRMWARE UPDATE PROCESS")
        print("="*60)

        try:

            # Final confirmation with version info
            print("\n" + "-"*60)
            print(f"Current firmware version: {current_version}")
            print(f"New firmware version:     {new_version}")
            print("-"*60)
            confirm = input("\nConfirm firmware update (yes/no): ").strip().lower()
            if confirm not in ['yes', 'y']:
                print("Firmware update cancelled by user.")
                return False

            print("\n" + "="*60)
            print("Starting firmware update process...")
            print("="*60)

            # Step 1: Read firmware file content
            print(f"\nStep 1: Reading firmware file: {firmware_file_path}...", end="", flush=True)
            with open(firmware_file_path, 'r') as f:
                firmware_content = f.read()
            print("Done.")

            # Step 2: Turn off reader
            print("\nStep 2: Turning off reader...", end="", flush=True)
            self._command_manager._send_command("OF")
            time.sleep(2)
            print("Done.")

            # Step 3: Send FW command
            print("Step 3: Initiating firmware update mode...", end="", flush=True)
            self._command_manager._send_command("FW")
            print("Done.")

            # Step 4: Wait for "Update(Y)?" prompt and send Y
            print("Step 4: Waiting for 'Update(Y)?' prompt...", end="", flush=True)
            prompt_found = False
            timeout = time.time() + 10  # 10 second timeout

            while time.time() < timeout:
                if self._connection.in_waiting:
                    line = self._connection.readline().decode(errors="ignore").strip()
                    if "update" in line.lower() and "(y)" in line.lower():
                        prompt_found = True
                        print("Received!")
                        break
                time.sleep(0.2)

            if not prompt_found:
                print("TIMEOUT!")
                print("Did not receive 'Update(Y)?' prompt. Update aborted.")
                return False

            print("Step 5: Starting update execution...", end="", flush=True)
            self._command_manager._send_command("Y")
            print("Started.")

            # Step 6: Wait for "Start" prompt
            print("Step 6: Waiting for 'Start' prompt...", end="", flush=True)
            start_found = False
            timeout = time.time() + 30  # 30 second timeout

            while time.time() < timeout:
                if self._connection.in_waiting:
                    line = self._connection.readline().decode(errors="ignore").strip()
                    if "start" in line.lower():
                        start_found = True
                        print("Received!")
                        break
                time.sleep(0.5)

            if not start_found:
                print("TIMEOUT!")
                print("Did not receive 'Start' prompt. Update may have failed.")
                return False

            # Step 7: Send firmware content
            print("Step 7: Uploading firmware data...", end="", flush=True)
            self._command_manager._send_command(firmware_content)
            print("Done.")

            # Step 8: Capture response from device
            print("Step 8: Waiting for device response...", end="", flush=True)
            response_lines = []
            response_timeout = time.time() + 60  # 60 second timeout for firmware processing
            last_data_time = time.time()

            while time.time() < response_timeout:
                if self._connection.in_waiting:
                    line = self._connection.readline().decode(errors="ignore").strip()
                    if line:
                        response_lines.append(line)
                        last_data_time = time.time()

                # If no data for 3 seconds, assume response is complete
                if time.time() - last_data_time > 3:
                    break

                time.sleep(0.2)

            print("Done.")

            # Display response
            if response_lines:
                print("\nDevice Response:")
                print("-"*60)
                for line in response_lines:
                    print(line)
                print("-"*60)
            else:
                print("\nNo response received from device.")

            # Make user verfiy update success
            print("\nPlease verify the firmware update was successful.")
            verify = None
            while verify not in ['yes', 'y', 'no', 'n']:
                verify = input("Did the update complete successfully? (yes/no): ").strip().lower()

            if verify in ['no', 'n']:
                print("Firmware update reported as unsuccessful by user.")
                return False
            else:
                print("Firmware update reported as successful by user.")

            print("\n" + "="*60)
            print("FIRMWARE UPDATE COMPLETED")
            print("="*60)

            return True

        except Exception as e:
            print(f"\nError during firmware update: {e}")
            return False




