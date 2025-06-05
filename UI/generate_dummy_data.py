import random
from datetime import datetime, timedelta
from firebase_admin import db, credentials, initialize_app
import names
import uuid
import os

# Initialize Firebase
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Current file location
PARENT_DIR = os.path.dirname(BASE_DIR)  # Parent directory
SERVICE_ACCOUNT_FILE = os.path.join(
    PARENT_DIR, "db", "farm-management-FireBase_credentials.json")
DATABASE_URL = "https://farm-management-86035-default-rtdb.europe-west1.firebasedatabase.app/"

# Check if the file exists
if not os.path.exists(SERVICE_ACCOUNT_FILE):
    raise FileNotFoundError(
        f"Could not find the Firebase credentials file at: {SERVICE_ACCOUNT_FILE}")

# Initialize Firebase
cred = credentials.Certificate(SERVICE_ACCOUNT_FILE)
initialize_app(cred, {"databaseURL": DATABASE_URL})

def get_real_names():
    first_names = [
        "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda", "William", "Elizabeth",
        "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica", "Thomas", "Sarah", "Charles", "Karen"
    ]
    last_names = [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
        "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin"
    ]
    return first_names, last_names

def generate_customers():
    num_customers = random.randint(2000, 5000)
    customers = {}
    first_names, last_names = get_real_names()
    for i in range(num_customers):
        customer_id = str(uuid.uuid4())
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        customers[customer_id] = {
            "ID": customer_id,
            "CustomerID": customer_id,
            "Name": name,
            "Email": f"customer{i}@example.com",
            "Phone": f"05{random.randint(10000000, 99999999)}",
            "Address": f"{random.randint(100, 999)} {random.choice(['Main St', 'Oak Ave', 'Pine Rd', 'Maple Blvd'])}, {random.choice(['Tel Aviv', 'Jerusalem', 'Haifa', 'Rishon LeZion'])}",
            "CreatedAt": (datetime.now() - timedelta(days=random.randint(1, 7*365))).strftime("%Y-%m-%d")
        }
    return customers

def generate_growing_beds():
    num_beds = random.randint(300, 800)
    beds = {}
    stages = ["Empty", "Spawn Run", "Pinning", "Fruiting", "Harvesting"]
    mushroom_types = ["Portobello", "Shiitake", "Oyster", "Button", "Lion's Mane"]
    for i in range(num_beds):
        bed_id = str(uuid.uuid4())
        current_stage = random.choice(stages)
        start_date = datetime.now() - timedelta(days=random.randint(1, 5*365))
        beds[bed_id] = {
            "ID": bed_id,
            "BedID": bed_id,
            "Name": f"Bed {i+1}",
            "Location": f"Section {random.choice(['A', 'B', 'C'])}-{random.randint(1, 10)}",
            "Size": f"{random.randint(2, 5)}x{random.randint(2, 5)}",
            "CurrentGrowthStage": current_stage,
            "MushroomType": random.choice(mushroom_types),
            "Start_date": start_date.strftime("%Y-%m-%d"),
            "ExpectedHarvestDate": (start_date + timedelta(days=random.randint(30, 60))).strftime("%Y-%m-%d"),
            "Temperature": round(random.uniform(18, 24), 1),
            "Humidity": round(random.uniform(80, 95), 1),
            "Status": "Active" if current_stage != "Empty" else "Inactive"
        }
    return beds

def generate_warehouse_items():
    num_items = random.randint(300, 800)
    items = {}
    categories = ["Substrate", "Spawn", "Equipment", "Packaging", "Supplies"]
    for i in range(num_items):
        item_id = str(uuid.uuid4())
        category = random.choice(categories)
        stock = random.randint(0, 100)
        items[item_id] = {
            "ID": item_id,
            "ItemID": item_id,
            "Name": f"{category} Item {i+1}",
            "Category": category,
            "Stock": stock,
            "MinStock": 10,
            "Unit": random.choice(["kg", "units", "boxes"]),
            "LastRestocked": (datetime.now() - timedelta(days=random.randint(1, 365))).strftime("%Y-%m-%d"),
            "Status": "Low Stock" if stock < 10 else "In Stock"
        }
    return items

def generate_products(num_products=20):
    mushroom_names = [
        "Portobello", "Shiitake", "Forest Mix", "Oyster", "Champignon", "King Oyster", "Black Forest", "White Forest",
        "Enoki", "Maitake", "Pioppino", "Lion's Mane", "Morel", "Winter Mix", "Summer Mix", "Gourmet Mix", "Asian Mix",
        "Italian Mix", "Salad Mix", "Chef's Mix"
    ]
    products = {}
    for i in range(num_products):
        product_id = str(uuid.uuid4())
        name = mushroom_names[i % len(mushroom_names)]
        products[product_id] = {
            "ProductID": product_id,
            "Name": name,
            "Category": random.choice(["A", "B", "C", "D", "E"]),
            "Price": round(random.uniform(50, 500), 2)
        }
    return products

