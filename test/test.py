from datetime import date
from pathlib import Path

from oregon_processing.oregon_communicator import OregonCommunicator


def main():
    with OregonCommunicator() as communicator:
        if not communicator.is_connected:
            print("Failed to connect to Oregon RFID device. Aborting.")
            return

        health_report = communicator.check_system_status_health()
        if not health_report['healthy']:
            print("Device health check failed. Please address the issues before proceeding.")
            return

        result = communicator.control_device_datetime(tolerance_seconds=10)
        if not result['synced']:
            print("Device clock is not in sync. Cannot proceed with data export.")
            return

        first_date = date(2021, 9, 1)
        last_date = date(2022, 1, 11)
        communicator.export_system_status_logs(first_date=first_date, last_date=last_date, output_dir=Path("system_logs"))
        communicator.export_records(first_date=first_date, last_date=last_date, output_dir=Path("records"))


if __name__ == "__main__":
    main()