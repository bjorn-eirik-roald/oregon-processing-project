# -*- coding: utf-8 -*-
"""
Format Manager for Oregon RFID device record format operations
"""


class FormatManager:
    """Manages device detection record format configuration and state."""

    def __init__(self, communicator, command_manager):
        """
        Initialize FormatManager.

        Parameters
        ----------
        communicator : OregonCommunicator
            OregonCommunicator instance for device communication.
        command_manager : CommandManager
            CommandManager instance for sending commands to device.
        """
        self._communicator = communicator
        self._command_manager = command_manager
        self._detection_record_format = None
        self._startup_format = None

        # Store startup format when initialized
        if self._communicator.is_connected:
            self._startup_format = self._fetch_detection_record_format()

    def _fetch_detection_record_format(self) -> dict:
        """
        Fetch and parse the detection record format from the device using the FM command.

        Returns
        -------
        dict
            {
              'columns_raw': raw string from FM command response,
              'columns': list of data columns excluding 'SPC',
              'column_indices': dict mapping column names to their indices
            }
        """
        if not self._communicator.is_connected:
            raise ConnectionError("Not connected to device.")

        response_lines = self._command_manager.send_command("FM")

        if len(response_lines) != 1:
            raise ValueError(f"Unexpected number of lines in FM response: {len(response_lines)}")

        columns_raw = response_lines[0].strip()
        tokens = columns_raw.split()
        columns = [t for t in tokens if t != 'SPC']

        if "TAG" not in columns:
            raise ValueError("TAG column not found in detection record format.")

        # Create a dictionary mapping column names to their indices
        column_indices = {col: idx for idx, col in enumerate(columns)}

        return {
            'columns_raw': columns_raw,
            'columns': columns,
            'column_indices': column_indices,
        }

    def set_detection_record_format(self, format_string: str) -> bool:
        """
        Set the detection record format on the device using the FM command.

        Parameters
        ----------
        format_string : str
            The format string to set (e.g., "DTY ARR SPC TRF DUR SPC TTY SPC TAG SCD NCD EFA")

        Returns
        -------
        bool
            True if format was set successfully, False otherwise.
        """
        if not self._communicator.is_connected:
            print("Not connected to device.")
            return False

        try:
            fm_command = f"FM {format_string}"
            self._command_manager.send_command(fm_command)

            # Verify the format was set and update cache
            self._detection_record_format = self._fetch_detection_record_format()

            if self._detection_record_format['columns_raw'] == format_string:
                return True
            else:
                print(f"WARNING: Format mismatch. Expected '{format_string}', got '{self._detection_record_format['columns_raw']}'")
                return False

        except Exception as e:
            print(f"Error setting detection record format: {e}")
            return False

    def restore_startup_format(self) -> bool:
        """
        Restore the device to its startup detection record format.

        Returns
        -------
        bool
            True if format was restored or no change was needed, False if restoration failed.
        """
        if not self._communicator.is_connected:
            return False

        if self._startup_format is None:
            # No startup format stored, nothing to restore
            return True

        current_format = self._fetch_detection_record_format()

        # Compare formats - if they're the same, no need to restore
        if current_format['columns_raw'] == self._startup_format['columns_raw']:
            return True

        print("\n" + "-" * 70)
        print("Restoring original detection record format...", end="", flush=True)
        if not self.restore_startup_format():
            print("WARNING: Failed to restore original detection record format.")
        print("Done.")
        print("-" * 70)

        # Format has changed - restore to startup format using set_detection_record_format
        return self.set_detection_record_format(self._startup_format['columns_raw'])

    def get_format_info(self) -> dict:
        """
        Get the current detection record format information.

        Returns
        -------
        dict
            Format information with 'columns_raw', 'columns', and 'column_indices'
        """
        return self._fetch_detection_record_format()
