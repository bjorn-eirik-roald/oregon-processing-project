# -*- coding: utf-8 -*-
"""
Oregon RFID Communicator
"""

import serial
import serial.tools.list_ports

class OregonCommunicator:
    """Class to communicate with Oregon device via serial port."""

    BAUD_RATES = [9600, 57600, 115200]

    def __init__(self):
        self.connection = None
        self.port = None
        self.baudrate = None

    def connect(self):
        """Try all available ports with all baud rates until success."""
        ports = [p.device for p in serial.tools.list_ports.comports()]
        for port in ports:
            for baud in self.BAUD_RATES:
                try:
                    ser = serial.Serial(port, baudrate=baud, timeout=1)
                    # test connection with SY command
                    ser.write(b"SY\r\n")
                    response = ser.readline().decode(errors="ignore").strip()
                    if response:  # got something back
                        self.connection = ser
                        self.port = port
                        self.baudrate = baud
                        print(f"Connected to {port} at {baud}")
                        return True
                    ser.close()
                except Exception as e:
                    pass  # try next
        print("No device found.")
        return False

    def send_command(self, command):
        """Send command and return response."""
        if not self.connection:
            raise ConnectionError("Not connected to device.")
        self.connection.write((command + "\r\n").encode())
        return self.connection.readline().decode(errors="ignore").strip()

    def system_status(self):
        """Request system status (SY)."""
        return self.send_command("SY")

    def power_on(self):
        """Turn unit on."""
        return self.send_command("ON")

    def power_off(self):
        """Turn unit off."""
        return self.send_command("OFF")

    def close(self):
        """Close serial connection."""
        if self.connection:
            self.connection.close()
            print("Connection closed.")
            self.connection = None
