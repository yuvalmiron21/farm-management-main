import pandas as pd
from datetime import datetime
from typing import Optional
import json
import os
from firebase_admin import credentials, db, initialize_app


class Batch:
    _batch_id_counter = 1  # Static counter for generating unique batch IDs
    def __init__(
        self,
        mushroom_type: Optional[str] = None,
        iteration_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        room_number: Optional[int] = None,
        substrate: Optional[float] = None
    ):
        self.batch_id = Batch._batch_id_counter
        Batch._batch_id_counter += 1
        self.mushroom_type = mushroom_type
        self.iteration_id = iteration_id
        self.start_date = start_date
        self.room_number = room_number
        self.substrate = substrate

    def __repr__(self):
        return (
            f"Batch(batch_id={self.batch_id}, mushroom_type='{self.mushroom_type}', "
            f"iteration_id={self.iteration_id}, start_date={self.start_date}, "
            f"room_number={self.room_number}, substrate={self.substrate})"
        )

class Log:
    _log_id_counter = 1  # Static counter for generating unique log IDs

    def __init__(
        self,
        batch_id: int,
        days_after_plant: Optional[int] = None,
        date: Optional[datetime] = None,
        hour: Optional[str] = None,
        air_temp: Optional[float] = None,
        substrate_temp: Optional[float] = None,
        rh_humidity: Optional[float] = None,
        co2: Optional[float] = None,
        day_hours: Optional[int] = None,
        harvest: Optional[float] = None,
        if_bagged: Optional[bool] = None
    ):
        self.log_id = Log._log_id_counter
        Log._log_id_counter += 1  # Increment the counter

        self.batch_id = batch_id
        self.days_after_plant = days_after_plant
        self.date = date
        self.hour = hour
        self.air_temp = air_temp
        self.substrate_temp = substrate_temp
        self.rh_humidity = rh_humidity
        self.co2 = co2
        self.day_hours = day_hours
        self.harvest = harvest
        self.if_bagged = if_bagged

    def __repr__(self):
        return (
            f"Log(log_id={self.log_id}, batch_id={self.batch_id}, days_after_plant={self.days_after_plant}, "
            f"date={self.date}, hour='{self.hour}', air_temp={self.air_temp}, substrate_temp={self.substrate_temp}, "
            f"rh_humidity={self.rh_humidity}, co2={self.co2}, day_hours={self.day_hours}, "
            f"harvest='{self.harvest}', if_bagged={self.if_bagged})"
        )




def create_objects_from_df(iteration_table, log_table):
    """
    Reads an Excel file with two sheets to create lists of Batch and Log objects.

    :param file_path: Path to the Excel file.
    :return: Tuple containing a list of Batch objects and a list of Log objects.
    """

    # Create lists to store Batch and Log objects
    batches = []
    logs = []

    # Map Mahzor_id to Batch ID
    mahzor_to_batch_id = {}

    # Process iteration_table to create Batch objects
    if not iteration_table.empty:
        for _, row in iteration_table.iterrows():
            try:
                # Keep the date as is if it's already in datetime format
                start_date = row.get("Start_date")
                if start_date is not None and not pd.isna(start_date) and not isinstance(start_date, datetime):
                    try:
                        start_date = datetime.strptime(str(start_date), "%d/%m/%Y")
                    except ValueError:
                        try:
                            start_date = datetime.strptime(str(start_date), "%Y-%m-%d")
                        except ValueError:
                            print(f"⚠️ Unable to parse start_date: {start_date}")
                            start_date = None
                elif start_date is not None and pd.isna(start_date):
                    start_date = None

                batch = Batch(
                    mushroom_type=row.get("mushroom_type"),
                    iteration_id=row.get("Iteration_ID"),
                    start_date=start_date,
                    room_number=row.get("Room_number"),
                    substrate=row.get("Substrate")
                )
                batches.append(batch)
                
                # Only map if MAHZOR_ID exists and is not None
                mahzor_id = row.get("MAHZOR_ID")
                if mahzor_id is not None and not pd.isna(mahzor_id):
                    mahzor_to_batch_id[mahzor_id] = batch.batch_id
            except Exception as e:
                print(f"⚠️ Error processing batch row: {str(e)}")
                continue
    else:
        print("⚠️ Empty iteration_table, no batches to process")

    # Process log_table to create Log objects
    if not log_table.empty:
        for _, row in log_table.iterrows():
            try:
                # Match the batch_id using the Mahzor_id from the log
                mahzor_id = row.get("Mahzor_id")
                batch_id = mahzor_to_batch_id.get(mahzor_id) if mahzor_id is not None else None

                # Keep the date as is if it's already in datetime format
                log_date = row.get("Date")
                if log_date is not None and not pd.isna(log_date) and not isinstance(log_date, datetime):
                    try:
                        log_date = datetime.strptime(str(log_date), "%d/%m/%Y")
                    except ValueError:
                        try:
                            log_date = datetime.strptime(str(log_date), "%Y-%m-%d")
                        except ValueError:
                            print(f"⚠️ Unable to parse log_date: {log_date}")
                            log_date = None
                elif log_date is not None and pd.isna(log_date):
                    log_date = None

                log = Log(
                    batch_id=batch_id,
                    days_after_plant=row.get("Days_after_plant"),
                    date=log_date,
                    hour=row.get("Hour"),
                    air_temp=row.get("AIR_temp"),
                    substrate_temp=row.get("Substrate_temp"),
                    rh_humidity=row.get("RH_Humadity"),
                    co2=row.get("CO2"),
                    day_hours=row.get("day_hours"),
                    harvest=row.get("Katif"),
                    if_bagged=bool(row.get("if_bagged")) if row.get("if_bagged") is not None else None
                )
                logs.append(log)
            except Exception as e:
                print(f"⚠️ Error processing log row: {str(e)}")
                continue
    else:
        print("⚠️ Empty log_table, no logs to process")

    return batches, logs


