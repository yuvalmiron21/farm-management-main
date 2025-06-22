from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel, QScrollArea, QFrame, QSizePolicy, QSpacerItem
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QIcon, QColor, QPixmap
import google.generativeai as genai
import os
from dotenv import load_dotenv
from firebase_admin import db
from PyQt5.QtWidgets import QApplication
import logging
import time
import random
from requests.exceptions import ConnectionError, Timeout
from UI.retry_utils import retry_with_backoff

# Find the project root and load .env from there
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dotenv_path = os.path.join(project_root, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
    print("✅ .env file loaded successfully.")
else:
    print("⚠️ .env file not found. Please ensure it is in the project root.")

class ChatMessage(QFrame):
    def __init__(self, text, is_user=True, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 2, 10, 2)
        layout.setSpacing(0)
        bubble = QLabel(text)
        bubble.setWordWrap(True)
        bubble.setTextInteractionFlags(Qt.TextSelectableByMouse)
        if is_user:
            bubble.setFont(QFont("Segoe UI", 11))
            bubble.setStyleSheet("""
                QLabel {
                    background-color: #dcf8c6;
                    color: #222;
                    border-radius: 16px;
                    padding: 10px 16px;
                    margin-left: 40px;
                    margin-right: 0px;
                    max-width: 350px;
                }
            """)
            layout.addStretch()
            layout.addWidget(bubble)
        else:
            bubble.setFont(QFont("Segoe UI", 8))
            bubble.setStyleSheet("""
                QLabel {
                    background-color: #ffffff;
                    color: #333;
                    border-radius: 12px;
                    padding: 8px 12px;
                    margin-right: 40px;
                    margin-left: 0px;
                    max-width: 340px;
                    border: 1px solid #f0f0f0;
                }
            """)
            layout.addWidget(bubble)
            layout.addStretch()

class ChatGUI(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI Assistant")
        self.setGeometry(100, 100, 420, 600)
        self.setStyleSheet("""
            QWidget {
                background-color: #ece5dd;
            }
        """)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setMinimumSize(350, 500)

        # Main vertical layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header (WhatsApp style)
        header = QFrame()
        header.setObjectName("chatHeader")
        header.setStyleSheet("""
            QFrame {
                background-color: #075e54;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }
        """)
        header.setFixedHeight(56)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 0, 12, 0)
        header_layout.setSpacing(8)
        self.header = header  # Save reference for mouse events

        # Custom logo as avatar
        logo_path = os.path.join(os.path.dirname(__file__), "chat_logo.png")
        logo_label = QLabel()
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            pixmap = pixmap.scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(pixmap)
            logo_label.setFixedSize(40, 40)
            logo_label.setStyleSheet("border-radius: 20px; background: white;")
        else:
            logo_label.setText("🍄")
            logo_label.setFixedSize(40, 40)
            logo_label.setStyleSheet("border-radius: 20px; background: #25d366; color: white; font-size: 24px;")
        header_layout.addWidget(logo_label)

        # Title
        title = QLabel("AI Assistant")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        title.setStyleSheet("color: white;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        # Exit button
        exit_btn = QPushButton()
        exit_btn.setIcon(QIcon.fromTheme("window-close"))
        exit_btn.setText("✕")
        exit_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: white;
                font-size: 18px;
                border: none;
                padding: 0 8px;
            }
            QPushButton:hover {
                color: #25d366;
            }
        """)
        exit_btn.setCursor(Qt.PointingHandCursor)
        exit_btn.setFixedSize(32, 32)
        exit_btn.clicked.connect(self.close)
        header_layout.addWidget(exit_btn)

        main_layout.addWidget(header)

        # Chat area (scrollable)
        self.chat_area = QScrollArea()
        self.chat_area.setWidgetResizable(True)
        self.chat_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: #ece5dd;
            }
        """)
        self.chat_container = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setAlignment(Qt.AlignTop)
        self.chat_layout.setSpacing(4)
        self.chat_area.setWidget(self.chat_container)
        main_layout.addWidget(self.chat_area)

        # Status bar
        self.status_label = QLabel("Thinking...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("Segoe UI", 10))
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #f0f0f0;
                color: #555;
                padding: 4px;
                border-top: 1px solid #ddd;
            }
        """)
        self.status_label.hide()
        main_layout.addWidget(self.status_label)

        # Input area (fixed at bottom)
        input_frame = QFrame()
        input_frame.setStyleSheet("background: #f7f7f7; border-bottom-left-radius: 8px; border-bottom-right-radius: 8px;")
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(12, 8, 12, 8)
        input_layout.setSpacing(8)

        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Type a message...")
        self.message_input.setFont(QFont("Segoe UI", 11))
        self.message_input.setStyleSheet("""
            QLineEdit {
                background: white;
                border-radius: 18px;
                border: 1px solid #ddd;
                padding: 10px 16px;
                font-size: 14px;
            }
        """)
        self.message_input.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.message_input)

        self.send_button = QPushButton()
        self.send_button.setIcon(QIcon.fromTheme("send"))
        self.send_button.setText("➤")
        self.send_button.setStyleSheet("""
            QPushButton {
                background-color: #25d366;
                color: white;
                border: none;
                border-radius: 18px;
                font-size: 18px;
                padding: 8px 18px;
                min-width: 36px;
            }
            QPushButton:hover {
                background-color: #128c7e;
            }
        """)
        self.send_button.setCursor(Qt.PointingHandCursor)
        self.send_button.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_button)

        main_layout.addWidget(input_frame)

        # Add welcome message
        self.add_message("Hello! I'm your AI assistant. How can I help you with your mushroom farm today?", False)

        # Initialize Gemini
        self.initialize_gemini()

        # Drag support
        self._drag_active = False
        self._drag_position = None

    def initialize_gemini(self):
        try:
            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise ValueError("GEMINI_API_KEY not found or is empty. Please check your .env file.")
            
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('models/gemini-1.5-flash-latest')
            print("✅ Gemini initialized successfully.")
        except Exception as e:
            error_message = f"Error initializing AI: {str(e)}"
            print(f"🚨 {error_message}")
            self.add_message(error_message, False)

    def add_message(self, text, is_user=True):
        message = ChatMessage(text, is_user)
        self.chat_layout.addWidget(message)
        # Scroll to bottom
        self.chat_area.verticalScrollBar().setValue(
            self.chat_area.verticalScrollBar().maximum()
        )

    @retry_with_backoff
    def get_summarized_farm_context(self):
        """Fetches a summarized context of the farm instead of the whole database."""
        try:
            summary_parts = []
            
            # Beds summary
            beds = db.reference('GrowingBed').get() or {}
            total_beds = len(beds)
            active_beds = sum(1 for b in beds.values() if b.get('CurrentGrowthStage', 'Empty') != 'Empty')
            summary_parts.append(f"- Beds: {active_beds}/{total_beds} active.")

            # Orders summary
            orders = db.reference('Order').get() or {}
            pending_orders = sum(1 for o in orders.values() if o.get('Status', 'Completed') == 'Pending')
            summary_parts.append(f"- Orders: {pending_orders} pending.")

            # Customer summary
            customers = db.reference('Customer').get() or {}
            summary_parts.append(f"- Customers: {len(customers)} total.")

            # Alerts summary
            warehouse = db.reference('Warehouse').get() or {}
            stock_alerts = [item.get('Name') for item in warehouse.values() if float(item.get('Stock', 999)) < 10]
            if stock_alerts:
                summary_parts.append(f"- Alerts: Critical stock for {', '.join(stock_alerts)}.")

            return "Farm Status Summary:\n" + "\n".join(summary_parts)
            
        except Exception as e:
            return f"Error fetching farm summary: {str(e)}"

    def get_farm_context(self):
        try:
            farm_data = db.reference('/').get()
            return str(farm_data)
        except Exception as e:
            return f"Error fetching farm data: {str(e)}"

    def send_message(self):
        user_message = self.message_input.text().strip()
        if not user_message:
            return
        
        self.add_message(user_message, True)
        self.message_input.clear()
        
        # Disable input and show thinking status
        self.message_input.setEnabled(False)
        self.send_button.setEnabled(False)
        self.status_label.setText("🤔 Thinking...")
        self.status_label.show()
        QApplication.processEvents()  # Force UI update

        try:
            # Check if Gemini model is initialized
            if not hasattr(self, 'model'):
                raise ValueError("AI model is not initialized. Cannot send message.")

            farm_context = self.get_summarized_farm_context()
            prompt = (
                "You are an expert AI assistant for a mushroom farm. "
                "You must answer in Hebrew."
                f"Here is a summary of the current farm data for context:\n{farm_context}\n\n"
                f"User question: {user_message}\n\nPlease provide a helpful and concise response in Hebrew."
            )
            
            response = self.model.generate_content(prompt)
            self.add_message(response.text, False)
        except Exception as e:
            error_message = f"An error occurred: {str(e)}"
            print(f"🚨 {error_message}")
            self.add_message(error_message, False)
        finally:
            # Hide status and re-enable input
            self.status_label.hide()
            self.message_input.setEnabled(True)
            self.send_button.setEnabled(True)
            self.message_input.setFocus()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Only start drag if click is in header
            if self.header.geometry().contains(event.pos()):
                self._drag_active = True
                self._drag_position = event.globalPos() - self.frameGeometry().topLeft()
                event.accept()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_active and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self._drag_position)
            event.accept()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_active = False
        super().mouseReleaseEvent(event) 