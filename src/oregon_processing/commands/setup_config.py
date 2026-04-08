# -*- coding: utf-8 -*-
"""
Configuration Setup Script
Standalone script to create or update the communicator configuration file.
"""

from oregon_processing.util import OregonConfig
from oregon_processing.util import ConfigNotFoundError, InvalidConfigError

def setup_config():
    try:
        OregonConfig.create_or_overwrite_config()
    except (ConfigNotFoundError, InvalidConfigError) as e:
        print(f"\n\n"+str(e) + "\n\nPlease ensure the configuration file is present and valid, then try again.")

if __name__ == "__main__":
    setup_config()
