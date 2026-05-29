# -*- coding: utf-8 -*-
"""
Open Terminal connection to Oregon RFID Device
"""

from oregon_processing.util import (ConfigNotFoundError, InvalidConfigError, ConnectionFailedError, UnexpectedResponseError,
                                    CommandTransmissionError, UserCancelledError, DeviceHealthError, ClockSyncError, ModeChangeError)
from oregon_processing.util import LoggingManager, get_logger
from oregon_processing.util.communicator import Communicator

def open_terminal():

    try:
        with LoggingManager(write_to_console=True, write_to_report_file=False):
            logger = get_logger(__name__)
            with Communicator() as communicator:
                if communicator.is_connected:
                    communicator.start_interactive_terminal()
                else:
                    logger.info("Connection not established. Aborting terminal session.")
    except (ConfigNotFoundError, InvalidConfigError) as e:
        print(f"\n\n"+str(e) + "\n\nPlease ensure the configuration file is present and valid, then try again.")
    except (ConnectionFailedError, UnexpectedResponseError, CommandTransmissionError, UserCancelledError, DeviceHealthError, ClockSyncError, ModeChangeError) as e:
        print(f"\n\n"+"An error occurred while opening the terminal connection\nPlease check the log file for details and try again.\n\n")

if __name__ == "__main__":
    open_terminal()
