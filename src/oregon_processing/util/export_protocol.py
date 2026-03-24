import logging
from contextlib import ExitStack

from oregon_processing.util.communicator import Communicator
from oregon_processing.util.oregon_config import OregonConfig
from oregon_processing.util.database_manager import DatabaseManager
from oregon_processing.util.logging_manager import LoggingManager, get_logger

class ExportProtocol:

    def __init__(self):
        self._exit_stack = None
        self._config = None
        self._communicator = None
        self._database_manager = None
        self._logging_manager = None
        self._logger = None

    def __enter__(self):
        self._exit_stack = ExitStack()

        logging_extra = {'process_name': 'Export Protocol'}
        try:
            self._config = OregonConfig()

            # Set up logging with crash logs directory
            crash_log_file = DatabaseManager.prepare_crash_log_file(self._config)
            self._logging_manager = self._exit_stack.enter_context(
                LoggingManager(
                    write_to_console = True,
                    write_to_report_file = True,
                    report_file = crash_log_file,
                    relative_base_paths = [self._config.root_output_dir],
                    console_level = logging.INFO,
                    file_level = logging.DEBUG,)
                    )

            self._logger = get_logger(__name__)

            self._communicator = self._exit_stack.enter_context(Communicator())

            if self._communicator.is_connected:
                self._database_manager = self._exit_stack.enter_context(DatabaseManager(self._config, self._communicator))
                self._database_manager.prepare_directories()

                # Update log file to final location
                report_file_dir = self._database_manager.log_dir
                report_file_name = self._logging_manager.report_file.name
                report_file = report_file_dir / report_file_name
                self._logging_manager.transfer_log_file(report_file)
        except Exception:
            if self._logger:
                self._logger.exception("Failed to initialize export protocol", extra=logging_extra)
            else:
                print("Failed to initialize export protocol")
            if self._exit_stack:
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

        if self._config is None:
            self._logger.error("Configuration manager not initialized. Aborting.", extra=logging_extra)
            return

        if not self._communicator.is_connected:
            self._logger.error("Oregon RFID device is not connected. Aborting.", extra=logging_extra)
            return

        health_report = self._communicator.check_device_health()
        if len(health_report['critical_warnings']) > 0:
            message = "Device health check failed. Please address the following critical issues before proceeding: \n  -" + "\n  -".join(health_report.get('critical_warnings', []))
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
