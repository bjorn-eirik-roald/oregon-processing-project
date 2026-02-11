# -*- coding: utf-8 -*-
"""
Configuration Setup Script
Standalone script to create or update the oregon_communicator configuration file.

Usage:
    python -m oregon_processing.app.setup_config
    or via entry point: setup-oregon-config
"""

from oregon_processing.util.config_manager import ConfigManager


def run():
    """Run the configuration setup wizard."""
    print("\n" + display.SECTION_SEPARATOR * display.SECTION_LINE_LENGTH)
    print("Oregon RFID Communicator - Configuration Setup")
    print(display.SECTION_SEPARATOR * display.SECTION_LINE_LENGTH)

    config = ConfigManager.create_new_config()

    if config:
        print("\n" + display.SECTION_SEPARATOR * display.SECTION_LINE_LENGTH)
        print("Configuration Setup Complete!")
        print(display.SECTION_SEPARATOR * display.SECTION_LINE_LENGTH)
        with config:
            pass  # The __enter__ method prints the configuration summary
    else:
        print("\nConfiguration setup was cancelled.")


if __name__ == "__main__":
    run()
