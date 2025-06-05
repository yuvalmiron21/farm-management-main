class User:
    def __init__(self, user_id, name, email, role):
        """
        User model representing a user in the system.
        """
        self.user_id = user_id
        self.name = name
        self.email = email
        self.role = role  # e.g., Admin, Manager, Worker

    def to_dict(self):
        """
        Convert the user object to a dictionary for saving to JSON.
        """
        return {
            "UserID": self.user_id,
            "Name": self.name,
            "Email": self.email,
            "Role": self.role
        }

    @staticmethod
    def from_dict(data):
        """
        Create a user object from a dictionary.
        """
        return User(
            user_id=data["UserID"],
            name=data["Name"],
            email=data["Email"],
            role=data["Role"]
        )
