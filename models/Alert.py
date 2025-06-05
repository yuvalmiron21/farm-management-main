class Alert:
    def __init__(self, alert_id, bed_id, message, alert_date, severity):
        """
        Alert model representing a system alert.
        """
        self.alert_id = alert_id
        self.bed_id = bed_id  # Link to GrowingBed
        self.message = message
        self.alert_date = alert_date
        self.severity = severity  # e.g., Low, Medium, High

    def to_dict(self):
        """
        Convert the alert object to a dictionary for saving to JSON.
        """
        return {
            "AlertID": self.alert_id,
            "BedID": self.bed_id,
            "Message": self.message,
            "AlertDate": self.alert_date,
            "Severity": self.severity
        }

    @staticmethod
    def from_dict(data):
        """
        Create an alert object from a dictionary.
        """
        return Alert(
            alert_id=data["AlertID"],
            bed_id=data["BedID"],
            message=data["Message"],
            alert_date=data["AlertDate"],
            severity=data["Severity"]
        )

def get_growing_bed(self, growing_beds):
    """
    Return the growing bed object linked to this alert.
    """
    return next((bed for bed in growing_beds if bed.bed_id == self.bed_id), None)
