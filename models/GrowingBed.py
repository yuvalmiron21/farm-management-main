class GrowingBed:
    def __init__(self, bed_id, name, location, size, status, crop_type=None, planting_date=None, harvest_date=None):
        """
        GrowingBed model representing a growing bed in the farm.
        """
        self.bed_id = bed_id
        self.name = name
        self.location = location
        self.size = size  # in square meters
        self.status = status  # e.g., Available, Occupied, Maintenance
        self.crop_type = crop_type
        self.planting_date = planting_date
        self.harvest_date = harvest_date

    def to_dict(self):
        """
        Convert the growing bed object to a dictionary for saving to JSON.
        """
        return {
            "ID": self.bed_id,
            "Name": self.name,
            "Location": self.location,
            "Size": self.size,
            "Status": self.status,
            "CropType": self.crop_type,
            "PlantingDate": self.planting_date,
            "HarvestDate": self.harvest_date
        }

    @staticmethod
    def from_dict(data):
        """
        Create a growing bed object from a dictionary.
        """
        return GrowingBed(
            bed_id=data["ID"],
            name=data["Name"],
            location=data["Location"],
            size=data["Size"],
            status=data["Status"],
            crop_type=data.get("CropType"),
            planting_date=data.get("PlantingDate"),
            harvest_date=data.get("HarvestDate")
        ) 