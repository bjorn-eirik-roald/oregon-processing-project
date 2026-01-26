# -*- coding: utf-8 -*-
"""
Oregon RFID Terminal
"""


from oregon_processing.util.oregon_communicator import OregonCommunicator

def run():
    with OregonCommunicator() as communicator:

        communicator.start_interactive_terminal()

if __name__ == '__main__':
    run()