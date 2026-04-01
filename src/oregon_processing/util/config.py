
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from abc import ABC

from oregon_processing.util.exceptions import ConfigNotFoundError, InvalidConfigError

class Config(ABC):

    """
    Abstract base class for configuration handlers.
    Defines general config interface and attribute/type mapping.
    """

    CONFIG_FILE_NAME: str = ""
    APP_DIR_PARTS: tuple = ()
    ATTR_MAP: dict = {}

    def __init__(self):
        self._config_file_path = self.get_config_file_path()
        self._attributes = {}
        self._load_and_validate()

    @property
    def config_file_path(self) -> Path:
        return self._config_file_path

    @classmethod
    def create_or_overwrite_config(cls) -> bool:
        """
        Interactively create or overwrite the config file, prompting for all required values
        based on ATTR_MAP. Writes config if confirmed by the user.
        """
        config_path = cls.get_config_file_path()
        existing_data = cls._read_existing_config_if_available(config_path)
        if existing_data is None:
            if not cls._prompt_yes_no("No config file found. Create a new config?"):
                print("Config creation cancelled.")
                return False
        else:
            if not cls._prompt_yes_no("Config file already exists. Overwrite it?"):
                print("Config overwrite cancelled.")
                return False
        # Build defaults for all attributes
        defaults = {k: existing_data.get(k, "") if existing_data else "" for k in cls.ATTR_MAP}
        payload = {}
        for key, attr_info in cls.ATTR_MAP.items():
            typ = attr_info['type']
            display_name = attr_info.get('display', key)
            prompt = f"Enter {display_name}"
            default = defaults[key]
            if typ is str:
                value = cls._prompt_str_value(prompt, default)
            elif typ is float:
                value = cls._prompt_float_value(prompt, default)
            elif typ is int:
                value = cls._prompt_int_value(prompt, default)
            elif typ is Path:
                path = cls._prompt_directory(prompt, default)
                value = str(path)
            else:
                raise InvalidConfigError(f"Unsupported config attribute type: {typ} for {key}")

            payload[key] = value

        errors = cls._validate_payload(payload)
        if errors:
            print("Invalid config:")
            for err in errors:
                print(f"- {err}")
            return False
        print("\nConfiguration to save:")
        for key, value in payload.items():
            display_name = cls.ATTR_MAP[key].get('display', key)
            print(f"- {display_name}: {value}")
        if not cls._prompt_yes_no("Confirm and write config file?"):
            print("Config write cancelled.")
            return False
        cls._write_config(config_path, payload)
        print(f"Config written to: {config_path}")
        return True

    @classmethod
    def get_config_dir(cls) -> Path:
        appdata = os.getenv("APPDATA")
        if appdata:
            return Path(appdata).joinpath(*cls.APP_DIR_PARTS)
        fallback = Path.home() / "AppData" / "Roaming"
        return fallback.joinpath(*cls.APP_DIR_PARTS)

    @classmethod
    def get_config_file_path(cls) -> Path:
        return cls.get_config_dir() / cls.CONFIG_FILE_NAME

    @classmethod
    def _read_existing_config_if_available(cls, config_path: Path) -> dict[str, Any] | None:
        if not config_path.exists():
            return None
        try:
            with config_path.open("r", encoding="utf-8") as file_handle:
                loaded_data = json.load(file_handle)
            return loaded_data if isinstance(loaded_data, dict) else None
        except (OSError, json.JSONDecodeError):
            return None

    @classmethod
    def _write_config(cls, config_path: Path, payload: dict[str, Any]) -> None:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with config_path.open("w", encoding="utf-8") as file_handle:
            json.dump(payload, file_handle, indent=2, ensure_ascii=False)
            file_handle.write("\n")



    @staticmethod
    def _validate_payload(payload: Any) -> list[str]:
        """
        Validate the config payload for required fields and correct types/values using ATTR_MAP.
        Returns a list of all error messages found in the config.
        """
        errors = []
        if not isinstance(payload, dict):
            errors.append("Invalid config: expected a JSON object.")
            return errors
        for key, attr_info in Config.ATTR_MAP.items():
            typ = attr_info['type']
            if key not in payload:
                errors.append(f"Invalid config: missing '{key}'.")
                continue
            value = payload[key]
            try:
                if typ is float:
                    Config._to_float(key, value)
                elif typ is int:
                    Config._to_int(key, value)
                elif typ is str:
                    Config._to_string(key, value)
                elif typ is Path:
                    Config._to_path(key, value)
                else:
                    errors.append(f"Unsupported config attribute type: {typ} for {key}")
            except Exception as e:
                errors.append(f"Invalid config: {key}: {e}")
        return errors

    def _load_and_validate(self) -> None:
        if not self._config_file_path.exists():
            raise ConfigNotFoundError(
                f"No config file found at '{self._config_file_path}'.\n"
                f"Run {self.__class__.__name__}.create_or_overwrite_config() to create a config file before continuing. \n"
                f"You can also use designated config creation scripts in the bin directory."
            )

        with self._config_file_path.open("r", encoding="utf-8") as file_handle:
            payload = json.load(file_handle)

        errors = self._validate_payload(payload)

        if errors:
            raise InvalidConfigError("; ".join(errors))
        for key, attr_info in self.ATTR_MAP.items():
            value = payload[key]
            typ = attr_info['type']
            if typ is Path:
                value = self._to_path(key, value)
            elif typ is int:
                value = self._to_int(key, value)
            elif typ is float:
                value = self._to_float(key, value)
            elif typ is str:
                value = self._to_string(key, value)
            setattr(self, key, value)

    # Utility conversion methods (can be used by subclasses)
    @staticmethod
    def _to_path(field_name: str, value: Any) -> Path:
        if isinstance(value, Path):
            path = value
        elif isinstance(value, str):
            normalized = value.strip()
            if normalized == "":
                raise InvalidConfigError(f"Invalid config: '{field_name}' must be a directory path.")
            path = Path(normalized)
        else:
            raise InvalidConfigError(f"Invalid config: '{field_name}' must be a directory path.")
        if not path.exists() or not path.is_dir():
            raise InvalidConfigError(f"Invalid config: '{field_name}' directory does not exist: {path}")
        return path

    @staticmethod
    def _to_string(field_name: str, value: Any) -> str:
        if isinstance(value, str):
            return value
        if value is None:
            raise InvalidConfigError(f"Invalid config: '{field_name}' must be a string.")
        return str(value)

    @staticmethod
    def _to_float(field_name: str, value: Any) -> float:
        if isinstance(value, bool) or value is None:
            raise InvalidConfigError(f"Invalid config: '{field_name}' must be a float.")
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            normalized = value.strip().replace(" ", "").replace(",", ".")
            if normalized == "":
                raise InvalidConfigError(f"Invalid config: '{field_name}' must be a float.")
            return float(normalized)
        raise InvalidConfigError(f"Invalid config: '{field_name}' must be a float.")

    @staticmethod
    def _to_int(field_name: str, value: Any) -> int:
        if isinstance(value, bool) or value is None:
            raise InvalidConfigError(f"Invalid config: '{field_name}' must be an int.")
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            if value.is_integer():
                return int(value)
            raise InvalidConfigError(f"Invalid config: '{field_name}' must be an int.")
        if isinstance(value, str):
            normalized = value.strip().replace(" ", "")
            if normalized == "":
                raise InvalidConfigError(f"Invalid config: '{field_name}' must be an int.")
            if "." in normalized or "," in normalized:
                as_float = float(normalized.replace(",", "."))
                if not as_float.is_integer():
                    raise InvalidConfigError(f"Invalid config: '{field_name}' must be an int.")
                return int(as_float)
            return int(normalized)
        raise InvalidConfigError(f"Invalid config: '{field_name}' must be an int.")

    @staticmethod
    def _prompt_yes_no(prompt: str) -> bool:
        suffix = "[y/n]"
        while True:
            answer = input(f"{prompt} {suffix}: ").strip().lower()
            if answer in {"y", "yes"}:
                return True
            if answer in {"n", "no"}:
                return False
            print("Invalid answer. Please respond with 'y' or 'n'.")

    @classmethod
    def _prompt_directory(cls, prompt: str, default_value: str) -> Path:
        while True:
            default_text = "" if default_value in (None, "") else str(default_value)
            prompt_suffix = f" [Press Enter to use {default_text}]" if default_text else ""
            answer = input(f"{prompt}{prompt_suffix}: ").strip()
            selected = answer or default_text
            if not selected:
                print("A directory path is required.")
                continue
            try:
                return cls._to_path(prompt, selected)
            except InvalidConfigError:
                print(f"Invalid input: '{selected}' is not a valid directory path. Please enter a valid directory path.")

    @classmethod
    def _prompt_str_value(cls, prompt: str, default_value: str) -> str:
        while True:
            default_text = "" if default_value in (None, "") else str(default_value)
            prompt_suffix = f" [Press Enter to use {default_text}]" if default_text else ""
            answer = input(f"{prompt}{prompt_suffix}: ").strip()
            selected = answer or default_text
            if not selected:
                print("A value is required.")
                continue
            try:
                return cls._to_string(prompt, selected)
            except InvalidConfigError:
                print(f"Invalid input: '{selected}' is not a valid string. Please enter a valid string value.")

    @classmethod
    def _prompt_float_value(cls, prompt: str, default_value) -> float:
        while True:
            default_text = "" if default_value in (None, "") else str(default_value)
            prompt_suffix = f" [Press Enter to use {default_text}]" if default_text else ""
            answer = input(f"{prompt}{prompt_suffix}: ").strip()
            selected = answer or default_text
            if not selected:
                print("A value is required.")
                continue
            try:
                return cls._to_float(prompt, selected)
            except InvalidConfigError:
                print(f"Invalid input: '{selected}' is not a valid number. Please enter a valid float value.")

    @classmethod
    def _prompt_int_value(cls, prompt: str, default_value) -> int:
        while True:
            default_text = "" if default_value in (None, "") else str(default_value)
            prompt_suffix = f" [Press Enter to use {default_text}]" if default_text else ""
            answer = input(f"{prompt}{prompt_suffix}: ").strip()
            selected = answer or default_text
            if not selected:
                print("A value is required.")
                continue
            try:
                return cls._to_int(prompt, selected)
            except InvalidConfigError:
                print(f"Invalid input: '{selected}' is not a valid integer. Please enter a valid integer value.")


