import os
import bcrypt
from firebase_admin import credentials, initialize_app, db
import firebase_admin

# Initialize Firebase
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(BASE_DIR)
SERVICE_ACCOUNT_FILE = os.path.join(PARENT_DIR, "db", "farm-management-FireBase_credentials.json")
DATABASE_URL = "https://farm-management-86035-default-rtdb.europe-west1.firebasedatabase.app/"

# Initialize Firebase only if not already initialized
if not firebase_admin._apps:
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        raise FileNotFoundError(f"Firebase credentials file not found at: {SERVICE_ACCOUNT_FILE}")
    cred = credentials.Certificate(SERVICE_ACCOUNT_FILE)
    initialize_app(cred, {"databaseURL": DATABASE_URL})

class UserManagement:
    @staticmethod
    def get_user_by_username(username):
        """Get user by username from database"""
        ref = db.reference('Users')
        users = ref.get() or {}
        for uid, user in users.items():
            if user.get('Username') == username:
                return uid, user
        return None, None

    @staticmethod
    def add_user(username, password, role="user"):
        """Add new user to database"""
        ref = db.reference('Users')
        _, existing = UserManagement.get_user_by_username(username)
        
        if existing:
            return False, "Username already exists"
        
        if len(password) < 4:
            return False, "Password must be at least 4 characters"
        
        # Hash password using bcrypt
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        
        user_data = {
            "Username": username,
            "Password": password_hash,
            "Role": role,
            "LoggedIn": False
        }
        
        ref.push(user_data)
        return True, "User created successfully"

    @staticmethod
    def authenticate_user(username, password):
        """Authenticate user and update login status"""
        _, user = UserManagement.get_user_by_username(username)
        
        if not user:
            return False, None, "User not found"
        
        if not bcrypt.checkpw(password.encode(), user['Password'].encode()):
            return False, None, "Invalid password"
        
        # Update login status
        ref = db.reference('Users')
        users = ref.get() or {}
        for uid, u in users.items():
            if u.get('Username') == username:
                ref.child(uid).update({"LoggedIn": True})
                break
        
        return True, user['Role'], "Login successful"

    @staticmethod
    def logout_user(username):
        """Logout user by updating login status"""
        ref = db.reference('Users')
        users = ref.get() or {}
        for uid, user in users.items():
            if user.get('Username') == username:
                ref.child(uid).update({"LoggedIn": False})
                return True
        return False

    @staticmethod
    def get_all_users():
        """Get all users from database"""
        ref = db.reference('Users')
        users = ref.get() or {}
        return [(uid, u['Username'], u['Role']) for uid, u in users.items()]

    @staticmethod
    def delete_user(uid):
        """Delete user from database"""
        ref = db.reference(f'Users/{uid}')
        ref.delete()
        return True

    @staticmethod
    def update_user(uid, username, role):
        """Update user information"""
        ref = db.reference(f'Users/{uid}')
        ref.update({
            "Username": username,
            "Role": role
        })
        return True

    @staticmethod
    def get_logged_in_user():
        """Get currently logged in user"""
        ref = db.reference('Users')
        users = ref.get() or {}
        for user in users.values():
            if user.get('LoggedIn', False):
                return user
        return None

    @staticmethod
    def create_default_admin():
        """Create default admin user if no users exist"""
        ref = db.reference('Users')
        users = ref.get() or {}
        
        if not users:
            UserManagement.add_user(
                username="admin",
                password="admin123",
                role="admin"
            )
            return True
        return False

# Initialize default admin if needed
UserManagement.create_default_admin() 