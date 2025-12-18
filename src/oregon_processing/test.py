# -*- coding: utf-8 -*-
"""
Oregon RFID Communicator
"""

from oregon_communicator import OregonCommunicator

if __name__ == '__main__':
    
    with OregonCommunicator() as communicator:
    
        communicator.connect(preferred_baud=115200, preferred_port="COM7")
        #communicator.connect()
            
        print(communicator.system_status())
        communicator.interactive_terminal()