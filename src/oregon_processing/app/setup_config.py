# -*- coding: utf-8 -*-
"""
Configuration Setup Script
Standalone script to create or update the communicator configuration file.

Usage:
    python -m oregon_processing.app.setup_config
    or via entry point: setup-config
"""

from oregon_processing.util.config_manager import ConfigManager
from oregon_processing.util.logging_manager import LoggingManager
import logging


def run():
    """Run the configuration setup wizard."""
    with LoggingManager('setup_config', file_logging=False):
        logger = logging.getLogger('oregon_processing')
        logging_extra = {'process_name': 'Setup Config'}

        logger.info("Starting configuration setup wizard.", extra=logging_extra)

        config = ConfigManager.create_new_config()

        if config:
            logger.info("Configuration setup completed successfully.", extra=logging_extra)
            with config:
                pass  # The __enter__ method prints the configuration summary
        else:
            logger.info("Configuration setup was cancelled.", extra=logging_extra)


if __name__ == "__main__":
    run()
