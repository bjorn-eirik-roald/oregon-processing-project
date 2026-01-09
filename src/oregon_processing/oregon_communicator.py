# -*- coding: utf-8 -*-
"""
Oregon RFID Communicator
"""

from inspect import signature
import time
import serial
import serial.tools.list_ports

# Support
try:
    import readline  # Linux / macOS
except ImportError:
    import pyreadline3 as readline  # Windows



class OregonCommunicator:
    """Class to communicate with Oregon device via serial port."""

    BAUD_RATES = [115200, 57600, 9600]
    VALID_MAIN_COMMANDS = {
        # Reader power / operation
        "ON", "ST", "OF",

        # Bluetooth
        "BT0", "BT1",

        # Status / diagnostics
        "SY", "NO", "AB", "QU", "HE",

        # Beeper / LEDs / display
        "BP0", "BP1", "BP2",
        "BR1", "BR2", "BR3",
        "DK",

        # Antenna / tuning
        "TU", "TO", "AP", "AS", "MQ",
        "SM", "SMA",
        "MX", "MV",

        # Timing / scheduling
        "TM", "DT", "TZ",
        "OVG", "OVN",

        # Scan / detection behavior
        "DM",
        "FS",
        "TF",
        "TC",
        "RE",
        "MP",
        "PH0", "PH1",
        "HD", "HDR", "HDC", "HDL",
        "MC",

        # Configuration / identity
        "RN", "SC",
        "BC", "BCR",

        # Datalogger / records
        "UH",
        "UP", "UP*", "UPS",
        "UD", "UT",
        "ER",
        "CO",
        "TL",
        "FM", "FN",
        "WE0", "WE1",
        "LA",
        "CS",
        "MG",

        # Network / multi-reader
        "NL", "SL",

        # GNSS / location / sensors
        "GNS0", "GNS1",
        "LO",
        "TS",

        # Utilities
        "CV",

        # Firmware / maintenance
        "FW",
        "RD",
        "RB",
        "FR", "FRD", "FRR", "FRA",
    }

    def __init__(self):
        self.connection = None
        self.port = None
        self.baudrate = None
        self.last_prompt_signature = None

    def __enter__(self):
        """Allow use in 'with' statement."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Ensure the connection is closed when leaving context."""
        self.close()

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

    def _select_baud_rate(self):
        """Allow user to select baud rate(s) to use for connection."""
        print("\n=== Baud Rate Selection ===")
        print("Available baud rates:")
        for i, baud in enumerate(self.BAUD_RATES, 1):
            print(f"  {i}. {baud}")
        print(f"  {len(self.BAUD_RATES) + 1}. Try all baud rates")
        print(f"  {len(self.BAUD_RATES) + 2}. Abort connection process")

        while True:
            choice = input("\nSelect a baud rate option (enter option number): ").strip()
            index = int(choice) - 1

            # Return selected baud rate(s)
            if 0 <= index < len(self.BAUD_RATES):
                return [self.BAUD_RATES[index]]
            # User chose to try all baud rates
            elif index == len(self.BAUD_RATES):
                return self.BAUD_RATES
            #User cancelled
            elif index == len(self.BAUD_RATES) + 1:
                return None
            # Invalid selection
            else:
                print("Invalid selection!", end=" ")

    def _attempt_connection(self, ports, bauds):
        """Helper method to attempt connection on a list of ports with specified baud rates."""
        for port in ports:
            for baud in bauds:
                print(f"Attempting connection to {port} at {baud} baud...", end="", flush=True)

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
                        print("SUCCESS!")
                        print(f"Successfully connected to {port} at {baud} baud")
                        # Send a quick SY command to verify comms and capture prompt signature
                        self._post_connect_handshake()
                        return True

                    ser.close()
                    print("No response.")

                except Exception as e:
                    print(f" Error: {e}")

        print("No device found on the attempted port(s).")
        return False

    def _handle_manual_port_selection(self, ports, bauds):
        """Handle user selecting a specific port. Returns True if connection successful."""
        if not ports:
            print("No ports available.")
            return False

        print("\nAvailable ports:")
        for i, port in enumerate(ports, 1):
            print(f"  {i}. {port.device} - {port.description}")
        print(f"  {len(ports) + 1}. Cancel and return to main menu")

        # Loop until valid port is selected
        while True:
            port_choice = input("\nSelect a port (enter number): ").strip()
            port_index = int(port_choice) - 1

            if 0 <= port_index < len(ports):
                selected_port = ports[port_index].device
                if self._attempt_connection([selected_port], bauds):
                    return True
                return False
            elif port_index == len(ports):
                print("Cancelled. Returning to main menu.")
                return False
            else:
                print("Invalid port selection. Please try again.")

    def _handle_prolific_port_search(self, ports, bauds):
        """Search for and attempt connection on Prolific ports. Returns True if connection successful."""

        print("\nSearching for Prolific USB serial adapter ports...")

        # Filter for Prolific ports (common for USB serial adapters)
        prolific_ports = [p.device for p in ports if "prolific" in p.description.lower()]

        if prolific_ports:
            print(f"Found Prolific port(s): {prolific_ports}")

            if self._attempt_connection(prolific_ports, bauds):
                return True

            # Prolific ports found but connection failed
            print("Connection failed. Device did not respond.")
            return False
        else:
            # No Prolific ports found
            print("No Prolific USB serial adapter ports found.")
            return False

    def _handle_all_ports_selection(self, ports, bauds):
        """Handle attempting connection on all available ports. Returns True if connection successful."""
        if not ports:
            print("No ports available.")
            return False

        port_devices = [p.device for p in ports]
        print(f"\nAttempting all available ports: {port_devices}")
        return self._attempt_connection(port_devices, bauds)

    def _post_connect_handshake(self):
        """Send a quick SY command to verify connection and capture prompt signature."""

        if not self.connection:
            return
        try:
            # Ignore returned lines; purpose is to confirm comms and set last_prompt_signature
            self.send_command_and_receive_response("sy")
        except Exception:
            # Non-fatal; connection is still established
            pass

    def connect(self):
        """Attempt to connect to Oregon RFID sensor with circular retry options."""

        print("=== Oregon RFID Communicator Connection ===")

        # Ask user to select baud rate upfront
        bauds = self._select_baud_rate()
        if not bauds:
            print("Connection process aborted by user.")
            return False

        #loop until connection is successful or user aborts
        while True:

            ports = [p for p in serial.tools.list_ports.comports()]

            # select option for selecting port
            print("\nOptions:")
            print("  1. Select a specific port to attempt")
            print("  2. Attempt all available ports")
            print("  3. Search for Prolific ports")
            print("  4. Abort connection process")

            # Loop until valid choice is made
            while True:
                choice = input("\nEnter your choice (1, 2, 3, or 4): ").strip()

                # Validate input
                if choice not in ["1", "2", "3", "4"]:
                    print("Invalid choice. Please enter 1, 2, 3, or 4.")
                    continue

                # Valid choice - process accordingly
                if choice == "1":
                    result = self._handle_manual_port_selection(ports, bauds)
                    if result:
                        return True
                    else:
                        break  # Exit choice loop to restart options

                elif choice == "2":
                    result = self._handle_all_ports_selection(ports, bauds)
                    if result:
                        return True
                    else:
                        break  # Exit choice loop to restart options

                elif choice == "3":
                    result = self._handle_prolific_port_search(ports, bauds)
                    if result:
                        return True
                    else:
                        break  # Exit choice loop to restart Prolific search
                elif choice == "4":
                    print("Connection process aborted by user.")
                    return False

    def _is_valid_command(self, command: str) -> bool:
        """Basic validation: command must start with two-letter main code followed by a space or end."""
        if not command or len(command) < 2:
            return False

        main = command[:2].upper()

        if main not in self.VALID_MAIN_COMMANDS:
            return False

        # Require a space or end after the two-letter main code
        if len(command) == 2:
            return True
        return command[2].isspace()

    def _validate_prompt_signature(self, signature: str) -> bool:
        """
        Validate an Oregon RFID prompt signature.

        Oregon RFID devices prepend each serial output line with a
        4-character prompt signature describing the current device state.
        The format is positional and must be interpreted by character index:

            [0][1][2][3]
            |  |  |  |
            |  |  |  └─ Audible feedback state
            |  |  └──── Time synchronization source
            |  └────── Run / scan state
            └───────── Network / operating mode

        Character definitions:

        Character 1 = Operating mode:
            '0' : Off with power
            'H' : Host mode (generates system timing for network)
            'N' : Node mode (synchronized to host)

        Character 2 = Run state:
            'R' : Running; scanning enabled, detections saved to file
            'S' : Standby; not scanning, database accessible
            'Z' : Off

        Character 3 = Time synchronization:
            'G' : Synchronized to GNSS signals
            'N' : Synchronized to network signal
            'U' : Unsynchronized

        Character 4 = Beeper state:
            'B' : Beeper enabled
            '*' : Beeper disabled

        Validation rules:
            - Signature must be exactly 4 characters long
            - Each character must be valid for its position
            - Signature must be a string (not None)

        Example:
            "HRGB" → valid
            "HSU*" → valid
            "HRGX" → invalid (unknown beeper state)
            "ABCD" → invalid
            "HRG"  → invalid (wrong length)

        Parameters
        ----------
        signature : str
            Four-character prompt signature (e.g. "HRGB").

        Returns
        -------
        bool
            True if the signature is valid according to the Oregon RFID
            prompt signature specification, otherwise False.
        """

        if not isinstance(signature, str):
            raise TypeError("Signature must be a string.")

        if len(signature) != 4:
            return False

        valid_sets = (
            {'0', 'H', 'N'},  # operating mode
            {'R', 'S', 'Z'},  # run state
            {'G', 'N', 'U'},  # time sync
            {'B', '*'}       # beeper
        )

        valid_signature = all(c in valid for c, valid in zip(signature, valid_sets))

        if valid_signature:
            self.last_prompt_signature = signature

        return valid_signature

    def send_command_and_receive_response(self, command, timeout=5):
        """
        Send a command and read lines until a known prompt ending appears.
        Uses an idle timeout: the clock resets each time data arrives. Returns the
        cleaned response (list of lines) with echoed command and prompts removed.
        """
        if not self.connection:
            raise ConnectionError("Not connected to device.")

        # Clear stale input
        self.connection.reset_input_buffer()

        # Send command
        self.connection.write((command + "\r\n").encode())
        self.connection.flush()

        lines = []
        last_data_time = time.time()

        while True:
            line = self.connection.readline().decode(errors="ignore").strip()
            if line:
                # check for valid prompt signature to end reading
                if self._validate_prompt_signature(line[:4]):
                    self.last_prompt_signature = line[:4]
                    break

                lines.append(line)
                last_data_time = time.time()

            # Idle timeout: only break if no new data arrives within timeout
            if time.time() - last_data_time > timeout:
                break

        # Remove echoed command and empty lines
        cleaned = [l for l in lines if l and l != command]
        return cleaned

    def interactive_terminal(self):
        print("\nEntering interactive terminal. Type 'exit' to quit.")

        try:
            while True:
                prompt = f"\n{self.last_prompt_signature or ''}>> "
                cmd = input(prompt).strip()
                if not cmd:
                    continue

                # Exit on 'exit' or 'quit'
                if cmd.lower() in ("exit", "quit"):
                    print("Exiting terminal.")
                    break

                # Validate command format
                if not self._is_valid_command(cmd):
                    print("Invalid command. Use a two-letter code followed by a space (e.g., 'SY ').")
                    print(f"Valid codes: {sorted(self.VALID_MAIN_COMMANDS)}")
                    continue

                # send command and get cleaned response
                lines = self.send_command_and_receive_response(cmd)
                if lines:
                    print("\n".join(lines))
                else:
                    print("Command received without error")

        except KeyboardInterrupt:
            print("\nTerminal interrupted by user.")




