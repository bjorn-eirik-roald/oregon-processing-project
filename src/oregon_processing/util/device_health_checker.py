# -*- coding: utf-8 -*-
"""
Health Manager - Manages system health checks for Oregon RFID device.

Provides methods for checking device health status, including supply voltage
and other system parameters.
"""

import logging



class DeviceHealthChecker:
    """Manages system health checks for Oregon RFID device."""

    CRITICAL_VOLTAGE_THRESHOLD = 10.0  # volts #TODO Set appropriate threshold

    def __init__(self, communicator):
        """
        Initialize DeviceHealthChecker.

        Parameters
        ----------
        communicator : OregonCommunicator
            OregonCommunicator instance for device communication.
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

        warnings = []
        parsed_status = self._communicator.get_system_status()


        # Check supply voltage
        if parsed_status['supply_voltage']:
            try:
                voltage = float(parsed_status['supply_voltage'])
                if voltage < self.CRITICAL_VOLTAGE_THRESHOLD:
                    warnings.append(f"Low supply voltage: {voltage}V (should be >= {self.CRITICAL_VOLTAGE_THRESHOLD}V)")
            except (ValueError, TypeError):
                warnings.append(f"Could not parse supply voltage: {parsed_status['supply_voltage']}")

        health_report = {
            'healthy': len(warnings) == 0,
            'warnings': warnings
        }

        # Report health status
        if not health_report['healthy']:
            warning_message = f"{len(health_report['warnings'])} issue(s) detected during health check."

            for warning in health_report['warnings']:
                warning_message += f"\n  - {warning}"

            self._logger.warning(warning_message, extra=logging_extra)

        else:
            self._logger.info("All parameters within normal range", extra=logging_extra)

        return health_report
