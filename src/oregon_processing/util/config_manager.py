import os
import json
import getpass
import logging
from pathlib import Path




class ConfigManager:
    APP_NAME = "oregon_communicator"
    CONFIG_FILENAME = "config.json"
    REQUIRED_KEYS = {"user", "data_dir_path"}

    def __init__(self, validate: bool = True):
        """
        Initialize ConfigManager.

        Parameters
        ----------
        validate : bool
            If True, validate the config file. If False, load it without validation.
            Set to False when reading an existing config for setup/migration purposes.
        """
        self.logger = logging.getLogger('oregon_processing.config_manager')
        self._username = getpass.getuser()
        self._appdata_dir = self._get_appdata_dir()
        self._config_path = self._appdata_dir / self.CONFIG_FILENAME
        self._config = None

        if self._config_path.exists():
            if validate:
                self._load_and_validate()
            else:
                self._load_without_validation()
        else:
            logging_extra = {'process_name': 'Configuration'}
            self.logger.info(f"Config file not found at {self._config_path}. Creating a new one before continuing.", extra=logging_extra)
            ConfigManager.create_new_config()
            self._load_and_validate()

    def __enter__(self):
        """Enter context manager; print configuration summary."""
        self.summarize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        pass

    @property
    def config_path(self) -> Path:
        """Get the config file path."""
        return self._config_path

    @property
    def user(self) -> str:
        """Get the username from the config."""
        return self._config["user"]

    @property
    def data_dir(self) -> Path:
        """Get the data directory path from the config."""
        return Path(self._config["data_dir_path"])

    def summarize(self) -> None:
        """Print a concise summary of the loaded configuration."""
        logging_extra = {'process_name': 'Configuration'}
        summary = "Configuration summary:\n"
        summary += f"  User: {self.user}\n"
        summary += f"  Data directory: {self.data_dir}"
        self.logger.info(summary, extra=logging_extra)

    @staticmethod
    def _strip_quotes(value: str) -> str:
        """Remove surrounding single or double quotes if present."""
        value = value.strip()
        if (
            (value.startswith('"') and value.endswith('"')) or
            (value.startswith("'") and value.endswith("'"))
        ):
            return value[1:-1]
        return value

    def _get_appdata_dir(self) -> Path:
        appdata = os.environ.get("APPDATA")
        if not appdata:
            raise EnvironmentError("APPDATA environment variable not found.")
        return Path(appdata) / self.APP_NAME

    def _load_and_validate(self):
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in config file: {e}")

        # Validate required keys
        if not self.REQUIRED_KEYS.issubset(data.keys()):
            missing = self.REQUIRED_KEYS - data.keys()
            raise ValueError(f"Missing required config keys: {missing}")

        # Validate user
        if not isinstance(data["user"], str) or not data["user"].strip():
            raise ValueError("Config key 'user' must be a non-empty string.")

        # Validate data_dir_path
        raw_path = self._strip_quotes(data["data_dir_path"])
        path = Path(raw_path)

        if not path.exists() or not path.is_dir():
            raise ValueError(
                f"Config key 'data_dir_path' must be a valid existing directory: {path}"
            )

        # Normalize path
        data["data_dir_path"] = str(path.resolve())

        self._config = data

    def _load_without_validation(self):
        """Load config without validation. Used when reading existing config for setup purposes."""
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._config = data
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in config file: {e}")

    @classmethod
    def config_exists(cls) -> bool:
        """Check if the config file exists without initializing an instance."""
        appdata = os.environ.get("APPDATA")
        if not appdata:
            return False
        config_path = Path(appdata) / cls.APP_NAME / cls.CONFIG_FILENAME
        return config_path.exists()

    @classmethod
    def create_new_config(cls):
        appdata_dir = Path(os.environ.get("APPDATA", "")) / cls.APP_NAME
        config_path = appdata_dir / cls.CONFIG_FILENAME
        appdata_dir.mkdir(parents=True, exist_ok=True)

        existing_config = None
        if config_path.exists():
            instance = cls(validate=False)  # Load without validation
            existing_config = instance._config
            while True:
                response = input(f"\nA config file for this user ({instance.user}) already exists: {config_path}\nDo you want to overwrite it? (y/n): ").strip().lower()
                if response in ('y', 'n', 'yes', 'no'):
                    break
                print("Please enter 'y' or 'n'.")

            if not response in ('y', 'yes'):
                print("Config creation cancelled.")
                return None

        logger = logging.getLogger('oregon_processing.config_manager')
        logging_extra = {'process_name': 'Configuration'}
        logger.info("Creating new configuration for oregon_communicator\n", extra=logging_extra)

        user = getpass.getuser()

        # Get data directory with existing value as default if overwriting
        default_data_dir = existing_config.get("data_dir_path") if existing_config else None
        while True:
            prompt = "Enter data directory path"
            if default_data_dir:
                prompt += f" [{default_data_dir}]"
            prompt += ": "
            data_dir = input(prompt).strip()

            # Use existing value if user just presses enter
            if not data_dir and default_data_dir:
                data_dir = default_data_dir

            if not data_dir:
                print("Data directory path cannot be empty.\n")
                continue

            data_dir = cls._strip_quotes(data_dir)
            path = Path(data_dir)

            if path.exists() and path.is_dir():
                data_dir = str(path.resolve())
                break

            print("Invalid directory path. Please enter an existing directory.\n")

        config_data = {
            "user": user,
            "data_dir_path": data_dir
        }

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4)

        logger.info(f"\nConfig file created at:\n{config_path}", extra=logging_extra)

        return cls()