def convert_to_datetime(value):
    """ Converts timestamp (milliseconds) or date string to datetime object """
    if isinstance(value, int):  # Check if it's a timestamp
        return datetime.utcfromtimestamp(value / 1000)  # Convert from ms to seconds
    elif isinstance(value, str):  # Check if it's a date string
        try:
            return datetime.strptime(value, "%d/%m/%Y")
        except ValueError:
            return None  # Handle invalid date formats
    return None  # Handle None values

def run_example():
    try:
        ref_batches = db.reference("Batches")
        batches_data = ref_batches.get()

        ref_logs = db.reference("Logs")
        logs_data = ref_logs.get()

        print("🔥 Raw Batches Data:", batches_data)
        print("🔥 Raw Logs Data:", logs_data)

        # Check if the data is a string and convert it
        if isinstance(batches_data, str):
            try:
                batches_data = json.loads(batches_data)  # Convert JSON string to Python object
            except json.JSONDecodeError:
                print("🚨 Failed to decode Batches JSON")
                batches_data = []  # Fallback to empty list

        if isinstance(logs_data, str):
            try:
                logs_data = json.loads(logs_data)
            except json.JSONDecodeError:
                print("🚨 Failed to decode Logs JSON")
                logs_data = []

        print("✅ Parsed Batches Data:", batches_data)
        print("✅ Parsed Logs Data:", logs_data)

        # Handle None or empty data
        if not batches_data:
            print("⚠️ No batches data found in Firebase")
            batches_data = []
        if not logs_data:
            print("⚠️ No logs data found in Firebase")
            logs_data = []

        # Ensure the data is in list format
        if isinstance(batches_data, dict):
            batches_data = list(batches_data.values())

        if isinstance(logs_data, dict):
            logs_data = list(logs_data.values())

        # Create DataFrames with error handling
        df_batches = pd.DataFrame(batches_data) if batches_data else pd.DataFrame()
        df_logs = pd.DataFrame(logs_data) if logs_data else pd.DataFrame()

        # Handle Start_date column with error checking
        if not df_batches.empty and "Start_date" in df_batches.columns:
            df_batches["Start_date"] = df_batches["Start_date"].apply(convert_to_datetime)
        elif not df_batches.empty:
            print("⚠️ No 'Start_date' column found in batches data. Available columns:", df_batches.columns.tolist())
            # Add a default Start_date column if missing
            df_batches["Start_date"] = None

        # Handle Date column with error checking
        if not df_logs.empty and "Date" in df_logs.columns:
            df_logs["Date"] = df_logs["Date"].apply(convert_to_datetime)
        elif not df_logs.empty:
            print("⚠️ No 'Date' column found in logs data. Available columns:", df_logs.columns.tolist())
            # Add a default Date column if missing
            df_logs["Date"] = None

        # Convert DataFrames to objects
        batch_list, log_list = create_objects_from_df(df_batches, df_logs)

        return batch_list, log_list

    except Exception as e:
        print(f"🚨 Error in run_example: {str(e)}")
        # Return empty lists as fallback
        return [], []