class GrowingBed:
    def __init__(self, bed_id, farm_id, mushroom_type_id, managed_by_user_id, current_growth_stage, temperature, humidity, co2_level, last_updated):
        self.bed_id = bed_id
        self.farm_id = farm_id
        self.mushroom_type_id = mushroom_type_id
        self.managed_by_user_id = managed_by_user_id
        self.current_growth_stage = current_growth_stage
        self.temperature = temperature
        self.humidity = humidity
        self.co2_level = co2_level
        self.last_updated = last_updated

    def to_dict(self):
        return {
            "BedID": self.bed_id,
            "FarmID": self.farm_id,
            "MushroomTypeID": self.mushroom_type_id,
            "ManagedByUserID": self.managed_by_user_id,
            "CurrentGrowthStage": self.current_growth_stage,
            "Temperature": self.temperature,
            "Humidity": self.humidity,
            "CO2Level": self.co2_level,
            "LastUpdated": self.last_updated
        }

    @staticmethod
    def from_dict(data):
        return GrowingBed(
            bed_id=data["BedID"],
            farm_id=data["FarmID"],
            mushroom_type_id=data["MushroomTypeID"],
            managed_by_user_id=data["ManagedByUserID"],
            current_growth_stage=data["CurrentGrowthStage"],
            temperature=data["Temperature"],
            humidity=data["Humidity"],
            co2_level=data["CO2Level"],
            last_updated=data["LastUpdated"]
        )
def get_farm(self, farms):
    """
    Return the farm object linked to this growing bed.
    """
    return next((farm for farm in farms if farm.farm_id == self.farm_id), None)

def get_mushroom_type(self, mushroom_types):
    """
    Return the mushroom type object linked to this growing bed.
    """
    return next((mushroom for mushroom in mushroom_types if mushroom.mushroom_type_id == self.mushroom_type_id), None)

def get_manager(self, users):
    """
    Return the user object managing this growing bed.
    """
    return next((user for user in users if user.user_id == self.managed_by_user_id), None)
