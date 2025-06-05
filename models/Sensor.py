class Sensor:
    def __init__(self, sensor_id, bed_id, type, value, last_updated):
        """
        Sensor model representing a sensor attached to a growing bed.
        """
        self.sensor_id = sensor_id
        self.bed_id = bed_id  # Link to GrowingBed
        self.type = type  # Type of the sensor (e.g., Temperature, Humidity, CO2)
        self.value = value  # Current value of the sensor
        self.last_updated = last_updated  # Timestamp of the last update

    def to_dict(self):
        """
        Convert the sensor object to a dictionary for saving to JSON.
        """
        return {
            "SensorID": self.sensor_id,
            "BedID": self.bed_id,
            "Type": self.type,
            "Value": self.value,
            "LastUpdated": self.last_updated
        }

    @staticmethod
    def from_dict(data):
        """
        Create a sensor object from a dictionary.
        """
        return Sensor(
            sensor_id=data["SensorID"],
            bed_id=data["BedID"],
            type=data["Type"],
            value=data["Value"],
            last_updated=data["LastUpdated"]
        )

    def get_growing_bed(self, growing_beds):
        """
        Return the growing bed object linked to this sensor.
        """
        return next((bed for bed in growing_beds if bed.bed_id == self.bed_id), None)
