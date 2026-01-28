# -*- coding: utf-8 -*-
"""
Data Exporter for Oregon RFID device data
"""

import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Union, TYPE_CHECKING

if TYPE_CHECKING:
    from oregon_processing.util.oregon_communicator import OregonCommunicator
    from oregon_processing.util.format_manager import FormatManager
    from oregon_processing.util.command_manager import CommandManager


class DataExporter:
    """Handles exporting data from the Oregon RFID communicator."""

    DEFAULT_DETECTION_RECORD_FORMAT = 'DTY ARR SPC TRF DUR SPC TTY SPC TAG SCD NCD EFA'
    def __init__(self, communicator: "OregonCommunicator", format_manager: "FormatManager", command_manager: "CommandManager"):
        """
        Initialize DataExporter with communicator and manager instances.

        Parameters
        ----------
        communicator : OregonCommunicator
            Connected OregonCommunicator instance to use for data retrieval.
        format_manager : FormatManager
            Format manager instance for handling detection record format operations.
        command_manager : CommandManager
            Command manager instance for sending commands to device.
        """
        self._communicator = communicator
        self._format_manager = format_manager
        self._command_manager = command_manager

    def __enter__(self):
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        pass

    def _split_detection_record(self, record_line: str, format_info: dict) -> list:
        """
        Split a detection record line into parts, handling the ARR field which contains spaces.

        The ARR (arrival datetime) field has the format "YYYY-MM-DD HH:MM:SS.ddd" which contains
        a space between the date and time. When splitting by spaces, this creates two tokens
        instead of one, so we need to merge them back together.

        Note: Some records may be missing trailing fields (e.g., HDP) that FM reports.

        Parameters
        ----------
        record_line : str
            The detection record line to split
        format_info : dict
            Format information containing 'columns' and 'column_indices'

        Returns
        -------
        list
            List of field values with ARR properly merged if present

        Raises
        ------
        ValueError
            If the record has an unexpected number of parts
        """
        # Split by spaces
        parts = record_line.split()

        columns = format_info['columns']
        column_indices = format_info['column_indices']
        arr_index = column_indices.get('ARR')

        if arr_index is None:
            raise ValueError("ARR index not found in format info.")



        # If ARR is in the format, we expect one extra part (because ARR contains a space)
        # Check if we have enough parts to merge ARR
        if len(parts) < arr_index + 2:
            raise ValueError(
                f"Not enough parts to merge ARR at index {arr_index}, got {len(parts)} parts"
            )

        # Merge the two ARR parts (date and time) back together
        # The date part is at arr_index, time part is at arr_index+1
        arr_date = parts[arr_index]
        arr_time = parts[arr_index + 1]
        parts[arr_index] = f"{arr_date} {arr_time}"

        # Remove the time part (which is now merged into arr_index)
        parts.pop(arr_index + 1)

        # After merging, we might have fewer parts than columns if trailing fields are missing
        # This is acceptable - some records may not have all fields (e.g., HDP)

        return parts

    def export_system_status(self, output_dir: Path) -> bool:
        """
        Run the SY (system status) command and write the response to a text file.

        Parameters
        ----------
        output_dir : str or Path
            Directory where system status will be written.

        Returns
        -------
        bool
            True if successful, False otherwise.
        """

        if isinstance(output_dir, str):
            try:
                output_dir = Path(output_dir)
            except Exception as e:
                print(f"Error converting output directory string to Path object: {e}")
                return False

        if not self._communicator.is_connected:
            print("Not connected to device.")
            return False

        if not output_dir.exists():
            output_dir.mkdir(parents=True, exist_ok=True)

        output_filepath = output_dir / f"{self._communicator.serial_number}_system_status_{datetime.now().strftime('%Y_%m_%d_%H%M%S')}.txt"

        try:
            print(f"\nExporting system status to file...", end="")
            parsed_status = self._communicator.get_system_status()

            with open(output_filepath, 'w') as f:
                f.write("Oregon RFID System Status\n")
                f.write("Export Date/Time: " + time.strftime("%Y-%m-%d %H:%M:%S") + "\n")
                f.write("=========================\n\n")

                # Write system status
                f.write(f"Device Type: {parsed_status['device_type']}\n")
                f.write(f"Version: {parsed_status['version']}\n")
                f.write(f"Serial Number: {parsed_status['serial_number']}\n")
                f.write(f"Reader Name: {parsed_status['reader_name']}\n")
                f.write(f"Mode: {parsed_status['mode']}\n")
                f.write(f"Supply Voltage: {parsed_status['supply_voltage']}\n")
                f.write(f"Standby Amps: {parsed_status['standby_amps']}\n")
                f.write(f"Noise: {parsed_status['noise']}\n")
                f.write(f"Shutdown Supercap: {parsed_status['shutdown_supercap']}\n")
                f.write(f"Sleep Battery: {parsed_status['sleep_battery']}\n")
                f.write(f"Tags in Archive: {parsed_status['tags_in_archive']}\n\n")

                if parsed_status['warnings']:
                    f.write("Warnings:\n")
                    for warning in parsed_status['warnings']:
                        f.write(f"  - {warning}\n")
                    f.write("\n")
                else:
                    f.write("No warnings detected.\n\n")

            print("Done.")
            print(f"System status written to {output_filepath}")

            return True

        except Exception as e:
            print(f"Error writing system status to file: {e}")
            return False

    def export_upload_log(self, output_dir: Path) -> bool:
        """
        Run the UH (upload log) command and write the response to a text file.

        Parameters
        ----------
        output_dir : str or Path
            Directory where output file will be written.

        Returns
        -------
        bool
            True if successful, False otherwise.
        """

        if isinstance(output_dir, str):
            try:
                output_dir = Path(output_dir)
            except Exception as e:
                print(f"Error converting output directory string to Path object: {e}")
                return False

        if not self._communicator.is_connected:
            print("Not connected to device.")
            return False

        if not output_dir.exists():
            output_dir.mkdir(parents=True, exist_ok=True)

        output_filepath = output_dir / f"{self._communicator.serial_number}_upload_log_{datetime.now().strftime('%Y_%m_%d_%H%M%S')}.txt"

        try:
            print(f"\nExporting upload log to file:", flush=True)
            upload_history_lines = self._command_manager.send_command("UH")

            with open(output_filepath, 'w') as f:
                f.write("Oregon RFID Upload Log\n")
                f.write("Export Date/Time: " + time.strftime("%Y-%m-%d %H:%M:%S") + "\n")
                f.write("=========================\n\n")

                # Write upload log
                f.write('\n'.join(upload_history_lines))

            print(f"  Upload log written to {output_filepath}")
            print(f"  Total lines written: {len(upload_history_lines)}")

            return True

        except Exception as e:
            print(f"Error writing upload log to file: {e}")
            return False

    def export_system_status_logs(self, first_date: date, last_date: Union[date, None] = None, output_dir: Path = Path("")) -> bool:
        """
        Export system status logs for all dates in a range.

        This method retrieves the last upload date, then runs export_system_status_log()
        for each day in the range up to and including today.

        Parameters
        ----------
        first_date : date object
        output_dir : str or Path
            Directory where output files will be written (default: current directory)

        Returns
        -------
        bool
            True if all exports completed successfully, False if any failed.
        """

        if last_date is None:
            last_date = date.today()

        if isinstance(output_dir, str):
            try:
                output_dir = Path(output_dir)
            except Exception as e:
                print(f"Error converting output directory string to Path object: {e}")
                return False

        if not self._communicator.is_connected:
            print("Not connected to device.")
            return False

        try:

            if first_date > last_date:
                print(f"First date ({first_date}) is in the future. No logs to export.")
                return False

            # Header
            print("\n" + "=" * 70)
            print("EXPORTING SYSTEM STATUS LOGS")
            print("=" * 70)
            print(f"Date range: {first_date} to {last_date}")
            print(f"Output directory: {output_dir}")

            # Prepare ranges and formatting
            num_dates = (last_date - first_date).days + 1
            all_dates = [first_date + timedelta(days=i) for i in range(num_dates)]
            max_counter_width = len(f"({num_dates}/{num_dates})")
            max_line_width = len(str(1440))  # assume up to one line per minute per day

            print("\n" + "-" * 70)
            print("Exporting Logs")
            print("-" * 70)

            all_successful = True
            export_count = 0

            for date_num, current in enumerate(all_dates, start=1):

                output_filepath = f"{output_dir}/{self._communicator.serial_number}_system_log_{current.strftime('%Y_%m_%d')}.txt"

                counter = f"({date_num}/{num_dates})"
                spacing = " " * (max_counter_width - len(counter))
                print(f"  - {spacing}{counter} {current}. Exporting...", end="", flush=True)

                try:
                    success = True
                    # Send ER command with date
                    command = f"ER {current.strftime('%Y-%m-%d')}"
                    response = self._command_manager.send_command(command)
                except Exception as e:
                    print(f"ERROR. {e}")
                    success = False
                    all_successful = False
                    response = []

                # Generate output filename with date
                with open(output_filepath, 'w') as f:
                    f.write("Oregon RFID System Log (Event Records)\n")
                    f.write("Export Date/Time: " + time.strftime("%Y-%m-%d %H:%M:%S") + "\n")
                    f.write("Date of Log: " + current.strftime("%Y-%m-%d") + "\n")
                    f.write("=========================\n\n")

                    # Write system log (event records)
                    f.write('\n'.join(response))

                if success:
                    print(f"Done. Lines written: {len(response)}.")
                    export_count += 1

            failed_exports = num_dates - export_count

            print("\n" + "-" * 70)
            print("SUMMARY")
            print("-" * 70)
            print(f"Total dates processed: {num_dates}")
            print(f"Successful exports:    {export_count}")
            print(f"Failed exports:        {failed_exports}")

            print("\n" + "=" * 70)
            if all_successful:
                print("EXPORT COMPLETE")
            else:
                print("EXPORT COMPLETE WITH ERRORS")
            print("=" * 70)

            return True if all_successful else False

        except Exception as e:
            print(f"Error during batch export: {e}")
            print("\n" + "=" * 70)
            print("EXPORT FAILED")
            print("=" * 70)
            return False

    def export_detection_records(self, first_date: date, last_date: Union[date, None] = None, output_dir: Path = Path(""), sep=',') -> bool:
        """
        Export detection records (S-type) for a date range using the UP* command.

        The UP* command returns all record types (S: Detection, E: Event, G: GNSS),
        but this method filters and exports only detection records (S-type) within
        the specified date range.

        Parameters
        ----------
        first_date : date object
            Start date for export (inclusive)
        last_date : date object, optional
            End date for export (inclusive). If None, defaults to current date.
        output_dir : str or Path
            Directory where output files will be written (default: current directory)
        sep : str, optional
            Separator to use in the output file (default: ',')

        Returns
        -------
        bool
            True if all exports completed successfully, False if any failed.
        """

        if last_date is None:
            last_date = date.today()

        if isinstance(output_dir, str):
            try:
                output_dir = Path(output_dir)
            except Exception as e:
                print(f"Error converting output directory string to Path object: {e}")
                return False

        if not self._communicator.is_connected:
            print("Not connected to device.")
            return False

        if not output_dir.exists():
            output_dir.mkdir(parents=True, exist_ok=True)

        if first_date > last_date:
            print(f"First date ({first_date}) is after last date ({last_date}). No records to export.")
            return False

        upload_history = self._communicator.get_upload_history()
        total_number_of_records = upload_history["total_records"]

        print("\n" + "=" * 70)
        print("EXPORTING DETECTION RECORDS")
        print("=" * 70)
        print(f"Date range: {first_date} to {last_date}")
        print(f"Total records on device: {total_number_of_records}")
        print(f"Output directory: {output_dir}")

        print("\n" + "-" * 70)
        print("PHASE 1: Retrieving Records from Device")
        print("-" * 70)
        print("Setting detection record format to default for export...", end="", flush=True)
        if not self._format_manager.set_detection_record_format(self.DEFAULT_DETECTION_RECORD_FORMAT):
            print("Failed to set detection record format. Cannot continue.")
            return False
        print("Done.")
        print("Requesting all records from device...", end="", flush=True)
        response = self._command_manager.send_command("UP*")
        print("Done.")

        print("\n" + "-" * 70)
        print("PHASE 2: Processing Records")
        print("-" * 70)
        # Retrieve detection record format to determine column order, tag index, and datetime index

        format_info = self._format_manager.get_format_info()
        format_columns_str = sep.join(format_info['columns'])
        column_indices = format_info['column_indices']
        arr_idx = column_indices.get('ARR')
        tag_idx = column_indices.get('TAG')

        if arr_idx is None:
            raise RuntimeError("ARR index not found in detection record format info. This is required for date filtering. Cannot continue.")

        if tag_idx is None:
            raise RuntimeError("Tag index not found in detection record format info. This is required for unique tag counting. Cannot continue.")

        print("Filtering detection records in date range...", end="", flush=True)
        # Convert dates to strings for comparison (YYYY-MM-DD format sorts chronologically)
        first_date_str = first_date.strftime("%Y-%m-%d")
        last_date_str = last_date.strftime("%Y-%m-%d")

        # Filter detection records (S-type) in date range - single pass with early termination
        filtered_detection_records = []
        for line in response:
            if not line.startswith("S"):
                continue

            # Split detection record properly handling ARR datetime field
            try:
                parts = self._split_detection_record(line, format_info)
            except ValueError:
                print(f"Warning: Skipping malformed detection record during filtering: {line}")
                continue  # Skip malformed detection records


            # Extract date portion from ARR field (YYYY-MM-DD HH:MM:SS.ddd)
            record_date_str = parts[arr_idx].split()[0]  # Get YYYY-MM-DD part

            if record_date_str > last_date_str:
                break  # Early exit - records are chronological, no need to continue
            if record_date_str >= first_date_str:
                filtered_detection_records.append(parts)

        print("Done.")

        print("Organizing detection records by date........", end="", flush=True)
        detection_records_by_date = {} # dict with date keys and list of detection records values
        all_dates = [first_date + timedelta(days=i) for i in range((last_date - first_date).days + 1)]
        num_dates = len(all_dates)

        unique_tags = set()

        current_date = None
        for detection_record in filtered_detection_records:

            record_date = datetime.strptime(detection_record[arr_idx].split()[0], "%Y-%m-%d").date()
            record_tag = detection_record[tag_idx]

            if record_date != current_date:
                current_date = record_date
                detection_records_by_date[current_date] = []

            detection_records_by_date[current_date].append(sep.join(detection_record))
            unique_tags.add(record_tag)

        print("Done.")

        print("\n" + "-" * 70)
        print("SUMMARY")
        print("-" * 70)

        # Calculate max width for summary number alignment
        max_summary_width = max(
            len(str(len(filtered_detection_records))),
            len(str(len(detection_records_by_date))),
            len(str(num_dates - len(detection_records_by_date)))
        )

        print(f"Total detection records in date range: {str(len(filtered_detection_records)).rjust(max_summary_width)}")
        print(f"Number of dates with records:          {str(len(detection_records_by_date)).rjust(max_summary_width)}")
        print(f"Number of dates without records:       {str(num_dates - len(detection_records_by_date)).rjust(max_summary_width)}")
        print(f"Number of unique tags:                 {str(len(unique_tags)).rjust(max_summary_width)}")

        print("\n" + "-" * 70)
        print("PHASE 3: Exporting Files")
        print("-" * 70)

        # Calculate max width for counter alignment
        max_counter_width = len(f"({num_dates}/{num_dates})")

        # Calculate max width for record count alignment
        max_record_count = max((len(recs) for recs in detection_records_by_date.values()), default=0)
        max_count_width = len(str(max_record_count))

        for date_num, current_date in enumerate(all_dates):
            counter = f"({date_num + 1}/{num_dates})"
            spacing = " " * (max_counter_width - len(counter))
            print(f"  - {spacing}{counter} {current_date}. ", end="", flush=True)

            if current_date not in detection_records_by_date:
                count_str = "0".rjust(max_count_width)
                unique_tags_count = 0
            else:
                count_str = str(len(detection_records_by_date[current_date])).rjust(max_count_width)
                # Compute unique tags using FM-derived tag index when available; fallback to slice
                if tag_idx is not None:
                    def _extract_tag(line: str) -> str:
                        try:
                            parts = self._split_detection_record(line, format_info)
                            return parts[tag_idx] if tag_idx < len(parts) else line[22:34]
                        except (ValueError, IndexError):
                            return line[22:34]
                    unique_tags_count = len(set(_extract_tag(r) for r in detection_records_by_date.get(current_date, [])))
                else:
                    unique_tags_count = len(set(r[22:34] for r in detection_records_by_date.get(current_date, [])))

            print(f"Number of detection records: {count_str}. Unique tags: {unique_tags_count}. Exporting file...", end="", flush=True)

            output_filepath = output_dir / f"{self._communicator.serial_number}_records_{current_date.strftime('%Y_%m_%d')}.txt"
            with open(output_filepath, 'w') as f:
                f.write("Oregon RFID Detection Records\n")
                f.write("Export Date/Time: " + time.strftime("%Y-%m-%d %H:%M:%S") + "\n")
                f.write("Date of Record: " + current_date.strftime("%Y-%m-%d") + "\n")
                f.write("Number of Records: " + count_str.strip() + "\n")
                f.write("Number of unique tags: " + str(unique_tags_count) + "\n")
                f.write("=========================\n\n")
                f.write(f"{format_columns_str.replace(' ', sep)}\n\n")
                # Write detection records for the date
                if current_date in detection_records_by_date:
                    f.write('\n'.join(detection_records_by_date[current_date]))

            print("Done.")


        print("\n" + "=" * 70, flush=True)
        print("EXPORT COMPLETE", flush=True)
        print("=" * 70, flush=True)
        return True

