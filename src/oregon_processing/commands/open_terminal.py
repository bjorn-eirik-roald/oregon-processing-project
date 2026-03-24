# -*- coding: utf-8 -*-
"""
Oregon RFID Terminal
"""

from oregon_processing.util.logging_manager import LoggingManager, get_logger
from oregon_processing.util.communicator import Communicator

def open_terminal():
    with LoggingManager('terminal', file_logging=False):
        logger = get_logger(__name__)
        with Communicator() as communicator:
            if communicator.is_connected:
                communicator.start_interactive_terminal()
            else:
                logger.info("Connection not established. Aborting terminal session.", extra={"process_name": "Open Terminal"})
