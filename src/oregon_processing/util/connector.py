
from serial import Serial
from serial.tools import list_ports


from oregon_processing.util.logging_manager import get_logger


class ConnectionResult:
    """Class to encapsulate the result of a connection attempt."""

    def __init__(self, success, connection=None, port=None, baudrate=None, error_message=None):
        self.success: bool = success
        self.connection: Serial = connection
        self.port: str = port
        self.baudrate: int = baudrate
        self.error_message: str = error_message

class Connector:
    """Class to handle connection establishment with Oregon RFID devices."""

    BAUD_RATES = [115200, 57600, 9600]

    def __init__(self):
        self._logger = get_logger(__name__)

    def connect(self) -> ConnectionResult:
        """
        Attempt to connect to Oregon RFID sensor with circular retry options.

        Returns
        -------
        ConnectionResult
            ConnectionResult object with success status, connection, port, and baudrate if successful, error_message otherwise.
        """



        self._logger.info("Initializing connection attempt")

        first_attempt = True

        while True:

            if not first_attempt:
                # Ask user to select baud rate
                bauds = self._select_baud_rate()
                if not bauds:
                    return ConnectionResult(success=False, error_message="User cancelled baud rate selection.")

                # Ask user to select port(s)
                selected_ports = self._select_ports()

                if not selected_ports:
                    return ConnectionResult(success=False, error_message="User cancelled port selection.")
            else:
                # First attampt: Try defauilt baud rate and look for Prolific ports
                self._logger.debug("First connection attempt: trying default baud rate and searching for Prolific ports.")
                bauds = [self.BAUD_RATES[0]]  # Start with default baud rate
                selected_ports = self._handle_prolific_port_search(self._get_all_ports())

                first_attempt = False

            result = self._attempt_connection(selected_ports, bauds)

            if result:
                return result

            # Connection failed, ask if user wants to retry
            self._logger.info("Connection failed on all attempted port/baud combinations.")

            while True:
                retry = input("\nWould you like to retry? (y/n): ").strip().lower()
                if retry in ['y', 'yes', 'n', 'no']:
                    break

            if retry not in ['y', 'yes']:
                self._logger.debug("User has chosen not to retry connection. Exiting connection process.")
                return ConnectionResult(success=False, error_message="User chose not to retry connection.")
            else:
                self._logger.debug("User has chosen to retry connection.")

    def _select_baud_rate(self):
        """Allow user to select baud rate(s) to use for connection."""

        self._logger.debug("Prompting user to select baud rate(s) for connection attempt.")

        selection_options = "Available baud rates:\n"
        for i, baud in enumerate(self.BAUD_RATES, 1):
            selection_options += f"  {i}. {baud}\n"
        selection_options += f"  {len(self.BAUD_RATES) + 1}. Try all baud rates\n"
        selection_options += f"  {len(self.BAUD_RATES) + 2}. Abort connection process"

        self._logger.info(selection_options)

        while True:
            choice = input("\nSelect a baud rate option (enter option number): ").strip()
            print()  # Add spacing after selection input for readability
            try:
                index = int(choice) - 1
            except ValueError:
                self._logger.info("Invalid selection! Enter a number from the list.")
                continue



            # Return selected baud rate(s)
            if 0 <= index < len(self.BAUD_RATES):
                self._logger.debug(f"User selected baud rate: {self.BAUD_RATES[index]}")
                return [self.BAUD_RATES[index]]
            # User chose to try all baud rates
            elif index == len(self.BAUD_RATES):
                self._logger.debug("User selected option to try all baud rates.")
                return self.BAUD_RATES
            # User cancelled
            elif index == len(self.BAUD_RATES) + 1:
                self._logger.debug("User cancelled baud rate selection.")
                return None
            # Invalid selection
            else:
                print("Invalid selection! Enter a number from the list.")

    def _handle_manual_port_selection(self, ports):
        """Handle user selecting a specific port. Returns selected port device or None."""


        self._logger.debug("Prompting user to manually select a port from the list of available ports.")

        if not ports:
            self._logger.info("No ports available. Returning to previous menu.")
            return None

        selection_options = "Available ports:\n"
        for i, port in enumerate(ports, 1):
            selection_options += f"  {i}. {port.device} - {port.description}\n"
        selection_options += f"  {len(ports) + 1}. Cancel and return to previous menu\n"

        self._logger.info(selection_options)

        # Loop until valid port is selected
        while True:
            port_choice = input("\nSelect a port (enter number): ").strip()

            try:
                port_index = int(port_choice) - 1
            except ValueError:
                print("Invalid input. Please enter a number from the list.")
                continue

            if 0 <= port_index < len(ports):
                self._logger.debug(f"User selected port: {ports[port_index].device} - {ports[port_index].description}")
                return ports[port_index].device
            elif port_index == len(ports):
                self._logger.debug("User cancelled manual port selection. Returning to previous menu.")
                return None
            else:
                print("Invalid selection. Please enter a number from the list.")

    def _handle_prolific_port_search(self, ports):
        """Return list of Prolific ports (if any) for later connection attempt."""

        self._logger.debug("Searching for Prolific USB serial adapter ports among available ports.")

        # Filter for Prolific ports (common for USB serial adapters)
        prolific_ports = [p.device for p in ports if "prolific" in p.description.lower()]


        if prolific_ports:
            self._logger.info(f"Found Prolific USB serial adapter port(s): {prolific_ports}")
            return prolific_ports

        self._logger.info("No Prolific USB serial adapter ports found. Returning to previous menu.")
        return None

    def _handle_all_ports_selection(self, ports):
        """Return list of all available port devices for later connection attempt."""

        self._logger.debug("Creating list of all available ports for connection attempt.")

        if not ports:
            self._logger.info("No ports available. Returning to previous menu.")
            return None

        port_devices = [p.device for p in ports]
        self._logger.info(f"Each available port will be attempted: {port_devices}")
        return port_devices

    def _select_ports(self):

        self._logger.debug("Prompting user to select port(s) for connection attempt.")

        selection_options = "Port selection options:\n"
        selection_options += "  1. Select a specific port to attempt\n"
        selection_options += "  2. Attempt all available ports\n"
        selection_options += "  3. Search for Prolific USB serial adapter ports\n"
        selection_options += "  4. Abort connection process"

        while True:
            ports = self._get_all_ports()

            # select option for selecting port
            self._logger.info(selection_options)

            while True:
                choice = input("\nEnter your choice (1, 2, 3, or 4): ").strip()
                print()  # Add spacing after selection input for readability

                # Validate input
                if choice not in ["1", "2", "3", "4"]:
                    print("Invalid choice. Please enter 1, 2, 3, or 4.")
                    continue

                # Valid choice - process accordingly
                if choice == "1":
                    self._logger.debug("User selected option to manually select a port.")
                    selected_port = self._handle_manual_port_selection(ports)
                    selected_ports = [selected_port] if selected_port else None
                elif choice == "2":
                    self._logger.debug("User selected option to attempt all available ports.")
                    selected_ports = self._handle_all_ports_selection(ports)
                elif choice == "3":
                    self._logger.debug("User selected option to search for Prolific USB serial adapter ports.")
                    selected_ports = self._handle_prolific_port_search(ports)
                elif choice == "4":
                    self._logger.debug("User aborted the connection process.")
                    return False

                if selected_ports:
                    return selected_ports
                else:
                    # No valid selection; re-display options
                    break


    def _attempt_connection(self, ports, bauds) -> ConnectionResult:
        """Helper method to attempt connection on a list of ports with specified baud rates."""



        for port in ports:
            for baud in bauds:
                self._logger.info(f"Attempting connection to {port} at {baud} baud.")

                ser = None
                try:
                    ser: Serial = Serial(port, baudrate=baud, timeout=0.2, write_timeout=0.2)
                    ser.reset_input_buffer()
                    ser.reset_output_buffer()

                    ser.write(b"SY\r\n")
                    ser.flush()

                    response = ser.readline().decode(errors="ignore").strip()

                    if response:
                        self._logger.info(f"Successfully connected to {port} at {baud} baud.")
                        result = ConnectionResult(success=True, connection=ser, port=port, baudrate=baud)
                        return result
                    else:
                        ser.close()
                        self._logger.info("No response when attempting connection.")
                except Exception as e:

                    if ser and ser.is_open:
                        ser.close()

                    error_message = f"Error when connecting to {port} at {baud} baud: {e}"
                    self._logger.error(error_message)

        return ConnectionResult(success=False, error_message="Failed to connect on all attempted ports and baud rates.")

    def _get_all_ports(self):
        """
        Helper method to get list of all available ports.
        Returns
        -------
        list
            List of available port objects.
        """
        return [p for p in list_ports.comports()]
