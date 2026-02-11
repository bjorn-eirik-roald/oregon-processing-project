# -*- coding: utf-8 -*-
"""
Firmware Updater for Oregon RFID Device

Handles the firmware update process for Oregon RFID readers.
"""

import logging
import time


class FirmwareUpdater:
    """Handles firmware update process for Oregon RFID devices."""

    def __init__(self, communicator, command_manager):
        """
        Initialize the FirmwareUpdater.

        Parameters
        ----------
        communicator : OregonCommunicator
            OregonCommunicator instance for device communication.
        command_manager : CommandManager
            CommandManager instance for sending commands to device.
        """
        self._communicator = communicator
        self._command_manager = command_manager
        self._logger = logging.getLogger('oregon_processing.firmware_updater')

    def __enter__(self):
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Exit context manager."""
        pass

    def update(self, firmware_file_path: str, new_version: str) -> bool:
        """
        Update the firmware on the Oregon RFID reader.

        Process:
        1. Get current firmware version
        2. Confirm with user
        3. Turn off reader with OF command
        4. Run FW command
        5. Wait for prompt and confirm with Y
        6. Wait for "Start" prompt
        7. Send firmware file content

        Parameters
        ----------
        firmware_file_path : str
            Path to the firmware update file
        new_version : str
            Version string of the new firmware (e.g., "V2.2A")

        Returns
        -------
        bool
            True if update completed successfully, False otherwise.
        """

        logging_extra = {'process_name': 'Firmware Update'}

        if not self._communicator.is_connected:
            self._logger.error("Not connected to device.", extra=logging_extra)
            return False

        # Verify firmware file exists before starting
        try:
            with open(firmware_file_path, 'r') as f:
                firmware_content = f.read()
        except FileNotFoundError:
            self._logger.error(f"\nError: Firmware file not found: {firmware_file_path}", extra=logging_extra)
            return False
        except Exception as e:
            self._logger.error(f"\nError reading firmware file: {e}", extra=logging_extra)
            return False

        self._logger.info("\n" + "-"*60, extra=logging_extra)
        self._logger.info("FIRMWARE UPDATE PROCESS", extra=logging_extra)
        self._logger.info("-"*60, extra=logging_extra)

        try:
            # Final confirmation with version info
            self._logger.info("\n" + "-"*60, extra=logging_extra)
            self._logger.info(f"Current firmware version: {new_version}", extra=logging_extra)
            self._logger.info(f"New firmware version:     {new_version}", extra=logging_extra)
            self._logger.info("-"*60, extra=logging_extra)
            confirm = input("\nConfirm firmware update (yes/no): ").strip().lower()
            if confirm not in ['yes', 'y']:
                self._logger.info("Firmware update cancelled by user.", extra=logging_extra)
                return False

            self._logger.info("\n" + "-"*60, extra=logging_extra)
            self._logger.info("Starting firmware update process...", extra=logging_extra)
            self._logger.info("-"*60, extra=logging_extra)

            # Step 1: Read firmware file content
            self._logger.info(f"\nStep 1: Reading firmware file: {firmware_file_path}...", extra=logging_extra)
            with open(firmware_file_path, 'r') as f:
                firmware_content = f.read()
            self._logger.info("Done.", extra=logging_extra)

            # Step 2: Turn off reader
            self._logger.info("\nStep 2: Turning off reader...", extra=logging_extra)
            self._command_manager.send_command("OF")
            time.sleep(2)
            self._logger.info("Done.", extra=logging_extra)

            # Step 3: Send FW command
            self._logger.info("Step 3: Initiating firmware update mode...", extra=logging_extra)
            self._command_manager.send_command("FW")
            self._logger.info("Done.", extra=logging_extra)

            # Step 4: Wait for "Update(Y)?" prompt and send Y
            self._logger.info("Step 4: Waiting for 'Update(Y)?' prompt...", extra=logging_extra)
            prompt_found = False
            timeout = time.time() + 10  # 10 second timeout

            while time.time() < timeout:
                if self._connection.in_waiting:
                    line = self._connection.readline().decode(errors="ignore").strip()
                    if "update" in line.lower() and "(y)" in line.lower():
                        prompt_found = True
                        self._logger.info("Received!", extra=logging_extra)
                        break
                time.sleep(0.2)

            if not prompt_found:
                self._logger.error("TIMEOUT!", extra=logging_extra)
                self._logger.error("Did not receive 'Update(Y)?' prompt. Update aborted.", extra=logging_extra)
                return False

            self._logger.info("Step 5: Starting update execution...", extra=logging_extra)
            self._command_manager.send_command("Y")
            self._logger.info("Started.", extra=logging_extra)

            # Step 6: Wait for "Start" prompt
            self._logger.info("Step 6: Waiting for 'Start' prompt...", extra=logging_extra)
            start_found = False
            timeout = time.time() + 30  # 30 second timeout

            while time.time() < timeout:
                if self._communicator._connection.in_waiting:
                    line = self._communicator._connection.readline().decode(errors="ignore").strip()
                    if "start" in line.lower():
                        start_found = True
                        self._logger.info("Received!", extra=logging_extra)
                        break
                time.sleep(0.5)

            if not start_found:
                self._logger.error("TIMEOUT!", extra=logging_extra)
                self._logger.error("Did not receive 'Start' prompt. Update may have failed.", extra=logging_extra)
                return False

            # Step 7: Send firmware content
            self._logger.info("Step 7: Uploading firmware data...", extra=logging_extra)
            self._command_manager.send_command(firmware_content)
            self._logger.info("Done.", extra=logging_extra)

            # Step 8: Capture response from device
            self._logger.info("Step 8: Waiting for device response...", extra=logging_extra)
            response_lines = []
            response_timeout = time.time() + 60  # 60 second timeout for firmware processing
            last_data_time = time.time()

            while time.time() < response_timeout:
                if self._communicator._connection.in_waiting:
                    line = self._communicator._connection.readline().decode(errors="ignore").strip()
                    if line:
                        response_lines.append(line)
                        last_data_time = time.time()

                # If no data for 3 seconds, assume response is complete
                if time.time() - last_data_time > 3:
                    break

                time.sleep(0.2)

            self._logger.info("Done.", extra=logging_extra)

            # Display response
            if response_lines:
                self._logger.info("\nDevice Response:", extra=logging_extra)
                self._logger.info("-"*60, extra=logging_extra)
                for line in response_lines:
                    self._logger.info(line, extra=logging_extra)
                self._logger.info("-"*60, extra=logging_extra)
            else:
                self._logger.info("\nNo response received from device.", extra=logging_extra)

            # Make user verify update success
            self._logger.info("\nPlease verify the firmware update was successful.", extra=logging_extra)
            verify = None
            while verify not in ['yes', 'y', 'no', 'n']:
                verify = input("Did the update complete successfully? (yes/no): ").strip().lower()

            if verify in ['no', 'n']:
                self._logger.info("Firmware update reported as unsuccessful by user.", extra=logging_extra)
                return False
            else:
                self._logger.info("Firmware update reported as successful by user.", extra=logging_extra)

            self._logger.info("\n" + "-"*60, extra=logging_extra)
            self._logger.info("FIRMWARE UPDATE COMPLETED", extra=logging_extra)
            self._logger.info("-"*60, extra=logging_extra)

            return True

        except Exception as e:
            self._logger.error(f"\nError during firmware update: {e}", extra=logging_extra)
            return False
