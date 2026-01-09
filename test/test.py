# -*- coding: utf-8 -*-
"""
Oregon RFID Communicator Test
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import src modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from oregon_processing.oregon_communicator import OregonCommunicator
from datetime import date

if __name__ == '__main__':

    with OregonCommunicator() as communicator:

        communicator.connect()
        communicator.check_system_status_health()
        communicator.export_system_status('system_status.txt')
        communicator.export_upload_log('upload_log.txt')
        communicator.export_system_status_log(date(2026, 1, 8))
        communicator.export_system_status_logs_from_last_upload(Path('system_log'))
        #communicator.interactive_terminal()