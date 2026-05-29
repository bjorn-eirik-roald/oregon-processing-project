from dataclasses import dataclass


@dataclass(frozen=True)
class DirectoryNames:

    archive_dir_name: str = "00_archive"
    logs_dir_name: str = "01_logs"
    export_dir_name: str = "02_export_data"
    detection_record_export_dir_name: str = "01_detection_records"
    event_record_export_dir_name: str = "02_event_records"


directory_names = DirectoryNames()