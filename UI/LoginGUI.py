from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox,
    QHBoxLayout, QToolButton, QFrame, QSizePolicy
)
from PyQt5.QtGui import QFont, QPixmap, QMovie
from PyQt5.QtCore import Qt, QTimer, QSize
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
                    stop:0 #f8fafc, stop:1 #a5d6a7);
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignCenter)

        # Login panel
        panel = QFrame()
        panel.setStyleSheet("""
            QFrame {
                background: white;
                border-radius: 20px;
                padding: 32px 28px 28px 28px;
                border: 1.5px solid #e0e0e0;
                box-shadow: 0 6px 20px rgba(0,0,0,0.12);
            }
        """)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setSpacing(18)
        panel_layout.setAlignment(Qt.AlignTop)

        # Logo/title
        logo_layout = QVBoxLayout()
        logo = QLabel()
        logo_path = os.path.join(os.path.dirname(__file__), "logo_without_white.png")
        if os.path.exists(logo_path):
            pix = QPixmap(logo_path)
            pix = pix.scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo.setPixmap(pix)
        else:
            logo.setText("🍄")
            logo.setStyleSheet("color: #888; font-size: 48px;")
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
                border: 1.5px solid #e0e0e0;
                border-radius: 10px;
                font-size: 14px;
                background: #f8f9fa;
            }
            QLineEdit:focus {
                border: 1.5px solid #2e7d32;
                background: white;
            }
            QLineEdit:disabled {
                background: #f1f3f5;
                color: #868e96;
            }
        """)
        panel_layout.addWidget(self.username_input)

        # Password field
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setStyleSheet(self.username_input.styleSheet())
        panel_layout.addWidget(self.password_input)

        # Loading animation
        self.loading_label = QLabel()
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet("""
            QLabel {
                color: #2e7d32;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        self.loading_label.hide()
        panel_layout.addWidget(self.loading_label)

        # Loading GIF
        self.loading_movie = QMovie(os.path.join(os.path.dirname(__file__), "mushroom_loading.gif"))
        self.loading_movie.setScaledSize(QSize(100, 100))
        self.loading_movie.setCacheMode(QMovie.CacheAll)
        self.loading_movie.setSpeed(100)
        self.loading_label.setMovie(self.loading_movie)
        self.loading_movie.finished.connect(self.loading_movie.start)

        # Login button
        self.login_button = QPushButton("Login")
        self.login_button.setStyleSheet("""
            QPushButton {
                background: #43a047;
                color: white;
                border: none;
                padding: 12px;
                border-radius: 10px;
                font-size: 14px;
                font-weight: bold;
                transition: all 0.3s ease;
            }
            QPushButton:hover {
                background: #388e3c;
                box-shadow: 0 4px 12px rgba(67, 160, 71, 0.3);
            }
            QPushButton:pressed {
                background: #2e7d32;
                transform: translateY(1px);
            }
            QPushButton:disabled {
                background: #a5d6a7;
                color: #e8f5e9;
            }
        """)
        self.login_button.clicked.connect(self.handle_login)
        panel_layout.addWidget(self.login_button)

        main_layout.addWidget(panel)

    def set_loading_state(self, loading=True):
        self.username_input.setEnabled(not loading)
        self.password_input.setEnabled(not loading)
        self.login_button.setEnabled(not loading)
        
        if loading:
            self.loading_label.show()
            self.loading_movie.start()
            self.login_button.setText("Logging in...")
        else:
            self.loading_label.hide()
            self.loading_movie.stop()
            self.login_button.setText("Login")

    def handle_login(self):
        username = self.username_input.text()
        password = self.password_input.text()

        if not username or not password:
            QMessageBox.warning(self, "Error", "Please enter both username and password")
            return

        self.set_loading_state(True)
        
        # Simulate network delay
        QTimer.singleShot(1000, lambda: self.process_login(username, password))

    def process_login(self, username, password):
        success, role, message = UserManagement.authenticate_user(username, password)
        
        self.set_loading_state(False)
        
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