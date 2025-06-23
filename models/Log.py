import pandas as pd
from datetime import datetime, timedelta
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
        substrate: Optional[float] = None,
        batch_id: Optional[int] = None  # Add batch_id as optional parameter
    ):
        if batch_id is not None:
            self.batch_id = int(batch_id) # Ensure it's an int
            if self.batch_id >= Batch._batch_id_counter:
                Batch._batch_id_counter = self.batch_id + 1
        else:
            self.batch_id = Batch._batch_id_counter
            Batch._batch_id_counter += 1
            
        self.mushroom_type = mushroom_type
        self.iteration_id = iteration_id
        self.start_date = start_date
        self.room_number = room_number
        self.substrate = substrate

    def to_dict(self):
        return {
            "mushroom_type": self.mushroom_type,
            "iteration_id": self.iteration_id,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "room_number": self.room_number,
            "substrate": self.substrate,
            "batch_id": self.batch_id
        }

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

    def to_dict(self):
        return {
            "log_id": self.log_id,
            "batch_id": self.batch_id,
            "days_after_plant": self.days_after_plant,
            "date": self.date.isoformat() if self.date else None,
            "hour": self.hour,
            "air_temp": self.air_temp,
            "substrate_temp": self.substrate_temp,
            "rh_humidity": self.rh_humidity,
            "co2": self.co2,
            "day_hours": self.day_hours,
            "harvest": self.harvest,
            "if_bagged": self.if_bagged
        }

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
    id_map = {}

    # Process iteration_table to create Batch objects
    if not iteration_table.empty:
        for _, row in iteration_table.iterrows():
            try:
                # Keep the date as is if it's already in datetime format
                start_date = row.get("Start_date") or row.get("start_date")
                if start_date is not None and not pd.isna(start_date) and not isinstance(start_date, datetime):
                    try:
                        start_date = datetime.strptime(str(start_date), "%d/%m/%Y")
                    except ValueError:
                        try:
                            start_date = datetime.strptime(str(start_date), "%Y-%m-%d %H:%M:%S")
                        except ValueError:
                             try:
                                start_date = datetime.strptime(str(start_date), "%Y-%m-%d")
                             except ValueError:
                                print(f"⚠️ Unable to parse start_date: {start_date}")
                                start_date = None

                elif start_date is not None and pd.isna(start_date):
                    start_date = None

                # Try to get batch_id directly from the data
                batch_id_val = row.get('batch_id') or row.get('BatchID')

                batch = Batch(
                    batch_id=batch_id_val,
                    mushroom_type=row.get("mushroom_type"),
                    iteration_id=row.get("Iteration_ID") or row.get("iteration_id"),
                    start_date=start_date,
                    room_number=row.get("Room_number") or row.get("room_number"),
                    substrate=row.get("Substrate") or row.get("substrate")
                )
                batches.append(batch)
                
                # Legacy support for MAHZOR_ID
                mahzor_id = row.get("MAHZOR_ID")
                if mahzor_id is not None and not pd.isna(mahzor_id):
                    id_map[mahzor_id] = batch.batch_id
                # New support for batch_id
                if batch_id_val is not None:
                     id_map[batch_id_val] = batch.batch_id

            except Exception as e:
                import traceback
                print(f"⚠️ Error processing batch row: {str(e)}")
                traceback.print_exc()
                continue
    else:
        print("⚠️ Empty iteration_table, no batches to process")

    # Process log_table to create Log objects
    if not log_table.empty:
        for _, row in log_table.iterrows():
            try:
                # Match the batch_id using Mahzor_id or direct batch_id
                log_batch_id_ref = row.get("batch_id") or row.get("BatchID") or row.get("Mahzor_id")
                batch_id = id_map.get(int(log_batch_id_ref)) if log_batch_id_ref is not None and pd.notna(log_batch_id_ref) else None

                # Keep the date as is if it's already in datetime format
                log_date = row.get("Date") or row.get("date")
                if log_date is not None and not pd.isna(log_date) and not isinstance(log_date, datetime):
                    try:
                        log_date = datetime.strptime(str(log_date), "%d/%m/%Y")
                    except ValueError:
                        try:
                            log_date = datetime.strptime(str(log_date), "%Y-%m-%d %H:%M:%S")
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
                    days_after_plant=row.get("Days_after_plant") or row.get("days_after_plant"),
                    date=log_date,
                    hour=row.get("Hour") or row.get("hour"),
                    air_temp=row.get("AIR_temp") or row.get("air_temp"),
                    substrate_temp=row.get("Substrate_temp") or row.get("substrate_temp"),
                    rh_humidity=row.get("RH_Humadity") or row.get("rh_humidity"),
                    co2=row.get("CO2") or row.get("co2"),
                    day_hours=row.get("day_hours"),
                    harvest=row.get("Katif") or row.get("harvest"),
                    if_bagged=bool(row.get("if_bagged")) if pd.notna(row.get("if_bagged")) else None
                )
                logs.append(log)
            except Exception as e:
                import traceback
                print(f"⚠️ Error processing log row: {str(e)}")
                traceback.print_exc()

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
        print("🔄 Loading data from Firebase...")
        
        # Initialize Firebase if not already initialized
        try:
            from firebase_admin import _apps, credentials, initialize_app
            if not _apps:
                import os
                BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                SERVICE_ACCOUNT_FILE = os.path.join(BASE_DIR, "db", "farm-management-FireBase_credentials.json")
                DATABASE_URL = "https://mush-farm-management-default-rtdb.firebaseio.com/"
                
                if os.path.exists(SERVICE_ACCOUNT_FILE):
                    cred = credentials.Certificate(SERVICE_ACCOUNT_FILE)
                    initialize_app(cred, {"databaseURL": DATABASE_URL})
                    print("✅ Firebase initialized successfully")
                else:
                    print(f"⚠️ Firebase credentials file not found at: {SERVICE_ACCOUNT_FILE}")
                    return [], []
            else:
                print("✅ Firebase already initialized")
        except Exception as e:
            print(f"🚨 Error initializing Firebase: {str(e)}")
            return [], []
        
        ref_batches = db.reference("Batches")
        batches_data = ref_batches.get()

        ref_logs = db.reference("Logs")
        logs_data = ref_logs.get()

        # If data exists, use it
        if batches_data and logs_data:
            print("✅ Found existing Batches and Logs data. Processing...")
            # Fallback to original method if GrowingBed is empty
            
            # Check if the data is a string and convert it
            if isinstance(batches_data, str):
                try:
                    batches_data = json.loads(batches_data)
                except json.JSONDecodeError:
                    print("🚨 Failed to decode Batches JSON")
                    batches_data = []

            if isinstance(logs_data, str):
                try:
                    logs_data = json.loads(logs_data)
                except json.JSONDecodeError:
                    print("🚨 Failed to decode Logs JSON")
                    logs_data = []
            
            if isinstance(batches_data, dict):
                batches_data = list(batches_data.values())

            if isinstance(logs_data, dict):
                logs_data = list(logs_data.values())

            df_batches = pd.DataFrame(batches_data)
            df_logs = pd.DataFrame(logs_data)

            if "Start_date" in df_batches.columns:
                df_batches["Start_date"] = pd.to_datetime(df_batches["Start_date"])
            if "Date" in df_logs.columns:
                df_logs["Date"] = pd.to_datetime(df_logs["Date"])

            batch_list, log_list = create_objects_from_df(df_batches, df_logs)
            print(f"👍 Processed {len(batch_list)} batches and {len(log_list)} logs from existing data.")
            return batch_list, log_list

        # If no data, migrate from GrowingBed
        print("🤔 No existing Batches/Logs data found. Migrating from GrowingBed...")
        ref_growing_beds = db.reference("GrowingBed")
        growing_beds_data = ref_growing_beds.get()
        
        print("🔥 Raw GrowingBed Data:", "Loaded" if growing_beds_data else "Empty")
        
        if not growing_beds_data or not isinstance(growing_beds_data, dict):
             print("⚠️ No GrowingBed data to migrate. Returning empty lists.")
             return [],[]

        print("Found GrowingBed data, converting to batches and logs format...")
        
        batches_list = []
        logs_list = []
        
        for bed_id, bed_data in growing_beds_data.items():
            try:
                batch = Batch(
                    mushroom_type=bed_data.get("MushroomType"),
                    iteration_id=int(''.join(filter(str.isdigit, bed_id))) if any(char.isdigit() for char in bed_id) else 0,
                    start_date=convert_to_datetime(bed_data.get("Start_date")),
                    room_number=int(''.join(filter(str.isdigit, bed_data.get("Location", "")))) if any(char.isdigit() for char in bed_data.get("Location", "")) else 0,
                    substrate=float(bed_data.get("Size", "0x0").split('x')[0]) * float(bed_data.get("Size", "0x0").split('x')[1]) if 'x' in bed_data.get("Size", "0x0") else 0
                )
                batches_list.append(batch)
                
                if bed_data.get("Temperature") is not None:
                    log = Log(
                        batch_id=batch.batch_id,
                        days_after_plant=0,
                        date=convert_to_datetime(bed_data.get("LastUpdated")) or datetime.now(),
                        hour=datetime.now().strftime("%H:%M"),
                        air_temp=float(bed_data.get("Temperature", 0)),
                        substrate_temp=float(bed_data.get("Temperature", 0)),
                        rh_humidity=float(bed_data.get("Humidity", 0)),
                        co2=float(bed_data.get("CO2Level", 0)),
                        day_hours=12,
                        harvest=0.0,
                        if_bagged=False
                    )
                    logs_list.append(log)
            except (ValueError, TypeError) as e:
                print(f"⚠️ Error processing growing bed {bed_id}: {str(e)}")
                continue
        
        print(f"✅ Converted {len(batches_list)} batches and {len(logs_list)} logs from GrowingBed data.")

        # Upload to Firebase
        if batches_list and logs_list:
            print("📤 Uploading migrated data to Firebase...")
            try:
                batches_to_upload = {f"batch_{b.batch_id}": b.to_dict() for b in batches_list}
                logs_to_upload = {f"log_{l.log_id}": l.to_dict() for l in logs_list}
                
                db.reference("Batches").set(batches_to_upload)
                db.reference("Logs").set(logs_to_upload)
                print("✅ Successfully uploaded Batches and Logs to Firebase.")
            except Exception as e:
                print(f"🚨 Failed to upload migrated data: {str(e)}")

        return batches_list, logs_list

    except Exception as e:
        print(f"🚨 Error in run_example: {str(e)}")
        import traceback
        traceback.print_exc()
        return [], []