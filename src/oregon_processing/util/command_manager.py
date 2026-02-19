# -*- coding: utf-8 -*-
"""
Oregon RFID Command Manager

Handles sending commands to the Oregon device, receiving responses,
and validating prompt signatures.
"""

import logging
import time


class CommandManager:
    """Manages command sending, receiving, and response validation for Oregon RFID devices."""

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

    def __init__(self, communicator):
        """
        Initialize the CommandManager.

        Parameters
        ----------
        communicator : Communicator
            Communicator instance for device communication.
        """
        self._logger = logging.getLogger('oregon_processing.command_manager')
        self._communicator = communicator
        self._last_prompt_signature = None

    def __enter__(self):
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        pass

    @property
    def prompt_signature(self):
        """Get the last received prompt signature."""
        self.send_command("SY")  # Update last prompt signature
        return self._last_prompt_signature

    def validate_command(self, command: str) -> bool:
        """
        Validate command by extracting the main code and checking against VALID_MAIN_COMMANDS.

        Splits the command at the first space and validates the first part (main code).
        Supports:
        - Fixed codes: SY, ON, ER, etc.
        - Codes with wildcards: UP* (where * matches any character or digit)
        - Pattern codes: UP# (where # can be any digit)

        Parameters
        ----------
        command : str
            Command string to validate (e.g., "SY", "DT 2025-01-19 09:18:02", "UP1").

        Returns
        -------
        bool
            True if the command is valid, False otherwise.
        """
        if not command or not command.strip():
            self._logger.warning("Empty command is not valid.", extra={'process_name': 'Command Validation'})
            return False

        # Split at space to get the main command code
        parts = command.strip().split(None, 1)  # Split on whitespace, max 1 split
        main_command = parts[0].upper()

        # Direct match in VALID_MAIN_COMMANDS
        if main_command in self.VALID_MAIN_COMMANDS:
            return True

        # Check for pattern matches (e.g., UP# where # is a digit)
        if main_command[:2] == "UP":
            suffix = main_command[2:]
            if suffix and all(c.isdigit() for c in suffix):
                return True

        self._logger.warning(f"Command '{command}' is not valid.", extra={'process_name': 'Command Validation'})
        return False

    def _is_ready_prompt(self, line: str) -> bool:
        """
        Check if a line is a ready prompt (unit is ready to receive a new command).

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
            'E' : Elapsed time (no absolute timestamp)

        Character 4 = Beeper state:
            'B' : Beeper enabled
            '*' : Beeper disabled

        Validation rules:
            - Signature must be exactly 4 characters long
            - Each character must be valid for its position
            - The line must contain ONLY the signature (and optional '>') with nothing after
            - This indicates the unit is ready to receive a new command

        Example:
            "HRGB>" → valid (unit ready)
            "HRGB" → valid (unit ready)
            "HSU*> RFM009 ORMR ready" → invalid (has data after prompt)
            "HRGX>" → invalid (unknown beeper state)
            "HRG>" → invalid (wrong length)

        Parameters
        ----------
        line : str
            Full line from device (e.g. "HRGB>", "HSU*> data here").

        Returns
        -------
        bool
            True if line contains a valid signature with nothing following it (unit is ready),
            False otherwise.
        """

        logger_extra = {'process_name': 'Prompt Validation'}

        if not isinstance(line, str) or len(line) < 4:
            return False

        signature = line[:4]

        if not isinstance(signature, str):
            error_msg = f"Expected signature to be a string, got {type(signature)} instead."
            self._logger.error(error_msg, extra=logger_extra)
            raise TypeError(error_msg)

        if len(signature) != 4:
            return False

        valid_sets = (
            {'0', 'H', 'N'},  # operating mode
            {'R', 'S', 'Z'},  # run state
            {'G', 'N', 'U', 'E'}, # time sync state
            {'B', '*'}       # beeper
        )

        valid_signature = all(c in valid for c, valid in zip(signature, valid_sets))

        if not valid_signature:
            return False

        # Check if there's anything after the signature except optional '>' and whitespace
        remainder = line[4:].lstrip('>').strip()

        if not remainder:
            # Signature is valid and nothing follows - unit is ready
            self._last_prompt_signature = signature
            return True

        # Signature is valid but data follows - unit is not ready
        return False

    def _transmit_command(self, command: str):
        """
        Send a command to the device.

        Parameters
        ----------
        command : str
            Command string to send (e.g., "SY").

        Raises
        ------
        ConnectionError
            If not connected to device.
        """

        if not self._communicator.is_connected:
            raise ConnectionError("Not connected to device.")

        # Clear buffer by actually reading and discarding stray bytes
        self._communicator._connection.reset_input_buffer()
        time.sleep(0.05)  # Brief pause to let buffer clear

        # Drain any remaining bytes that reset_input_buffer() missed
        self._communicator._connection.timeout = 0.1
        while self._communicator._connection.in_waiting > 0:
            self._communicator._connection.read(self._communicator._connection.in_waiting)
            time.sleep(0.01)

        # Send the command
        self._communicator._connection.write((command + "\r\n").encode())
        self._communicator._connection.flush()

    def send_command(self, command: str, timeout: float = 5) -> list:
        """
        Send a command and read lines until a prompt signature indicates completion.

        The device sometimes emits stray prompt signatures (or prefixes the prompt on
        the same line as data). We now:
        - Strip prompt signatures from the front of any line and keep the remainder.
        - Ignore signature-only lines until we've received at least one data line.
        - Stop reading once a standalone prompt arrives after data, or when the idle
          timeout elapses.

        Returns the cleaned response (list of lines) with echoed command and prompts
        removed.

        Parameters
        ----------
        command : str
            Command to send to the device.
        timeout : float
            Idle timeout in seconds. The timeout resets each time data arrives.
            Default: 5 seconds.

        Returns
        -------
        list
            Cleaned response lines (echoed command and prompt removed).

        Raises
        ------
        ConnectionError
            If not connected to device.
        """
        if not self._communicator.is_connected:
            raise ConnectionError("Not connected to device.")

        # Send command
        self._transmit_command(command)

        lines = []
        last_data_time = time.time()

        while True:
            line = self._communicator._connection.readline().decode(errors="ignore").strip()

            if line:
                raw_line = line
                prompt_ready = self._is_ready_prompt(line)

                if prompt_ready:
                    # Signature is valid and nothing follows - unit is ready, we can stop
                    break

                # Check if line starts with valid signature
                if len(line) >= 4 and self._is_ready_prompt(line):
                    # This shouldn't happen (would be caught above), but handle it gracefully
                    pass
                elif len(line) >= 4:
                    # Try to extract data after a potential prompt
                    potential_sig = line[:4]
                    try:
                        if all(c in valid for c, valid in zip(potential_sig, (
                            {'0', 'H', 'N'}, {'R', 'S', 'Z'}, {'G', 'N', 'U', 'E'}, {'B', '*'}
                        ))):
                            # Valid signature with data after it
                            data = line[4:].lstrip('>').strip()
                            if data:
                                lines.append(data)
                                last_data_time = time.time()
                                continue
                    except:
                        pass

                # Line doesn't start with valid signature, treat as data
                if line:
                    lines.append(line)
                    last_data_time = time.time()

            # Idle timeout: only break if no new data arrives within timeout
            if time.time() - last_data_time > timeout:
                break

        # Remove echoed command and empty lines
        cleaned = [l for l in lines if l and l != command]
        return cleaned


