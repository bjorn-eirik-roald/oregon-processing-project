# -*- coding: utf-8 -*-
"""
Format Manager for Oregon RFID device record format operations
"""

import logging
from statistics import mode


class FormatManager:
    """Manages device detection record format configuration and state."""

    FIELD_NAMES = {
        'DTY': 'Detection type',
        'TCH': 'Tag technology',
        'TTY': 'Tag type',
        'PFG': 'Phantom flag',
        'TAG': 'Tag ID number',
        'ANT': 'Antenna number',
        'ARR': 'Arrival date and time',
        'TRF': 'Time reference',
        'DEP': 'Departure date and time',
        'NCD': 'Number of consecutive detections',
        'EMP': 'Number of empty scans preceding detection',
        'LAT': 'Latitude',
        'LON': 'Longitude',
        'ALT': 'Altitude in meters',
        'SIV': 'Satellites in view',
        'HDP': 'Location horizontal accuracy',
        'TSS': 'Tag signal strength',
        'SPV': 'Power supply voltage',
        'CPA': 'Power supply amperage during charge pulse',
        'LSA': 'Power supply amperage with charge pulse off',
        'EFA': 'Effective amps',
        'CPT': 'Charge pulse time in milliseconds',
        'LST': 'Listen time in milliseconds',
        'ANV': 'Antenna voltage',
        'ANA': 'Antenna amperage',
        'NOI': 'Noise',
        'DUR': 'Duration of tag detection event',
        'CLS': 'Tag size class',
        'SCD': 'Site code',
        'SPC': 'Output one space character',
        }

    def __init__(self, communicator, command_manager):
        """
        Initialize FormatManager.

        Parameters
        ----------
        communicator : Communicator
            Communicator instance for device communication.
        command_manager : CommandManager
            CommandManager instance for sending commands to device.
        """
        self._communicator = communicator
        self._command_manager = command_manager
        self._detection_record_format = None
        self._startup_format = None
        self._logger = logging.getLogger('oregon_processing.format_manager')

        # Store startup format when initialized
        if self._communicator.is_connected:
            self._startup_format = self._fetch_detection_record_format()

    def __enter__(self):
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager; restore startup format."""
        self._restore_startup_format()

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
        logging_extra = {'process_name': 'Format Manager'}

        if not self._communicator.is_connected:
            raise ConnectionError("Not connected to device.")

        old_mode = None

        if self._communicator.mode.lower() != 'standby':
            old_mode = self._communicator.mode
            self._communicator.change_mode('Standby')

        response_lines = self._command_manager.send_command("FM")

        if old_mode:
            self._communicator.change_mode(old_mode)

        if len(response_lines) != 1:
            raise ValueError(f"Unexpected number of lines in FM response: {len(response_lines)}")

        columns_raw = response_lines[0].strip()
        tokens = columns_raw.split()
        columns = [t for t in tokens if t != 'SPC']

        # Create a dictionary mapping column names to their indices
        column_indices = {col: idx for idx, col in enumerate(columns)}

        # Create a subset of FIELD_NAMES for only the columns in the format

        if any(col not in self.FIELD_NAMES for col in columns):
            unknown_cols = [col for col in columns if col not in self.FIELD_NAMES]
            self._logger.warning(f"WARNING: Unknown columns in detection record format: {unknown_cols}", extra=logging_extra)

        field_names = {col: self.FIELD_NAMES.get(col, "Unknown") for col in columns}

        return {
            'columns_raw': columns_raw,
            'columns': columns,
            'column_indices': column_indices,
            'field_names': field_names,
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
        logging_extra = {'process_name': 'Format Manager'}

        if not self._communicator.is_connected:
            self._logger.error("Not connected to device.", extra=logging_extra)
            return False

        try:
            fm_command = f"FM {format_string}"
            self._command_manager.send_command(fm_command)

            # Verify the format was set and update cache
            self._detection_record_format = self._fetch_detection_record_format()

            if self._detection_record_format['columns_raw'] == format_string:
                return True
            else:
                self._logger.warning(f"WARNING: Format mismatch. Expected '{format_string}', got '{self._detection_record_format['columns_raw']}'", extra=logging_extra)
                return False

        except Exception as e:
            self._logger.error(f"Error setting detection record format: {e}", extra=logging_extra)
            return False

    def _restore_startup_format(self) -> bool:
        """
        Restore the device to its startup detection record format.

        Returns
        -------
        bool
            True if format was restored or no change was needed, False if restoration failed.
        """
        logging_extra = {'process_name': 'Format Manager'}

        if not self._communicator.is_connected:
            return False

        if self._startup_format is None:
            # No startup format stored, nothing to restore
            return True

        current_format = self._fetch_detection_record_format()

        # Compare formats - if they're the same, no need to restore
        if current_format['columns_raw'] == self._startup_format['columns_raw']:
            return True


        success = self.set_detection_record_format(self._startup_format['columns_raw'])
        if not success:
            self._logger.warning("WARNING: Failed to restore original detection record format.", extra=logging_extra)
        else:
            self._logger.info("Original detection record format restored.", extra=logging_extra)


        # Format has changed - restore to startup format using set_detection_record_format
        return success

    def get_format_info(self) -> dict:
        """
        Get the current detection record format information.

        Returns
        -------
        dict
            Format information with 'columns_raw', 'columns', and 'column_indices'
        """
        return self._fetch_detection_record_format()


