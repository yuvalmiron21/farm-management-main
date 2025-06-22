from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox,
    QHBoxLayout, QToolButton, QFrame, QSizePolicy, QProgressBar
)
from PyQt5.QtGui import QFont, QPixmap, QMovie
from PyQt5.QtCore import Qt, QTimer, QSize
from Main_gui import Main_gui
from UserDashboard import UserDashboard
from user_management import UserManagement
from SimpleLoadingWindow import SimpleLoadingWindow
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
                /* border: 1.5px solid #e0e0e0; */
                /* box-shadow: 0 6px 20px rgba(0,0,0,0.12); */
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
        pw_layout = QHBoxLayout()
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setStyleSheet(self.username_input.styleSheet())
        pw_layout.addWidget(self.password_input)

        # Eye toggle button
        self.pw_eye_btn = QToolButton()
        self.pw_eye_btn.setCheckable(True)
        self.pw_eye_btn.setCursor(Qt.PointingHandCursor)
        self.pw_eye_btn.setStyleSheet("border: none; padding: 0 6px;")
        self.pw_eye_btn.setIconSize(QSize(20, 20))
        self.pw_eye_btn.setToolTip("Show/Hide Password")
        # Use unicode eye/eye-off icons for cross-platform
        self.pw_eye_btn.setText("👁️")
        self.pw_eye_btn.toggled.connect(self.toggle_password_visibility)
        pw_layout.addWidget(self.pw_eye_btn)
        panel_layout.addLayout(pw_layout)

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

        # Progress bar for login
        self.login_progress = QProgressBar()
        self.login_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #e0e0e0;
                border-radius: 5px;
                text-align: center;
                background: #f8f9fa;
                height: 8px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #43a047, stop:1 #66bb6a);
                border-radius: 4px;
            }
        """)
        self.login_progress.setRange(0, 100)
        self.login_progress.setValue(0)
        self.login_progress.hide()
        panel_layout.addWidget(self.login_progress)

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
            self.login_progress.show()
            self.loading_movie.start()
            self.login_button.setText("Logging in...")
            self.login_button.setStyleSheet("""
                QPushButton {
                    background: #a5d6a7;
                    color: #e8f5e9;
                    border: none;
                    padding: 12px;
                    border-radius: 10px;
                    font-size: 14px;
                    font-weight: bold;
                }
            """)
            
            # Animate progress bar
            self.progress_timer = QTimer()
            self.progress_timer.timeout.connect(self.update_login_progress)
            self.progress_timer.start(50)  # Update every 50ms
        else:
            self.loading_label.hide()
            self.login_progress.hide()
            self.loading_movie.stop()
            self.login_button.setText("Login")
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
            
            if hasattr(self, 'progress_timer'):
                self.progress_timer.stop()
                
    def update_login_progress(self):
        """Update the login progress bar"""
        current_value = self.login_progress.value()
        if current_value < 90:  # Don't go to 100% until login is complete
            self.login_progress.setValue(current_value + 2)

    def handle_login(self):
        username = self.username_input.text()
        password = self.password_input.text()

        if not username or not password:
            QMessageBox.warning(self, "Error", "Please enter both username and password")
            return

        self.set_loading_state(True)
        
        # Use a shorter delay for better UX
        QTimer.singleShot(500, lambda: self.process_login(username, password))

    def process_login(self, username, password):
        success, role, message = UserManagement.authenticate_user(username, password)
        
        # Complete the progress bar
        self.login_progress.setValue(100)
        QTimer.singleShot(200, lambda: self.set_loading_state(False))
        
        if success:
            # Show loading window
            loading_window = SimpleLoadingWindow()
            loading_window.show()
            
            # Close login window
            self.close()
            
            # Show appropriate dashboard after a short delay
            QTimer.singleShot(1500, lambda: self.show_dashboard(username, role, loading_window))
        else:
            QMessageBox.warning(self, "Error", message)
            
    def show_dashboard(self, username, role, loading_window):
        """Show the appropriate dashboard and close loading window"""
        if role == "admin":
            user_data = {"username": username, "role": role}
            self.main_window = Main_gui(user_data)
            self.main_window.show()
        else:
            self.user_dashboard = UserDashboard(username)
            self.user_dashboard.show()
        
        # Close loading window
        loading_window.close()

    def toggle_password_visibility(self, checked):
        if checked:
            self.password_input.setEchoMode(QLineEdit.Normal)
            self.pw_eye_btn.setText("🙈")
        else:
            self.password_input.setEchoMode(QLineEdit.Password)
            self.pw_eye_btn.setText("👁️")

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    login_window = LoginGUI()
    login_window.show()
    sys.exit(app.exec_())


# UserName:Admin Password: 1234