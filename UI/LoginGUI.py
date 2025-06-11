from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox,
    QHBoxLayout, QToolButton, QFrame
)
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtCore import Qt
from Main_gui import Main_gui
from UserDashboard import UserDashboard
from user_management import UserManagement
import os

class LoginGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mush | Login")
        self.setGeometry(100, 100, 420, 380)
        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #f8fafc, stop:1 #e0e7ef);
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignCenter)

        # Login panel
        panel = QFrame()
        panel.setStyleSheet("""
            QFrame {
                background: white;
                border-radius: 18px;
                padding: 32px 28px 28px 28px;
                border: 1.5px solid #e0e0e0;
                box-shadow: 0px 8px 32px rgba(44,62,80,0.08);
            }
        """)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setSpacing(18)
        panel_layout.setAlignment(Qt.AlignTop)

        # Logo/title
        logo_layout = QVBoxLayout()
        logo = QLabel()
        logo_path = os.path.join(os.path.dirname(__file__), "logo_without_blue.png")
        if os.path.exists(logo_path):
            pix = QPixmap(logo_path)
            pix = pix.scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo.setPixmap(pix)
        else:
            logo.setText("[Logo not found]")
            logo.setStyleSheet("color: #888; font-size: 12px;")
        logo.setAlignment(Qt.AlignCenter)
        logo_layout.addWidget(logo, alignment=Qt.AlignCenter)
        panel_layout.insertLayout(0, logo_layout)

        subtitle = QLabel("Farm Management System")
        subtitle.setFont(QFont("Segoe UI", 12))
        subtitle.setStyleSheet("color: #888; margin-bottom: 8px;")
        panel_layout.addWidget(subtitle)

        # Username field
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        self.username_input.setStyleSheet("""
            QLineEdit {
                padding: 12px;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #43a047;
            }
        """)
        panel_layout.addWidget(self.username_input)

        # Password field
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setStyleSheet("""
            QLineEdit {
                padding: 12px;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #43a047;
            }
        """)
        panel_layout.addWidget(self.password_input)

        # Login button
        login_button = QPushButton("Login")
        login_button.setStyleSheet("""
            QPushButton {
                background: #43a047;
                color: white;
                border: none;
                padding: 12px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #388e3c;
            }
            QPushButton:pressed {
                background: #2e7d32;
            }
        """)
        login_button.clicked.connect(self.handle_login)
        panel_layout.addWidget(login_button)

        main_layout.addWidget(panel)

    def handle_login(self):
        username = self.username_input.text()
        password = self.password_input.text()

        if not username or not password:
            QMessageBox.warning(self, "Error", "Please enter both username and password")
            return

        success, role, message = UserManagement.authenticate_user(username, password)
        
        if success:
            if role == "admin":
                user_data = {"username": username, "role": role}
                self.main_window = Main_gui(user_data)
                self.main_window.show()
            else:
                self.user_dashboard = UserDashboard(username)
                self.user_dashboard.show()
            self.close()
        else:
            QMessageBox.warning(self, "Error", message)

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    login_window = LoginGUI()
    login_window.show()
    sys.exit(app.exec_())


# UserName:Admin Password: 1234