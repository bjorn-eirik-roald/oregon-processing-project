from oregon_processing.util.logging_manager import get_logger
from oregon_processing.util.oregon_config import OregonConfig
from oregon_processing.util.communicator import Communicator
from oregon_processing.util.util_functions import extract_filename_date

from datetime import date, datetime, timedelta
from pathlib import Path




class DatabaseManager:
    """Manages database directories and date range tracking for exports."""

    DEFAULT_FIRST_DATE = date(2018, 1, 1)

    def __init__(self, config: OregonConfig, communicator: "Communicator"):
        """
        Initialize DatabaseManager.

        Parameters
        ----------
        config : OregonConfig
            Configuration manager instance for data directory
        communicator : Communicator
            Communicator instance for device information
        """
        self._config = config
        self._communicator = communicator
        self._logger = get_logger(__name__)

        # Root directories
        self._data_dir = None
        self._export_logs_base_dir = None
        self._log_dir = None
        self._crash_log_dir = None
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
    def log_dir(self) -> Path:
        """Get the export logs directory path (for specific serial number)."""
        if self._log_dir is None:
            raise RuntimeError("Directories not prepared yet.")
        return self._log_dir

    @property
    def crash_logs_dir(self) -> Path:
        """Get the crash logs directory path (for undefined/pre-connection crashes)."""
        if self._crash_log_dir is None:
            raise RuntimeError("Directories not prepared yet.")
        return self._crash_log_dir

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

    def prepare_crash_log_file(self) -> Path:
        """Prepare and return the crash logs directory path."""
        crash_logs_dir = self._config.crash_logs_dir
        crash_logs_dir.mkdir(parents=True, exist_ok=True)

        crash_log_file = crash_logs_dir / f"crash_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        return crash_log_file

    def prepare_directories(self) -> None:
        """Prepare and create necessary directories for export."""
        logging_extra = {'process_name': 'Output Directory Setup'}

        self._logger.info("Preparing output directories.", extra=logging_extra)

        # Get serial number from communicator
        serial_number = self._communicator.serial_number

        self._root_output_dir = self._config.root_output_dir
        self._root_log_dir = self._config.root_log_dir
        self._root_export_data_dir = self._config.root_export_data_dir

        # Add serial number subdirectory to export logs, detection records, and event records
        self._log_dir = self._config.root_log_dir / serial_number
        self._detection_records_dir = self._config.root_detection_records_dir / serial_number
        self._event_records_dir = self._config.root_event_records_dir / serial_number

        self._logger.info(f"Root output directory: {self._root_output_dir}", extra=logging_extra)
        self._logger.info(f"Root Export data directory: {Path(self._root_export_data_dir).relative_to(self._root_output_dir)}", extra=logging_extra)
        self._logger.info(f"Detection records directory: {Path(self._detection_records_dir).relative_to(self._root_output_dir)}", extra=logging_extra)
        self._logger.info(f"Event records directory: {Path(self._event_records_dir).relative_to(self._root_output_dir)}", extra=logging_extra)
        self._logger.info(f"Export logs directory: {Path(self._log_dir).relative_to(self._root_output_dir)}", extra=logging_extra)
        self._logger.info(f"Crash logs directory: {Path(self._crash_log_dir).relative_to(self._root_output_dir)}", extra=logging_extra)


        # Create all directories
        directories = [
            (self._log_dir, "Export logs directory"),
            (self._crash_log_dir, "Crash logs directory"),
            (self._root_export_data_dir, "Root export data directory"),
            (self._detection_records_dir, "Detection records directory"),
            (self._event_records_dir, "Event records directory"),
        ]

        for dir_path, dir_name in directories:
            if not dir_path.exists():
                self._logger.info(f"Creating {dir_name}: {dir_path}", extra=logging_extra)
                dir_path.mkdir(parents=True, exist_ok=True)

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

        self._logger.info("Scanning for existing detection record files...", extra=logging_extra)
        record_files = list(self._detection_records_dir.glob("*.txt"))
        self._logger.info(f"Found {len(record_files)} detection record file(s) from current RFID reader.", extra=logging_extra)

        self._logger.info("Scanning for existing event record files...", extra=logging_extra)
        event_files = list(self._event_records_dir.glob("*.txt"))
        self._logger.info(f"Found {len(event_files)} event record file(s) from current RFID reader.", extra=logging_extra)

        self._logger.info("Extracting dates from filenames...", extra=logging_extra)

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

        self._logger.info(f"Detection records: {len(missing_record_dates)} missing/incomplete date(s) out of {len(expected_dates)}", extra=logging_extra)
        if missing_record_dates:
            self._logger.info(f"Missing detection dates: {self._format_date_intervals(missing_record_dates)}", extra=logging_extra)

        self._logger.info(f"Event records: {len(missing_event_dates)} missing/incomplete date(s) out of {len(expected_dates)}", extra=logging_extra)
        if missing_event_dates:
            self._logger.info(f"Missing event dates: {self._format_date_intervals(missing_event_dates)}", extra=logging_extra)

        return {
            'records': missing_record_dates,
            'system_logs': missing_event_dates
        }

    @classmethod
    def prepare_crash_log_dir(cls, config: OregonConfig) -> Path:
        """Create and return the crash logs directory path."""
        crash_logs_dir = config.crash_logs_dir
        crash_logs_dir.mkdir(parents=True, exist_ok=True)
        return crash_logs_dir

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

