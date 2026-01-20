from oregon_processing.oregon_communicator import OregonCommunicator
from datetime import date
from pathlib import Path

if __name__ == "__main__":
    with OregonCommunicator() as communicator:

        if not communicator.is_connected:
            print("Failed to connect to Oregon RFID device. Aborting.")
        else:
            communicator.control_device_datetime(tolerance_seconds=10)

            communicator.export_system_status_logs(first_date=date(2022, 8, 1), output_dir=Path("system_logs"))