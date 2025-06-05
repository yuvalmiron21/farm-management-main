import os
import sys
import bcrypt
from firebase_admin import credentials, initialize_app, db

# --- אתחול Firebase ---
import firebase_admin
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(BASE_DIR)
SERVICE_ACCOUNT_FILE = os.path.join(PARENT_DIR, "db", "farm-management-FireBase_credentials.json")
DATABASE_URL = "https://farm-management-86035-default-rtdb.europe-west1.firebasedatabase.app/"
if not firebase_admin._apps:
    cred = credentials.Certificate(SERVICE_ACCOUNT_FILE)
    initialize_app(cred, {"databaseURL": DATABASE_URL})
# --- סוף אתחול ---

def get_user_by_username(username):
    ref = db.reference('Users')
    users = ref.get() or {}
    for uid, user in users.items():
        if user.get('Username') == username:
            return uid, user
    return None, None

def add_user(username, password, role):
    ref = db.reference('Users')
    _, existing = get_user_by_username(username)
    if existing:
        return False, "Username already exists"
    if len(password) < 4:
        return False, "Password must be at least 4 characters"
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    user_data = {
        "Username": username,
        "Password": password_hash,
        "Role": role
    }
    ref.push(user_data)
    return True, "User created successfully"

def check_user(username, password):
    _, user = get_user_by_username(username)
    if user and bcrypt.checkpw(password.encode(), user['Password'].encode()):
        return True, user['Role']
    return False, None

def get_all_users():
    ref = db.reference('Users')
    users = ref.get() or {}
    return [(uid, u['Username'], u['Role']) for uid, u in users.items()]

def delete_user(uid):
    ref = db.reference(f'Users/{uid}')
    ref.delete()

def update_user(uid, username, role):
    ref = db.reference(f'Users/{uid}')
    ref.update({"Username": username, "Role": role})

# פונקציה ליצירת משתמשי דמו בסיסיים (admin ו-user1)
def create_initial_users():
    users = [
        ("admin", "1234", "admin"),
        ("user1", "1111", "user")
    ]
    for username, password, role in users:
        ok, msg = add_user(username, password, role)
        print(f"{username}: {msg}")

def delete_non_bcrypt_users():
    ref = db.reference('Users')
    users = ref.get() or {}
    for uid, user in users.items():
        pw = user.get('Password', '')
        if not pw.startswith('$2b$'):
            print(f"Deleting user {user.get('Username', uid)} (non-bcrypt password)")
            ref.child(uid).delete()

if __name__ == "__main__":
    delete_non_bcrypt_users()
    create_initial_users()
    sys.exit(0) 