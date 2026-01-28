import sys
from contextlib import ExitStack
from pathlib import Path
from datetime import datetime

from oregon_processing.util.oregon_communicator import OregonCommunicator
from oregon_processing.util.config_manager import ConfigManager
from oregon_processing.util.database_manager import DatabaseManager
from oregon_processing.util.tee_stream import TeeStream



SECTION_LINE_LENGTH = 70

class ExportProtocol:
    def __enter__(self):
        self._exit_stack = ExitStack()

        self._session = self._exit_stack.enter_context(_ExportProtocolSession())
        return self._session

    def __exit__(self, exc_type, exc_value, traceback):
        self._exit_stack.__exit__(exc_type, exc_value, traceback)


class _ExportProtocolSession:

    def __init__(self):
        self._exit_stack = None
        self._config_manager = None
        self._communicator = None
        self._database_manager = None
        self._tee_stream = None

    def __enter__(self):
        self._exit_stack = ExitStack()

        self._config_manager = self._exit_stack.enter_context(ConfigManager())
        self._communicator = self._exit_stack.enter_context(OregonCommunicator())
        self._database_manager = self._exit_stack.enter_context(DatabaseManager(self._config_manager, self._communicator))
        self._database_manager.prepare_directories()

        # Create log file in the database root directory with timestamp
        log_filename = f"export_protocol_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        log_file_path = self._database_manager.log_dir / log_filename
        self._tee_stream = self._exit_stack.enter_context(TeeStream(log_file_path))

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self._exit_stack:
            return self._exit_stack.__exit__(exc_type, exc_value, traceback)
        return False

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