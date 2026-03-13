from dataclasses import dataclass


@dataclass(frozen=True)
class DirectoryNames:

    root_export_logs_dir_name = "01_export_logs"
    root_export_data_dir_name = "02_export_data"
    root_detection_records_dir_name = "01_detection_records"
    root_event_records_dir_name = "02_event_records"
    root_crash_logs_dir_name = "00_undefined_serial_number_crashes"


directory_names = DirectoryNames()