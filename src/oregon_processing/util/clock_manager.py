# -*- coding: utf-8 -*-
"""
Oregon RFID Clock Manager - Handles device date/time operations
"""

from datetime import datetime, timedelta, timezone


class ClockManager:
    """Manages device clock synchronization and datetime operations."""

    TIME_STATUSES_SYNCED = {
        'G': "GNSS Time",
        'N': "Network time using CAT5 cable",
        'U': "Uncalibrated (entered with DT command)",
        'E': "Ellapsed time since power-up"
    }

    def __init__(self, command_manager):
        """
        Initialize ClockManager.

        Parameters
        ----------
        command_manager : CommandManager
            Reference to the CommandManager for sending device commands.
        """
        self.command_manager = command_manager

    def _parse_tz_response(self, tz_line: str) -> timezone:
        """
        Parse timezone response from TZ command.

        Parameters
        ----------
        tz_line : str
            The raw TZ response line from the device.

        Returns
        -------
        timezone
            Timezone object representing the device's timezone offset.
        """
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

        When sync_status is 'E' (elapsed time since power-up), the response contains only
        time (HH:MM:SS.milliseconds) instead of a full date.

        Parameters
        ----------
        dt_line : str
            The raw DT response line from the device.

        Returns
        -------
        dict
            Parsed DT response with keys:
            - 'datetime': datetime object (None if elapsed time)
            - 'elapsed_time': timedelta object (None if absolute datetime)
            - 'milliseconds': Milliseconds component (int, 0-999)
            - 'sync_status': Single character sync status ('G', 'N', 'U', or 'E')
        """

        parts = dt_line.split()

        if len(parts) < 2:
            raise ValueError(f"Unrecognized DT response format: {dt_line}")

        sync_status = parts[-1]  # Last element is always sync status

        # Handle elapsed time format: HH:MM:SS.milliseconds E
        if sync_status == 'E':
            if len(parts) != 2:
                raise ValueError(f"Unrecognized DT response format: {dt_line}")

            time_str = parts[0]  # HH:MM:SS.milliseconds

            # Parse time and milliseconds
            if '.' in time_str:
                time_part, milliseconds_str = time_str.split('.')
                milliseconds = int(milliseconds_str)
            else:
                time_part = time_str
                milliseconds = 0

            # Parse time components
            try:
                hours, minutes, seconds = map(int, time_part.split(':'))
            except ValueError:
                raise ValueError(f"Unrecognized DT response format: {dt_line}")

            # Create timedelta for elapsed time
            elapsed = timedelta(hours=hours, minutes=minutes, seconds=seconds, milliseconds=milliseconds)

            return {
                'datetime': None,
                'elapsed_time': elapsed,
                'milliseconds': milliseconds,
                'sync_status': sync_status
            }

        # Handle absolute datetime format: YYYY-MM-DD HH:MM:SS.milliseconds [G|N|U]
        if len(parts) < 3:
            raise ValueError(f"Unrecognized DT response format: {dt_line}")

        date_str = parts[0]  # YYYY-MM-DD
        time_str = parts[1]  # HH:MM:SS.milliseconds

        # Parse time and milliseconds
        if '.' in time_str:
            time_part, milliseconds_str = time_str.split('.')
            milliseconds = int(milliseconds_str)
        else:
            time_part = time_str
            milliseconds = 0

        return {
            'datetime': datetime.strptime(f"{date_str} {time_part}", "%Y-%m-%d %H:%M:%S"),
            'elapsed_time': None,
            'milliseconds': milliseconds,
            'sync_status': sync_status
        }

    def get_device_datetime(self) -> dict:
        """
        Retrieve the device's current date and time using the DT and TZ commands.

        When sync_status is 'E' (elapsed time), returns elapsed_time instead of datetime.
        When sync_status is 'G', 'N', or 'U', returns timezone-aware datetime object.

        Returns
        -------
        dict
            Parsed device datetime with keys:
            - 'datetime': Timezone-aware datetime object (None if elapsed time)
            - 'elapsed_time': timedelta object (None if absolute datetime)
            - 'milliseconds': Milliseconds component (int, 0-999)
            - 'sync_status': Single character sync status ('G', 'N', 'U', or 'E')
        """

        # Send DT command and get response
        try:
            lines = self.command_manager.send_command_and_receive_response("DT")
        except Exception as e:
            raise Exception(f"Error sending DT command: {e}")

        if len(lines) != 1:
            raise ValueError(f"Unexpected number of lines in DT response: {len(lines)}")

        parsed_dt = self._parse_dt_response(lines[0].strip())

        # If elapsed time (sync_status 'E'), return without querying timezone
        if parsed_dt['sync_status'] == 'E':
            return {
                'datetime': None,
                'elapsed_time': parsed_dt['elapsed_time'],
                'milliseconds': parsed_dt['milliseconds'],
                'sync_status': parsed_dt['sync_status'],
            }

        # For absolute datetime, query timezone offset
        try:
            lines = self.command_manager.send_command_and_receive_response("TZ")
        except Exception as e:
            raise Exception(f"Error sending TZ command: {e}")

        tz_line = lines[0].strip()
        device_tz = self._parse_tz_response(tz_line)

        device_dt = parsed_dt['datetime']
        datetime_aware = device_dt.replace(tzinfo=device_tz)

        return {
            'datetime': datetime_aware,
            'elapsed_time': None,
            'milliseconds': parsed_dt['milliseconds'],
            'sync_status': parsed_dt['sync_status'],
        }

    def control_device_datetime(self, tolerance_seconds: int = 15, attempt_sync: bool = True) -> dict:
        """
        Check if device datetime is synchronized with system time and optionally update it.

        When device has elapsed time only (not synchronized), displays uptime and returns with error.
        When device has absolute datetime, compares with system time and prompts for sync if needed.

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

        print("\n" + "=" * 70, flush=True)
        print("DEVICE DATE/TIME CHECK", flush=True)
        print("=" * 70, flush=True)

        device_result = self.get_device_datetime()
        system_datetime = datetime.now()
        system_datetime_utc = system_datetime.astimezone(timezone.utc)

        # Initialize report with defaults
        report = {
            'synced': False,
            'device_datetime': None,
            'elapsed_time': None,
            'system_datetime': system_datetime,
            'difference_seconds': None,
            'was_updated': False,
            'update_command_sent': None,
            'update_response': None,
            'error': None
        }

        # Handle elapsed time case (device not synchronized)
        if device_result['datetime'] is None:
            print("\n" + "-" * 70)
            print("TIME STATUS")
            print("-" * 70)
            print(f"Status: ⚠ OUT OF SYNC", flush=True)
            sync_status_name = self.TIME_STATUSES_SYNCED.get(device_result['sync_status'], "Unknown")
            print(f"Sync Source: {sync_status_name}")
            print(f"Elapsed Time: {device_result['elapsed_time']}", flush=True)
            print(f"System Time: {system_datetime.strftime('%Y-%m-%d %H:%M:%S')} (local)", flush=True)
            print("\n⚠ Device clock is not synchronized. Cannot perform time-dependent operations.")

            report['elapsed_time'] = device_result['elapsed_time']
            report['error'] = 'Device clock not synchronized (elapsed time mode)'

            print("\n" + "=" * 70)
            print("CHECK COMPLETE")
            print("=" * 70)
            return report

        # Handle absolute datetime
        device_datetime = device_result['datetime']
        device_datetime_utc = device_datetime.astimezone(timezone.utc)
        time_diff = (device_datetime_utc - system_datetime_utc).total_seconds()
        is_synced = abs(time_diff) <= tolerance_seconds

        # Display sync status
        print("\n" + "-" * 70)
        print("SYNC STATUS")
        print("-" * 70)

        device_offset_hours = device_datetime.utcoffset().total_seconds() / 3600
        system_offset_hours = system_datetime.astimezone().utcoffset().total_seconds() / 3600
        device_tz_str = f"(UT{device_offset_hours:+.1f})"
        system_tz_str = f"(UT{system_offset_hours:+.1f})"

        print(f"Status: {'✓ IN SYNC' if is_synced else '⚠ OUT OF SYNC'}", flush=True)
        sync_status_name = self.TIME_STATUSES_SYNCED.get(device_result['sync_status'], "Unknown")
        print(f"Device Time: {device_datetime.strftime('%Y-%m-%d %H:%M:%S')} {device_tz_str} [Source: {sync_status_name}]")
        print(f"System Time: {system_datetime.strftime('%Y-%m-%d %H:%M:%S')} {system_tz_str}")

        if not is_synced:
            print(f"Difference: {time_diff:+.1f}s ({abs(time_diff):.1f}s {'ahead' if time_diff > 0 else 'behind'})")

        # Update report
        report['synced'] = is_synced
        report['device_datetime'] = device_datetime
        report['difference_seconds'] = time_diff

        # Attempt sync if out of sync and requested
        if not is_synced and attempt_sync:
            print("\n" + "-" * 70)
            print("CLOCK SYNC ACTION REQUIRED")
            print("-" * 70)

            confirm = None
            while confirm not in ['y', 'yes', 'n', 'no']:
                confirm = input("\nUpdate device time to match system time? (yes/no): ").strip().lower()

            if confirm not in ['y', 'yes']:
                print("Device time sync cancelled.")
                print("\n" + "=" * 70)
                print("CHECK COMPLETE")
                print("=" * 70)
                return report

            try:
                print("\n" + "-" * 70)
                print("UPDATING DEVICE TIME")
                print("-" * 70)

                print("Setting device timezone to UTC...", end="", flush=True)
                self.command_manager.send_command_and_receive_response("TZ 0")
                print("Done.")

                print("Sending device time...", end="", flush=True)
                dt_command = system_datetime_utc.strftime("DT %Y-%m-%d %H:%M:%S")
                response_lines = self.command_manager.send_command_and_receive_response(dt_command)
                print("Done.")

                report['was_updated'] = True
                report['update_command_sent'] = dt_command
                report['update_response'] = response_lines
                report['synced'] = True

            except Exception as e:
                report['error'] = f'Failed to update device datetime: {e}'
                print("ERROR.")
                print(f"\nError: {e}")

        print("\n" + "=" * 70)
        print("CHECK COMPLETE")
        print("=" * 70)
        return report
