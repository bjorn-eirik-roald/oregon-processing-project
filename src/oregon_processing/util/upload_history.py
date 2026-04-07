
from dataclasses import dataclass, field
from datetime import datetime

from oregon_processing.util.command_manager import CommandManager
from oregon_processing.util.exceptions import UnexpectedResponseError
from oregon_processing.util.logging_manager import get_logger
from oregon_processing.util.device_mode_manager import DeviceModeManager


@dataclass
class UploadRecord:
    """Data class representing a single upload record."""
    num: int
    date: str
    time: str
    records: int


@dataclass
class UploadHistory:
    """Manages upload history for processed data."""

    reader_name: str = ""
    site: str = ""
    upload_count: int = 0
    uploads: list[UploadRecord] = field(default_factory=list)
    new_records: int = 0
    total_records: int = 0
    raw_output: str = ""

class UploadHistoryChecker:

    def __init__(self, command_manager: CommandManager, mode_manager: DeviceModeManager):
        self._logger = get_logger(__name__)

        self._command_manager = command_manager
        self._mode_manager = mode_manager

    def get_upload_history(self) -> UploadHistory:

        """
        Parse upload history output from UH command.

        Returns
        -------
        UploadHistory
        """


        mode = self._mode_manager.get_current_mode() # update mode property
        old_mode = None
        if mode.lower() != 'standby':
            old_mode = mode
            self.change_mode('Standby')

        upload_history_lines = self._command_manager.send_command("UH")

        if old_mode:
            self.change_mode(old_mode)

        upload_history: UploadHistory = UploadHistory()

        for i, line in enumerate(upload_history_lines):
            line_stripped = line.strip()

            # Parse header line: "Reader: <name>  Site: <site>"
            if line_stripped.startswith('Reader:'):
                parts = line_stripped.split('Site:')
                if len(parts) == 2:
                    reader_part = parts[0].replace('Reader:', '').strip()
                    site_part = parts[1].strip()
                    upload_history.reader_name = reader_part
                    upload_history.site = site_part

            # Parse upload histories count
            elif 'Upload Histories:' in line:
                parts = line_stripped.split('Upload Histories:')
                if len(parts) == 2:
                    try:
                        upload_history.upload_count = int(parts[1].strip())
                    except ValueError:
                        error_message = f"Unrecognized line format in upload history at row {i + 1}: '{line}'"
                        self._logger.error(error_message)
                        raise UnexpectedResponseError(error_message)

            # Skip header row (Num   UP Date    Time    Records)
            elif line_stripped.startswith('Num'):
                continue

            # Parse upload record lines (numbered entries)
            elif line_stripped and line_stripped[0].isdigit():
                parts = line_stripped.split()
                if len(parts) >= 4:
                    try:
                        upload_record = UploadRecord(
                            num=int(parts[0]),
                            date=parts[1],
                            time=parts[2],
                            records=int(parts[3])
                        )
                        upload_history.uploads.append(upload_record)
                    except (ValueError, IndexError):
                        error_message = f"Unrecognized line format in upload history at row {i + 1}: '{line}'"
                        self._logger.error(error_message)
                        raise UnexpectedResponseError(error_message)

            # Parse NEW records line
            elif line_stripped.startswith('NEW'):
                parts = line_stripped.split()
                if len(parts) >= 2:
                    try:
                        upload_history.new_records = int(parts[-1])
                    except ValueError:
                        error_message = f"Unrecognized line format in upload history at row {i + 1}: '{line}'"
                        self._logger.error(error_message)
                        raise UnexpectedResponseError(error_message)

            # Parse Total line
            elif line_stripped.startswith('Total'):
                parts = line_stripped.split()
                if len(parts) >= 2:
                    try:
                        upload_history.total_records = int(parts[-1])
                    except ValueError:
                        error_message = f"Unrecognized line format in upload history at row {i + 1}: '{line}'"
                        self._logger.error(error_message)
                        raise UnexpectedResponseError(error_message)

            else:
                error_message = f"Unrecognized line format in upload history at row {i + 1}: '{line}'"
                self._logger.error(error_message)
                raise UnexpectedResponseError(error_message)


        # Store the most recent upload date (last entry in uploads list)
        if upload_history.uploads:
            last_upload = upload_history.uploads[-1]

            upload_datetime = datetime.strptime(f"{last_upload.date} {last_upload.time}", "%Y-%m-%d %H:%M:%S")
            self._last_upload_date = upload_datetime.date()

        return upload_history