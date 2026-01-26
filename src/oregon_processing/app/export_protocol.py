from oregon_processing.util.oregon_communicator import OregonCommunicator
from oregon_processing.util.config_manager import ConfigManager
from oregon_processing.util.database_manager import DatabaseManager



SECTION_LINE_LENGTH = 70

class ExportProtocol:
    def __enter__(self):
        self._session = _ExportProtocolSession()
        self._session.__enter__()
        return self._session

    def __exit__(self, exc_type, exc_value, traceback):
        if self._session:
            self._session.__exit__(exc_type, exc_value, traceback)


class _ExportProtocolSession:

    def __init__(self):
        self._start_up_mode = None
        self._config_manager = None
        self._communicator = None
        self._database_manager = None

    def __enter__(self):
        self._load_configuration()
        self._communicator = OregonCommunicator()
        self._communicator.__enter__()
        self._database_manager = DatabaseManager(self._config_manager, self._communicator.reader_name)
        self._database_manager.prepare_directories()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self._communicator:
            self._communicator.exit()

        if self._database_manager:
            self._database_manager.exit()

    def _load_configuration(self):
        print("\n"+"=" * SECTION_LINE_LENGTH, flush=True)
        print("CONFIGURATION", flush=True)
        print("=" * SECTION_LINE_LENGTH, flush=True)

        print("\nLoading configuration...", end="", flush=True)
        self._config_manager = ConfigManager()
        print(" Done.", flush=True)
        print("-"*SECTION_LINE_LENGTH, flush=True)
        print("Configuration summary:", flush=True)
        print(f"  User: {self._config_manager.user}", flush=True)
        print(f"  Data directory: {self._config_manager.data_dir}", flush=True)

        print("\n"+"=" * SECTION_LINE_LENGTH, flush=True)
        print("END OF CONFIGURATION", flush=True)
        print("=" * SECTION_LINE_LENGTH, flush=True)

    def run_export_protocol(self):
        print("\n"+"=" * SECTION_LINE_LENGTH, flush=True)
        print("=" * SECTION_LINE_LENGTH, flush=True)
        print("Oregon RFID Export Protocol", flush=True)
        print("=" * SECTION_LINE_LENGTH, flush=True)
        print("=" * SECTION_LINE_LENGTH, flush=True)

        if self._config_manager is None:
            print("Configuration manager not initialized. Aborting.", flush=True)
            return

        if not self._communicator.is_connected:
            print("Oregon RFID device is not connected. Aborting.", flush=True)
            return

        self._communicator.change_mode('Standby')

        health_report = self._communicator.check_system_status_health()
        if not health_report['healthy']:
            print("\nDevice health check failed. Please address the issues before proceeding.", flush=True)
            return

        result = self._communicator.control_device_datetime(tolerance_seconds=10)
        if not result['synced']:
            print("\nDevice clock is not in sync. Please address the issues before proceeding.", flush=True)
            return

        previous_export_dates = self._database_manager.get_export_dates()

        self._communicator.export_system_status_logs(
            first_date=previous_export_dates['system_logs'],
            last_date=None,
            output_dir=self._database_manager.system_logs_dir
        )
        self._communicator.export_detection_records(
            first_date=previous_export_dates['records'],
            last_date=None,
            output_dir=self._database_manager.records_dir
        )


def run():

    with ExportProtocol() as export_protocol:
        export_protocol.run_export_protocol()

if __name__ == "__main__":
    run()