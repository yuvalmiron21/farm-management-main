import pandas as pd
from datetime import datetime
from typing import List, Tuple
from models.Log import Batch, Log, run_example
import numpy as np
import logging

logging.getLogger('pandas').setLevel(logging.ERROR)
logging.getLogger('numpy').setLevel(logging.ERROR)

# Global cache for batches and logs
_cached_data = None
_last_update_time = None

class AnalyticsBackend:
    def __init__(self):
        global _cached_data, _last_update_time
        current_time = datetime.now()
        
        # Only reload data if cache is empty or older than 5 minutes
        if (_cached_data is None or 
            _last_update_time is None or 
            (current_time - _last_update_time).total_seconds() > 300):
            try:
                _cached_data = run_example()
                _last_update_time = current_time
            except Exception as e:
                print(f"🚨 Error loading data in AnalyticsBackend: {str(e)}")
                _cached_data = ([], [])  # Fallback to empty lists
                _last_update_time = current_time
        
        # Handle empty or None data
        if _cached_data is None or len(_cached_data) != 2:
            print("⚠️ Invalid cached data structure, using empty lists")
            all_batches, self.logs = [], []
        else:
            all_batches, self.logs = _cached_data
        
        # Ensure we have lists (not None)
        if all_batches is None:
            all_batches = []
        if self.logs is None:
            self.logs = []
        
        # Filter batches to only include those with logs
        if self.logs:
            batch_ids_with_logs = set(log.batch_id for log in self.logs if log.batch_id is not None)
            self.batches = [batch for batch in all_batches if batch.batch_id in batch_ids_with_logs]
        else:
            self.batches = all_batches  # Keep all batches if no logs
        
        print(f"AnalyticsBackend initialized with {len(self.batches)} batches and {len(self.logs)} logs")

    def calculate_yield_percentage(self, batch_id: str = "All Batches") -> float:
        """
        Calculate the yield percentage for a specific batch or all batches.
        """
        total_harvest = 0
        total_substrate = 0

        if batch_id == "All Batches":
            # Calculate for all batches
            for batch in self.batches:  # Now only includes batches with logs
                batch_harvest = sum(
                    float(log.harvest) for log in self.logs
                    if log.batch_id == batch.batch_id and log.harvest is not None and not pd.isna(log.harvest)
                )
                total_harvest += batch_harvest
                total_substrate += batch.substrate
        else:
            # Calculate for a specific batch
            batch_id = int(batch_id)
            batch = next((batch for batch in self.batches if batch.batch_id == batch_id), None)
            if batch:  # This batch is guaranteed to have logs
                total_harvest = sum(
                    float(log.harvest) for log in self.logs
                    if log.batch_id == batch_id and log.harvest is not None and not pd.isna(log.harvest)
                )
                total_substrate = batch.substrate

        if total_substrate == 0:
            return 0  # Avoid division by zero

        return (total_harvest / total_substrate) * 100

    def generate_statistics(self) -> str:
        total_batches = len(self.batches)  # Now only counts batches with logs
        total_logs = len(self.logs)
        
        # Handle empty logs gracefully
        if not self.logs:
            return (f"Total Active Batches: {total_batches}\n"
                    f"Total Logs: {total_logs}\n"
                    f"No data available for statistics")
        
        # Calculate averages with error handling
        try:
            air_temps = [log.air_temp for log in self.logs if log.air_temp is not None and not pd.isna(log.air_temp)]
            avg_air_temp = pd.Series(air_temps).mean() if air_temps else 0
            
            humidities = [log.rh_humidity for log in self.logs if log.rh_humidity is not None and not pd.isna(log.rh_humidity)]
            avg_rh_humidity = pd.Series(humidities).mean() if humidities else 0
            
            co2_vals = [log.co2 for log in self.logs if log.co2 is not None and not pd.isna(log.co2)]
            avg_co2 = pd.Series(co2_vals).mean() if co2_vals else 0
        except Exception as e:
            print(f"⚠️ Error calculating statistics: {str(e)}")
            avg_air_temp = avg_rh_humidity = avg_co2 = 0

        return (f"Total Active Batches: {total_batches}\n"
                f"Total Logs: {total_logs}\n"
                f"Average Air Temp: {avg_air_temp:.2f}°C\n"
                f"Average Humidity: {avg_rh_humidity:.2f}%\n"
                f"Average CO₂: {avg_co2:.2f} ppm")

    def get_earliest_date(self) -> datetime:
        try:
            valid_dates = [log.date for log in self.logs if log.date is not None and not pd.isna(log.date)]
            return min(valid_dates) if valid_dates else datetime.today()
        except Exception as e:
            print(f"⚠️ Error getting earliest date: {str(e)}")
            return datetime.today()

    def get_latest_date(self) -> datetime:
        try:
            valid_dates = [log.date for log in self.logs if log.date is not None and not pd.isna(log.date)]
            return max(valid_dates) if valid_dates else datetime.today()
        except Exception as e:
            print(f"⚠️ Error getting latest date: {str(e)}")
            return datetime.today()

    def get_mushroom_types(self) -> List[str]:
        try:
            types = [str(batch.mushroom_type) for batch in self.batches if batch.mushroom_type is not None and batch.mushroom_type != ""]
            return list(set(types)) if types else ["No Data"]
        except Exception as e:
            print(f"⚠️ Error getting mushroom types: {str(e)}")
            return ["No Data"]

    def get_batch_ids(self) -> List[int]:
        return sorted([batch.batch_id for batch in self.batches])  # Now only returns IDs of batches with logs

    def get_air_temp_data(self, batch_id: str, mushroom_type: str, start_date: datetime, end_date: datetime) -> List[
        Tuple[int, float]]:
        try:
            filtered_logs = [
                log for log in self.logs
                if (batch_id == "All Batches" or any(
                    batch.batch_id == int(batch_id) for batch in self.batches if batch.batch_id == log.batch_id))
                   and (mushroom_type == "All Types" or any(
                    batch.mushroom_type == mushroom_type for batch in self.batches if batch.batch_id == log.batch_id))
                   and (start_date is None or (log.date is not None and pd.Timestamp(log.date) >= pd.Timestamp(start_date)))
                   and (end_date is None or (log.date is not None and pd.Timestamp(log.date) <= pd.Timestamp(end_date)))
                   and log.air_temp is not None
                   and log.date is not None
            ]
            return sorted([(int(log.date.timestamp()), log.air_temp) for log in filtered_logs])
        except Exception as e:
            print(f"⚠️ Error getting air temp data: {str(e)}")
            return []

    def get_humidity_data(self, batch_id: str, mushroom_type: str, start_date: datetime, end_date: datetime) -> List[
        Tuple[int, float]]:
        try:
            filtered_logs = [
                log for log in self.logs
                if (batch_id == "All Batches" or any(
                    batch.batch_id == int(batch_id) for batch in self.batches if batch.batch_id == log.batch_id))
                   and (mushroom_type == "All Types" or any(
                    batch.mushroom_type == mushroom_type for batch in self.batches if batch.batch_id == log.batch_id))
                   and (start_date is None or (log.date is not None and pd.Timestamp(log.date) >= pd.Timestamp(start_date)))
                   and (end_date is None or (log.date is not None and pd.Timestamp(log.date) <= pd.Timestamp(end_date)))
                   and log.rh_humidity is not None
                   and log.date is not None
            ]
            return sorted([(int(log.date.timestamp()), log.rh_humidity) for log in filtered_logs])
        except Exception as e:
            print(f"⚠️ Error getting humidity data: {str(e)}")
            return []

    def get_co2_data(self, batch_id: str, mushroom_type: str, start_date: datetime, end_date: datetime) -> List[
        Tuple[int, float]]:
        try:
            filtered_logs = [
                log for log in self.logs
                if (batch_id == "All Batches" or any(
                    batch.batch_id == int(batch_id) for batch in self.batches if batch.batch_id == log.batch_id))
                   and (mushroom_type == "All Types" or any(
                    batch.mushroom_type == mushroom_type for batch in self.batches if batch.batch_id == log.batch_id))
                   and (start_date is None or (log.date is not None and pd.Timestamp(log.date) >= pd.Timestamp(start_date)))
                   and (end_date is None or (log.date is not None and pd.Timestamp(log.date) <= pd.Timestamp(end_date)))
                   and log.co2 is not None and not np.isnan(log.co2)
                   and log.date is not None
            ]

            timestamp_dict = {}
            for log in filtered_logs:
                ts = int(log.date.timestamp())
                if ts in timestamp_dict:
                    timestamp_dict[ts].append(log.co2)
                else:
                    timestamp_dict[ts] = [log.co2]

            cleaned_data = [(ts, np.mean(values)) for ts, values in timestamp_dict.items()]
            return sorted(cleaned_data)
        except Exception as e:
            print(f"⚠️ Error getting CO2 data: {str(e)}")
            return []

    def get_substrate_temp_data(self, batch_id: str, mushroom_type: str, start_date: datetime, end_date: datetime) -> List[Tuple[int, float]]:
        try:
            filtered_logs = [
                log for log in self.logs
                if (batch_id == "All Batches" or any(
                    batch.batch_id == int(batch_id) for batch in self.batches if batch.batch_id == log.batch_id))
                   and (mushroom_type == "All Types" or any(
                    batch.mushroom_type == mushroom_type for batch in self.batches if batch.batch_id == log.batch_id))
                   and (start_date is None or (log.date is not None and pd.Timestamp(log.date) >= pd.Timestamp(start_date)))
                   and (end_date is None or (log.date is not None and pd.Timestamp(log.date) <= pd.Timestamp(end_date)))
                   and log.substrate_temp is not None
                   and log.date is not None
            ]
            return sorted([(int(log.date.timestamp()), log.substrate_temp) for log in filtered_logs])
        except Exception as e:
            print(f"⚠️ Error getting substrate temp data: {str(e)}")
            return []

