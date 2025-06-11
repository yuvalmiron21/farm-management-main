from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFrame, QScrollArea, QMessageBox, QDialog, QStackedWidget, QSizePolicy, QMainWindow, QSpacerItem
)
from PyQt5.QtGui import QFont, QIcon, QColor, QPixmap
from PyQt5.QtCore import Qt, QSize, QPoint
from Order_gui import OrderGUI
from Growing_bed_gui import GrowingBedGUI
from Customer_gui import CustomerGUI
from WarehouseGUI import WarehouseGUI
from FarmVisualGUI import FarmVisualGUI
from AnalyticsApp import AnalyticsApp
from firebase_admin import db
import os

class Sidebar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(220)
        self.setStyleSheet("""
            QFrame {
                background: #23272e;
                border-right: 1px solid #222;
            }
            QPushButton {
                text-align: left;
                padding: 15px;
                border: none;
                font-size: 15px;
                color: #e0e0e0;
                background: transparent;
            }
            QPushButton:hover {
                background: #2e7d32;
                color: #fff;
            }
            QPushButton:checked {
                background: #43a047;
                color: #fff;
                border-left: 4px solid #fff;
            }
        """)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Logo and title
        logo_layout = QHBoxLayout()
        logo = QLabel()
        pix = QPixmap(32, 32)
        pix.fill(QColor("#43a047"))
        logo.setPixmap(pix)
        logo.setFixedSize(32, 32)
        title = QLabel("Mush")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        title.setStyleSheet("color: #fff;")
        logo_layout.addWidget(logo)
        logo_layout.addWidget(title)
        logo_layout.addStretch()
        layout.addLayout(logo_layout)
        layout.addSpacing(18)

        # Menu buttons with emojis
        self.buttons = []
        menu_items = [
            ("Dashboard", "dashboard", "🏠"),
            ("Orders", "orders", "📦"),
            ("Growing Beds", "growing_beds", "🌱"),
            ("Customers", "customers", "👥"),
            ("Warehouse", "warehouse", "🏪"),
            ("Farm Visual", "farm_visual", "🌾"),
            ("Analytics", "analytics", "📈")
        ]
        for text, name, emoji in menu_items:
            btn = QPushButton(f"{emoji}  {text}")
            btn.setCheckable(True)
            btn.setProperty("page", name)
            btn.clicked.connect(lambda checked, b=btn: self.button_clicked(b))
            layout.addWidget(btn)
            self.buttons.append(btn)
        layout.addStretch()
        # Logout button
        logout_btn = QPushButton("🚪  Logout")
        logout_btn.setStyleSheet("""
            QPushButton {
                color: #ff7675;
                margin: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #2d3436;
            }
        """)
        logout_btn.clicked.connect(self.logout)
        layout.addWidget(logout_btn)

    def button_clicked(self, button):
        for btn in self.buttons:
            btn.setChecked(btn == button)
        # Find the QMainWindow parent
        win = self.parent()
        while win and not hasattr(win, 'change_page'):
            win = win.parent()
        if win and hasattr(win, 'change_page'):
            win.change_page(button.property("page"))

    def logout(self):
        from user_management import UserManagement
        win = self.parent()
        while win and not hasattr(win, 'username'):
            win = win.parent()
        if win and hasattr(win, 'username'):
            UserManagement.logout_user(win.username)
        if win:
            win.close()
        from LoginGUI import LoginGUI
        login = LoginGUI()
        login.show()

class KpiCard(QFrame):
    def __init__(self, title, value, icon, color):
        super().__init__()
        self.setStyleSheet(f"""
            QFrame {{
                background: {color};
                border-radius: 16px;
                padding: 18px 24px;
                min-width: 200px;
            }}
            QLabel {{
                color: #222;
            }}
        """)
        layout = QVBoxLayout(self)
        icon_label = QLabel(icon)
        icon_label.setFont(QFont("Segoe UI Emoji", 36))
        icon_label.setAlignment(Qt.AlignHCenter)
        layout.addWidget(icon_label)
        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 14))
        title_label.setAlignment(Qt.AlignHCenter)
        layout.addWidget(title_label)
        value_label = QLabel(str(value))
        value_label.setFont(QFont("Segoe UI", 18, QFont.Bold))
        value_label.setAlignment(Qt.AlignHCenter)
        layout.addWidget(value_label)

