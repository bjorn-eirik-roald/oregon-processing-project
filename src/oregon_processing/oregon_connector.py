import serial
import serial.tools.list_ports


class OregonConnector:
    """Class to handle connection establishment with Oregon RFID devices."""

    BAUD_RATES = [115200, 57600, 9600]

    def __init__(self):
        pass

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
            try:
                index = int(choice) - 1
            except ValueError:
                print("Invalid selection! Enter a number from the list.", end=" ")
                continue

            # Return selected baud rate(s)
            if 0 <= index < len(self.BAUD_RATES):
                return [self.BAUD_RATES[index]]
            # User chose to try all baud rates
            elif index == len(self.BAUD_RATES):
                return self.BAUD_RATES
            # User cancelled
            elif index == len(self.BAUD_RATES) + 1:
                print("Baud rate selection aborted.")
                return None
            # Invalid selection
            else:
                print("Invalid selection! Enter a number from the list.", end=" ")


        print("No device found on the attempted port(s).")
        return None

    def _handle_manual_port_selection(self, ports):
        """Handle user selecting a specific port. Returns selected port device or None."""
        if not ports:
            print("\nNo ports available.")
            return None

        print("\nAvailable ports:")
        for i, port in enumerate(ports, 1):
            print(f"  {i}. {port.device} - {port.description}")
        print(f"  {len(ports) + 1}. Cancel and return to main menu")

        # Loop until valid port is selected
        while True:
            port_choice = input("\nSelect a port (enter number): ").strip()

            try:
                port_index = int(port_choice) - 1
            except ValueError:
                print("Invalid input. Please enter a number from the list.")
                continue

            if 0 <= port_index < len(ports):
                return ports[port_index].device
            elif port_index == len(ports):
                print("Cancelled. Returning to main menu.")
                return None
            else:
                print("Invalid port selection. Please try again.")

    def _handle_prolific_port_search(self, ports):
        """Return list of Prolific ports (if any) for later connection attempt."""

        print("\nSearching for Prolific USB serial adapter ports:", flush=True)

        # Filter for Prolific ports (common for USB serial adapters)
        prolific_ports = [p.device for p in ports if "prolific" in p.description.lower()]


        if prolific_ports:
            print(f"  Found Prolific port(s): {prolific_ports}")
            return prolific_ports

        print("  No Prolific USB serial adapter ports found.")
        return None

    def _handle_all_ports_selection(self, ports):
        """Return list of all available port devices for later connection attempt."""
        if not ports:
            print("\nNo ports available.")
            return None

        port_devices = [p.device for p in ports]
        print(f"\nEach available port will be attempted: {port_devices}")
        return port_devices

    def _select_ports(self):
        print("\n\n=== Port Selection ===")
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
                    selected_port = self._handle_manual_port_selection(ports)
                    selected_ports = [selected_port] if selected_port else None
                elif choice == "2":
                    selected_ports = self._handle_all_ports_selection(ports)
                elif choice == "3":
                    selected_ports = self._handle_prolific_port_search(ports)
                elif choice == "4":
                    print("Connection process aborted by user.")
                    return None

                if selected_ports:
                    return selected_ports
                else:
                    # No valid selection; re-display options
                    break


    def _attempt_connection(self, ports, bauds):
        """Helper method to attempt connection on a list of ports with specified baud rates."""
        for port in ports:
            for baud in bauds:
                print(f"\nAttempting connection to {port} at {baud} baud...", end="", flush=True)

                try:
                    ser = serial.Serial(port, baudrate=baud, timeout=0.2, write_timeout=0.2)
                    ser.reset_input_buffer()
                    ser.reset_output_buffer()

                    ser.write(b"SY\r\n")
                    ser.flush()

                    response = ser.readline().decode(errors="ignore").strip()

                    if response:
                        print("SUCCESS!")
                        print(f"Successfully connected to {port} at {baud} baud")
                        return {'connection': ser, 'port': port, 'baudrate': baud}

                    ser.close()
                    print("No response.")

                except Exception as e:
                    print(f" Error: {e}")

    def connect(self):
        """
        Attempt to connect to Oregon RFID sensor with circular retry options.

        Returns
        -------
        dict or None
            Dictionary with 'connection', 'port', and 'baudrate' keys if successful, None otherwise.
        """

        print("\n\n=== Oregon RFID Communicator Connection ===")

        while True:
            # Ask user to select baud rate
            bauds = self._select_baud_rate()
            if not bauds:
                return None

            # Ask user to select port(s)
            selected_ports = self._select_ports()

            if not selected_ports:
                return None

            result = self._attempt_connection(selected_ports, bauds)

            if result:
                return result


