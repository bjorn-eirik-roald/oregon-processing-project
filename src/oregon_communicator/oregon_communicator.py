# -*- coding: utf-8 -*-
"""
Oregon RFID Communicator
"""

import time
import serial
import serial.tools.list_ports

from prompt_toolkit import prompt
from prompt_toolkit.history import InMemoryHistory

class OregonCommunicator:
    """Class to communicate with Oregon device via serial port."""

    BAUD_RATES = [115200, 57600, 9600]

    def __init__(self):
        self.connection = None
        self.port = None
        self.baudrate = None

    def __enter__(self):
        """Allow use in 'with' statement."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Ensure the connection is closed when leaving context."""
        self.close()

    def connect(self, preferred_port=None, preferred_baud=None):
        """Try all available ports with all baud rates until success."""
        
        print("Attempting to connect to various ports using multiple baud rates")
        ports = [p.device for p in serial.tools.list_ports.comports()]

        if preferred_port and preferred_baud:
            ports = [preferred_port] + [p for p in ports if p != preferred_port]
            bauds = [preferred_baud] + [b for b in self.BAUD_RATES if b != preferred_baud]
        else:
            bauds = self.BAUD_RATES

        for port in ports:
            for baud in bauds:
                try:
                    ser = serial.Serial(port, baudrate=baud, timeout=0.2, write_timeout=0.2)
                    ser.reset_input_buffer()
                    ser.reset_output_buffer()

                    ser.write(b"SY\r\n")
                    ser.flush()

                    response = ser.readline().decode(errors="ignore").strip()

                    if response:
                        self.connection = ser
                        self.port = port
                        self.baudrate = baud
                        print(f"Connected to {port} at {baud}")
                        return True

                    ser.close()

                except Exception:
                    continue

        print("No device found.")
        return False

    def send_command(self, command):
        """Send command and return response."""
        if not self.connection:
            raise ConnectionError("Not connected to device.")
        self.connection.write((command + "\r\n").encode())
        return self.connection.readline().decode(errors="ignore").strip()
    
    def send_and_receive(self, command, prompt_endings=("HREB>", "HZEB>"), timeout=2):
        """
        Send a command and read lines until a known prompt ending appears.
        Returns the cleaned response (list of lines) with echoed command and prompts removed.
        """
        if not self.connection:
            raise ConnectionError("Not connected to device.")
        
        # Clear stale input
        self.connection.reset_input_buffer()
        
        # Send command
        self.connection.write((command + "\r\n").encode())
        self.connection.flush()

        lines = []
        start_time = time.time()
        
        while True:
            line = self.connection.readline().decode(errors="ignore").strip()
            if line:
                lines.append(line)
                
                # check for known prompt
                if any(line.endswith(p) for p in prompt_endings):
                    break
                
                if time.time() - start_time > timeout:
                    break  # timeout safety
        
        
        cleaned = [l for l in lines if l.strip() and l.strip() not in (command, *prompt_endings)] 
         
        return cleaned

    def interactive_terminal(self):
        print("Entering interactive terminal. Type 'exit' to quit.")
    
        try:
            while True:
                cmd = input(">> ").strip()
                if not cmd:
                    continue
                if cmd.lower() in ("exit", "quit"):
                    print("Exiting terminal.")
                    break
    
                # send command and get cleaned response
                lines = self.send_and_receive(cmd)
                if lines:
                    print("\n".join(lines))
                else:
                    print("(no response)")
    
        except KeyboardInterrupt:
            print("\nTerminal interrupted by user.")

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
            try:
                self.connection.close()
                print(f"Connection to {self.port} closed.")
            except Exception as e:
                print(f"Error closing connection: {e}")
            finally:
                self.connection = None
                self.port = None
                self.baudrate = None
