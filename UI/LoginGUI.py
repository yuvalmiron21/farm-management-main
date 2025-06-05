from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox,
    QHBoxLayout, QToolButton, QFrame
)
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtCore import Qt
from Main_gui import Main_gui
from user_db import check_user

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

        # Logo/title
        logo_layout = QHBoxLayout()
        logo = QLabel("🍄")
        logo.setFont(QFont("Segoe UI Emoji", 32, QFont.Bold))
        logo.setStyleSheet("color: #43a047;")
        logo.setAlignment(Qt.AlignCenter)
        logo_layout.addWidget(logo)
        title = QLabel("Mush")
        title.setFont(QFont("Segoe UI", 28, QFont.Bold))
        title.setStyleSheet("color: #43a047; margin-left: 8px;")
        logo_layout.addWidget(title)
        logo_layout.addStretch()
        panel_layout.addLayout(logo_layout)

        subtitle = QLabel("Farm Management System")
        subtitle.setFont(QFont("Segoe UI", 12))
        subtitle.setStyleSheet("color: #888; margin-bottom: 8px;")
        panel_layout.addWidget(subtitle)

        # Username field with icon
        user_layout = QHBoxLayout()
        user_icon = QLabel("👤")
        user_icon.setFont(QFont("Segoe UI Emoji", 18))
        user_icon.setFixedWidth(32)
        user_icon.setAlignment(Qt.AlignCenter)
        user_layout.addWidget(user_icon)
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        self.username_input.setMinimumHeight(36)
        self.username_input.setFont(QFont("Segoe UI", 11))
        user_layout.addWidget(self.username_input)
        panel_layout.addLayout(user_layout)

        # Password field with icon + eye
        pw_layout = QHBoxLayout()
        lock_icon = QLabel("🔒")
        lock_icon.setFont(QFont("Segoe UI Emoji", 18))
        lock_icon.setFixedWidth(32)
        lock_icon.setAlignment(Qt.AlignCenter)
        pw_layout.addWidget(lock_icon)
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setMinimumHeight(36)
        self.password_input.setFont(QFont("Segoe UI", 11))
        pw_layout.addWidget(self.password_input)
        self.show_pw_btn = QToolButton()
        self.show_pw_btn.setText("👁️")
        self.show_pw_btn.setCheckable(True)
        self.show_pw_btn.setToolTip("Show/Hide Password")
        self.show_pw_btn.setStyleSheet("font-size: 18px; background: transparent; border: none;")
        self.show_pw_btn.toggled.connect(self.toggle_password_visibility)
        pw_layout.addWidget(self.show_pw_btn)
        panel_layout.addLayout(pw_layout)

        # Login button
        self.login_button = QPushButton("Login")
        self.login_button.setMinimumHeight(44)
        self.login_button.setFont(QFont("Segoe UI", 13, QFont.Bold))
        self.login_button.setStyleSheet("""
            QPushButton {
                background-color: #43a047;
                color: white;
                border-radius: 8px;
                font-weight: bold;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background-color: #388e3c;
            }
        """)
        self.login_button.clicked.connect(self.handle_login)
        panel_layout.addWidget(self.login_button)

        main_layout.addWidget(panel, alignment=Qt.AlignCenter)

    def toggle_password_visibility(self, checked):
        if checked:
            self.password_input.setEchoMode(QLineEdit.Normal)
            self.show_pw_btn.setText("🙈")
        else:
            self.password_input.setEchoMode(QLineEdit.Password)
            self.show_pw_btn.setText("👁️")

    def handle_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()
        if not username or not password:
            QMessageBox.warning(self, "Error", "Please enter both username and password.")
            return
        try:
            ok, role = check_user(username, password)
            if ok:
                QMessageBox.information(self, "Success", "Login successful!")
                self.open_main_gui(username, role)
                return
            else:
                QMessageBox.warning(self, "Error", "Invalid username or password.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to log in: {str(e)}")

    def open_main_gui(self, username, role):
        self.main_window = Main_gui(username, role)
        self.main_window.show()
        self.close()

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    login_window = LoginGUI()
    login_window.show()
    sys.exit(app.exec_())


# UserName:Admin Password: 1234