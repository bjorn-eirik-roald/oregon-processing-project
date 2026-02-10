import logging
from oregon_processing.util.config_manager import ConfigManager
from oregon_processing.util.oregon_communicator import OregonCommunicator
from oregon_processing.util.util_functions import extract_filename_date

from datetime import date, datetime, timedelta
from pathlib import Path

from oregon_processing.util.display_constants import display


class DatabaseManager:
    """Manages database directories and date range tracking for exports."""

    # Folder structure constants
    EXPORT_LOGS_DIR_NAME = "01_export_logs"
    EXPORT_DATA_DIR_NAME = "02_export_data"
    DETECTION_RECORDS_DIR_NAME = "01_detection_records"
    EVENT_RECORDS_DIR_NAME = "02_event_records"
    CRASH_LOGS_DIR_NAME = "00_crash_logs"

    DEFAULT_FIRST_DATE = date(2018, 1, 1)

    @classmethod
    def prepare_crash_logs_dir(cls, config_manager: ConfigManager) -> Path:
        """Create and return the crash logs directory path."""
        data_dir = config_manager.data_dir
        crash_logs_dir = data_dir / cls.EXPORT_LOGS_DIR_NAME / cls.CRASH_LOGS_DIR_NAME
        crash_logs_dir.mkdir(parents=True, exist_ok=True)
        return crash_logs_dir

    def __init__(self, config_manager: ConfigManager, communicator: "OregonCommunicator"):
        """
        Initialize DatabaseManager.

        Parameters
        ----------
        config_manager : ConfigManager
            Configuration manager instance for data directory
        communicator : OregonCommunicator
            OregonCommunicator instance for device information
        """
        self._config_manager = config_manager
        self._communicator = communicator
        self.logger = logging.getLogger('oregon_processing.database_manager')

        # Root directories
        self._data_dir = None
        self._export_logs_base_dir = None
        self._export_logs_dir = None
        self._crash_logs_dir = None
        self._export_data_dir = None

        # Export data subdirectories
        self._detection_records_dir = None
        self._event_records_dir = None

    def __enter__(self):
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        pass


    @property
    def data_dir(self) -> Path:
        """Get the root data directory path."""
        if self._data_dir is None:
            raise RuntimeError("Directories not prepared yet.")
        return self._data_dir

    @property
    def export_logs_dir(self) -> Path:
        """Get the export logs directory path (for specific serial number)."""
        if self._export_logs_dir is None:
            raise RuntimeError("Directories not prepared yet.")
        return self._export_logs_dir

    @property
    def crash_logs_dir(self) -> Path:
        """Get the crash logs directory path (for undefined/pre-connection crashes)."""
        if self._crash_logs_dir is None:
            raise RuntimeError("Directories not prepared yet.")
        return self._crash_logs_dir

    @property
    def export_data_dir(self) -> Path:
        """Get the export data directory path."""
        if self._export_data_dir is None:
            raise RuntimeError("Directories not prepared yet.")
        return self._export_data_dir

    @property
    def detection_records_dir(self) -> Path:
        """Get the detection records directory path."""
        if self._detection_records_dir is None:
            raise RuntimeError("Directories not prepared yet.")
        return self._detection_records_dir

    @property
    def event_records_dir(self) -> Path:
        """Get the event records directory path."""
        if self._event_records_dir is None:
            raise RuntimeError("Directories not prepared yet.")
        return self._event_records_dir

    @property
    def records_dir(self) -> Path:
        """Get the records directory path (alias for detection_records_dir for backward compatibility)."""
        return self.detection_records_dir

    @property
    def system_logs_dir(self) -> Path:
        """Get the system logs directory path (alias for event_records_dir for backward compatibility)."""
        return self.event_records_dir

    def prepare_directories(self) -> None:
        """Prepare and create necessary directories for export."""
        logging_extra = {'process_name': 'Output Directory Setup'}

        self.logger.info("Preparing output directories.", extra=logging_extra)

        # Get serial number from communicator
        serial_number = self._communicator.serial_number

        self._data_dir = self._config_manager.data_dir
        self._export_logs_base_dir = self._data_dir / self.EXPORT_LOGS_DIR_NAME
        self._export_data_dir = self._data_dir / self.EXPORT_DATA_DIR_NAME

        # Add serial number subdirectory to export logs, detection records, and event records
        self._export_logs_dir = self._export_logs_base_dir / serial_number
        self._crash_logs_dir = self._export_logs_base_dir / "undefined"
        self._detection_records_dir = self._export_data_dir / self.DETECTION_RECORDS_DIR_NAME / serial_number
        self._event_records_dir = self._export_data_dir / self.EVENT_RECORDS_DIR_NAME / serial_number

        self.logger.info(f"Export logs directory: {self._export_logs_dir}", extra=logging_extra)
        self.logger.info(f"Crash logs directory: {self._crash_logs_dir}", extra=logging_extra)
        self.logger.info(f"Export data directory: {self._export_data_dir}", extra=logging_extra)
        self.logger.info(f"Detection records directory: {self._detection_records_dir}", extra=logging_extra)
        self.logger.info(f"Event records directory: {self._event_records_dir}", extra=logging_extra)

        # Create all directories
        directories = [
            (self._export_logs_dir, "Export logs directory"),
            (self._crash_logs_dir, "Crash logs directory"),
            (self._export_data_dir, "Export data directory"),
            (self._detection_records_dir, "Detection records directory"),
            (self._event_records_dir, "Event records directory"),
        ]

        for dir_path, dir_name in directories:
            if not dir_path.exists():
                self.logger.info(f"Creating {dir_name}: {dir_path}", extra=logging_extra)
                dir_path.mkdir(parents=True, exist_ok=True)

    def _format_date_intervals(self, dates: list) -> str:
        """
        Convert a list of dates into formatted intervals.

        Parameters
        ----------
        dates : list
            Sorted list of date objects

        Returns
        -------
        str
            Formatted string of date intervals (e.g., "2021-01-01 to 2021-01-15, 2021-02-01 to 2021-02-10")
        """
        if not dates:
            return "None"

        intervals = []
        interval_start = dates[0]
        interval_end = dates[0]

        for date_obj in dates[1:]:
            if (date_obj - interval_end).days == 1:
                # Consecutive date, extend interval
                interval_end = date_obj
            else:
                # Gap found, save interval and start new one
                if interval_start == interval_end:
                    intervals.append(str(interval_start))
                else:
                    intervals.append(f"{interval_start} to {interval_end}")
                interval_start = date_obj
                interval_end = date_obj

        # Add final interval
        if interval_start == interval_end:
            intervals.append(str(interval_start))
        else:
            intervals.append(f"{interval_start} to {interval_end}")

        return ", ".join(intervals)

    def get_export_dates(self) -> dict:
        """
        Determine missing dates by comparing present dates with expected date range.

        Includes the last available date as missing to account for potential incomplete
        exports (if exported mid-day, the last date's files may be incomplete).

        Returns
        -------
        dict
            Dictionary with 'records' and 'system_logs' keys containing lists of missing dates
        """
        logging_extra = {'process_name': 'Determine Export Date Range'}


        if self._detection_records_dir is None or self._event_records_dir is None:
            raise RuntimeError("Directories not prepared yet.")

        self.logger.info("Scanning for existing detection record files...", extra=logging_extra)
        record_files = list(self._detection_records_dir.glob("*.txt"))
        self.logger.info(f"Found {len(record_files)} detection record file(s) from current RFID reader.", extra=logging_extra)

        self.logger.info("Scanning for existing event record files...", extra=logging_extra)
        event_files = list(self._event_records_dir.glob("*.txt"))
        self.logger.info(f"Found {len(event_files)} event record file(s) from current RFID reader.", extra=logging_extra)

        self.logger.info("Extracting dates from filenames...", extra=logging_extra)

        record_file_dates = set(d for d in [extract_filename_date(f.name) for f in record_files] if d is not None)
        event_file_dates = set(d for d in [extract_filename_date(f.name) for f in event_files] if d is not None)

        # Generate expected date range from DEFAULT_FIRST_DATE to today
        today = date.today()
        current_date = self.DEFAULT_FIRST_DATE
        expected_dates = []
        while current_date <= today:
            expected_dates.append(current_date)
            current_date += timedelta(days=1)

        # Find missing dates for each file type
        missing_record_dates = sorted([d for d in expected_dates if d not in record_file_dates])
        missing_event_dates = sorted([d for d in expected_dates if d not in event_file_dates])

        # Get last available dates
        last_record_date = max(record_file_dates) if record_file_dates else None
        last_event_date = max(event_file_dates) if event_file_dates else None

        # Add last available dates to missing list to account for potential incomplete exports
        if last_record_date and last_record_date not in missing_record_dates:
            missing_record_dates = sorted(missing_record_dates + [last_record_date])
        if last_event_date and last_event_date not in missing_event_dates:
            missing_event_dates = sorted(missing_event_dates + [last_event_date])

        self.logger.info(f"Detection records: {len(missing_record_dates)} missing/incomplete date(s) out of {len(expected_dates)}", extra=logging_extra)
        if missing_record_dates:
            self.logger.info(f"Missing detection dates: {self._format_date_intervals(missing_record_dates)}", extra=logging_extra)

        self.logger.info(f"Event records: {len(missing_event_dates)} missing/incomplete date(s) out of {len(expected_dates)}", extra=logging_extra)
        if missing_event_dates:
            self.logger.info(f"Missing event dates: {self._format_date_intervals(missing_event_dates)}", extra=logging_extra)

        return {
            'records': missing_record_dates,
            'system_logs': missing_event_dates
        }