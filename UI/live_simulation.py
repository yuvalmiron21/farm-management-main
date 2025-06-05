import random
from datetime import datetime, timedelta
from firebase_admin import db
import time
import threading
from PyQt5.QtCore import QObject, pyqtSignal
import uuid

class MushroomSimulator(QObject):
    update_signal = pyqtSignal(str, dict)  # Signal for UI updates

    def __init__(self):
        super().__init__()
        self.running = False
        self.simulation_thread = None
        self.growth_stages = {
            "Spawn Run": {
                "duration": (10, 14),  # days
                "temp_range": (22, 24),
                "humidity_range": (85, 90),
                "next_stage": "Pinning"
            },
            "Pinning": {
                "duration": (5, 7),
                "temp_range": (18, 20),
                "humidity_range": (90, 95),
                "next_stage": "Fruiting"
            },
            "Fruiting": {
                "duration": (7, 10),
                "temp_range": (18, 22),
                "humidity_range": (85, 90),
                "next_stage": "Harvesting"
            },
            "Harvesting": {
                "duration": (3, 5),
                "temp_range": (18, 20),
                "humidity_range": (80, 85),
                "next_stage": "Empty"
            }
        }

    def start_simulation(self):
        """Start the live simulation"""
        if not self.running:
            self.running = True
            self.simulation_thread = threading.Thread(target=self._simulation_loop)
            self.simulation_thread.daemon = True
            self.simulation_thread.start()

    def stop_simulation(self):
        """Stop the live simulation"""
        self.running = False
        if self.simulation_thread:
            self.simulation_thread.join()

    def _simulation_loop(self):
        """Main simulation loop"""
        while self.running:
            try:
                self._update_growing_beds()
                self._update_batches()
                self._create_logs()
                time.sleep(60)  # Update every minute
            except Exception as e:
                print(f"Error in simulation loop: {str(e)}")
                time.sleep(5)

    def _update_growing_beds(self):
        """Update growing beds status and conditions"""
        beds_ref = db.reference('GrowingBed')
        beds_data = beds_ref.get()
        
        if not beds_data:
            return
            
        # Convert to dict if it's a list
        if isinstance(beds_data, list):
            beds = {str(i): bed for i, bed in enumerate(beds_data)}
        else:
            beds = beds_data
        
        for bed_id, bed in beds.items():
            if bed.get('CurrentGrowthStage') in self.growth_stages:
                stage_info = self.growth_stages[bed['CurrentGrowthStage']]
                
                # Update temperature and humidity with small random variations
                current_temp = bed.get('Temperature', 20)
                current_humidity = bed.get('Humidity', 85)
                
                new_temp = current_temp + random.uniform(-0.2, 0.2)
                new_humidity = current_humidity + random.uniform(-0.5, 0.5)
                
                # Keep within ranges
                new_temp = max(min(new_temp, stage_info['temp_range'][1]), stage_info['temp_range'][0])
                new_humidity = max(min(new_humidity, stage_info['humidity_range'][1]), stage_info['humidity_range'][0])
                
                # Update bed data
                bed['Temperature'] = round(new_temp, 1)
                bed['Humidity'] = round(new_humidity, 1)
                
                # Check if it's time to move to next stage
                start_date = datetime.strptime(bed.get('StartDate', datetime.now().strftime('%Y-%m-%d')), '%Y-%m-%d')
                days_in_stage = (datetime.now() - start_date).days
                min_duration, max_duration = stage_info['duration']
                
                if days_in_stage >= min_duration:
                    if random.random() < (days_in_stage - min_duration) / (max_duration - min_duration):
                        bed['CurrentGrowthStage'] = stage_info['next_stage']
                        bed['StartDate'] = datetime.now().strftime('%Y-%m-%d')
                        if stage_info['next_stage'] == 'Empty':
                            bed['Status'] = 'Inactive'
                        else:
                            bed['Status'] = 'Active'
                
                beds_ref.child(bed_id).update(bed)
                self.update_signal.emit('GrowingBed', bed)

    def _update_batches(self):
        """Update batch information"""
        batches_ref = db.reference('Batches')
        batches_data = batches_ref.get()
        
        if not batches_data:
            return
            
        # Convert to dict if it's a list
        if isinstance(batches_data, list):
            batches = {str(i): batch for i, batch in enumerate(batches_data)}
        else:
            batches = batches_data
        
        for batch_id, batch in batches.items():
            if batch.get('Status') == 'Growing':
                # Simulate yield growth
                current_yield = batch.get('Yield', 0)
                if current_yield < 20:  # Maximum yield
                    growth_rate = random.uniform(0.1, 0.3)
                    new_yield = min(current_yield + growth_rate, 20)
                    batch['Yield'] = round(new_yield, 2)
                    
                    # Random chance of failure
                    if random.random() < 0.01:  # 1% chance of failure
                        batch['Status'] = 'Failed'
                        batch['Notes'] = f"Batch failed due to {random.choice(['contamination', 'temperature fluctuation', 'humidity issues'])}"
                    
                    batches_ref.child(batch_id).update(batch)
                    self.update_signal.emit('Batches', batch)

    def _create_logs(self):
        """Create new log entries"""
        logs_ref = db.reference('Logs')
        batches_ref = db.reference('Batches')
        batches_data = batches_ref.get()
        
        if not batches_data:
            return
            
        # Convert to dict if it's a list
        if isinstance(batches_data, list):
            batches = {str(i): batch for i, batch in enumerate(batches_data)}
        else:
            batches = batches_data
        
        active_batches = {bid: batch for bid, batch in batches.items() if batch.get('Status') == 'Growing'}
        
        if active_batches:
            # Create new log entry
            batch_id = random.choice(list(active_batches.keys()))
            log_types = ["Temperature", "Humidity", "Watering", "Ventilation", "Growth"]
            
            log = {
                "LogID": str(uuid.uuid4()),
                "BatchID": batch_id,
                "LogDate": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "LogType": random.choice(log_types),
                "Value": round(random.uniform(18, 28), 1) if random.random() > 0.5 else "",
                "Notes": f"Automated log entry for {batch_id[:8]}"
            }
            
            logs_ref.push(log)
            self.update_signal.emit('Logs', log)

def start_live_simulation():
    """Start the live simulation"""
    simulator = MushroomSimulator()
    simulator.start_simulation()
    return simulator

if __name__ == "__main__":
    simulator = start_live_simulation()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        simulator.stop_simulation() 