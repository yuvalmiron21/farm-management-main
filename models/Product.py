class Product:
    def __init__(self, product_id, name, description, price, stock_quantity):
        """
        Product model representing a product in the system.
        """
        self.product_id = product_id
        self.name = name
        self.description = description
        self.price = price
        self.stock_quantity = stock_quantity

    def to_dict(self):
        """
        Convert the product object to a dictionary for saving to JSON.
        """
        return {
            "ProductID": self.product_id,
            "Name": self.name,
            "Description": self.description,
            "Price": self.price,
            "StockQuantity": self.stock_quantity
        }

    @staticmethod
    def from_dict(data):
        """
        Create a product object from a dictionary.
        """
        return Product(
            product_id=data["ProductID"],
            name=data["Name"],
            description=data["Description"],
            price=data["Price"],
            stock_quantity=data["StockQuantity"]
        )
