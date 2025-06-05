class Customer:
    def __init__(self, customer_id, name, email, phone, address):
        """
        Customer model representing a customer in the system.
        """
        self.customer_id = customer_id
        self.name = name
        self.email = email
        self.phone = phone
        self.address = address

    def to_dict(self):
        """
        Convert the customer object to a dictionary for saving to JSON.
        """
        return {
            "ID": self.customer_id,
            "Name": self.name,
            "Email": self.email,
            "Phone": self.phone,
            "Address": self.address
        }

    @staticmethod
    def from_dict(data):
        """
        Create a customer object from a dictionary.
        """
        return Customer(
            customer_id=data["ID"],
            name=data["Name"],
            email=data["Email"],
            phone=data["Phone"],
            address=data["Address"]
        )
