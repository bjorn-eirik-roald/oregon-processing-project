# -*- coding: utf-8 -*-
"""
Oregon RFID Terminal
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import src modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from oregon_processing.util.oregon_communicator import OregonCommunicator

def run():
    with OregonCommunicator() as communicator:

        communicator.start_interactive_terminal()

if __name__ == '__main__':
    run()