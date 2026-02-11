import sys
import logging
from contextlib import ExitStack
from pathlib import Path
from datetime import datetime

from oregon_processing.util.oregon_communicator import OregonCommunicator
from oregon_processing.util.config_manager import ConfigManager
from oregon_processing.util.database_manager import DatabaseManager
from oregon_processing.util.logging_manager import LoggingManager


class ExportProtocol:
    def __enter__(self):
        try:
            self._exit_stack = ExitStack()

            self._session = self._exit_stack.enter_context(_ExportProtocolSession())
            return self._session
        except Exception:
            # Create a temporary logger to capture initialization errors
            logger = logging.getLogger('oregon_processing.export_protocol')
            logger.exception("Failed to enter ExportProtocol context")
            self._exit_stack.close()
            raise

    def __exit__(self, exc_type, exc_value, traceback):
        self._exit_stack.__exit__(exc_type, exc_value, traceback)


class _ExportProtocolSession:

    def __init__(self):
        self._exit_stack = None
        self._config_manager = None
        self._communicator = None
        self._database_manager = None
        self._logging_manager = None
        self._logger = None

    def __enter__(self):
        self._exit_stack = ExitStack()

        logging_extra = {'process_name': 'Export Protocol'}
        try:
            self._config_manager = self._exit_stack.enter_context(ConfigManager())

            # Set up logging with crash logs directory
            crash_logs_dir = DatabaseManager.prepare_crash_logs_dir(self._config_manager)
            self._logging_manager = self._exit_stack.enter_context(
                LoggingManager(log_name="export_protocol", log_dir=crash_logs_dir)
            )
            self._logger = self._logging_manager.get_logger('export_protocol')

            self._communicator = self._exit_stack.enter_context(OregonCommunicator())

            if self._communicator.is_connected:
                self._database_manager = self._exit_stack.enter_context(DatabaseManager(self._config_manager, self._communicator))
                self._database_manager.prepare_directories()

                # Update log directory to final location
                self._logging_manager.set_log_directory(self._database_manager.export_logs_dir)
        except Exception:
            self._logger.exception("Failed to initialize export protocol", extra=logging_extra)
            self._exit_stack.close()
            raise
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self._exit_stack:
            return self._exit_stack.__exit__(exc_type, exc_value, traceback)
        return False

    def run_export_protocol(self):


        logging_extra = {'process_name': 'Export Protocol'}

        self._logger.info("Oregon RFID Export Protocol Initiated", extra=logging_extra)

        if self._config_manager is None:
            self._logger.error("Configuration manager not initialized. Aborting.", extra=logging_extra)
            return

        if not self._communicator.is_connected:
            self._logger.error("Oregon RFID device is not connected. Aborting.", extra=logging_extra)
            return

        health_report = self._communicator.check_device_health()
        if not health_report['healthy']:
            message = "Device health check failed. Please address the following issues before proceeding: \n  -" + "\n  -".join(health_report.get('warnings', []))
            self._logger.error(message, extra=logging_extra)
            return

        result = self._communicator.control_device_datetime(tolerance_seconds=10)
        if not result['synced']:
            self._logger.error("Device clock is not in sync. Please address the issues before proceeding.", extra=logging_extra)
            return

        missing_export_dates = self._database_manager.get_export_dates()

        self._communicator.export_event_records(
            dates=missing_export_dates['system_logs'],
            output_dir=self._database_manager.event_records_dir
        )
        self._communicator.export_detection_records(
            dates=missing_export_dates['records'],
            output_dir=self._database_manager.records_dir
        )


def run():

    with ExportProtocol() as export_protocol:
        export_protocol.run_export_protocol()

if __name__ == "__main__":
    run()