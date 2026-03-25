# -*- coding: utf-8 -*-
"""
Configuration Setup Script
Standalone script to create or update the communicator configuration file.
"""

from oregon_processing.util.oregon_config import OregonConfig

def setup_config():
    """Run the configuration setup wizard."""

    OregonConfig.create_or_overwrite_config()
