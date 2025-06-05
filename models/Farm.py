class Farm:
    def __init__(self, farm_id, name, location, capacity):
        self.farm_id = farm_id
        self.name = name
        self.location = location
        self.capacity = capacity

    def to_dict(self):
        return {
            "FarmID": self.farm_id,
            "Name": self.name,
            "Location": self.location,
            "Capacity": self.capacity
        }

    @staticmethod
    def from_dict(data):
        return Farm(
            farm_id=data["FarmID"],
            name=data["Name"],
            location=data["Location"],
            capacity=data["Capacity"]
        )
