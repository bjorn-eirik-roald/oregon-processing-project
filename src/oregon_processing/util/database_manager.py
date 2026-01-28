from oregon_processing.util.config_manager import ConfigManager
from oregon_processing.util.oregon_communicator import OregonCommunicator
from oregon_processing.util.util_functions import extract_filename_date

from datetime import date, datetime
from pathlib import Path



SECTION_LINE_LENGTH = 40


class DatabaseManager:
    """Manages database directories and date range tracking for exports."""

    # Folder structure constants
    EXPORT_LOGS_DIR_NAME = "01_export_logs"
    EXPORT_DATA_DIR_NAME = "02_export_data"
    DETECTION_RECORDS_DIR_NAME = "01_detection_records"
    EVENT_RECORDS_DIR_NAME = "02_event_records"

    DEFAULT_FIRST_DATE = date(2021, 1, 1)

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

        # Root directories
        self._data_dir = None
        self._export_logs_dir = None
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
        """Get the export logs directory path."""
        if self._export_logs_dir is None:
            raise RuntimeError("Directories not prepared yet.")
        return self._export_logs_dir

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

        print("\n" + "=" * 70, flush=True)
        print("PREPARING DIRECTORIES", flush=True)
        print("=" * 70, flush=True)

        # Get serial number from communicator
        serial_number = self._communicator.serial_number

        self._data_dir = self._config_manager.data_dir
        self._export_logs_dir = self._data_dir / self.EXPORT_LOGS_DIR_NAME
        self._export_data_dir = self._data_dir / self.EXPORT_DATA_DIR_NAME

        # Add serial number subdirectory to detection and event records
        self._detection_records_dir = self._export_data_dir / self.DETECTION_RECORDS_DIR_NAME / serial_number
        self._event_records_dir = self._export_data_dir / self.EVENT_RECORDS_DIR_NAME / serial_number

        print("\n" + "-" * 70)
        print("Directory Setup")
        print("-" * 70)
        print(f"Data directory: {self._data_dir}")
        print(f"Serial number: {serial_number}")

        # Create all directories
        directories = [
            (self._export_logs_dir, "Export logs directory"),
            (self._export_data_dir, "Export data directory"),
            (self._detection_records_dir, "Detection records directory"),
            (self._event_records_dir, "Event records directory"),
        ]

        for dir_path, dir_name in directories:
            if not dir_path.exists():
                print(f"Creating {dir_name}: {dir_path}")
                dir_path.mkdir(parents=True, exist_ok=True)
            else:
                print(f"{dir_name} exists: {dir_path}")

        print("\n" + "=" * 70)
        print("DIRECTORIES READY")
        print("=" * 70)

    def get_export_dates(self) -> dict:
        """
        Determine the export date range based on existing files.

        Returns
        -------
        dict
            Dictionary with 'records' and 'system_logs' keys containing the start date for next export
        """

        if self._detection_records_dir is None or self._event_records_dir is None:
            raise RuntimeError("Directories not prepared yet.")

        print("\n" + "=" * 70, flush=True)
        print("DETERMINING EXPORT DATE RANGE", flush=True)
        print("=" * 70, flush=True)

        print("\n" + "-" * 70)
        print("Scanning Existing Files")
        print("-" * 70)
        print("Scanning for existing detection record files...", end="", flush=True)
        record_files = list(self._detection_records_dir.glob("*.txt"))
        print(f" Found {len(record_files)} file(s).")

        print("Scanning for existing event record files...", end="", flush=True)
        event_files = list(self._event_records_dir.glob("*.txt"))
        print(f" Found {len(event_files)} file(s).")

        print("\n" + "-" * 70)
        print("Extracting Dates from Filenames")
        print("-" * 70)

        record_file_dates = [extract_filename_date(f.name) for f in record_files]
        event_file_dates = [extract_filename_date(f.name) for f in event_files]

        first_record_date = min((d for d in record_file_dates if d is not None), default=None)
        last_record_date = max((d for d in record_file_dates if d is not None), default=None)
        first_event_date = min((d for d in event_file_dates if d is not None), default=None)
        last_event_date = max((d for d in event_file_dates if d is not None), default=None)

        print(f"Detection records date range: {first_record_date or 'N/A'} to {last_record_date or 'N/A'}")
        print(f"Event records date range: {first_event_date or 'N/A'} to {last_event_date or 'N/A'}")

        print("\n" + "-" * 70)
        print("Determining Export Range")
        print("-" * 70)

        if first_record_date and first_event_date:
            if first_record_date != first_event_date:
                print("⚠ Warning: Mismatch in first dates between detection records and event records.")

        if last_record_date and last_event_date:
            if last_record_date != last_event_date:
                print("⚠ Warning: Mismatch in last dates between detection records and event records.")

        # Determine separate previous export dates for records and event records
        if last_record_date is None:
            records_prev_date = self.DEFAULT_FIRST_DATE
            print(f"No previous detection record export dates found. Using default first export date: {records_prev_date}")
        else:
            records_prev_date = last_record_date
            print(f"Previous detection record export date determined. Next export will start from: {records_prev_date}")

        if last_event_date is None:
            event_prev_date = self.DEFAULT_FIRST_DATE
            print(f"No previous event record export dates found. Using default first export date: {event_prev_date}")
        else:
            event_prev_date = last_event_date
            print(f"Previous event record export date determined. Next export will start from: {event_prev_date}")

        return {
            'records': records_prev_date,
            'system_logs': event_prev_date
        }