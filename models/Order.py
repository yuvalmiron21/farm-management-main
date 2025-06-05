class Order:
    def __init__(self, order_id, customer_id, order_date, total_amount, status):
        """
        Order model representing an order placed by a customer.
        """
        self.order_id = order_id
        self.customer_id = customer_id  # Link to Customer
        self.order_date = order_date
        self.total_amount = total_amount
        self.status = status  # e.g., Pending, Shipped, Delivered

    def to_dict(self):
        """
        Convert the order object to a dictionary for saving to JSON.
        """
        return {
            "OrderID": self.order_id,
            "CustomerID": self.customer_id,
            "OrderDate": self.order_date,
            "TotalAmount": self.total_amount,
            "Status": self.status
        }

    @staticmethod
    def from_dict(data):
        """
        Create an order object from a dictionary.
        """
        return Order(
            order_id=data["OrderID"],
            customer_id=data["CustomerID"],
            order_date=data["OrderDate"],
            total_amount=data["TotalAmount"],
            status=data["Status"]
        )
def get_customer(self, customers):
    """
    Return the customer object linked to this order.
    """
    return next((customer for customer in customers if customer.customer_id == self.customer_id), None)
