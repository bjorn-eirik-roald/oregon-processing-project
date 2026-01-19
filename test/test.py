from oregon_processing.oregon_communicator import OregonCommunicator


if __name__ == "__main__":
    with OregonCommunicator() as communicator:

        if not communicator.is_connected:
            print("Failed to connect to Oregon RFID device. Aborting.")
        else:
            communicator.control_device_datetime(tolerance_seconds=10)
            communicator.start_interactive_terminal()