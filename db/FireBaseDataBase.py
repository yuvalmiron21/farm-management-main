from botocore import model
from flask import Flask, request, jsonify
from firebase_admin import credentials, db, initialize_app
from models import Customer  # Import your models here
from models import Farm
from models import Mushroom_type

# Initialize Firebase
SERVICE_ACCOUNT_FILE = "farm-management-FireBase_credentials.json"  # עדכון שם הקובץ
DATABASE_URL = "https://farm-management-86035-default-rtdb.europe-west1.firebasedatabase.app/"
cred = credentials.Certificate(SERVICE_ACCOUNT_FILE)
initialize_app(cred, {"databaseURL": DATABASE_URL})

app = Flask(__name__)

# Helper functions
def get_all_records(model_name):
    ref = db.reference(model_name)
    data = ref.get()
    if data:
        return [model.from_dict(value) for key, value in data.items()]
    return []

def get_record_by_id(model_name, model_class, record_id):
    ref = db.reference(model_name)
    data = ref.get()
    if data:
        for key, value in data.items():
            obj = model_class.from_dict(value)
            if getattr(obj, "customer_id", None) == record_id or getattr(obj, "id", None) == record_id:
                return obj
    return None

def add_record(model_name, obj):
    ref = db.reference(model_name)
    ref.push(obj.to_dict())

def update_record(model_name, record_id, model_class, updated_data):
    ref = db.reference(model_name)
    data = ref.get()
    if data:
        for key, value in data.items():
            obj = model_class.from_dict(value)
            if getattr(obj, "customer_id", None) == record_id or getattr(obj, "id", None) == record_id:
                ref.child(key).update(updated_data)
                return True
    return False

def delete_record(model_name, record_id, model_class):
    ref = db.reference(model_name)
    data = ref.get()
    if data:
        for key, value in data.items():
            obj = model_class.from_dict(value)
            if getattr(obj, "customer_id", None) == record_id or getattr(obj, "id", None) == record_id:
                ref.child(key).delete()
                return True
    return False

def upload_or_replace_table(table_name, json_data):
    """Uploads or replaces a table in the database with given JSON data."""
    ref = db.reference(table_name)
    ref.set(json_data)  # Replaces all data in the table
    return True

def retrieve_table_as_json(table_name):
    """Retrieves the table data in JSON format from the database."""
    ref = db.reference(table_name)
    data = ref.get()
    return jsonify(data) if data else jsonify({"error": "No data found for table."})


# Flask routes
@app.route('/api/<model_name>', methods=['GET'])
def api_get_all(model_name):
    if model_name == "Customer":
        records = get_all_records("Customer")
        return jsonify([record.to_dict() for record in records])
    return jsonify({"error": "Model not found"}), 404

@app.route('/api/<model_name>/<record_id>', methods=['GET'])
def api_get_record(model_name, record_id):
    if model_name == "Customer":
        record = get_record_by_id("Customer", Customer, record_id)
        if record:
            return jsonify(record.to_dict())
    return jsonify({"error": f"Record with ID {record_id} not found in {model_name}"}), 404

@app.route('/api/<model_name>', methods=['POST'])
def api_add_record(model_name):
    if model_name == "Customer":
        data = request.json
        obj = Customer.from_dict(data)
        add_record("Customer", obj)
        return jsonify({"message": "Record added successfully"}), 201
    return jsonify({"error": "Model not found"}), 404

@app.route('/api/<model_name>/<record_id>', methods=['PUT'])
def api_update_record(model_name, record_id):
    if model_name == "Customer":
        data = request.json
        if update_record("Customer", record_id, Customer, data):
            return jsonify({"message": "Record updated successfully"})
    return jsonify({"error": f"Record with ID {record_id} not found in {model_name}"}), 404

@app.route('/api/<model_name>/<record_id>', methods=['DELETE'])
def api_delete_record(model_name, record_id):
    if model_name == "Customer":
        if delete_record("Customer", record_id, Customer):
            return jsonify({"message": "Record deleted successfully"})
    return jsonify({"error": f"Record with ID {record_id} not found in {model_name}"}), 404

@app.route('/api/upload_table/<table_name>', methods=['POST'])
def api_upload_or_replace_table(table_name):
    data = request.json
    if upload_or_replace_table(table_name, data):
        return jsonify({"message": "Table uploaded or replaced successfully"})
    return jsonify({"error": "Failed to upload data"}), 500

@app.route('/api/retrieve_table/<table_name>', methods=['GET'])
def api_retrieve_table_as_json(table_name):
    return retrieve_table_as_json(table_name)

def get_all_data():
    ref = db.reference('/')
    data = ref.get()
    return data

def test_firebase_connection():
    """Test connection to Firebase and print all data."""
    try:
        ref = db.reference('/')  # גישה לנתיב הראשי במסד הנתונים
        data = ref.get()
        print("Firebase connection successful.")
        print("Current database state:")
        print(data)
    except Exception as e:
        print("Failed to connect to Firebase.")
        print(f"Error: {e}")

if __name__ == '__main__':
    test_firebase_connection()  # קריאה לפונקציה

    app.run(port=5000, debug=True)
