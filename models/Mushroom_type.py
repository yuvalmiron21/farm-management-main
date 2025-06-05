class MushroomType:
    def __init__(self, mushroom_type_id, name, temp_min, temp_max, humidity_min, humidity_max, co2_min, co2_max, growth_duration, yield_per_cycle):
        self.mushroom_type_id = mushroom_type_id
        self.name = name
        self.temp_min = temp_min
        self.temp_max = temp_max
        self.humidity_min = humidity_min
        self.humidity_max = humidity_max
        self.co2_min = co2_min
        self.co2_max = co2_max
        self.growth_duration = growth_duration
        self.yield_per_cycle = yield_per_cycle

    def to_dict(self):
        return {
            "MushroomTypeID": self.mushroom_type_id,
            "Name": self.name,
            "OptimalTemperatureMin": self.temp_min,
            "OptimalTemperatureMax": self.temp_max,
            "OptimalHumidityMin": self.humidity_min,
            "OptimalHumidityMax": self.humidity_max,
            "OptimalCO2LevelMin": self.co2_min,
            "OptimalCO2LevelMax": self.co2_max,
            "GrowthDuration": self.growth_duration,
            "YieldPerCycle": self.yield_per_cycle
        }

    @staticmethod
    def from_dict(data):
        return MushroomType(
            mushroom_type_id=data["MushroomTypeID"],
            name=data["Name"],
            temp_min=data["OptimalTemperatureMin"],
            temp_max=data["OptimalTemperatureMax"],
            humidity_min=data["OptimalHumidityMin"],
            humidity_max=data["OptimalHumidityMax"],
            co2_min=data["OptimalCO2LevelMin"],
            co2_max=data["OptimalCO2LevelMax"],
            growth_duration=data["GrowthDuration"],
            yield_per_cycle=data["YieldPerCycle"]
        )
