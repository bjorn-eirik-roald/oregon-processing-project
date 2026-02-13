# -*- coding: utf-8 -*-
"""
Oregon RFID Terminal
"""

from oregon_processing.util.logging_manager import LoggingManager
from oregon_processing.util.oregon_communicator import OregonCommunicator
import logging

def run():
    with LoggingManager('terminal', file_logging=False):
        logger = logging.getLogger('oregon_processing')
        with OregonCommunicator() as communicator:
            if communicator.is_connected:
                communicator.start_interactive_terminal()
            else:
                logger.info("Connection not established. Aborting terminal session.", extra={"process_name": "Open Terminal"})

if __name__ == '__main__':
    run()