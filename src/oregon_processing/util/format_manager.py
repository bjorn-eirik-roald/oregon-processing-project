# -*- coding: utf-8 -*-
"""
Format Manager for Oregon RFID device record format operations
"""


class FormatManager:
    """Manages device record format configuration and state."""

    def __init__(self, communicator):
        """
        Initialize FormatManager.

        Parameters
        ----------
        communicator : OregonCommunicator
            OregonCommunicator instance for device communication.
        """
        self._communicator = communicator
        self._event_record_format = None
        self._startup_format = None

        # Store startup format when initialized
        if self._communicator.is_connected:
            self._startup_format = self._fetch_event_record_format()

    def _fetch_event_record_format(self) -> dict:
        """
        Fetch and parse the event record format from the device using the FM command.

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

        response_lines = self._communicator.send_command("FM")

        if len(response_lines) != 1:
            raise ValueError(f"Unexpected number of lines in FM response: {len(response_lines)}")

        columns_raw = response_lines[0].strip()
        tokens = columns_raw.split()
        columns = [t for t in tokens if t != 'SPC']

        if "TAG" not in columns:
            raise ValueError("TAG column not found in event record format.")

        # Create a dictionary mapping column names to their indices
        column_indices = {col: idx for idx, col in enumerate(columns)}

        return {
            'columns_raw': columns_raw,
            'columns': columns,
            'column_indices': column_indices,
        }

    def set_event_record_format(self, format_string: str) -> bool:
        """
        Set the event record format on the device using the FM command.

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
            self._communicator.send_command(fm_command)

            # Verify the format was set and update cache
            self._event_record_format = self._fetch_event_record_format()

            if self._event_record_format['columns_raw'] == format_string:
                return True
            else:
                print(f"WARNING: Format mismatch. Expected '{format_string}', got '{self._event_record_format['columns_raw']}'")
                return False

        except Exception as e:
            print(f"Error setting event record format: {e}")
            return False

    def restore_startup_format(self) -> bool:
        """
        Restore the device to its startup event record format.

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

        current_format = self._fetch_event_record_format()

        # Compare formats - if they're the same, no need to restore
        if current_format['columns_raw'] == self._startup_format['columns_raw']:
            return True

        # Format has changed - restore to startup format using set_event_record_format
        return self.set_event_record_format(self._startup_format['columns_raw'])

    def get_format_info(self) -> dict:
        """
        Get the current event record format information.

        Returns
        -------
        dict
            Format information with 'columns_raw', 'columns', and 'column_indices'
        """
        return self._fetch_event_record_format()