def generate_orders(customers, products):
    num_orders = random.randint(10000, 20000)
    orders = {}
    statuses = ["Pending", "Processing", "Shipped", "Delivered", "Cancelled"]
    customer_ids = list(customers.keys())
    product_ids = list(products.keys())
    product_order_counts = {pid: 0 for pid in product_ids}
    repeat_customers = random.sample(customer_ids, k=int(len(customer_ids)*0.5))
    customer_order_counts = {cid: random.randint(1, 20) for cid in customer_ids}
    all_order_customers = []
    for cid, count in customer_order_counts.items():
        all_order_customers.extend([cid]*count)
    random.shuffle(all_order_customers)
    for i in range(num_orders):
        order_id = str(uuid.uuid4())
        customer_id = random.choice(all_order_customers)
        # פיזור מוצרים: כל מוצר יקבל לפחות 200 הזמנות
        if i < len(product_ids)*200:
            product_id = product_ids[i // 200]
        else:
            product_id = random.choice(product_ids)
        product_order_counts[product_id] += 1
        order_date = datetime.now() - timedelta(days=random.randint(1, 7*365))
        month = order_date.month
        base_amount = random.uniform(100, 1000)
        if month in [11, 12, 1]:
            base_amount *= 1.3
        elif month in [6, 7, 8]:
            base_amount *= 0.8
        total_amount = round(base_amount, 2)
        # רווח ריאלי: 70%-90% מהסכום, ב-5% מההזמנות הפסד
        if random.random() < 0.05:
            cost = round(total_amount * random.uniform(1.01, 1.15), 2)  # הפסד
        else:
            cost = round(total_amount * random.uniform(0.7, 0.9), 2)
        orders[order_id] = {
            "OrderID": order_id,
            "CustomerID": customer_id,
            "ProductID": product_id,
            "OrderDate": order_date.strftime("%Y-%m-%d"),
            "Status": random.choice(statuses),
            "TotalAmount": total_amount,
            "Cost": cost,
            "ShippingAddress": customers[customer_id]["Address"],
            "PaymentMethod": random.choice(["Credit Card", "Bank Transfer", "Cash"]),
            "Notes": f"Order #{i+1} notes"
        }
    print(f"Product order distribution: min={min(product_order_counts.values())}, max={max(product_order_counts.values())}")
    return orders

def generate_batches(growing_beds):
    num_batches = random.randint(800, 2000)
    batches = {}
    bed_ids = list(growing_beds.keys())
    for i in range(num_batches):
        batch_id = str(uuid.uuid4())
        bed_id = random.choice(bed_ids)
        start_date = datetime.now() - timedelta(days=random.randint(1, 5*365))
        substrate = round(random.uniform(10, 50), 2)
        yield_kg = round(substrate * random.uniform(0.5, 1.2), 2)
        batches[batch_id] = {
            "ID": batch_id,
            "BatchID": batch_id,
            "BedID": bed_id,
            "Start_date": start_date.strftime("%Y-%m-%d"),
            "ExpectedHarvestDate": (start_date + timedelta(days=random.randint(30, 60))).strftime("%Y-%m-%d"),
            "Status": random.choice(["Growing", "Harvested", "Failed"]),
            "Yield": yield_kg,
            "Substrate": substrate,
            "Notes": f"Batch #{i+1} notes"
        }
    return batches

def generate_logs(batches):
    num_logs = random.randint(3000, 8000)
    logs = {}
    batch_ids = list(batches.keys())
    log_types = ["Temperature", "Humidity", "Watering", "Ventilation", "Harvest", "Issue"]
    for i in range(num_logs):
        log_id = str(uuid.uuid4())
        batch_id = random.choice(batch_ids)
        log_date = datetime.now() - timedelta(days=random.randint(1, 5*365), hours=random.randint(0,23), minutes=random.randint(0,59))
        log_type = random.choice(log_types)
        air_temp = round(random.uniform(18, 28), 1)
        substrate_temp = round(random.uniform(18, 28), 1)
        rh_humidity = round(random.uniform(80, 95), 1)
        co2 = round(random.uniform(400, 2000), 1)
        harvest = round(random.uniform(0, 10), 2) if log_type == "Harvest" else 0
        if log_type == "Temperature":
            value = air_temp
        elif log_type == "Humidity":
            value = rh_humidity
        elif log_type == "Harvest":
            value = harvest
        else:
            value = 0
        logs[log_id] = {
            "LogID": log_id,
            "BatchID": batch_id,
            "LogDate": log_date.strftime("%Y-%m-%d %H:%M:%S"),
            "Date": log_date.strftime("%Y-%m-%d %H:%M:%S"),
            "LogType": log_type,
            "Value": value,
            "AIR_temp": air_temp,
            "Substrate_temp": substrate_temp,
            "RH_Humadity": rh_humidity,
            "CO2": co2,
            "Katif": harvest,
            "Notes": f"Log entry for {log_type} on batch {batch_id[:8]}"
        }
    return logs

def delete_all_tables():
    tables = [
        'Customer',
        'GrowingBed',
        'Warehouse',
        'Order',
        'Batches',
        'Logs',
        'Harvests',
        'Users'
    ]
    for table in tables:
        db.reference(table).delete()
    print("All relevant tables deleted from Firebase.")

def upload_dummy_data():
    try:
        delete_all_tables()
        customers = generate_customers()
        growing_beds = generate_growing_beds()
        warehouse_items = generate_warehouse_items()
        products = generate_products(20)
        orders = generate_orders(customers, products)
        batches = generate_batches(growing_beds)
        logs = generate_logs(batches)
        db.reference('Customer').set(customers)
        db.reference('GrowingBed').set(growing_beds)
        db.reference('Warehouse').set(warehouse_items)
        db.reference('Products').set(products)
        db.reference('Order').set(orders)
        db.reference('Batches').set(batches)
        db.reference('Logs').set(logs)
        print("Successfully uploaded all dummy data!")
        return True
    except Exception as e:
        print(f"Error uploading dummy data: {str(e)}")
        return False

if __name__ == "__main__":
    upload_dummy_data() 