
from oregon_processing.util.config import Config
from oregon_processing.util.config import NoConfigError  # Not used directly here but reimported for clarity in other modules.
from pathlib import Path
from oregon_processing.util.directory_names import directory_names

class OregonConfig(Config):
    """
    Realized config for Oregon processing, with specific attributes and validation.
    """
    CONFIG_FILE_NAME = "OregonConfig.json"
    APP_DIR_PARTS = ("oregon_processing",)
    ATTR_MAP = {
        "_root_output_dir": {"type": Path, "display": "Root output directory"},
        "_user": {"type": str, "display": "User"}
    }

    def __init__(self):
        super().__init__()

    @property
    def config_path(self) -> Path:
        """Get the config file path."""
        return self._config_path

    @property
    def user(self) -> str:
        """Get the username from the config."""
        return self._user

    @property
    def root_output_dir(self) -> Path:
        """
        Returns the root output folder for all Agresso postback files.
        Raises if not loaded.
        """
        if self._root_output_dir is None:
            raise RuntimeError("Configuration has not been loaded.")
        return self._root_output_dir

    @property
    def root_export_data_dir(self) -> Path:
        """Get the root export data directory path from the config."""
        return self.root_output_dir / directory_names.root_export_data_dir_name

    @property
    def root_detection_records_dir(self) -> Path:
        """Get the root detection records directory path from the config."""
        return self.root_export_data_dir / directory_names.root_detection_records_dir_name

    @property
    def root_event_records_dir(self) -> Path:
        """Get the root event records directory path from the config."""
        return self.root_export_data_dir / directory_names.root_event_records_dir_name

    @property
    def root_log_dir(self) -> Path:
        """Get the export logs directory path from the config."""
        return self.root_output_dir / directory_names.root_log_dir_name

    @property
    def crash_logs_dir(self) -> Path:
        """Get the crash logs directory path from the config."""
        return self.root_log_dir / directory_names.crash_logs_dir_name




if __name__ == "__main__":

    OregonConfig.create_or_overwrite_config()
    config = OregonConfig()
    print("Config loaded successfully. Current values:")
    for key in config.ATTR_MAP:
        print(f"\t- {key}: {getattr(config, key, None)}")

    OregonConfig.create_or_overwrite_config()