# -*- coding: utf-8 -*-
"""
Firmware Updater for Oregon RFID Device

Handles the firmware update process for Oregon RFID readers.
"""

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

        if not self._communicator.is_connected:
            print("Not connected to device.")
            return False

        # Verify firmware file exists before starting
        try:
            with open(firmware_file_path, 'r') as f:
                firmware_content = f.read()
        except FileNotFoundError:
            print(f"\nError: Firmware file not found: {firmware_file_path}")
            return False
        except Exception as e:
            print(f"\nError reading firmware file: {e}")
            return False

        print("\n" + "="*60)
        print("FIRMWARE UPDATE PROCESS")
        print("="*60)

        try:
            # Final confirmation with version info
            print("\n" + "-"*60)
            print(f"Current firmware version: {new_version}")
            print(f"New firmware version:     {new_version}")
            print("-"*60)
            confirm = input("\nConfirm firmware update (yes/no): ").strip().lower()
            if confirm not in ['yes', 'y']:
                print("Firmware update cancelled by user.")
                return False

            print("\n" + "="*60)
            print("Starting firmware update process...")
            print("="*60)

            # Step 1: Read firmware file content
            print(f"\nStep 1: Reading firmware file: {firmware_file_path}...", end="", flush=True)
            with open(firmware_file_path, 'r') as f:
                firmware_content = f.read()
            print("Done.")

            # Step 2: Turn off reader
            print("\nStep 2: Turning off reader...", end="", flush=True)
            self._command_manager.send_command("OF")
            time.sleep(2)
            print("Done.")

            # Step 3: Send FW command
            print("Step 3: Initiating firmware update mode...", end="", flush=True)
            self._command_manager.send_command("FW")
            print("Done.")

            # Step 4: Wait for "Update(Y)?" prompt and send Y
            print("Step 4: Waiting for 'Update(Y)?' prompt...", end="", flush=True)
            prompt_found = False
            timeout = time.time() + 10  # 10 second timeout

            while time.time() < timeout:
                if self._connection.in_waiting:
                    line = self._connection.readline().decode(errors="ignore").strip()
                    if "update" in line.lower() and "(y)" in line.lower():
                        prompt_found = True
                        print("Received!")
                        break
                time.sleep(0.2)

            if not prompt_found:
                print("TIMEOUT!")
                print("Did not receive 'Update(Y)?' prompt. Update aborted.")
                return False

            print("Step 5: Starting update execution...", end="", flush=True)
            self._command_manager.send_command("Y")
            print("Started.")

            # Step 6: Wait for "Start" prompt
            print("Step 6: Waiting for 'Start' prompt...", end="", flush=True)
            start_found = False
            timeout = time.time() + 30  # 30 second timeout

            while time.time() < timeout:
                if self._communicator._connection.in_waiting:
                    line = self._communicator._connection.readline().decode(errors="ignore").strip()
                    if "start" in line.lower():
                        start_found = True
                        print("Received!")
                        break
                time.sleep(0.5)

            if not start_found:
                print("TIMEOUT!")
                print("Did not receive 'Start' prompt. Update may have failed.")
                return False

            # Step 7: Send firmware content
            print("Step 7: Uploading firmware data...", end="", flush=True)
            self._command_manager.send_command(firmware_content)
            print("Done.")

            # Step 8: Capture response from device
            print("Step 8: Waiting for device response...", end="", flush=True)
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

            print("Done.")

            # Display response
            if response_lines:
                print("\nDevice Response:")
                print("-"*60)
                for line in response_lines:
                    print(line)
                print("-"*60)
            else:
                print("\nNo response received from device.")

            # Make user verify update success
            print("\nPlease verify the firmware update was successful.")
            verify = None
            while verify not in ['yes', 'y', 'no', 'n']:
                verify = input("Did the update complete successfully? (yes/no): ").strip().lower()

            if verify in ['no', 'n']:
                print("Firmware update reported as unsuccessful by user.")
                return False
            else:
                print("Firmware update reported as successful by user.")

            print("\n" + "="*60)
            print("FIRMWARE UPDATE COMPLETED")
            print("="*60)

            return True

        except Exception as e:
            print(f"\nError during firmware update: {e}")
            return False
