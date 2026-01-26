from oregon_processing.util.config_manager import ConfigManager
from oregon_processing.util.util_functions import extract_filename_date

from datetime import date, datetime
from pathlib import Path



SECTION_LINE_LENGTH = 40


class DatabaseManager:
    """Manages database directories and date range tracking for exports."""

    RECORD_DIR_NAME = "records"
    SYSTEM_LOGS_DIR_NAME = "system_logs"
    DEFAULT_FIRST_DATE = date(2021, 1, 1)

    def __init__(self, config_manager: ConfigManager, reader_name: str):
        """
        Initialize DatabaseManager.

        Parameters
        ----------
        config_manager : ConfigManager
            Configuration manager instance for data directory
        reader_name : str
            Name of the reader for directory organization
        """
        self._config_manager = config_manager
        self._reader_name = reader_name
        self._records_dir = None
        self._system_logs_dir = None

    def prepare_directories(self) -> None:
        """Prepare and create necessary directories for export."""

        print("\n" + "=" * 70, flush=True)
        print("PREPARING DIRECTORIES", flush=True)
        print("=" * 70, flush=True)

        data_dir = self._config_manager.data_dir
        reader_data_dir = data_dir / self._reader_name
        self._records_dir = reader_data_dir / self.RECORD_DIR_NAME
        self._system_logs_dir = reader_data_dir / self.SYSTEM_LOGS_DIR_NAME

        print("\n" + "-" * 70)
        print("Directory Setup")
        print("-" * 70)
        print(f"Reader data directory: {reader_data_dir}")

        if not self._records_dir.exists():
            print(f"Creating records directory: {self._records_dir}")
            self._records_dir.mkdir(parents=True, exist_ok=True)
        else:
            print(f"Records directory exists: {self._records_dir}")

        if not self._system_logs_dir.exists():
            print(f"Creating system logs directory: {self._system_logs_dir}")
            self._system_logs_dir.mkdir(parents=True, exist_ok=True)
        else:
            print(f"System logs directory exists: {self._system_logs_dir}")

        print("\n" + "=" * 70)
        print("DIRECTORIES READY")
        print("=" * 70)

    @property
    def records_dir(self) -> Path:
        """Get the records directory path."""
        if self._records_dir is None:
            raise RuntimeError("Directories not prepared yet.")
        return self._records_dir

    @property
    def system_logs_dir(self) -> Path:
        """Get the system logs directory path."""
        if self._system_logs_dir is None:
            raise RuntimeError("Directories not prepared yet.")
        return self._system_logs_dir

    def get_export_dates(self) -> dict:
        """
        Determine the export date range based on existing files.

        Returns
        -------
        dict
            Dictionary with 'records' and 'system_logs' keys containing the start date for next export
        """

        if self._records_dir is None or self._system_logs_dir is None:
            raise RuntimeError("Directories not prepared yet.")

        print("\n" + "=" * 70, flush=True)
        print("DETERMINING EXPORT DATE RANGE", flush=True)
        print("=" * 70, flush=True)

        print("\n" + "-" * 70)
        print("Scanning Existing Files")
        print("-" * 70)
        print("Scanning for existing record files...", end="", flush=True)
        record_files = list(self._records_dir.glob("*.txt"))
        print(f" Found {len(record_files)} file(s).")

        print("Scanning for existing system log files...", end="", flush=True)
        system_log_files = list(self._system_logs_dir.glob("*.txt"))
        print(f" Found {len(system_log_files)} file(s).")

        print("\n" + "-" * 70)
        print("Extracting Dates from Filenames")
        print("-" * 70)

        record_file_dates = [extract_filename_date(f.name) for f in record_files]
        system_log_file_dates = [extract_filename_date(f.name) for f in system_log_files]

        first_record_date = min((d for d in record_file_dates if d is not None), default=None)
        last_record_date = max((d for d in record_file_dates if d is not None), default=None)
        first_system_log_date = min((d for d in system_log_file_dates if d is not None), default=None)
        last_system_log_date = max((d for d in system_log_file_dates if d is not None), default=None)

        print(f"Records date range: {first_record_date or 'N/A'} to {last_record_date or 'N/A'}")
        print(f"System logs date range: {first_system_log_date or 'N/A'} to {last_system_log_date or 'N/A'}")

        print("\n" + "-" * 70)
        print("Determining Export Range")
        print("-" * 70)

        if first_record_date and first_system_log_date:
            if first_record_date != first_system_log_date:
                print("⚠ Warning: Mismatch in first dates between records and system logs.")

        if last_record_date and last_system_log_date:
            if last_record_date != last_system_log_date:
                print("⚠ Warning: Mismatch in last dates between records and system logs.")

        # Determine separate previous export dates for records and system logs
        if last_record_date is None:
            records_prev_date = self.DEFAULT_FIRST_DATE
            print(f"No previous record export dates found. Using default first export date: {records_prev_date}")
        else:
            records_prev_date = last_record_date
            print(f"Previous record export date determined. Next records export will start from: {records_prev_date}")

        if last_system_log_date is None:
            system_logs_prev_date = self.DEFAULT_FIRST_DATE
            print(f"No previous system log export dates found. Using default first export date: {system_logs_prev_date}")
        else:
            system_logs_prev_date = last_system_log_date
            print(f"Previous system log export date determined. Next system logs export will start from: {system_logs_prev_date}")

        return {
            'records': records_prev_date,
            'system_logs': system_logs_prev_date
        }