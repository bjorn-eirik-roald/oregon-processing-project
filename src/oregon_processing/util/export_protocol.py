from contextlib import ExitStack
from datetime import datetime

from oregon_processing.util.communicator import Communicator
from oregon_processing.util.oregon_config import OregonConfig
from oregon_processing.util.database_manager import DatabaseManager, ExportDates
from oregon_processing.util.logging_manager import LoggingManager, get_logger
from oregon_processing.util.clock_manager import ClockCheckResult
from oregon_processing.util.device_health_checker import DeviceHealthReport
from oregon_processing.util.exceptions import CommandTransmissionError, ConfigNotFoundError, ConnectionFailedError, DeviceHealthError, InvalidConfigError, UnexpectedResponseError, UserAbortError
from oregon_processing.util.system_status import SystemStatus

class ExportProtocol:

    EXPORT_EVENT_RECORD_FLAG = False

    def __init__(self):
        self._exit_stack = None
        self._config = None
        self._communicator = None
        self._database_manager = None
        self._logging_manager = None
        self._logger = None

    def __enter__(self):
        self._exit_stack = ExitStack()

        try:
            self._config = OregonConfig()

            # Set up logging with crash logs directory
            crash_log_file = DatabaseManager.prepare_crash_log_file(self._config)
            self._logging_manager = self._exit_stack.enter_context(
                LoggingManager(
                    write_to_console = True,
                    write_to_report_file = True,
                    report_file = crash_log_file,
                    relative_base_paths = {"output_dir": self._config.root_output_dir}
                    )
            )

            self._logger = get_logger(__name__)

            self._communicator = self._exit_stack.enter_context(Communicator())

            system_status: SystemStatus = self._communicator.get_system_status()
            self._database_manager = DatabaseManager(self._config, system_status)
            self._database_manager.prepare_directories(system_status.serial_number)

            # Update log file to final location
            report_file_dir = self._database_manager.log_dir
            report_file = report_file_dir / f"export_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            self._logging_manager.transfer_log_file(report_file)
        except (ConfigNotFoundError, InvalidConfigError, ConnectionFailedError, UnexpectedResponseError, CommandTransmissionError, UserAbortError) as e:
            self._exit_stack.close()
            raise
        except Exception as e:
            if self._logger:
                self._logger.exception("Failed to initialize export protocol:\n\n {}".format(e))
            else:
                print(f"Failed to initialize export protocol:\n\n {e}")

            self._exit_stack.close()
            raise

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self._exit_stack:
            return self._exit_stack.__exit__(exc_type, exc_value, traceback)
        return False

    def run_export_protocol(self):

        self._logger.info("Oregon RFID Export Protocol Initiated")

        if not self._communicator.is_connected:
            self._logger.error("Oregon RFID device is not connected. Aborting.")
            return

        # Execute device health check on device
        health_report: DeviceHealthReport = self._communicator.check_device_health()
        if len(health_report.critical_warnings) > 0:
            error_message = "Device health check failed. Please address the following critical issues before proceeding: \n  -" + "\n  -".join(health_report.critical_warnings)
            self._logger.error(error_message)
            raise DeviceHealthError(error_message)

        # Execute device clock sync check on device
        clock_check_result: ClockCheckResult = self._communicator.control_device_datetime(tolerance_seconds=10)
        if not clock_check_result.synchronized:
            error_message = "Device clock is not in sync and could not be automatically updated. Please address the issue before proceeding."
            self._logger.error(error_message)
            raise DeviceHealthError(error_message)

        # get dates where exports are needed based on what is already in the database
        export_dates: ExportDates = self._database_manager.get_export_dates()


        if self.EXPORT_EVENT_RECORD_FLAG:
            self._communicator.export_event_records(
                dates=export_dates.event_record_dates,
                output_dir=self._database_manager.event_records_dir
            )
        else:
            self._logger.info("Skipping event record export as currently configured.")

        self._communicator.export_detection_records(
            dates=export_dates.detection_record_dates,
            output_dir=self._database_manager.records_dir
        )
