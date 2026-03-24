# -*- coding: utf-8 -*-
"""
Health Manager - Manages system health checks for Oregon RFID device.

Provides methods for checking device health status, including supply voltage
and other system parameters.
"""

from oregon_processing.util.logging_manager import get_logger

#import Oregon Communicator in type checking block to avoid circular import issues
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from oregon_processing.util.communicator import Communicator



class DeviceHealthChecker:
    """Manages system health checks for Oregon RFID device."""

    RECOMMENDED_VOLTAGE = 14.0
    CRITICAL_VOLTAGE_THRESHOLD = 12.5

    def __init__(self, communicator: "Communicator"):
        """
        Initialize DeviceHealthChecker.

        Parameters
        ----------
        communicator : Communicator
            Communicator instance for device communication.
        """
        self._communicator = communicator
        self._logger = logging.getLogger('oregon_processing.device_health_checker')

    def __enter__(self):
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        pass

    def check_device_health(self):
        """
        Calls for system status and checks parsed system status for potential issues.

        Returns
        -------
        dict
            Dictionary with 'healthy' (bool) and 'warnings' (list of str) keys.
        """

        logging_extra = {'process_name': 'Health Check'}

        self._logger.info("Initializing health check of Oregon RFID device.", extra=logging_extra)
        self._logger.info("Retrieving System Status.", extra=logging_extra)

        critical_warnings = []
        non_critical_warnings = []
        parsed_status = self._communicator.get_system_status()
        prompt_signature = self._communicator.prompt_signature

        if prompt_signature[2] != 'G':
            non_critical_warnings.append(
                f"Device time is not synchronized to GNSS signals (current state: '{prompt_signature[2]}')"
            )

        # Check supply voltage
        if parsed_status['supply_voltage']:
            try:
                voltage = float(parsed_status['supply_voltage'])
                if voltage < self.RECOMMENDED_VOLTAGE:
                    non_critical_warnings.append(
                        f"Low supply voltage: {voltage}V (recommended to be >= {self.RECOMMENDED_VOLTAGE}V)"
                    )

                if voltage < self.CRITICAL_VOLTAGE_THRESHOLD:
                    critical_warnings.append(
                        f"Critical low supply voltage: {voltage}V (must be >= {self.CRITICAL_VOLTAGE_THRESHOLD}V)"
                    )

            except (ValueError, TypeError):
                non_critical_warnings.append(
                    f"Could not parse supply voltage: {parsed_status['supply_voltage']}"
                )


        health_report = {
            'healthy': len(critical_warnings) == 0 and len(non_critical_warnings) == 0,
            'critical_warnings': critical_warnings,
            'warnings': non_critical_warnings
        }

        # Report health status
        if not health_report['healthy']:
            total_issues = len(critical_warnings) + len(non_critical_warnings)
            warning_message = f"{total_issues} issue(s) detected during health check."

            if critical_warnings:
                warning_message += "\n  Critical:"
                for warning in critical_warnings:
                    warning_message += f"\n    - {warning}"

            if non_critical_warnings:
                warning_message += "\n  Non-critical:"
                for warning in non_critical_warnings:
                    warning_message += f"\n    - {warning}"

            self._logger.warning(warning_message, extra=logging_extra)

        else:
            self._logger.info("All parameters within normal range", extra=logging_extra)

        return health_report
