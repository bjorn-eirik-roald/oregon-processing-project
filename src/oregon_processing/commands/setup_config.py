# -*- coding: utf-8 -*-
"""
Configuration Setup Script
Standalone script to create or update the communicator configuration file.

Usage:
    python -m oregon_processing.app.setup_config
    or via entry point: setup-config
"""

from oregon_processing.util.oregon_config import OregonConfig
from oregon_processing.util.logging_manager import LoggingManager


def setup_config():
    """Run the configuration setup wizard."""

    OregonConfig.create_or_overwrite_config()
