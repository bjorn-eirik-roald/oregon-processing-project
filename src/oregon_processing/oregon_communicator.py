# -*- coding: utf-8 -*-
"""
Oregon RFID Communicator
"""

import time
import serial
import serial.tools.list_ports


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

    def connect(self):
        """Attempt to connect to Oregon RFID sensor with circular retry options."""

        # Ask user to select baud rate upfront
        bauds = self._select_baud_rate()
        if not bauds:
            print("Connection cancelled.")
            return False

        print("\nAttempting to connect to Oregon RFID sensor:")
        while True:

            all_ports = [p for p in serial.tools.list_ports.comports()]

            # Attempt to connect using Prolific ports
            if self._handle_prolific_port_search(all_ports, bauds):
                return True

            print("\nOptions:")
            print("1. Select a specific port to attempt.")
            print("2. Attempt all available ports.")
            print("3. Search for Prolific ports again.")
            print("4. Abort connection process.")

            # Loop until valid choice is made
            while True:
                choice = input("\nEnter your choice (1, 2, 3, or 4): ").strip()

                # Validate input
                if choice not in ["1", "2", "3", "4"]:
                    print("Invalid choice. Please enter 1, 2, 3, or 4.")
                    continue

                # Valid choice - process accordingly
                if choice == "1":
                    if self._handle_manual_port_selection(all_ports, bauds):
                        return True
                    break  # Exit choice loop to restart options

                elif choice == "2":
                    if self._handle_all_ports_selection(all_ports, bauds):
                        return True
                    break  # Exit choice loop to restart options

                elif choice == "3":
                    break  # Exit choice loop to restart Prolific search

                elif choice == "4":
                    print("Connection process aborted by user.")
                    return False

    def _handle_prolific_port_search(self, all_ports, bauds):
        """Search for and attempt connection on Prolific ports. Returns True if connection successful."""
        print("Attempting to find and connnect to Prolific USB serial adapter ports:")

        # Filter for Prolific ports (common for USB serial adapters)
        prolific_ports = [p.device for p in all_ports if "prolific" in p.description.lower()]

        if prolific_ports:
            print(f"\t- Found Prolific port(s): {prolific_ports}")
            print("\t- Attempting connection on Prolific port(s)...", end="", flush=True)

            if self._attempt_connection(prolific_ports, bauds):
                print("Connected successfully!")
                return True

            # Prolific ports found but connection failed
            print("Connection failed on Prolific port(s). Device did not respond.")
            return False
        else:
            # No Prolific ports found
            print("\t- No Prolific USB serial adapter ports found.")
            return False

    def _handle_manual_port_selection(self, all_ports, bauds):
        """Handle user selecting a specific port. Returns True if connection successful."""
        if not all_ports:
            print("No ports available.")
            return False

        print("\nAvailable ports:")
        for i, port in enumerate(all_ports, 1):
            print(f"{i}. {port.device} - {port.description}")
        print(f"{len(all_ports) + 1}. Cancel and return to main menu")

        # Loop until valid port is selected
        while True:
            port_choice = input("\nSelect a port (enter number): ").strip()
            try:
                port_index = int(port_choice) - 1
                if 0 <= port_index < len(all_ports):
                    selected_port = all_ports[port_index].device
                    if self._attempt_connection([selected_port], bauds):
                        return True
                    return False
                elif port_index == len(all_ports):
                    print("Returning to main menu.")
                    return False
                else:
                    print("Invalid port selection. Please try again.")
            except ValueError:
                print("Invalid input. Please enter a number.")

    def _handle_all_ports_selection(self, all_ports, bauds):
        """Handle attempting connection on all available ports. Returns True if connection successful."""
        if not all_ports:
            print("No ports available.")
            return False

        ports = [p.device for p in all_ports]
        print(f"Will attempt to connect to: {ports}")
        return self._attempt_connection(ports, bauds)

    def _select_baud_rate(self):
        """Allow user to select baud rate(s) to use for connection."""
        print("\n=== Baud Rate Selection ===")
        print("Available baud rates:")
        for i, baud in enumerate(self.BAUD_RATES, 1):
            print(f"{i}. {baud}")
        print(f"{len(self.BAUD_RATES) + 1}. Try all baud rates")

        choice = input("\nSelect a baud rate option (enter option number): ").strip()
        try:
            index = int(choice) - 1
            if 0 <= index < len(self.BAUD_RATES):
                return [self.BAUD_RATES[index]]
            elif index == len(self.BAUD_RATES):
                return self.BAUD_RATES
            else:
                print("Invalid selection.")
                return None
        except ValueError:
            print("Invalid input. Please enter an option number.")
            return None

    def _attempt_connection(self, ports, bauds):
        """Helper method to attempt connection on a list of ports with specified baud rates."""

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
                        print(f"Successfully connected to {port} at {baud} baud")
                        return True

                    ser.close()

                except Exception:
                    continue

        print("No device found on the attempted port(s).")
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

    def get_system_status(self):
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
