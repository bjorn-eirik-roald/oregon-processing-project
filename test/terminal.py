# -*- coding: utf-8 -*-
"""
Oregon RFID Terminal
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import src modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from oregon_processing.oregon_communicator import OregonCommunicator

if __name__ == '__main__':

    with OregonCommunicator() as communicator:

        communicator.connect()
        communicator.interactive_terminal()