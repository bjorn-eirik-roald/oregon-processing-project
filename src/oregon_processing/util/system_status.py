from oregon_processing.util.command_manager import CommandManager
from oregon_processing.util.logging_manager import get_logger

from oregon_processing.util.exceptions import UnexpectedResponseError
from oregon_processing.util.device_mode_manager import DeviceModeManager

from dataclasses import dataclass, field
from typing import Optional, List, ClassVar

import re

class FirmwareVersion:
    """Class to represent the firmware version of the Oregon RFID device."""

    def __init__(self, version_str: str):
        """
        Initialize FirmwareVersion by parsing version string.

        Parameters
        ----------
        version_str : str
            Version string in format like 'V2.74N' or 'V2.74'.
        """
        self._original_str = version_str

        self._version_number = None
        self._major = None
        self._minor = None
        self._suffix = None

        self._parse_version_string(version_str)

    @property
    def version_number(self) -> Optional[float]:
        """Get the version number as a float (e.g., 2.74)."""
        return self._version_number

    @property
    def major(self) -> Optional[int]:
        """Get the major version number (e.g., 2 in V2.74)."""
        return self._major

    @property
    def minor(self) -> Optional[int]:
        """Get the minor version number (e.g., 74 in V2.74)."""
        return self._minor

    @property
    def suffix(self) -> Optional[str]:
        """Get the suffix of the version (e.g., 'N' or 'M'), or None if no suffix."""
        return self._suffix

    @property
    def original_str(self) -> str:
        """Get the original version string."""
        return self._original_str

    def _parse_version_string(self, version_str: str):
        """
        Parse the version string and set major, minor, and suffix attributes.

        Parameters
        ----------
        version_str : str
            Version string in format like 'V2.74N' or 'V2.74' or 'V1.998'.
        """
        # Starts with 'V' followed by unknown number of digits for major, then a dot, then unknown number of digits for minor, then optional single letter suffix
        match = re.match(r"V([0-9]+)\.([0-9]+)([A-Z]*)", version_str)
        if match:
            self._major = int(match.group(1))
            self._minor = int(match.group(2))
            self._suffix = match.group(3) if match.group(3) else None
            self._version_number = float(f"{self._major}.{self._minor}")
        else:
            raise UnexpectedResponseError(f"Invalid version string format: {version_str}")

@dataclass
class SystemStatus:
    """Class to represent the system status and prerequisites for Oregon RFID processing."""

    # --- Class constants (NOT dataclass fields) ---
    MUST_HAVE_FIELDS: ClassVar[list[str]] = ['device_type', 'version', 'serial_number', 'reader_name', 'mode']
    ACCEPTED_DEVICE_TYPES: ClassVar[list[str]] = ['ORSR', 'ORMR']
    ACCEPTED_MODES: ClassVar[list[str]] = list(DeviceModeManager.MODES.keys())

    # --- Data fields ---
    device_type: Optional[str] = None
    version: Optional[FirmwareVersion] = None
    serial_number: Optional[str] = None
    reader_name: Optional[str] = None
    mode: Optional[str] = None
    supply_voltage: Optional[float] = None
    standby_amps: Optional[float] = None
    noise: Optional[float] = None
    antenna_1: Optional[str] = None
    antenna_2: Optional[str] = None
    antenna_3: Optional[str] = None
    antenna_4: Optional[str] = None
    shutdown_supercap: Optional[str] = None
    sleep_battery: Optional[str] = None
    tags_in_archive: Optional[int] = None
    bluetooth_status: Optional[str] = None
    gnss_log_interval_minutes: Optional[int] = None
    raw_output: Optional[str] = None
    warnings: List[str] = field(default_factory=list)

    # --- Logic ---
    def check_prerequisites(self):
        if self.device_type not in self.ACCEPTED_DEVICE_TYPES:
            raise UnexpectedResponseError(
                f"Unsupported device type '{self.device_type}'. "
                f"Only {self.ACCEPTED_DEVICE_TYPES} are supported."
            )

        if self.mode not in self.ACCEPTED_MODES:
            raise UnexpectedResponseError(
                f"Unsupported device mode '{self.mode}'. "
                f"Expected one of: {self.ACCEPTED_MODES}"
            )

        for field_name in self.MUST_HAVE_FIELDS:
            value = getattr(self, field_name)
            if not value:
                raise UnexpectedResponseError(
                    f"Missing expected field '{field_name}' in system status. "
                    f"Value: '{value}'"
                )

