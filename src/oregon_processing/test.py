# -*- coding: utf-8 -*-
"""
Oregon RFID Communicator
"""

from oregon_communicator import OregonCommunicator

if __name__ == '__main__':

    with OregonCommunicator() as communicator:

        communicator.connect()
        communicator.export_system_status_to_file('system_status.txt')
        communicator.export_upload_log_to_file('upload_log.txt')
        #communicator.interactive_terminal()