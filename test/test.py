from oregon_processing.oregon_communicator import OregonCommunicator


with OregonCommunicator() as communicator:

    communicator.connect()
    communicator.control_device_datetime(tolerance_seconds=10)
    communicator.start_interactive_terminal()