class ModernAddButton(QPushButton):
    def __init__(self, icon, tooltip, color, callback):
        super().__init__(icon, "")
        self.setToolTip(tooltip)
        self.setFixedSize(48, 48)
        self.setIconSize(QSize(32, 32))
        self.setStyleSheet(f"""
            QPushButton {{
                background: {color};
                border-radius: 24px;
                border: none;
            }}
            QPushButton:hover {{
                background: #388e3c;
            }}
        """)
        self.clicked.connect(callback)

class UserDashboard(QMainWindow):
    def __init__(self, username):
        super().__init__()
        self.username = username
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setWindowTitle(f"Mush | User Dashboard - {username}")
        self.setMinimumSize(1200, 800)
        self._old_pos = None
        self.chat_button = None
        self.chat_gui = None
        self.init_ui()
        self.add_floating_chat_button()
        self.showMaximized()

    def init_ui(self):
        # Custom title bar
        title_bar = QFrame()
        title_bar.setObjectName("titleBar")
        title_bar.setStyleSheet("""
            QFrame#titleBar {
                background: #23272e;
                min-height: 38px;
                max-height: 38px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }
        """)
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(8, 0, 8, 0)
        logo = QLabel()
        pix = QPixmap(32, 32)
        pix.fill(QColor("#43a047"))
        logo.setPixmap(pix)
        logo.setFixedSize(32, 32)
        title_layout.addWidget(logo)
        title_label = QLabel(f"Mush | User Dashboard - {self.username}")
        title_label.setStyleSheet("color: #fff; font-size: 16px; font-weight: bold;")
        title_layout.addWidget(title_label)
        title_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        # Minimize button
        btn_min = QPushButton("–")
        btn_min.setFixedSize(32, 28)
        btn_min.setStyleSheet("background: none; color: #fff; font-size: 18px; border: none;")
        btn_min.clicked.connect(self.showMinimized)
        title_layout.addWidget(btn_min)
        # Maximize/restore button
        btn_max = QPushButton("❐")
        btn_max.setFixedSize(32, 28)
        btn_max.setStyleSheet("background: none; color: #fff; font-size: 16px; border: none;")
        btn_max.clicked.connect(self.toggle_max_restore)
        title_layout.addWidget(btn_max)
        # Close button
        btn_close = QPushButton("✕")
        btn_close.setFixedSize(32, 28)
        btn_close.setStyleSheet("background: none; color: #ff7675; font-size: 18px; border: none;")
        btn_close.clicked.connect(self.close)
        title_layout.addWidget(btn_close)
        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(title_bar)
        # Content area
        content_frame = QFrame()
        content_layout = QHBoxLayout(content_frame)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        self.sidebar = Sidebar(self)
        content_layout.addWidget(self.sidebar)
        self.content = QStackedWidget()
        self.content.setStyleSheet("background: #f8fafc;")
        content_layout.addWidget(self.content)
        main_layout.addWidget(content_frame)
        self.init_pages()
        self.change_page("dashboard")
        # Drag window events
        title_bar.mousePressEvent = self.title_bar_mouse_press
        title_bar.mouseMoveEvent = self.title_bar_mouse_move

    def toggle_max_restore(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def title_bar_mouse_press(self, event):
        if event.button() == Qt.LeftButton:
            self._old_pos = event.globalPos()

    def title_bar_mouse_move(self, event):
        if self._old_pos is not None:
            delta = event.globalPos() - self._old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self._old_pos = event.globalPos()

    def fetch_kpi_data(self):
        # Fetch counts from Firebase
        orders = db.reference('Order').get() or {}
        customers = db.reference('Customer').get() or {}
        beds = db.reference('GrowingBed').get() or {}
        warehouse = db.reference('Warehouse').get() or {}
        return {
            'orders': len(orders),
            'customers': len(customers),
            'beds': len(beds),
            'warehouse': len(warehouse)
        }

    def init_pages(self):
        dashboard = QWidget()
        dashboard_layout = QVBoxLayout(dashboard)
        dashboard_layout.setContentsMargins(30, 30, 30, 30)
        dashboard_layout.setSpacing(24)
        # Top bar
        top_bar = QHBoxLayout()
        user_icon = QLabel("👤")
        user_icon.setFont(QFont("Segoe UI Emoji", 24))
        user_label = QLabel(f"Welcome, {self.username}!")
        user_label.setFont(QFont("Segoe UI", 22, QFont.Bold))
        user_label.setStyleSheet("color: #23272e;")
        top_bar.addWidget(user_icon)
        top_bar.addWidget(user_label)
        top_bar.addStretch()
        dashboard_layout.addLayout(top_bar)
        # KPI cards + add buttons
        kpi_row = QHBoxLayout()
        kpi_data = self.fetch_kpi_data()
        kpi_info = [
            ("Orders", kpi_data['orders'], "📦", "#e0f7fa", lambda: self.change_page("orders"), "Add Order"),
            ("Customers", kpi_data['customers'], "👥", "#f3e5f5", lambda: self.change_page("customers"), "Add Customer"),
            ("Beds", kpi_data['beds'], "🌱", "#e8f5e9", lambda: self.change_page("growing_beds"), "Add Bed"),
            ("Warehouse", kpi_data['warehouse'], "🏪", "#fff3e0", lambda: self.change_page("warehouse"), "Add Warehouse Item")
        ]
        for title, value, icon, color, callback, tooltip in kpi_info:
            vbox = QVBoxLayout()
            vbox.setAlignment(Qt.AlignHCenter)
            vbox.addWidget(KpiCard(title, value, icon, color))
            add_btn = ModernAddButton(QIcon(), tooltip, "#43a047", callback)
            add_btn.setText("+")
            add_btn.setFont(QFont("Segoe UI Emoji", 18, QFont.Bold))
            vbox.addWidget(add_btn, alignment=Qt.AlignHCenter)
            kpi_row.addLayout(vbox)
        dashboard_layout.addLayout(kpi_row)
        dashboard_layout.addStretch()
        self.content.addWidget(dashboard)
        # Add other pages
        self.content.addWidget(OrderGUI())
        self.content.addWidget(GrowingBedGUI())
        self.content.addWidget(CustomerGUI())
        self.content.addWidget(WarehouseGUI())
        self.content.addWidget(FarmVisualGUI())
        self.content.addWidget(AnalyticsApp())

    def change_page(self, page_name):
        page_index = {
            "dashboard": 0,
            "orders": 1,
            "growing_beds": 2,
            "customers": 3,
            "warehouse": 4,
            "farm_visual": 5,
            "analytics": 6
        }
        self.content.setCurrentIndex(page_index.get(page_name, 0))

    def add_floating_chat_button(self):
        if hasattr(self, 'chat_button') and self.chat_button:
            self.chat_button.deleteLater()
        self.chat_button = QPushButton(self)
        self.chat_button.setObjectName("floatingChatBtn")
        icon_path = os.path.join(os.path.dirname(__file__), "chat_logo.png")
        if os.path.exists(icon_path):
            self.chat_button.setIcon(QIcon(icon_path))
            self.chat_button.setIconSize(QSize(60, 60))
        else:
            self.chat_button.setText("💬")
        self.chat_button.setStyleSheet("""
            QPushButton#floatingChatBtn {
                background-color: #25d366;
                border-radius: 34px;
                padding: 0px;
                min-width: 68px;
                min-height: 68px;
                max-width: 68px;
                max-height: 68px;
                color: white;
                font-size: 38px;
                box-shadow: 0px 4px 16px rgba(0,0,0,0.18);
            }
            QPushButton#floatingChatBtn:hover {
                background-color: #128c7e;
            }
        """)
        self.chat_button.setCursor(Qt.PointingHandCursor)
        self.chat_button.clicked.connect(self.open_chat)
        self.position_floating_chat_button()
        self.chat_button.raise_()
        self.chat_button.show()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.position_floating_chat_button()

    def position_floating_chat_button(self):
        if hasattr(self, 'chat_button') and self.chat_button:
            margin = 32
            btn_size = 68
            x = self.width() - btn_size - margin
            y = self.height() - btn_size - margin
            self.chat_button.move(x, y)
            self.chat_button.raise_()
            self.chat_button.show()

    def open_chat(self):
        from ChatGUI import ChatGUI
        try:
            if not self.chat_gui:
                self.chat_gui = ChatGUI(self)
            self.chat_gui.show()
            self.chat_gui.raise_()
            self.chat_gui.activateWindow()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open AI Assistant: {str(e)}") 