import logging
import serial
import serial.tools.list_ports
from oregon_processing.util.display_constants import display


class OregonConnector:
    """Class to handle connection establishment with Oregon RFID devices."""

    BAUD_RATES = [115200, 57600, 9600]

    def __init__(self):
        self.logger = logging.getLogger('oregon_processing.oregon_connector')

    def __enter__(self):
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Exit context manager."""
        pass

    def _select_baud_rate(self):
        """Allow user to select baud rate(s) to use for connection."""
        logging_extra = {'process_name': 'Baud Rate Selection'}

        selection_options = "Available baud rates:\n"
        for i, baud in enumerate(self.BAUD_RATES, 1):
            selection_options += f"  {i}. {baud}\n"
        selection_options += f"  {len(self.BAUD_RATES) + 1}. Try all baud rates\n"
        selection_options += f"  {len(self.BAUD_RATES) + 2}. Abort connection process"

        self.logger.info(selection_options, extra=logging_extra)

        while True:
            choice = input("\nSelect a baud rate option (enter option number): ").strip()
            print()  # Add spacing after selection input for readability
            try:
                index = int(choice) - 1
            except ValueError:
                self.logger.info("Invalid selection! Enter a number from the list.", extra=logging_extra)
                continue



            # Return selected baud rate(s)
            if 0 <= index < len(self.BAUD_RATES):
                self.logger.info(f"Selected baud rate: {self.BAUD_RATES[index]}", extra=logging_extra)
                return [self.BAUD_RATES[index]]
            # User chose to try all baud rates
            elif index == len(self.BAUD_RATES):
                self.logger.info("Selected option to try all baud rates.", extra=logging_extra)
                return self.BAUD_RATES
            # User cancelled
            elif index == len(self.BAUD_RATES) + 1:
                self.logger.info("Baud rate selection aborted.", extra=logging_extra)
                return None
            # Invalid selection
            else:
                self.logger.info("Invalid selection! Enter a number from the list.", extra=logging_extra)

    def _handle_manual_port_selection(self, ports):
        """Handle user selecting a specific port. Returns selected port device or None."""
        logging_extra = {'process_name': 'Port Selection'}

        if not ports:
            self.logger.info("\nNo ports available.", extra=logging_extra)
            return None

        selection_options = "Available ports:\n"
        for i, port in enumerate(ports, 1):
            selection_options += f"  {i}. {port.device} - {port.description}\n"
        selection_options += f"  {len(ports) + 1}. Cancel and return to main menu\n"

        self.logger.info(selection_options, extra=logging_extra)

        # Loop until valid port is selected
        while True:
            port_choice = input("\nSelect a port (enter number): ").strip()

            try:
                port_index = int(port_choice) - 1
            except ValueError:
                self.logger.info("Invalid input. Please enter a number from the list.", extra=logging_extra)
                continue

            if 0 <= port_index < len(ports):
                self.logger.info(f"Selected port: {ports[port_index].device} - {ports[port_index].description}", extra=logging_extra)
                return ports[port_index].device
            elif port_index == len(ports):
                self.logger.info("Cancelled. Returning to main menu.", extra=logging_extra)
                return None
            else:
                self.logger.info("Invalid port selection. Please try again.", extra=logging_extra)

    def _handle_prolific_port_search(self, ports):
        """Return list of Prolific ports (if any) for later connection attempt."""
        logging_extra = {'process_name': 'Port Selection'}

        # Filter for Prolific ports (common for USB serial adapters)
        prolific_ports = [p.device for p in ports if "prolific" in p.description.lower()]


        if prolific_ports:
            self.logger.info(f"Found Prolific USB serial adapter port(s): {prolific_ports}", extra=logging_extra)
            return prolific_ports

        self.logger.info("No Prolific USB serial adapter ports found.", extra=logging_extra)
        return None

    def _handle_all_ports_selection(self, ports):
        """Return list of all available port devices for later connection attempt."""
        logging_extra = {'process_name': 'Port Selection'}

        if not ports:
            self.logger.info("\nNo ports available.", extra=logging_extra)
            return None

        port_devices = [p.device for p in ports]
        self.logger.info(f"Each available port will be attempted: {port_devices}", extra=logging_extra)
        return port_devices

    def _select_ports(self):
        logging_extra = {'process_name': 'Port Selection'}

        selection_options = "Port selection options:\n"
        selection_options += "  1. Select a specific port to attempt\n"
        selection_options += "  2. Attempt all available ports\n"
        selection_options += "  3. Search for Prolific USB serial adapter ports\n"
        selection_options += "  4. Abort connection process"

        while True:
            ports = [p for p in serial.tools.list_ports.comports()]

            # select option for selecting port
            self.logger.info(selection_options, extra=logging_extra)

            while True:
                choice = input("\nEnter your choice (1, 2, 3, or 4): ").strip()
                print()  # Add spacing after selection input for readability

                # Validate input
                if choice not in ["1", "2", "3", "4"]:
                    self.logger.info("Invalid choice. Please enter 1, 2, 3, or 4.", extra=logging_extra)
                    continue

                # Valid choice - process accordingly
                if choice == "1":
                    self.logger.info("Selected option to manually select a port.", extra=logging_extra)
                    selected_port = self._handle_manual_port_selection(ports)
                    selected_ports = [selected_port] if selected_port else None
                elif choice == "2":
                    self.logger.info("Selected option to attempt all available ports.", extra=logging_extra)
                    selected_ports = self._handle_all_ports_selection(ports)
                elif choice == "3":
                    self.logger.info("Selected option to search for Prolific USB serial adapter ports.", extra=logging_extra)
                    selected_ports = self._handle_prolific_port_search(ports)
                elif choice == "4":
                    self.logger.info("Connection process aborted by user.", extra=logging_extra)
                    return False

                if selected_ports:
                    return selected_ports
                else:
                    # No valid selection; re-display options
                    break


    def _attempt_connection(self, ports, bauds):
        """Helper method to attempt connection on a list of ports with specified baud rates."""

        for port in ports:
            for baud in bauds:
                self.logger.info(f"Attempting connection to {port} at {baud} baud.", extra={'process_name': 'Connection Attempt'})

                try:
                    ser = serial.Serial(port, baudrate=baud, timeout=0.2, write_timeout=0.2)
                    ser.reset_input_buffer()
                    ser.reset_output_buffer()

                    ser.write(b"SY\r\n")
                    ser.flush()

                    response = ser.readline().decode(errors="ignore").strip()

                    if response:
                        self.logger.info(f"Successfully connected to {port} at {baud} baud.", extra={'process_name': 'Connection Attempt'})
                        return {'connection': ser, 'port': port, 'baudrate': baud}

                    ser.close()
                    self.logger.info("No response when attempting connection.", extra={'process_name': 'Connection Attempt'})

                except Exception as e:
                    self.logger.error(f" Error: {e}", extra={'process_name': 'Connection Attempt'})

        return None

    def connect(self):
        """
        Attempt to connect to Oregon RFID sensor with circular retry options.

        Returns
        -------
        dict or None
            Dictionary with 'connection', 'port', and 'baudrate' keys if successful, None otherwise.
        """

        self.logger.info("Initializing connection attempt", extra={'process_name': 'Connection'})

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

            # Connection failed, ask if user wants to retry
            self.logger.info("Connection failed on all attempted port/baud combinations.", extra={'process_name': 'Connection'})

            while True:
                retry = input("\nWould you like to retry? (y/n): ").strip().lower()
                if retry in ['y', 'yes', 'n', 'no']:
                    break

            if retry not in ['y', 'yes']:
                self.logger.info("User has chosen not to retry connection. Exiting connection process.", extra={'process_name': 'Connection'})
                return None
            else:
                self.logger.info("User has chosen to retry connection.", extra={'process_name': 'Connection'})

