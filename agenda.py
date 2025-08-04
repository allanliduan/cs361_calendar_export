import zoneinfo
from pathlib import Path
from typing import Dict, List, Any, Optional
import json
from datetime import datetime
from csv import writer
from icalendar import Calendar, vText, Event as Cal_Event
import pytz
from pytz.exceptions import UnknownTimeZoneError


class Agenda:
    """
    Class for handling parsing and exporting of events
    """

    def __init__(self,data):
        # Required fields
        self.export_type: str = ""
        self.valid_types = ['txt','csv','ics']
        self.export_path: Optional[str] = ""
        self.events: List[Dict[str, Any]] = []

        # Optional fields
        self.exist_ok: Optional[bool] = False
        self.timezone: Optional[str] = "US/Pacific"

        self._data = data

    def __repr__(self):
        print_str = f"export type: {self.export_type}\nevents: {self.events}\n"
        print_str += f"export path: {self.export_path}\n"
        print_str += f"timezone: {self.timezone}\n"

        return print_str

    def parse_data(self) -> bool:
        """
        Parse data received. Currently expected as json str from ZeroMQ.
        Required fields: export_type, events
        Optional fields: export_folder_path, timezone
        export_folder_path will be set to "EXPORT" if not provided.
        """
        try:
            data = self._data

            # Check if data is json/dictionary
            if not isinstance(data, dict):
                raise ValueError("Data is not a dictionary")

            # Check export type
            raw_export_type = data.get("export_type")
            if not isinstance(raw_export_type, str):
                raise ValueError("export_type is not a string")
            if raw_export_type not in self.valid_types:
                raise ValueError(f"export_type must be one of {self.valid_types}")
            self.export_type = raw_export_type

            # Check events
            raw_events = data.get("events")
            if not isinstance(raw_events, list):
                raise ValueError("events is not a list")
            self.events = raw_events

            # Check export folder path
            raw_export_path = data.get("export_folder_path","EXPORT")
            if raw_export_path :
                if not isinstance(raw_export_path, str):
                    raise ValueError("export_file_path is not a string")
                else:
                    self.export_path = raw_export_path

            # Optional field: timezone
            raw_timezone = data.get("timezone", "UTC")  # Default timezone
            if not isinstance(raw_timezone, str):
                raise ValueError("timezone must be a string")
            self.timezone = raw_timezone


        except json.JSONDecodeError as e:
            print(f"Invalid JSON data received: {e}")

        except ValueError as e:
            print(f"Invalid data {e}")

        except Exception as e:
            print(f"Error Parsing Data: {e}")

        else:
            # No exceptions
            return True
        # Exceptions found
        return False

    def create_file_name(self):
        """
        Create a file name based on the export type and current time.
        File name will be in the format YYYY-MM-DD_HH-MM-SS.export_type
        """

        current_time_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        if self.export_type == 'txt':
            return current_time_str+f'.{"txt"}'
        elif self.export_type == 'csv':
            return current_time_str+f'.{"csv"}'
        elif self.export_type == 'ics':
            return current_time_str+f'.{"ics"}'

    def check_export(self) -> None|Path:
        """
        Check if the export path is valid.
        If not, create the export folder.
        Return the file path object to the export file.
        """

        if not self.events:
            print("No valid events to export...")
            return

        folder_export_path: Path
        if not self.export_path:
            folder_export_path = Path.cwd() / "export"
        else:
            path_obj = Path(self.export_path)
            if path_obj.is_absolute():
                folder_export_path = path_obj
            else:
                folder_export_path = Path.cwd() / self.export_path

        if not folder_export_path.exists():
            try:
                folder_export_path.mkdir()
            except Exception as e:
                print(e)

        # Get file name from export type
        file_name = self.create_file_name()
        file_export_path = folder_export_path / file_name


        # File overwrite check
        # if file_export_path.exists() and file_export_path.is_file():
        #     print("File already exists, please provide unique file path")

        return file_export_path
    

    def get_export_funct(self):
        """
        Get the export function based on the export type.
        """
        if self.export_type == 'txt':
            return self.export_to_txt
        elif self.export_type == 'csv':
            return self.export_to_csv
        elif self.export_type == 'ics':
            return self.export_to_ics
        
    def export(self) -> Optional[str]:
        """
        Main call to export events
        """
        if not self.parse_data():
            return
        export_function = self.get_export_funct()
        export_file_path = self.check_export()
        if not export_file_path:
            print("No valid export file path")
            return
        export_path = export_function(export_file_path)
        return str(export_path) if export_path else None

    def export_to_txt(self, export_file_path: Path):
        """
        Export events to a text file.
        """
        try:
            with open(export_file_path,'w', encoding='utf8') as f:
                for event in self.events:
                    f.write(f"name : \t{event.get('name')}\n")
                    f.write(f"\tdate : \t{event.get('date')}\n")
        except Exception as e:
            print(e)

        return export_file_path

    def export_to_csv(self, export_file_path: Path):
        """
        Export events to a csv file.
        """
        def event_to_list(event:dict) -> list[list]:
            return list(event.values())

        try:
            with open(export_file_path, 'w', newline='', encoding='utf8') as f:
                csv_writer = writer(f, delimiter=',', quotechar='|')
                header = ['Name', 'Date']
                csv_writer.writerow(header)
                for event in self.events:
                    event_list = event_to_list(event)
                    csv_writer.writerow(event_list)

        except Exception as e:
            print(e)

        return export_file_path

    def export_to_ics(self, export_file_path: Path):
        """
        Export events to an ics file.
        """
        try:
            cal = self.convert_events_to_ics()
            with open(export_file_path,'wb') as f:
                f.write(cal.to_ical())
        except UnknownTimeZoneError:
            print(f"Invalid time-zone given. Please reference link for valid timezones.\nhttps://gist.github.com/heyalexej/8bf688fd67d7199be4a1682b3eec7568")
        except Exception as e:
            print(f"Error creating ics: {e.__class__.__name__}: {e}")
        else:
            return export_file_path
        return False

    def convert_events_to_ics(self) -> Calendar:
        """
        Logic for converting events to an ics file.
        """
        def get_datetime_from_string(date_str) -> datetime:
            date = datetime.strptime(date_str,'%Y-%m-%d')
            return date

        cal = Calendar()
        cal.add('prodid', '-//My calendar product//mxm.dk//')
        cal.add('version', '2.0')

        # loop through and convert to ical components
        for event in self.events:
            cal_event = Cal_Event()
            # Add event name
            event_name = event.get('name')
            cal_event.add('summary',vText(event_name))
            # Add event date, convert to datetime and localize to timezone
            date = event.get('date')
            date_start = get_datetime_from_string(date)
            tz = pytz.timezone(self.timezone) # https://stackoverflow.com/questions/4974712/python-setting-a-datetime-in-a-specific-timezone-without-utc-conversions
            pacific_time = tz.localize(date_start)
            cal_event.add ('dtstart',pacific_time)
            # Add this event to calendar
            cal.add_component(cal_event)

        return cal
