# -*- coding: utf-8 -*-
"""
Health Manager - Manages system health checks for Oregon RFID device.

Provides methods for checking device health status, including supply voltage
and other system parameters.
"""

from oregon_processing.util.display_constants import display


class DeviceHealthChecker:
    """Manages system health checks for Oregon RFID device."""

    CRITICAL_VOLTAGE_THRESHOLD = 14.0  # volts

    def __init__(self, communicator):
        """
        Initialize DeviceHealthChecker.

        Parameters
        ----------
        communicator : OregonCommunicator
            OregonCommunicator instance for device communication.
        """
        self._communicator = communicator

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

        print("\n" + display.SECTION_SEPARATOR * display.SECTION_LINE_LENGTH, flush=True)
        print("SYSTEM STATUS HEALTH CHECK", flush=True)
        print(display.SECTION_SEPARATOR * display.SECTION_LINE_LENGTH, flush=True)

        print("\n" + display.SUBSECTION_SEPARATOR * display.SECTION_LINE_LENGTH)
        print("Retrieving System Status")
        print(display.SUBSECTION_SEPARATOR * display.SECTION_LINE_LENGTH)
        print("Requesting system status from device...", end="", flush=True)

        warnings = []
        parsed_status = self._communicator.get_system_status()

        print("Done.")

        # Check supply voltage
        print("\n" + display.SUBSECTION_SEPARATOR * display.SECTION_LINE_LENGTH)
        print("Health Analysis")
        print(display.SUBSECTION_SEPARATOR * display.SECTION_LINE_LENGTH)

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
            print(f"\n⚠ WARNING: {len(health_report['warnings'])} issue(s) detected:")
            for warning in health_report['warnings']:
                print(f"  - {warning}")
        else:
            print("\n✓ System status check: All parameters within normal range")

        print("\n" + display.SECTION_SEPARATOR * display.SECTION_LINE_LENGTH)
        print("CHECK COMPLETE")
        print(display.SECTION_SEPARATOR * display.SECTION_LINE_LENGTH)

        return health_report
