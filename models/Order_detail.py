class OrderDetail:
    def __init__(self, order_detail_id, order_id, product_id, quantity, unit_price):
        """
        OrderDetail model representing a product within an order.
        """
        self.order_detail_id = order_detail_id
        self.order_id = order_id  # Link to Order
        self.product_id = product_id  # Link to Product
        self.quantity = quantity
        self.unit_price = unit_price

    def to_dict(self):
        """
        Convert the order detail object to a dictionary for saving to JSON.
        """
        return {
            "OrderDetailID": self.order_detail_id,
            "OrderID": self.order_id,
            "ProductID": self.product_id,
            "Quantity": self.quantity,
            "UnitPrice": self.unit_price
        }

    @staticmethod
    def from_dict(data):
        """
        Create an order detail object from a dictionary.
        """
        return OrderDetail(
            order_detail_id=data["OrderDetailID"],
            order_id=data["OrderID"],
            product_id=data["ProductID"],
            quantity=data["Quantity"],
            unit_price=data["UnitPrice"]
        )

def get_order(self, orders):
    """
    Return the order object linked to this order detail.
    """
    return next((order for order in orders if order.order_id == self.order_id), None)

def get_product(self, products):
    """
    Return the product object linked to this order detail.
    """
    return next((product for product in products if product.product_id == self.product_id), None)
