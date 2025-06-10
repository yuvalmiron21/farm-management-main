from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFrame, QScrollArea, QMessageBox, QDialog, QStackedWidget, QSizePolicy
)
from PyQt5.QtGui import QFont, QIcon, QColor, QPixmap
from PyQt5.QtCore import Qt, QSize
from Order_gui import OrderGUI
from Growing_bed_gui import GrowingBedGUI
from Customer_gui import CustomerGUI
from WarehouseGUI import WarehouseGUI
from FarmVisualGUI import FarmVisualGUI
from AnalyticsApp import AnalyticsApp
from firebase_admin import db

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

        # Menu buttons
        self.buttons = []
        menu_items = [
            ("Dashboard", "dashboard", "fa:home"),
            ("Orders", "orders", "fa:archive"),
            ("Growing Beds", "growing_beds", "fa:leaf"),
            ("Customers", "customers", "fa:users"),
            ("Warehouse", "warehouse", "fa:warehouse"),
            ("Farm Visual", "farm_visual", "fa:tree"),
            ("Analytics", "analytics", "fa:chart-line")
        ]
        for text, name, _ in menu_items:
            btn = QPushButton(f"  {text}")
            btn.setCheckable(True)
            btn.setProperty("page", name)
            btn.clicked.connect(lambda checked, b=btn: self.button_clicked(b))
            layout.addWidget(btn)
            self.buttons.append(btn)
        layout.addStretch()
        # Logout button
        logout_btn = QPushButton("  Logout")
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
        self.parent().change_page(button.property("page"))

    def logout(self):
        from user_management import UserManagement
        UserManagement.logout_user(self.parent().username)
        self.parent().close()
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

class UserDashboard(QWidget):
    def __init__(self, username):
        super().__init__()
        self.username = username
        self.setWindowTitle(f"Mush | User Dashboard - {username}")
        self.setGeometry(100, 100, 1200, 800)
        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.sidebar = Sidebar(self)
        main_layout.addWidget(self.sidebar)
        self.content = QStackedWidget()
        self.content.setStyleSheet("background: #f8fafc;")
        main_layout.addWidget(self.content)
        self.init_pages()
        self.change_page("dashboard")

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
            ("Orders", kpi_data['orders'], "📦", "#e0f7fa", self.open_order_gui, "Add Order"),
            ("Customers", kpi_data['customers'], "👥", "#f3e5f5", self.open_customer_gui, "Add Customer"),
            ("Beds", kpi_data['beds'], "🌱", "#e8f5e9", self.open_growing_bed_gui, "Add Bed"),
            ("Warehouse", kpi_data['warehouse'], "🏪", "#fff3e0", self.open_warehouse_gui, "Add Warehouse Item")
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

    def open_order_gui(self):
        self.order_window = OrderGUI()
        self.order_window.show()

    def open_growing_bed_gui(self):
        self.growing_bed_window = GrowingBedGUI()
        self.growing_bed_window.show()

    def open_customer_gui(self):
        self.customer_window = CustomerGUI()
        self.customer_window.show()

    def open_warehouse_gui(self):
        self.warehouse_window = WarehouseGUI()
        self.warehouse_window.show() 