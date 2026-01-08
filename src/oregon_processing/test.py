# -*- coding: utf-8 -*-
"""
Oregon RFID Communicator
"""

from oregon_communicator import OregonCommunicator

if __name__ == '__main__':

    with OregonCommunicator() as communicator:

        communicator.connect()
        communicator.interactive_terminal()