from oregon_processing.oregon_communicator import OregonCommunicator


with OregonCommunicator() as communicator:

    communicator.connect()
    result = communicator.control_device_datetime(tolerance_seconds=10)