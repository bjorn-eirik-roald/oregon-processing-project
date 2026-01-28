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
    print("\n" + "=" * 70)
    print("Oregon RFID Communicator - Configuration Setup")
    print("=" * 70)

    config = ConfigManager.create_new_config()

    if config:
        print("\n" + "=" * 70)
        print("Configuration Setup Complete!")
        print("=" * 70)
        with config:
            pass  # The __enter__ method prints the configuration summary
    else:
        print("\nConfiguration setup was cancelled.")


if __name__ == "__main__":
    run()