class SystemStatusChecker:
    """Class to check system status and prerequisites for Oregon RFID processing."""

    def __init__(self, command_manager: CommandManager):
        self._logger = get_logger(__name__)
        self._command_manager: CommandManager = command_manager

    def get_system_status(self) -> SystemStatus:

        status_lines = self._command_manager.send_command("SY")

        status = SystemStatus()  # create empty SystemStatus

        # Validate we have at least 3 lines to parse the row 1-3, which are always in teh same rows.
        if len(status_lines) < 3:
            error_message = f"Expected at least 3 lines in SY response, got {len(status_lines)}"
            self._logger.error(error_message)
            raise UnexpectedResponseError(error_message)

        for line_num, line in enumerate(status_lines):
            line = line.strip()

            if not line:
                error_message = f"Empty line encountered in SY response at row {line_num + 1} of SY response."
                self._logger.error(error_message)
                raise UnexpectedResponseError(error_message)

            line = line.lower()  # normalize to lowercase for easier parsing, but keep original line in case needed for error messages or raw output

            # Use specific parsing for the first 3 lines, then auto-parse the rest
            if line_num == 0:
                self._parse_line_1(line, status)
            elif line_num == 1:
                self._parse_line_2(line, status)
            elif line_num == 2:
                self._parse_line_3(line, status)
            else:
                self._auto_parse_line(line, status)

        try:
            status.check_prerequisites()  # validate prerequisites
        except UnexpectedResponseError as e:
            error_message = f"System status prerequisites check failed: {str(e)}"
            self._logger.error(error_message)
            raise UnexpectedResponseError(error_message)

        return status

    def _parse_line_1(self, line: str, status: SystemStatus):
        # Line 0: device type
        if not "oregon rfid" in line:
            error_message = f"Unexpected device type line format at row 1 of SY response: '{line}'"
            self._logger.error(error_message)
            raise UnexpectedResponseError(error_message)
        if 'single antenna' in line:
            status.device_type = 'ORSR'
        elif 'multiple antenna' in line:
            status.device_type = 'ORMR'
        else:
            error_message = f"Could not determine device type from line 1 of SY response: '{line}'"
            self._logger.error(error_message)
            raise UnexpectedResponseError(error_message)

    def _parse_line_2(self, line: str, status: SystemStatus):

        line_splits = line.split()
        if len(line_splits) != 2:
            error_message = f"Unexpected version/serial line format at row 2 of SY response: '{line}'"
            self._logger.error(error_message)
            raise UnexpectedResponseError(error_message)

        version_str = line_splits[0]

        try:
            version = FirmwareVersion(version_str)
        except UnexpectedResponseError as e:
            error_message = f"Unexpected version format in row 2 of SY response: '{line}' - {str(e)}"
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

        status.version = version
        status.serial_number = serial_number

    def _parse_line_3(self, line: str, status: SystemStatus):
        status.reader_name = line

    def _auto_parse_line(self, line: str, line_num: int, status: SystemStatus):

        if 'mode' in line:
            self._parse_mode_line(line, line_num, status)
        elif 'supply voltage' in line:
            self._parse_supply_voltage_line(line, line_num, status)
        elif ('standby amps' in line or 'sleep amps' in line) and 'amps' in line:
            self._parse_standby_amps_line(line, line_num, status)
        elif line.startswith('noise'):
            self._parse_noise_line(line, line_num, status)
        elif 'antenna' in line and '#' in line:
            self._parse_antenna_line(line, line_num, status)
        elif 'shutdown' in line and ('supercap' in line or 'supply' in line):
            self._parse_shutdown_line(line, line_num, status)
        elif 'sleep battery' in line or (line.startswith('battery') and 'sleep' not in line):
            self._parse_sleep_battery_line(line, line_num, status)
        elif 'tags in archive' in line:
            self._parse_tags_in_archive_line(line, line_num, status)
        elif 'bluetooth' in line:
            self._parse_bluetooth_line(line, line_num, status)
        elif "gnss logged every " in line or 'gnss log is off' in line:
            self._parse_gnss_log_line(line, line_num, status)
        else:
            error_message = f"Unrecognized line format in system status at row {line_num + 1} of SY response: '{line}'"
            self._logger.error(error_message)
            raise UnexpectedResponseError(error_message)

    def _parse_mode_line(self, line: str, status: SystemStatus):
        mode = line.split(' mode')[0].strip() or None

        # valdate mode is one of expected values
        if not DeviceModeManager.is_valid_mode(mode):
            error_message = f"Unexpected mode value parsed from SY response: '{mode}' in line: '{line}'"
            self._logger.error(error_message)
            raise UnexpectedResponseError(error_message)
        status.mode = mode

    def _parse_supply_voltage_line(self, line: str, line_num: int, status: SystemStatus):
        parts = line.split()
        supply_voltage = parts[-1]
        try:
            status.supply_voltage = float(supply_voltage)
        except ValueError:
            error_message = f"Could not parse supply voltage as float in SY response at row {line_num + 1}: '{line}'"
            self._logger.error(error_message)
            raise UnexpectedResponseError(error_message)

    def _parse_standby_amps_line(self, line: str, line_num: int, status: SystemStatus):
        parts = line.split()
        status.standby_amps = parts[-1] if parts else None

    def _parse_noise_line(self, line: str, line_num: int, status: SystemStatus):
        parts = line.split()
        status.noise = parts[-1] if parts else None

    def _parse_antenna_line(self, line: str, line_num: int, status: SystemStatus):
        parts = line.split()
        try:
            antenna_num = line.split('#')[1].strip().split()[0]
            antenna_value = parts[-1]

            if antenna_num == '1':
                status.antenna_1 = antenna_value
            elif antenna_num == '2':
                status.antenna_2 = antenna_value
            elif antenna_num == '3':
                status.antenna_3 = antenna_value
            elif antenna_num == '4':
                status.antenna_4 = antenna_value
            else:
                error_message = f"Unexpected antenna number parsed from SY response: '{antenna_num}' in line: '{line}'"
                self._logger.error(error_message)
                raise UnexpectedResponseError(error_message)
        except (IndexError):
            error_message = f"Unexpected antenna line format in SY response at row {line_num + 1}: '{line}'"
            self._logger.error(error_message)
            raise UnexpectedResponseError(error_message)

    def _parse_shutdown_line(self, line: str, line_num: int, status: SystemStatus):
        parts = line.split()
        status.shutdown_supercap = parts[-1] if parts else None

    def _parse_sleep_battery_line(self, line: str, line_num: int, status: SystemStatus):
        parts = line.split()
        status.sleep_battery = parts[-1] if parts else None

    def _parse_tags_in_archive_line(self, line: str, line_num: int, status: SystemStatus):
        parts = line.split()
        status.tags_in_archive = parts[-1] if parts else None

    def _parse_bluetooth_line(self, line: str, line_num: int, status: SystemStatus):
        status.bluetooth_status = line

    def _parse_gnss_log_line(self, line: str, line_num: int, status: SystemStatus):
        if "gnss logged every " in line:
            status.gnss_log_interval_minutes = True
        elif 'gnss log is off' in line:
            status.gnss_log_interval_minutes = False
        else:
            error_message = f"Unrecognized GNSS log line format in SY response at row {line_num + 1}: '{line}'"
            self._logger.error(error_message)
            raise UnexpectedResponseError(error_message)






