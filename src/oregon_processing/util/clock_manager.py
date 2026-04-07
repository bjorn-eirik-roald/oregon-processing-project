# -*- coding: utf-8 -*-
"""
Oregon RFID Clock Manager - Handles device date/time operations
"""
from __future__ import annotations
from typing import TYPE_CHECKING
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from oregon_processing.util.logging_manager import get_logger
from oregon_processing.util.exceptions import CommandTransmissionError, UnexpectedResponseError

if TYPE_CHECKING:
    from oregon_processing.util.command_manager import CommandManager


@dataclass
class ClockStatus:
    datetime: datetime | None = None
    elapsed_time: timedelta | None = None
    sync_status: str | None = None
    timezone: timezone | None = None

@dataclass
class ClockCheckResult:
    synced: bool
    device_datetime: datetime | None
    device_elapsed_time: timedelta | None
    computer_datetime: datetime
    difference_seconds: float | None

class ClockManager:
    """Manages device clock synchronization and datetime operations."""

    TIME_STATUSES = {
        'G': "GNSS Time",
        'N': "Network time using CAT5 cable",
        'U': "Uncalibrated (entered with DT command)",
        'E': "Ellapsed time since power-up"
    }

    def __init__(self, command_manager: CommandManager):
        """
        Initialize ClockManager.

        Parameters
        ----------
        command_manager : CommandManager
            CommandManager instance for sending commands to device.
        """
        self._logger = get_logger(__name__)

        self._command_manager = command_manager

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
        ClockCheckResult
            Data class instance with attributes: synced, device_datetime, elapsed_time, computer_datetime,
            difference_seconds, was_updated, update_command_sent, update_response, error
        """




        is_synced, time_diff, device_clock_status, computer_datetime = self._check_if_synched(tolerance_seconds=tolerance_seconds)

        clock_check_result = ClockCheckResult(
            synced=is_synced,
            device_datetime=device_clock_status.datetime,
            device_elapsed_time=device_clock_status.elapsed_time,
            computer_datetime=computer_datetime,
            difference_seconds=time_diff,
            )

        self._print_clock_status(is_synced, device_clock_status, computer_datetime, time_diff)


        # Attempt sync if out of sync and requested
        if not is_synced and attempt_sync:

            confirm = None
            while confirm not in ['y', 'yes', 'n', 'no']:
                confirm = input("\nUpdate device time to match computer time? (yes/no): ").strip().lower()
                print() # Add spacing after input for cleaner output

            if confirm in ['n', 'no']:
                self._logger.debug("User selected not to sync device time.")

                return clock_check_result

            elif confirm in ['y', 'yes']:
                self._logger.debug("User selected to synch computer/device times.")

            try:
                self._sync_device_time()
                is_synced, time_diff, device_clock_status, computer_datetime = self._check_if_synched(tolerance_seconds=tolerance_seconds)
                self._print_clock_status(is_synced, device_clock_status, computer_datetime, time_diff)
                clock_check_result.synced = is_synced
                clock_check_result.device_datetime = device_clock_status.datetime
                clock_check_result.device_elapsed_time = device_clock_status.elapsed_time
                clock_check_result.computer_datetime = computer_datetime


            except Exception as e:
                error_message = f"Failed to synchronize device time: {e}"
                self._logger.error(error_message)
                clock_check_result.error = error_message

            return clock_check_result

    def _get_device_datetime(self) -> ClockStatus:
        """
        Retrieve the device's current date and time using the DT and TZ commands.

        When sync_status is 'E' (elapsed time), returns elapsed_time instead of datetime.
        When sync_status is 'G', 'N', or 'U', returns timezone-aware datetime object.

        Returns
        -------
        ClockStatus
            Parsed device datetime with attributes:

            - 'datetime': Timezone-aware datetime object (None if elapsed time)
            - 'elapsed_time': timedelta object (None if absolute datetime)
            - 'milliseconds': Milliseconds component (int, 0-999)
            - 'timezone': Timezone object (None if elapsed time)
            - 'sync_status': Single character sync status ('G', 'N', 'U', or 'E')
        """


        clock_status: ClockStatus = ClockStatus()

        # Send DT command and get response
        dt_line: str = self._send_dt_command()
        self._parse_dt_response(dt_line, clock_status)


        tz_line: str = self._send_tz_command()
        self._parse_tz_response(tz_line, clock_status)

        device_datetime = clock_status.datetime
        device_tz = clock_status.timezone

        device_datetime_tz_aware = device_datetime.replace(tzinfo=device_tz) if device_datetime and device_tz else None
        clock_status.datetime = device_datetime_tz_aware

        return clock_status

    def _check_if_synched(self, tolerance_seconds: int) -> bool:
        """
        Compare device and computer datetimes and return whether they are in sync.

        Parameters
        ----------
        device_clock_status : ClockStatus
            Device clock status object.
        computer_datetime : datetime
            Computer datetime (assumed to be timezone-aware).
        tolerance_seconds : int
            Acceptable difference in seconds before device is considered out of sync.

        Returns
        -------
        float
            Difference in seconds between device and computer datetimes.
        """

        device_clock_status: ClockStatus = self._get_device_datetime()

        computer_datetime = datetime.now()

        sync_status = device_clock_status.sync_status

        device_datetime = device_clock_status.datetime

        if sync_status == 'E':
            # No absolute datetime available
            time_diff = None
            is_synced = False
        else:
            device_datetime_utc = device_datetime.astimezone(timezone.utc)
            computer_datetime_utc = computer_datetime.astimezone(timezone.utc)
            time_diff = abs(device_datetime_utc - computer_datetime_utc).total_seconds()
            is_synced = time_diff <= tolerance_seconds

        return is_synced, time_diff, device_clock_status, computer_datetime

    def _print_clock_status(self, is_synced: bool, device_clock_status: ClockStatus, computer_dt, time_diff) -> None:
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

        sync_status_name = self.TIME_STATUSES[device_clock_status.sync_status]
        device_tz = device_clock_status.timezone
        device_dt = device_clock_status.datetime
        device_elapsed_time = device_clock_status.elapsed_time

        device_tz_str = f"(UT{device_tz.utcoffset(None).total_seconds() / 3600:+.1f})" if device_tz else "(unknown)"
        computer_offset_hours = computer_dt.astimezone().utcoffset().total_seconds() / 3600
        computer_tz_str = f"(UT{computer_offset_hours:+.1f})"

        status_message = f"Device Clock Status:\n    {'✓ IN SYNC' if is_synced else '⚠ OUT OF SYNC'}\n    Device Clock Source: {sync_status_name}\n"


        if device_dt:
            status_message += f"    Device Time: {device_dt.strftime('%Y-%m-%d %H:%M:%S')} {device_tz_str}\n"
        else:
            # Format timedelta as HH:MM:SS.mmm
            total_seconds = int(device_elapsed_time.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            milliseconds = device_elapsed_time.microseconds // 1000
            status_message += f"    Device Time: elapsed-only (no absolute time): {hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}\n"

        status_message += f"    Computer Time: {computer_dt.strftime('%Y-%m-%d %H:%M:%S')} {computer_tz_str}"

        if time_diff is not None and not is_synced:
            status_message += f"\n    Computer/Device Time Difference: {time_diff:+.1f}s ({abs(time_diff):.1f}s {'ahead' if time_diff > 0 else 'behind'})"

        self._logger.info(status_message)

    def _sync_device_time(self) -> bool:
        """
        Synchronize device time with computer time.

        Parameters
        ----------
        computer_datetime : datetime
            Computer datetime (assumed to be timezone-aware).
        """


        self._logger.debug("Setting device timezone to UTC.")
        self._command_manager.send_command("TZ 0")
        self._logger.info(f"Device timezone set to UTC.")

        self._logger.debug(f"Setting device time to {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC.")
        computer_datetime_utc = datetime.now().astimezone(timezone.utc)
        dt_command = computer_datetime_utc.strftime("DT %Y-%m-%d %H:%M:%S")
        response_lines = self._command_manager.send_command(dt_command)

        if len(response_lines) == 0:
            error_message = "No response received after sending DT command."
            self._logger.error(error_message)
            raise CommandTransmissionError(error_message)

        self._logger.info(f"Device time was updated to {computer_datetime_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC.")

        return True

    def _send_dt_command(self) -> str:
        try:
            lines = self._command_manager.send_command("DT")
        except Exception as e:
            error_message = f"Failed to send DT command: {e}"
            self._logger.error(error_message)
            raise CommandTransmissionError(error_message)

        if len(lines) != 1:
            error_message = f"Unexpected number of lines in DT response: {len(lines)}. Response: {lines}"
            self._logger.error(error_message)
            raise UnexpectedResponseError(error_message)

        dt_line = lines[0].strip()

        return dt_line

    def _parse_dt_response(self, dt_line: str, clock_status: ClockStatus = None) -> ClockStatus:
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
        ClockStatus
            Parsed DT response encapsulated in a ClockStatus object.

        """

        if not clock_status:
            clock_status = ClockStatus()

        parts = dt_line.split()

        if len(parts) < 2:
            error_message = f"Unrecognized DT response format: {dt_line}"
            self._logger.error(error_message)
            raise UnexpectedResponseError(error_message)

        dt_line_format = None
        if parts[-1] == 'E':
            dt_line_format = "elapsed"
        elif parts[-1] in 'GNU':
            dt_line_format = "absolute"
        else:
            error_message = f"Unrecognized DT response format: {dt_line}"
            self._logger.error(error_message)
            raise UnexpectedResponseError(error_message)

        if dt_line_format == "elapsed":
            clock_status: ClockStatus = self._parse_elapsed_time_dt_response(dt_line, clock_status)
        elif dt_line_format == "absolute":
            clock_status: ClockStatus = self._parse_absolute_dt_response(dt_line, clock_status)

        return clock_status

    def _parse_elapsed_time_dt_response(self, dt_line: str, clock_status: ClockStatus = None) -> ClockStatus:
        """
        Parse a DT response line that contains elapsed time since power-up.

        Expected format: "HH:MM:SS.milliseconds E"

        Parameters
        ----------
        dt_line : str
            The raw DT response line from the device.

        Returns
        -------
        ClockStatus
            Parsed DT response encapsulated in a ClockStatus object with elapsed_time and sync_status.
        """

        if not clock_status:
            clock_status = ClockStatus()

        parts = dt_line.split()

        if len(parts) != 2:
            error_message = f"Unrecognized DT response format: {dt_line}"
            self._logger.error(error_message)
            raise UnexpectedResponseError(error_message)

        sync_status: str = parts[-1] # E for elapsed time
        time_str = parts[0]  # HH:MM:SS.milliseconds or HH:MM:SS if no milliseconds

        # Parse time and milliseconds
        milliseconds_used = '.' in time_str

        if milliseconds_used:
            time_part, milliseconds_str = time_str.split('.')
            milliseconds: int = int(milliseconds_str)
        else:
            time_part = time_str
            milliseconds: int = 0

        # Parse time components
        try:
            hours, minutes, seconds = [int(part) for part in time_part.split(':')]
        except ValueError:
            error_message = f"Failed to parse hours, minutes, and seconds from DT response: {dt_line}"
            self._logger.error(error_message)
            raise UnexpectedResponseError(error_message)

        # Create timedelta for elapsed time
        elapsed_time: timedelta = timedelta(hours=hours, minutes=minutes, seconds=seconds, milliseconds=milliseconds)

        clock_status.elapsed_time = elapsed_time
        clock_status.sync_status = sync_status
        return clock_status

    def _parse_absolute_dt_response(self, dt_line: str, clock_status: ClockStatus = None) -> ClockStatus:
        """
        Parse a DT response line that contains absolute datetime.

        Expected format: "YYYY-MM-DD HH:MM:SS.milliseconds [G|N|U] [optional timezone]"

        Parameters
        ----------
        dt_line : str
            The raw DT response line from the device.

        Returns
        -------
        ClockStatus
            Parsed DT response encapsulated in a ClockStatus object with datetime, sync_status, and timezone.
        """

        if not clock_status:
            clock_status = ClockStatus()

        parts = dt_line.split()
        if len(parts) < 3:
            error_message = f"Unrecognized DT response format: {dt_line}"
            self._logger.error(error_message)
            raise UnexpectedResponseError(error_message)

        date_str = parts[0]  # YYYY-MM-DD
        time_str = parts[1]  # HH:MM:SS.milliseconds
        sync_status: str = parts[2]  # G, N, or U (single character)

        # Validate sync status is a single recognized character
        if sync_status not in self.TIME_STATUSES:
            error_message = f"Unrecognized sync status '{sync_status}' in DT response: {dt_line}"
            self._logger.error(error_message)
            raise UnexpectedResponseError(error_message)

        # Parse time and milliseconds
        milliseconds_used = '.' in time_str

        if milliseconds_used:
            time_part, milliseconds_str = time_str.split('.')
            milliseconds = int(milliseconds_str)
        else:
            time_part = time_str
            milliseconds = 0

        dt_temp = datetime.strptime(f"{date_str} {time_part}", "%Y-%m-%d %H:%M:%S")
        day, month, year, hour, minute, second = dt_temp.day, dt_temp.month, dt_temp.year, dt_temp.hour, dt_temp.minute, dt_temp.second

        dt = datetime(year, month, day, hour, minute, second, microsecond=milliseconds*1000)

        clock_status.datetime = dt
        clock_status.sync_status = sync_status

        return clock_status

    def _send_tz_command(self) -> str:
        try:
            lines = self._command_manager.send_command("TZ")
        except Exception as e:
            error_message = f"Failed to send TZ command: {e}"
            self._logger.error(error_message)
            raise CommandTransmissionError(error_message)

        if len(lines) != 2: # TODO is it always two lines or does it vary based on sync status?
            error_message = f"Unexpected number of lines in TZ response: {len(lines)}. Response: {lines}"
            self._logger.error(error_message)
            raise UnexpectedResponseError(error_message)

        tz_line = lines[0].strip()

        return tz_line

    def _parse_tz_response(self, tz_line: str, clock_status: ClockStatus = None) -> timezone:
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

        if not clock_status:
            clock_status = ClockStatus()

        hours = 0
        minutes = 0
        sign = 1

        tz_line_format = None
        if tz_line.startswith("Hours:minutes to UT:"):
            tz_line_format = "hours_minutes"
        elif tz_line.startswith("Hours to UT:"):
            tz_line_format = "hours_only"
        else:
            error_message = f"Unrecognized timezone format: {tz_line}"
            self._logger.error(error_message)
            raise UnexpectedResponseError(error_message)

        # FORMAT 1: "Hours:minutes to UT: +3h30m"
        if tz_line_format == "hours_minutes":
            offset_part = tz_line.split("Hours:minutes to UT:")[1].strip()

            # Determine sign of timezone offset
            if offset_part.startswith('-'):
                sign = -1
                offset_part = offset_part[1:]
            elif offset_part.startswith('+'):
                sign = 1
                offset_part = offset_part[1:]
            else:
                error_message = f"Unrecognized timezone format. No sign found: {tz_line}"
                self._logger.error(error_message)
                raise UnexpectedResponseError(error_message)

            # Parse hours and minutes
            try:
                hours = int(offset_part.split('h')[0].strip())
                minutes = int(offset_part.split('h')[1].strip().split('m')[0].strip())
            except (IndexError, ValueError) as e:
                error_message = f"Failed to parse hours and minutes from TZ response: {tz_line}"
                self._logger.error(error_message)
                raise UnexpectedResponseError(error_message)


        #FORMAT 2: "Hours to UT: +0"
        elif tz_line_format == "hours_only":
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
                error_message = f"Unrecognized timezone format. No sign found: {tz_line}"
                self._logger.error(error_message)
                raise UnexpectedResponseError(error_message)

            # Parse hours only
            hours = int(offset_part)



        # Calculate total offset and return timezone object
        total_seconds = sign * (hours * 3600 + minutes * 60)

        return timezone(timedelta(seconds=total_seconds))
