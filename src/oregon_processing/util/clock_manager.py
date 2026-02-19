# -*- coding: utf-8 -*-
"""
Oregon RFID Clock Manager - Handles device date/time operations
"""

import logging
from datetime import datetime, timedelta, timezone




class ClockManager:
    """Manages device clock synchronization and datetime operations."""

    TIME_STATUSES_SYNCED = {
        'G': "GNSS Time",
        'N': "Network time using CAT5 cable",
        'U': "Uncalibrated (entered with DT command)",
        'E': "Ellapsed time since power-up"
    }

    def __init__(self, communicator, command_manager):
        """
        Initialize ClockManager.

        Parameters
        ----------
        communicator : Communicator
            Communicator instance for device communication.
        command_manager : CommandManager
            CommandManager instance for sending commands to device.
        """
        self._communicator = communicator
        self._command_manager = command_manager
        self._logger = logging.getLogger('oregon_processing.clock_manager')

    def __enter__(self):
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        pass

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
        logging_extra = {'process_name': 'Clock Manager'}

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
                self._logger.exception(f"Failed to parse hours and minutes from TZ response: {tz_line}", extra=logging_extra)
                raise

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

        logging_extra = {'process_name': 'Clock Manager'}

        parts = dt_line.split()

        if len(parts) < 2:
            raise ValueError(f"Unrecognized DT response format: {dt_line}")

        # Handle elapsed time format: HH:MM:SS.milliseconds E
        if parts[-1] == 'E' or (len(parts) == 2 and parts[-1] in 'GNUE'):
            if len(parts) != 2:
                raise ValueError(f"Unrecognized DT response format: {dt_line}")

            sync_status = parts[-1]
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
                self._logger.exception(f"Failed to parse hours, minutes, and seconds from DT response: {dt_line}", extra=logging_extra)
                raise

            # Create timedelta for elapsed time
            elapsed = timedelta(hours=hours, minutes=minutes, seconds=seconds, milliseconds=milliseconds)

            return {
                'datetime': None,
                'elapsed_time': elapsed,
                'milliseconds': milliseconds,
                'sync_status': sync_status
            }

        # Handle absolute datetime format: YYYY-MM-DD HH:MM:SS.milliseconds [G|N|U] [optional timezone]
        if len(parts) < 3:
            raise ValueError(f"Unrecognized DT response format: {dt_line}")

        date_str = parts[0]  # YYYY-MM-DD
        time_str = parts[1]  # HH:MM:SS.milliseconds
        sync_status = parts[2]  # G, N, or U (single character)

        # Validate sync status is a single recognized character
        if sync_status not in self.TIME_STATUSES_SYNCED:
            raise ValueError(f"Unrecognized sync status '{sync_status}' in DT response: {dt_line}")

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

        logging_extra = {'process_name': 'Clock Manager'}

        # Send DT command and get response
        try:
            lines = self._command_manager.send_command("DT")
        except Exception as e:
            self._logger.exception(f"Failed to send DT command.", extra=logging_extra)
            raise

        if len(lines) != 1:
            raise ValueError(f"Unexpected number of lines in DT response: {len(lines)}")

        parsed_dt = self._parse_dt_response(lines[0].strip())

        # If elapsed time (sync_status 'E'), return without querying timezone
        # Always fetch timezone so it is available even in elapsed-time mode
        try:
            lines = self._command_manager.send_command("TZ")
        except Exception as e:
            self._logger.exception(f"Failed to send TZ command.", extra=logging_extra)
            raise

        if len(lines) != 2: # TODO is it always two lines or does it vary based on sync status?
            raise ValueError(f"Unexpected number of lines in TZ response: {len(lines)}")

        tz_line = lines[0].strip()
        device_tz = self._parse_tz_response(tz_line)

        if parsed_dt['sync_status'] == 'E':
            return {
                'datetime': None,
                'elapsed_time': parsed_dt['elapsed_time'],
                'milliseconds': parsed_dt['milliseconds'],
                'sync_status': parsed_dt['sync_status'],
                'timezone': device_tz
            }

        device_dt = parsed_dt['datetime']
        datetime_aware = device_dt.replace(tzinfo=device_tz)

        return {
            'datetime': datetime_aware,
            'elapsed_time': None,
            'milliseconds': parsed_dt['milliseconds'],
            'sync_status': parsed_dt['sync_status'],
            'timezone': device_tz
        }

    def _sync_device_time(self, computer_datetime_utc: datetime, report: dict) -> None:
        """
        Synchronize device time with computer time.

        Parameters
        ----------
        computer_datetime_utc : datetime
            Computer datetime in UTC timezone.
        report : dict
            Report dictionary to update with sync results.
        """
        logging_extra_sync = {'process_name': 'Clock Sync'}

        self._logger.info("Setting device timezone to UTC.", extra=logging_extra_sync)
        self._command_manager.send_command("TZ 0")

        self._logger.info(f"Setting device time to {computer_datetime_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC.", extra=logging_extra_sync)
        dt_command = computer_datetime_utc.strftime("DT %Y-%m-%d %H:%M:%S")
        response_lines = self._command_manager.send_command(dt_command)

        report['was_updated'] = True
        report['update_command_sent'] = dt_command
        report['update_response'] = response_lines
        report['error'] = None
        report['elapsed_time'] = None

    def _refresh_after_update(self, computer_datetime_utc: datetime, tolerance_seconds: int, report: dict) -> None:
        """
        Refresh device datetime after sync and update report.

        Parameters
        ----------
        computer_datetime_utc : datetime
            Computer datetime in UTC timezone.
        tolerance_seconds : int
            Acceptable difference in seconds before device is considered out of sync.
        report : dict
            Report dictionary to update with refreshed device datetime.
        """
        refreshed = self.get_device_datetime()
        if refreshed['datetime']:
            device_dt = refreshed['datetime']
            device_dt_utc = device_dt.astimezone(timezone.utc)
            diff = (device_dt_utc - computer_datetime_utc).total_seconds()
            report['device_datetime'] = device_dt
            report['difference_seconds'] = diff
            report['synced'] = abs(diff) <= tolerance_seconds
        else:
            report['device_datetime'] = None
            report['difference_seconds'] = None
            report['synced'] = False

    def _print_clock_status(self, is_synced: bool, device_dt, device_tz, elapsed, computer_dt, time_diff, sync_status_name: str) -> None:
        """
        Print clock status information.

        Parameters
        ----------
        is_synced : bool
            Whether device time is in sync with computer time.
        device_dt : datetime or None
            Device datetime (None if elapsed time only).
        device_tz : timezone
            Device timezone.
        elapsed : timedelta or None
            Elapsed time since power-up (None if absolute datetime).
        computer_dt : datetime
            Computer datetime.
        time_diff : float or None
            Time difference in seconds (None if elapsed time).
        sync_status_name : str
            Human-readable sync status name.
        """
        logging_extra = {'process_name': 'Clock Manager'}


        device_tz_str = f"(UT{device_tz.utcoffset(None).total_seconds() / 3600:+.1f})" if device_tz else "(unknown)"
        computer_offset_hours = computer_dt.astimezone().utcoffset().total_seconds() / 3600
        computer_tz_str = f"(UT{computer_offset_hours:+.1f})"

        status_message = f"Device Clock Status: {'✓ IN SYNC' if is_synced else '⚠ OUT OF SYNC'} | Device Clock Source: {sync_status_name}"
        self._logger.info(status_message, extra=logging_extra)

        if device_dt:
            self._logger.info(f"Device Time: {device_dt.strftime('%Y-%m-%d %H:%M:%S')} {device_tz_str}", extra=logging_extra)
        else:
            # Format timedelta as HH:MM:SS.mmm
            total_seconds = int(elapsed.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            milliseconds = elapsed.microseconds // 1000
            self._logger.info(f"Device Time: elapsed-only (no absolute time): {hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}", extra=logging_extra)

        self._logger.info(f"Computer Time: {computer_dt.strftime('%Y-%m-%d %H:%M:%S')} {computer_tz_str}", extra=logging_extra)

        if time_diff is not None and not is_synced:
            self._logger.info(f"Computer/Device Time Difference: {time_diff:+.1f}s ({abs(time_diff):.1f}s {'ahead' if time_diff > 0 else 'behind'})", extra=logging_extra)

    def control_device_datetime(self, tolerance_seconds: int = 15, attempt_sync: bool = True) -> dict:
        """
        Check if device datetime is synchronized with computer time and optionally update it.

        When device has elapsed time only (not synchronized), displays uptime and returns with error.
        When device has absolute datetime, compares with computer time and prompts for sync if needed.

        Parameters
        ----------
        tolerance_seconds : int
            Acceptable difference in seconds before device is considered out of sync. Default: 15
        attempt_sync : bool
            If True and out of sync, prompt user to update device time. Default: True

        Returns
        -------
        dict
            Report with keys: synced, device_datetime, elapsed_time, computer_datetime,
            difference_seconds, was_updated, update_command_sent, update_response, error
        """

        logging_extra = {'process_name': 'Clock Manager'}

        self._logger.info("Checking device date/time.", extra=logging_extra)

        device_result = self.get_device_datetime()
        computer_datetime = datetime.now()
        computer_datetime_utc = computer_datetime.astimezone(timezone.utc)

        # Initialize report with defaults
        report = {
            'synced': False,
            'device_datetime': None,
            'elapsed_time': None,
            'computer_datetime': computer_datetime,
            'difference_seconds': None,
            'was_updated': False,
            'update_command_sent': None,
            'update_response': None,
            'error': None
        }

        sync_status = device_result['sync_status']
        sync_status_name = self.TIME_STATUSES_SYNCED[sync_status]

        device_tz = device_result['timezone']
        device_elapsed_time = device_result['elapsed_time']
        device_datetime = device_result['datetime']

        if sync_status == 'E':
            # No absolute datetime available
            time_diff = None
            is_synced = False
        else:
            device_datetime_utc = device_datetime.astimezone(timezone.utc)
            time_diff = (device_datetime_utc - computer_datetime_utc).total_seconds()
            is_synced = abs(time_diff) <= tolerance_seconds

        self._print_clock_status(is_synced, device_datetime, device_tz, device_elapsed_time, computer_datetime, time_diff, sync_status_name)

        # Update report
        report['synced'] = is_synced
        report['device_datetime'] = device_datetime
        report['difference_seconds'] = time_diff

        # Attempt sync if out of sync and requested
        if not is_synced and attempt_sync:

            confirm = None
            while confirm not in ['y', 'yes', 'n', 'no']:
                confirm = input("\nUpdate device time to match computer time? (yes/no): ").strip().lower()
                print() # Add spacing after input for cleaner output

            if confirm not in ['y', 'yes']:
                self._logger.info("User selected not to sync device time.", extra=logging_extra)

                return report
            else:
                self._logger.info("User selected to synch computer/device times.", extra=logging_extra)

            try:
                self._sync_device_time(computer_datetime_utc, report)
                self._refresh_after_update(computer_datetime_utc, tolerance_seconds, report)
            except Exception as e:
                report['error'] = f'Failed to update device datetime: {e}'
                self._logger.error(f"Failed to update device datetime: {e}", extra=logging_extra)

            # Final report of clock status after attempted update
            self._print_clock_status(
                report['synced'],
                report['device_datetime'],
                device_tz,
                device_elapsed_time,
                report['computer_datetime'],
                report['difference_seconds'],
                sync_status_name
            )

        return report


