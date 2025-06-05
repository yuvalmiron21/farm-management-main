import os
import sys
from PyQt5.QtWidgets import QApplication, QMessageBox
from firebase_admin import credentials, initialize_app, db, _apps
from LoginGUI import LoginGUI
from Main_gui import Main_gui

# Initialize Firebase
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(BASE_DIR)
SERVICE_ACCOUNT_FILE = os.path.join(PARENT_DIR, "db", "farm-management-FireBase_credentials.json")
DATABASE_URL = "https://farm-management-86035-default-rtdb.europe-west1.firebasedatabase.app/"

def initialize_firebase():
    try:
        if not _apps:
            if not os.path.exists(SERVICE_ACCOUNT_FILE):
                raise FileNotFoundError(f"Firebase credentials file not found at: {SERVICE_ACCOUNT_FILE}")
            cred = credentials.Certificate(SERVICE_ACCOUNT_FILE)
            initialize_app(cred, {"databaseURL": DATABASE_URL})
        return True
    except Exception as e:
        QMessageBox.critical(None, "Error", f"Failed to initialize Firebase: {str(e)}")
        return False

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    if not initialize_firebase():
        sys.exit(1)
    
    try:
        # תמיד פותח את מסך ההתחברות
        login_window = LoginGUI()
        login_window.show()
        sys.exit(app.exec_())
    except Exception as e:
        QMessageBox.critical(None, "Error", f"Application error: {str(e)}")
        sys.exit(1)
