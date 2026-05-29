from dataclasses import dataclass


@dataclass(frozen=True)
class FileNames:
    oregon_project_json_file_name: str = "oregon_project.json"


file_names = FileNames()