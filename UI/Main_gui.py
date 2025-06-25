import sys
import os
import pandas as pd
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget,
                             QPushButton, QMessageBox, QLabel, QFileDialog, QHBoxLayout,
                             QFrame, QComboBox, QRadioButton, QButtonGroup, QStackedWidget,
                             QScrollArea, QSizePolicy, QGraphicsDropShadowEffect, QLineEdit,
                             QTableWidget, QTableWidgetItem, QHeaderView, QStyledItemDelegate,
                             QToolButton, QMenu, QAction, QDialog, QSpacerItem, QGridLayout,
                             QGraphicsOpacityEffect, QGroupBox, QCheckBox)
from PyQt5.QtGui import QFont, QIcon, QColor, QPalette, QBrush, QPen, QPixmap, QFontDatabase
from PyQt5.QtCore import Qt, QSettings, QTranslator, QLocale, QTimer, QSize, QPoint, QPropertyAnimation, QEasingCurve
from firebase_admin import db, credentials, initialize_app
import firebase_admin
from Order_gui import OrderGUI
from GrowingBed_gui import GrowingBedGUI
from Customer_gui import CustomerGUI
from AnalyticsApp import AnalyticsApp
from FarmVisualGUI import FarmVisualGUI
from WarehouseGUI import WarehouseGUI
from AdminDashboard import AdminDashboard
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from collections import defaultdict
from datetime import datetime
import requests
from ChatGUI import ChatGUI
from user_management import UserManagement
from UI.UserManagementGUI import UserManagementGUI
from UI.live_simulation import MushroomSimulator
from db.cache_manager import CacheManager
from LoadingWindow import LoadingWindow
from SimpleLoadingWindow import SimpleLoadingWindow
import matplotlib.patheffects as patheffects
import matplotlib.patches as mpatches

# Initialize Firebase
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Current file location
PARENT_DIR = os.path.dirname(BASE_DIR)  # Parent directory
SERVICE_ACCOUNT_FILE = os.path.join(
    PARENT_DIR, "db", "farm-management-FireBase_credentials.json")
DATABASE_URL = "https://farm-management-86035-default-rtdb.europe-west1.firebasedatabase.app/"

# Check if the file exists
if not os.path.exists(SERVICE_ACCOUNT_FILE):
    raise FileNotFoundError(
        f"Could not find the Firebase credentials file at: {SERVICE_ACCOUNT_FILE}")

# Initialize Firebase only if not already initialized
if not firebase_admin._apps:
    cred = credentials.Certificate(SERVICE_ACCOUNT_FILE)
    initialize_app(cred, {"databaseURL": DATABASE_URL})

# Translation dictionaries for different languages
TRANSLATIONS = {
    'en': {
        'settings': 'Settings',
        'profile': 'Profile',
        'admin_name': 'Admin Name',
        'theme': 'Theme',
        'language': 'Language',
        'dark_mode': 'Dark Mode',
        'light_mode': 'Light Mode',
        'orders': 'Orders',
        'customers': 'Customers',
        'growing_beds': 'Growing Beds',
        'farm_visual': 'Farm Visual',
        'warehouse': 'Warehouse',
        'upload_excel': 'Upload Excel',
        'title': 'Mushroom Farm Management System',
        'dashboard': 'Dashboard',
        'logout': 'Logout',
        'view_analytics': 'View Analytics',
        'total_revenue': 'Total Revenue',
        'active_orders': 'Active Orders',
        'occupancy': 'Occupancy',
        'recent_orders': 'Recent Orders',
        'amount': 'Amount',
        'status': 'Status',
        'customer': 'Customer',
        'order_number': 'Order #',
        'alerts': 'Alerts: Critical Stock! | Delay in Order #1234 | ...',
        'revenue_over_time': 'Revenue Over Time',
        'bed_occupancy': 'Bed Occupancy',
    },
    'he': {
        'settings': 'הגדרות',
        'profile': 'פרופיל',
        'admin_name': 'שם מנהל',
        'theme': 'ערכת נושא',
        'language': 'שפה',
        'dark_mode': 'מצב כהה',
        'light_mode': 'מצב בהיר',
        'orders': 'הזמנות',
        'customers': 'לקוחות',
        'growing_beds': 'מצעי גידול',
        'farm_visual': 'תצוגת חווה',
        'warehouse': 'מחסן',
        'upload_excel': 'העלאת אקסל',
        'title': 'מערכת ניהול חוות פטריות'
    },
    'ar': {
        'settings': 'إعدادات',
        'profile': 'الملف الشخصي',
        'admin_name': 'اسم المشرف',
        'theme': 'المظهر',
        'language': 'اللغة',
        'dark_mode': 'الوضع الداكن',
        'light_mode': 'الوضع الفاتح',
        'orders': 'الطلبات',
        'customers': 'العملاء',
        'growing_beds': 'أسرّة النمو',
        'farm_visual': 'عرض المزرعة',
        'warehouse': 'المستودع',
        'upload_excel': 'تحميل إكسل',
        'title': 'نظام إدارة مزرعة الفطر'
    }
}

_cache_manager = CacheManager()

def get_monthly_revenue():
    ref = db.reference('Order')
    orders = ref.get() or {}
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    revenue_by_month = defaultdict(float)
    for order in orders.values():
        date_str = order.get('OrderDate', '')
        amount = float(order.get('TotalAmount', 0))
        try:
            if date_str:
                dt = datetime.strptime(date_str, '%Y-%m-%d')
                month_name = months[dt.month - 1]
                revenue_by_month[month_name] += amount
        except Exception:
            continue
    revenue = [revenue_by_month.get(m, 0) for m in months]
    return months, revenue

def get_bed_occupancy():
    beds = _cache_manager.get_data('GrowingBed') or {}
    stages = ['Spawn Run', 'Pinning', 'Fruiting', 'Harvesting', 'Empty']
    stage_counts = {stage: 0 for stage in stages}
    for bed in beds.values():
        stage = bed.get('CurrentGrowthStage', 'Empty')
        if stage in stage_counts:
            stage_counts[stage] += 1
        else:
            stage_counts['Empty'] += 1
    return stage_counts

def get_kpi_data():
    # Orders
    orders = _cache_manager.get_data('Order') or {}
    total_revenue = 0
    active_orders = 0
    active_statuses = {"Pending", "Processing", "Shipped"}
    for order in orders.values():
        try:
            total_revenue += float(order.get('TotalAmount', 0))
            if order.get('Status', '') in active_statuses:
                active_orders += 1
        except Exception:
            continue

    # Customers
    customers = _cache_manager.get_data('Customer') or {}
    num_customers = len(customers) if isinstance(customers, dict) else 0

    # Beds
    beds = _cache_manager.get_data('GrowingBed') or {}
    total_beds = len(beds)
    active_beds = sum(1 for bed in beds.values() if bed.get('CurrentGrowthStage', '') != 'Empty')
    occupancy = int((active_beds / total_beds) * 100) if total_beds > 0 else 0

    return {
        'total_revenue': total_revenue,
        'active_orders': active_orders,
        'num_customers': num_customers,
        'occupancy': occupancy
    }

def get_recent_orders(limit=10):
    orders = _cache_manager.get_data('Order') or {}
    # Sort by date descending
    def parse_date(order):
        try:
            return datetime.strptime(order.get('OrderDate', ''), '%Y-%m-%d')
        except Exception:
            return datetime.min
    sorted_orders = sorted(orders.values(), key=parse_date, reverse=True)
    # Get customer names if possible
    customers = _cache_manager.get_data('Customer') or {}
    def get_customer_name(cid):
        if not cid:
            return ""
        for cust in customers.values():
            if str(cust.get('ID', '')) == str(cid) or str(cust.get('CustomerID', '')) == str(cid):
                return cust.get('Name', cust.get('FullName', ''))
        return str(cid)
    recent = []
    for order in sorted_orders[:limit]:
        recent.append({
            'OrderID': order.get('OrderID', order.get('OrderKey', '')),
            'Customer': get_customer_name(order.get('CustomerID', '')),
            'Amount': float(order.get('TotalAmount', 0)),
            'Status': order.get('Status', ''),
            'OrderDate': order.get('OrderDate', '')
        })
    return recent

def get_alerts_from_firebase():
    alerts = []
    # Example: critical stock
    warehouse_ref = db.reference('Warehouse')
    warehouse = warehouse_ref.get() or {}
    for item in warehouse.values():
        if float(item.get('Stock', 0)) < 10:
            alerts.append(f"Critical stock: {item.get('Name', 'Unknown')}")
    # Example: delayed orders
    order_ref = db.reference('Order')
    orders = order_ref.get() or {}
    for order in orders.values():
        if order.get('Status') == 'Delayed':
            alerts.append(f"Order delayed: #{order.get('OrderID', order.get('OrderKey', ''))}")
    return alerts[:10]

def get_logged_in_user():
    users = _cache_manager.get_data('Users') or {}
    for user in users.values():
        if user.get('LoggedIn', False):
            return user
    return None

class StatusBadgeDelegate(QStyledItemDelegate):
    def __init__(self, status_colors, parent=None):
        super().__init__(parent)
        self.status_colors = status_colors

    def paint(self, painter, option, index):
        value = index.data()
        color = self.status_colors.get(value, "#616A6B")
        painter.save()
        rect = option.rect
        # Draw rounded rect badge
        painter.setRenderHint(painter.Antialiasing)
        painter.setBrush(QColor(color))
        painter.setPen(Qt.NoPen)
        badge_rect = rect.adjusted(8, 8, -8, -8)
        painter.drawRoundedRect(badge_rect, 12, 12)
        # Draw text
        painter.setPen(QColor("white"))
        font = QFont("Arial", 11, QFont.Bold)
        painter.setFont(font)
        painter.drawText(badge_rect, Qt.AlignCenter, str(value))
        painter.restore()

    def sizeHint(self, option, index):
        # Make the badge a bit taller
        size = super().sizeHint(option, index)
        size.setHeight(size.height() + 8)
        return size

class ModernKpiCard(QFrame):
    def __init__(self, title, value, icon, spark_data):
        super().__init__()
        color_map = {
            'Total Revenue': '#4F8EF7',
            'Active Orders': '#888888',  # gray
            'Customers': '#6C63FF',
            'Occupancy': '#00C48C'
        }
        color = color_map.get(title, '#4F8EF7')
        self.setMinimumHeight(150)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet("""
            QFrame {
                background: #fff;
                border-radius: 20px;
                border: 1.5px solid #e6e8ec;
            }
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(22)
        shadow.setColor(QColor(200, 200, 200, 60))
        shadow.setOffset(0, 6)
        self.setGraphicsEffect(shadow)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(22, 16, 22, 16)
        layout.setSpacing(12)
        # Left: icon + value + title (centered)
        left_col = QVBoxLayout()
        left_col.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        # Icon in colored circle
        icon_label = QLabel()
        icon_label.setFixedSize(44, 44)
        icon_label.setAlignment(Qt.AlignCenter)
        # Load icon from UI/dash KPI Icons
        import os
        icon_name = title.replace(' ', '') + '.png'  # e.g., ActiveOrders.png
        icon_path = os.path.join(os.path.dirname(__file__), 'dash KPI Icons', title + '.png')
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
            pixmap = pixmap.scaled(44, 44, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            icon_label.setPixmap(pixmap)
        else:
            icon_label.setText(icon)
            icon_label.setFont(QFont("Segoe UI Emoji", 26))
        left_col.addWidget(icon_label, alignment=Qt.AlignLeft)
        # Value
        value_label = QLabel(str(value))
        value_label.setFont(QFont("Segoe UI", 32, QFont.Bold))
        value_label.setStyleSheet("color: #23272e; margin-top: 4px; background: none; border: none;")
        value_label.setAlignment(Qt.AlignLeft)
        left_col.addWidget(value_label, alignment=Qt.AlignLeft)
        # Title
        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 15))
        title_label.setStyleSheet("color: #8b98a9; margin-top: 0px; background: none; border: none;")
        title_label.setAlignment(Qt.AlignLeft)
        left_col.addWidget(title_label, alignment=Qt.AlignLeft)
        left_col.addStretch(1)
        layout.addLayout(left_col, 2)
        # Right: sparkline
        spark = self.create_sparkline(spark_data, color)
        layout.addWidget(spark, 1)
    def create_sparkline(self, spark_data, color):
        fig = Figure(figsize=(1.8, 1.2), dpi=60)
        ax = fig.add_subplot(111)
        ax.plot(spark_data, color=color, linewidth=2.5)
        ax.fill_between(range(len(spark_data)), spark_data, color=color, alpha=0.13)
        ax.axis('off')
        fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
        canvas = FigureCanvas(fig)
        canvas.setFixedSize(90, 60)
        canvas.setStyleSheet("background: transparent; border: none;")
        return canvas

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(420)
        self.setStyleSheet("""
            QDialog {
                background: #f5f6fa;
            }
        """)
        # Main layout
        outer_layout = QVBoxLayout(self)
        outer_layout.setAlignment(Qt.AlignCenter)
        outer_layout.setContentsMargins(0, 60, 0, 0)
        # Card
        card = QFrame()
        card.setFixedWidth(420)
        card.setStyleSheet("""
            QFrame {
                background: #fff;
                border-radius: 18px;
                border: 1.5px solid #e0e6ed;
            }
        """)
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(22)
        shadow.setColor(QColor(200, 200, 200, 60))
        shadow.setOffset(0, 6)
        card.setGraphicsEffect(shadow)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(32, 32, 32, 32)
        card_layout.setSpacing(22)
        # Title
        title = QLabel("Settings")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        title.setStyleSheet("color: #23272e; margin-bottom: 8px;")
        card_layout.addWidget(title, alignment=Qt.AlignHCenter)
        # Theme
        theme_label = QLabel("Theme")
        theme_label.setFont(QFont("Segoe UI", 13, QFont.Bold))
        theme_label.setStyleSheet("color: #23272e; margin-bottom: 2px;")
        card_layout.addWidget(theme_label)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark"])
        self.theme_combo.setStyleSheet("font-size: 14px; padding: 8px; border: none; background: #f5f6fa;")
        card_layout.addWidget(self.theme_combo)
        # Notifications
        notif_label = QLabel("Notifications")
        notif_label.setFont(QFont("Segoe UI", 13, QFont.Bold))
        notif_label.setStyleSheet("color: #23272e; margin-bottom: 2px;")
        card_layout.addWidget(notif_label)
        self.notif_checkbox = QCheckBox("Enable notifications")
        self.notif_checkbox.setFont(QFont("Segoe UI", 12))
        card_layout.addWidget(self.notif_checkbox)
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)
        save_btn = QPushButton("Save")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setStyleSheet("""
            QPushButton {
                background: #43d39e;
                color: #fff;
                border-radius: 8px;
                font-size: 15px;
                font-weight: bold;
                padding: 10px 32px;
                border: none;
            }
            QPushButton:hover {
                background: #228B22;
            }
        """)
        save_btn.clicked.connect(self.save_settings)
        close_btn = QPushButton("Close")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: #e0e6ed;
                color: #23272e;
                border-radius: 8px;
                font-size: 15px;
                font-weight: bold;
                padding: 10px 32px;
                border: none;
            }
            QPushButton:hover {
                background: #b0b7c3;
            }
        """)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(close_btn)
        btn_layout.addStretch(1)
        card_layout.addLayout(btn_layout)
        # Add card to outer layout
        outer_layout.addStretch(1)
        outer_layout.addWidget(card, alignment=Qt.AlignHCenter)
        outer_layout.addStretch(1)
        self.setLayout(outer_layout)
        self.load_settings()

    def load_settings(self):
        settings = QSettings("MushFarm", "FarmManagement")
        theme = settings.value("theme", "Light")
        notifications = settings.value("notifications", "true") == "true"
        self.theme_combo.setCurrentText(theme)
        self.notif_checkbox.setChecked(notifications)

    def save_settings(self):
        settings = QSettings("MushFarm", "FarmManagement")
        theme = self.theme_combo.currentText()
        notifications = self.notif_checkbox.isChecked()
        settings.setValue("theme", theme)
        settings.setValue("notifications", "true" if notifications else "false")
        main_win = self.parentWidget()
        if hasattr(main_win, 'change_theme'):
            main_win.change_theme(theme.lower())
        QMessageBox.information(self, "Settings", "Settings saved successfully!")

class DashboardWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.kpi_data = get_kpi_data()
        self.init_ui()

    def init_ui(self):
        SIDE_MARGIN = 32
        INNER_SPACING = 24
        main_container = QWidget()
        main_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        grid = QGridLayout(main_container)
        grid.setSpacing(INNER_SPACING)
        grid.setContentsMargins(SIDE_MARGIN, SIDE_MARGIN, SIDE_MARGIN, SIDE_MARGIN)
        # --- KPI Row (4 columns) ---
        kpis = [
            ("Total Revenue", f"₪{self.kpi_data['total_revenue']:,.0f}", "💰", [100, 120, 90, 130, 150, 170, 160]),
            ("Active Orders", str(self.kpi_data['active_orders']), "📦", [10, 12, 8, 15, 13, 14, 16]),
            ("Customers", str(self.kpi_data['num_customers']), "👥", [200, 220, 210, 230, 250, 270, 260]),
            ("Occupancy", f"{self.kpi_data['occupancy']}%", "🌱", [60, 65, 70, 68, 72, 75, 80])
        ]
        kpi_cards = []
        for i, (title, value, icon, spark_data) in enumerate(kpis):
            kpi_card = ModernKpiCard(title, value, icon, spark_data)
            kpi_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            grid.addWidget(kpi_card, 0, i)
            kpi_cards.append(kpi_card)
        # הפוך את כל עמודות הגריד ל-Expanding
        for i in range(4):
            grid.setColumnStretch(i, 1)
        # --- Charts Row (2 charts, each spans 2 columns) ---
        revenue_card = QFrame()
        revenue_card.setStyleSheet('''
            QFrame {
                background: #fff;
                border-radius: 18px;
                border: 1.5px solid #e0e6ed;
                box-shadow: 0 4px 24px rgba(0,0,0,0.06);
            }
        ''')
        revenue_layout = QVBoxLayout(revenue_card)
        revenue_layout.setContentsMargins(24, 18, 24, 18)
        revenue_layout.setSpacing(0)
        revenue_chart = self.create_revenue_chart()
        revenue_chart.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        revenue_layout.addWidget(revenue_chart)
        revenue_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        grid.addWidget(revenue_card, 1, 0, 1, 2)
        occupancy_card = QFrame()
        occupancy_card.setStyleSheet('''
            QFrame {
                background: #fff;
                border-radius: 18px;
                border: 1.5px solid #e0e6ed;
                box-shadow: 0 4px 24px rgba(0,0,0,0.06);
            }
        ''')
        occupancy_layout = QVBoxLayout(occupancy_card)
        occupancy_layout.setContentsMargins(24, 18, 24, 18)
        occupancy_layout.setSpacing(0)
        occupancy_chart = self.create_occupancy_chart()
        occupancy_chart.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        occupancy_layout.addWidget(occupancy_chart)
        occupancy_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        grid.addWidget(occupancy_card, 1, 2, 1, 2)
        # --- Table (spans all columns) ---
        table_frame = QFrame()
        table_frame.setStyleSheet('''
            QFrame {
                background: #fff;
                border-radius: 18px;
                border: none;
                box-shadow: none;
            }
        ''')
        frame_layout = QVBoxLayout(table_frame)
        frame_layout.setContentsMargins(24, 18, 24, 18)
        frame_layout.setSpacing(0)
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["No", "Customer", "Amount", "Status", "Order Date"])
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        table.setAlternatingRowColors(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionMode(QTableWidget.NoSelection)
        table.setFocusPolicy(Qt.NoFocus)
        table.setStyleSheet('''
            QTableWidget {
                background: transparent;
                border: none;
                font-size: 12px;
                color: #23272e;
                font-family: 'Segoe UI';
            }
            QHeaderView::section {
                background: #f7f8fa;
                color: #8b98a9;
                font-size: 13px;
                font-weight: 600;
                border: none;
                border-bottom: 2px solid #e0e6ed;
                padding: 10px 0;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #e0e6ed;
                font-size: 12px;
            }
        ''')
        # Get real data
        data = get_recent_orders(10)
        table.setRowCount(len(data))
        status_colors = {
            "Paid": ("#e3f8f3", "#43d39e"),
            "Pending": ("#fff6e3", "#ff9800"),
            "Overdue": ("#ffe3e3", "#e74c3c"),
            "Processing": ("#e3e8ff", "#6C63FF"),
            "Shipped": ("#e3f0ff", "#2196f3"),
            "Delivered": ("#e3f8f3", "#43d39e"),
            "Completed": ("#e3f8f3", "#43d39e"),
            "Cancelled": ("#ffe3e3", "#e74c3c")
        }
        import hashlib
        color_palette = ["#43d39e", "#6C63FF", "#ff9800", "#228B22", "#b0b7c3"]
        for row, order in enumerate(data):
            # No
            item_no = QTableWidgetItem(str(row+1))
            item_no.setTextAlignment(Qt.AlignCenter)
            item_no.setFont(QFont("Segoe UI", 11))
            table.setItem(row, 0, item_no)
            # Customer name + Avatar
            customer_name = str(order['Customer'])
            customer_widget = QWidget()
            hbox = QHBoxLayout(customer_widget)
            hbox.setContentsMargins(0, 0, 0, 0)
            hbox.setSpacing(8)
            # Avatar
            color_idx = int(hashlib.md5(customer_name.encode()).hexdigest(), 16) % len(color_palette)
            bg_color = color_palette[color_idx]
            first_letter = customer_name[0].upper() if customer_name else "?"
            avatar_label = QLabel()
            avatar_label.setFixedSize(24, 24)
            avatar_label.setAlignment(Qt.AlignCenter)
            avatar_label.setStyleSheet(f"background: {bg_color}; border-radius: 12px; color: #fff; font-size: 12px; font-weight: bold; border: 2px solid #fff;")
            avatar_label.setText(first_letter)
            # Name
            name_label = QLabel(customer_name)
            name_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
            name_label.setStyleSheet("color: #23272e; background: none; border: none;")
            hbox.addWidget(avatar_label)
            hbox.addWidget(name_label)
            hbox.addStretch(1)
            table.setCellWidget(row, 1, customer_widget)
            # Amount
            item_amount = QTableWidgetItem(f"₪{order['Amount']:,.2f}")
            item_amount.setTextAlignment(Qt.AlignCenter)
            item_amount.setFont(QFont("Segoe UI", 12, QFont.Bold))
            table.setItem(row, 2, item_amount)
            # Status (תגית צבעונית)
            status = str(order['Status'])
            status_bg, status_fg = status_colors.get(status, ("#e0e6ed", "#23272e"))
            status_label = QLabel(status)
            status_label.setAlignment(Qt.AlignCenter)
            status_label.setStyleSheet(f"background: {status_bg}; color: {status_fg}; border-radius: 12px; padding: 2px 12px; font-size: 11px; font-weight: bold;")
            table.setCellWidget(row, 3, status_label)
            # Order Date (מתוך order)
            order_date = order.get('OrderDate', '')
            item_date = QTableWidgetItem(order_date)
            item_date.setTextAlignment(Qt.AlignCenter)
            item_date.setFont(QFont("Segoe UI", 11))
            table.setItem(row, 4, item_date)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        frame_layout.addWidget(table)
        table_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        grid.addWidget(table_frame, 2, 0, 1, 4)
        # --- Center everything ---
        outer_layout = QHBoxLayout(self)
        outer_layout.setContentsMargins(40, 0, 40, 0)  # שוליים של 40 פיקסל מימין ומשמאל
        outer_layout.addWidget(main_container)
        self.setLayout(outer_layout)

    def create_revenue_chart(self):
        months, revenue = get_monthly_revenue()
        fig = Figure(figsize=(6, 4))
        ax = fig.add_subplot(111)
        # קו ירוק מודרני
        line, = ax.plot(months, revenue, marker='o', color='#43d39e', linewidth=2.5, zorder=3)
        # נקודות לבנות עם גבול ירוק
        ax.scatter(months, revenue, color='#fff', edgecolor='#43d39e', s=80, zorder=4, linewidth=2)
        # צללית ירוקה בהירה
        ax.fill_between(months, revenue, color='#43d39e', alpha=0.10, zorder=2)
        # רקע לבן
        fig.patch.set_facecolor('white')
        ax.set_facecolor('white')
        # צירים וטקסט אפור בהיר
        ax.tick_params(axis='x', colors='#b0b7c3', labelsize=12)
        ax.tick_params(axis='y', colors='#b0b7c3', labelsize=12)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#e0e6ed')
        ax.spines['bottom'].set_color('#e0e6ed')
        # grid עדין
        ax.grid(True, linestyle='--', alpha=0.25, color='#b0b7c3', zorder=1)
        ax.set_title('Revenue Over Time', fontsize=16, color='#23272e', pad=18)
        fig.tight_layout()
        canvas = FigureCanvas(fig)
        canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # Tooltip מודרני
        annot = ax.annotate("", xy=(0,0), xytext=(15,15), textcoords="offset points",
                            bbox=dict(boxstyle="round,pad=0.4", fc="#fff", ec="#43d39e", lw=1.5, alpha=0.95, zorder=10),
                            arrowprops=dict(arrowstyle="->", color="#43d39e"))
        annot.set_visible(False)
        def update_annot(ind):
            x, y = line.get_data()
            idx = ind["ind"][0]
            annot.xy = (x[idx], y[idx])
            text = f"{months[idx]}: ₪{y[idx]:,.2f}"
            annot.set_text(text)
            annot.get_bbox_patch().set_facecolor("#fff")
            annot.get_bbox_patch().set_edgecolor("#43d39e")
            annot.get_bbox_patch().set_alpha(0.97)
        def hover(event):
            vis = annot.get_visible()
            if event.inaxes == ax:
                cont, ind = line.contains(event)
                if cont:
                    update_annot(ind)
                    annot.set_visible(True)
                    canvas.draw_idle()
                else:
                    if vis:
                        annot.set_visible(False)
                        canvas.draw_idle()
        canvas.mpl_connect("motion_notify_event", hover)
        return canvas

    def create_occupancy_chart(self):
        import matplotlib.patches as mpatches
        stage_counts = get_bed_occupancy()
        labels = list(stage_counts.keys())
        sizes = list(stage_counts.values())
        colors = ['#43d39e', '#b0b7c3', '#6C63FF', '#228B22', '#e0e6ed']

        fig = Figure(figsize=(6, 4))
        gs = fig.add_gridspec(1, 2, width_ratios=[2.5, 1], wspace=0.01)
        ax = fig.add_subplot(gs[0, 0])
        ax_legend = fig.add_subplot(gs[0, 1])
        ax_legend.axis('off')

        wedges, texts, autotexts = ax.pie(
            sizes,
            labels=labels,
            colors=colors,
            autopct='%1.1f%%',
            startangle=90,
            wedgeprops=dict(width=0.35, edgecolor='white'),
            textprops={'color': '#23272e', 'fontsize': 13},
            pctdistance=0.80
        )
        for autotext in autotexts:
            autotext.set_color('#23272e')
            autotext.set_fontsize(10)
            autotext.set_fontweight('bold')
            autotext.set_path_effects([patheffects.withStroke(linewidth=2, foreground='white')])

        # כותרת מעל הפאי, מיושרת שמאלה
        ax.set_title('Bed Occupancy', fontsize=16, color='#23272e', pad=18, loc='left')

        # Legend custom
        y0 = 0.85
        dy = 0.18
        ax_legend.text(0, 1.05, "Stage (Beds)", fontsize=13, color="#23272e", fontweight='bold')
        for i, (label, count, color) in enumerate(zip(labels, sizes, colors)):
            y = y0 - i * dy
            # עיגול צבעוני קטן יותר
            circ = mpatches.Circle((0.05, y), 0.025, color=color, transform=ax_legend.transAxes, clip_on=False)
            ax_legend.add_patch(circ)
            ax_legend.text(0.13, y, label, fontsize=12, color="#23272e", va='center', ha='left')
            ax_legend.text(0.85, y, str(count), fontsize=14, color="#23272e", va='center', ha='right', fontweight='bold')

        fig.tight_layout()
        canvas = FigureCanvas(fig)
        canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # הוספת hover effect
        def on_move(event):
            found = False
            for i, wedge in enumerate(wedges):
                if wedge.contains_point([event.x, event.y], radius=1.5):
                    wedge.set_alpha(0.7)
                    percent = (sizes[i] / sum(sizes) * 100) if sum(sizes) > 0 else 0
                    ax.set_title(f"{labels[i]}: {sizes[i]} beds ({percent:.1f}%)", fontsize=16, color='#43d39e', loc='left')
                    found = True
                else:
                    wedge.set_alpha(1.0)
            if not found:
                ax.set_title('Bed Occupancy', fontsize=16, color='#23272e', loc='left')
            canvas.draw_idle()
        canvas.mpl_connect('motion_notify_event', on_move)

        return canvas

    def create_orders_table(self):
        # עטיפת הטבלה ב-QFrame מודרני
        table_frame = QFrame()
        table_frame.setStyleSheet('''
            QFrame {
                background: #fff;
                border-radius: 18px;
                border: none;
                box-shadow: none;
            }
        ''')
        frame_layout = QVBoxLayout(table_frame)
        frame_layout.setContentsMargins(24, 18, 24, 18)
        frame_layout.setSpacing(0)
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["No", "Customer", "Amount", "Status", "Order Date"])
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        table.setAlternatingRowColors(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionMode(QTableWidget.NoSelection)
        table.setFocusPolicy(Qt.NoFocus)
        table.setStyleSheet('''
            QTableWidget {
                background: transparent;
                border: none;
                font-size: 12px;
                color: #23272e;
                font-family: 'Segoe UI';
            }
            QHeaderView::section {
                background: #f7f8fa;
                color: #8b98a9;
                font-size: 13px;
                font-weight: 600;
                border: none;
                border-bottom: 2px solid #e0e6ed;
                padding: 10px 0;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #e0e6ed;
                font-size: 12px;
            }
        ''')
        # Get real data
        data = get_recent_orders(10)
        table.setRowCount(len(data))
        status_colors = {
            "Paid": ("#e3f8f3", "#43d39e"),
            "Pending": ("#fff6e3", "#ff9800"),
            "Overdue": ("#ffe3e3", "#e74c3c"),
            "Processing": ("#e3e8ff", "#6C63FF"),
            "Shipped": ("#e3f0ff", "#2196f3"),
            "Delivered": ("#e3f8f3", "#43d39e"),
            "Completed": ("#e3f8f3", "#43d39e"),
            "Cancelled": ("#ffe3e3", "#e74c3c")
        }
        import hashlib
        color_palette = ["#43d39e", "#6C63FF", "#ff9800", "#228B22", "#b0b7c3"]
        for row, order in enumerate(data):
            # No
            item_no = QTableWidgetItem(str(row+1))
            item_no.setTextAlignment(Qt.AlignCenter)
            item_no.setFont(QFont("Segoe UI", 11))
            table.setItem(row, 0, item_no)
            # Customer name + Avatar
            customer_name = str(order['Customer'])
            customer_widget = QWidget()
            hbox = QHBoxLayout(customer_widget)
            hbox.setContentsMargins(0, 0, 0, 0)
            hbox.setSpacing(8)
            # Avatar
            color_idx = int(hashlib.md5(customer_name.encode()).hexdigest(), 16) % len(color_palette)
            bg_color = color_palette[color_idx]
            first_letter = customer_name[0].upper() if customer_name else "?"
            avatar_label = QLabel()
            avatar_label.setFixedSize(24, 24)
            avatar_label.setAlignment(Qt.AlignCenter)
            avatar_label.setStyleSheet(f"background: {bg_color}; border-radius: 12px; color: #fff; font-size: 12px; font-weight: bold; border: 2px solid #fff;")
            avatar_label.setText(first_letter)
            # Name
            name_label = QLabel(customer_name)
            name_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
            name_label.setStyleSheet("color: #23272e; background: none; border: none;")
            hbox.addWidget(avatar_label)
            hbox.addWidget(name_label)
            hbox.addStretch(1)
            table.setCellWidget(row, 1, customer_widget)
            # Amount
            item_amount = QTableWidgetItem(f"₪{order['Amount']:,.2f}")
            item_amount.setTextAlignment(Qt.AlignCenter)
            item_amount.setFont(QFont("Segoe UI", 12, QFont.Bold))
            table.setItem(row, 2, item_amount)
            # Status (תגית צבעונית)
            status = str(order['Status'])
            status_bg, status_fg = status_colors.get(status, ("#e0e6ed", "#23272e"))
            status_label = QLabel(status)
            status_label.setAlignment(Qt.AlignCenter)
            status_label.setStyleSheet(f"background: {status_bg}; color: {status_fg}; border-radius: 12px; padding: 2px 12px; font-size: 11px; font-weight: bold;")
            table.setCellWidget(row, 3, status_label)
            # Order Date (מתוך order)
            order_date = order.get('OrderDate', '')
            item_date = QTableWidgetItem(order_date)
            item_date.setTextAlignment(Qt.AlignCenter)
            item_date.setFont(QFont("Segoe UI", 11))
            table.setItem(row, 4, item_date)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        frame_layout.addWidget(table)
        return table_frame

class ModernSidebar(QFrame):
    def __init__(self, parent=None, nav_callbacks=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setStyleSheet("""
            QFrame#sidebar {
                background: #1A2238;
                min-width: 240px;
                max-width: 240px;
            }
            QPushButton {
                color: #fff;
                border: none;
                text-align: left;
                padding: 15px 25px;
                font-size: 15px;
                font-weight: 600;
                font-family: 'Segoe UI', Arial, sans-serif;
                border-radius: 8px;
                margin: 2px 10px;
            }
            QPushButton:hover {
                background: #353b48;
                color: #f1c40f;
            }
            QPushButton:checked {
                background: #43a047;
                color: white;
                font-weight: bold;
            }
        """)
        self.nav_callbacks = nav_callbacks
        self.collapsed = False
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        # --- Modern Logo/Title Section ---
        logo_frame = QFrame()
        logo_frame.setStyleSheet("background: transparent;")
        logo_layout = QVBoxLayout(logo_frame)
        logo_layout.setContentsMargins(0, 24, 0, 0)
        logo_layout.setSpacing(0)
        # לוגו (שחור-לבן)
        logo_icon = QLabel()
        logo_icon.setAlignment(Qt.AlignHCenter)
        logo_icon.setFixedSize(48, 48)
        logo_path = os.path.join(os.path.dirname(__file__), "logo_blackAndWhite.png")
        if os.path.exists(logo_path):
            pix = QPixmap(logo_path)
            pix = pix.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_icon.setPixmap(pix)
        else:
            logo_icon.setText("🌱")
            logo_icon.setFont(QFont("Segoe UI Emoji", 32))
            logo_icon.setStyleSheet("color: #fff;")
        logo_layout.addWidget(logo_icon, alignment=Qt.AlignHCenter)
        # כותרת MUSH
        title = QLabel("MUSH")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        title.setStyleSheet("color: #fff; letter-spacing: 2px;")
        title.setAlignment(Qt.AlignHCenter)
        logo_layout.addWidget(title, alignment=Qt.AlignHCenter)
        logo_layout.addSpacing(6)
        # שורת minimize
        min_row = QHBoxLayout()
        min_row.setContentsMargins(0, 8, 0, 0)
        min_row.setSpacing(0)
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Plain)
        line.setStyleSheet("color: #2e335a; background: #2e335a; min-height: 1px; max-height: 1px;")
        line.setFixedWidth(90)
        min_row.addWidget(line, stretch=0)
        min_row.addStretch(1)
        minimize_btn = QPushButton("< Minimize")
        minimize_btn.setFixedHeight(22)
        minimize_btn.setCursor(Qt.PointingHandCursor)
        minimize_btn.setStyleSheet("background: none; color: #b0b7c3; font-size: 15px; border: none; font-weight: 400; padding-left: 10px; padding-right: 8px;")
        minimize_btn.clicked.connect(self.toggle_collapse)
        min_row.addWidget(minimize_btn)
        logo_layout.addLayout(min_row)
        layout.addWidget(logo_frame)
        layout.addSpacing(10)
        # --- הצג/הסתר כותרות בהתאם למצב ---
        def update_logo_visibility():
            if self.collapsed:
                title.setVisible(False)
                logo_icon.setVisible(True)
            else:
                title.setVisible(True)
                logo_icon.setVisible(True)
        update_logo_visibility()
        self._update_logo_visibility = update_logo_visibility
        # Menu buttons
        self.buttons = []
        self.menu_items = [
            ("Dashboard", "dashboard", "Dashboard.png"),
            ("Admin Dashboard", "admin_dashboard", "Admin Dashboard.png"),
            ("Orders", "orders", "Orders.png"),
            ("Growing Beds", "growing_beds", "Growing Beds.png"),
            ("Customers", "customers", "Customers.png"),
            ("Warehouse", "warehouse", "Warehouse.png"),
            ("Farm Visual", "farm_visual", "Farm Visual.png"),
            ("Analytics", "analytics", "Analytics.png"),
            ("User Management", "user_management", "User Management.png"),
            ("Live Simulation", "live_simulation", "Live Simulation.png"),
            ("Settings", "settings", "Settings.png")
        ]
        for text, name, icon_file in self.menu_items:
            btn = QPushButton()
            btn.setCheckable(True)
            btn.setProperty("page", name)
            btn.clicked.connect(lambda checked, b=btn: self.button_clicked(b))
            
            # Load icon from file
            icon_path = os.path.join(os.path.dirname(__file__), "Menu icons", icon_file)
            if os.path.exists(icon_path):
                icon = QIcon(icon_path)
                btn.setIcon(icon)
                btn.setIconSize(QSize(24, 24))
                btn.setText(f"  {text}")
            else:
                # Fallback to emoji if icon file not found
                fallback_icons = {
                    "Dashboard": "📊",
                    "Admin Dashboard": "👑",
                    "Orders": "📦",
                    "Growing Beds": "🛏️",
                    "Customers": "👥",
                    "Warehouse": "🏪",
                    "Farm Visual": "🌾",
                    "Analytics": "📈",
                    "User Management": "👤",
                    "Live Simulation": "🧪",
                    "Settings": "⚙️"
                }
                btn.setText(f"{fallback_icons.get(text, '📋')}  {text}")
            
            layout.addWidget(btn)
            self.buttons.append(btn)
        layout.addStretch()

    def toggle_collapse(self):
        self.collapsed = not self.collapsed
        if self.collapsed:
            self.setFixedWidth(80)
            for i, btn in enumerate(self.buttons):
                icon_file = self.menu_items[i][2]
                icon_path = os.path.join(os.path.dirname(__file__), "Menu icons", icon_file)
                if os.path.exists(icon_path):
                    btn.setIcon(QIcon(icon_path))
                    btn.setIconSize(QSize(28, 28))
                    btn.setText("")
                else:
                    # Fallback to emoji
                    fallback_icons = {
                        "Dashboard": "📊",
                        "Admin Dashboard": "👑",
                        "Orders": "📦",
                        "Growing Beds": "🛏️",
                        "Customers": "👥",
                        "Warehouse": "🏪",
                        "Farm Visual": "🌾",
                        "Analytics": "📈",
                        "User Management": "👤",
                        "Live Simulation": "🧪",
                        "Settings": "⚙️"
                    }
                    text = self.menu_items[i][0]
                    btn.setText(fallback_icons.get(text, "📋"))
                btn.setStyleSheet("font-size: 20px; color: #fff; background: none; border: none; text-align: center; padding: 15px 0px;")
            # עדכן את כפתור ה-Minimize
            for child in self.findChildren(QPushButton):
                if child.text() == "< Minimize":
                    child.setText("> Expand")
                    break
        else:
            self.setFixedWidth(240)
            for i, btn in enumerate(self.buttons):
                text = self.menu_items[i][0]
                icon_file = self.menu_items[i][2]
                icon_path = os.path.join(os.path.dirname(__file__), "Menu icons", icon_file)
                if os.path.exists(icon_path):
                    btn.setIcon(QIcon(icon_path))
                    btn.setIconSize(QSize(24, 24))
                    btn.setText(f"  {text}")
                else:
                    # Fallback to emoji
                    fallback_icons = {
                        "Dashboard": "📊",
                        "Admin Dashboard": "👑",
                        "Orders": "📦",
                        "Growing Beds": "🛏️",
                        "Customers": "👥",
                        "Warehouse": "🏪",
                        "Farm Visual": "🌾",
                        "Analytics": "📈",
                        "User Management": "👤",
                        "Live Simulation": "🧪",
                        "Settings": "⚙️"
                    }
                    btn.setText(f"{fallback_icons.get(text, '📋')}  {text}")
                    btn.setIcon(QIcon())
                btn.setStyleSheet("")
            # עדכן את כפתור ה-Minimize
            for child in self.findChildren(QPushButton):
                if child.text() == "> Expand":
                    child.setText("< Minimize")
                    break
            self.update()
        # עדכן הצגת כותרות/לוגו
        if hasattr(self, '_update_logo_visibility'):
            self._update_logo_visibility()

    def button_clicked(self, button):
        for btn in self.buttons:
            btn.setChecked(btn == button)
        if self.nav_callbacks and button.property("page") in self.nav_callbacks:
            self.nav_callbacks[button.property("page")]()

class Main_gui(QMainWindow):
    def __init__(self, user_data):
        super().__init__()
        self.user_data = user_data
        self.chat_button = None
        self.chat_gui = None
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        
        # Show loading window first
        self.loading_window = SimpleLoadingWindow()
        self.loading_window.show()
        
        # Set default font for the entire application
        self.set_font()
        
        # Initialize UI components immediately
        self.init_ui()
        
        # The logout signal is handled by the ModernSidebar, so no connection is needed here.
        # if hasattr(self, 'user_dashboard') and self.user_dashboard:
        #      self.user_dashboard.logout_successful.connect(self.handle_logout)

        self.add_floating_chat_button()
        self.show_dashboard()  # Show dashboard by default
        self.showMaximized()
        self._old_pos = None

    def set_font(self):
        # Set Segoe UI as the default font for the entire application
        app_font = QFont("Segoe UI", 11, QFont.Bold)
        app_font.setStyleStrategy(QFont.PreferAntialias)
        QApplication.setFont(app_font)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
        # Apply QSS for all widgets
        QApplication.instance().setStyleSheet(f"""
            * {{
                font-family: 'Segoe UI';
                font-size: 11pt;
                font-weight: 600;
            }}
            QLabel, QPushButton, QComboBox, QLineEdit, QTableWidget, QHeaderView::section, QTableWidget::item, QMenu, QToolButton {{
                font-family: 'Segoe UI';
                font-weight: 600;
            }}
        """)

    def init_ui(self):
        self.setWindowTitle("Mushroom Farm Management System")
        self.setMinimumSize(1200, 800)
        self.setStyleSheet("""
            QMainWindow {
                background: #f5f6fa;
                font-family: 'Segoe UI';
                font-weight: 600;
            }
            QLabel {
                color: #2d3436;
                font-family: 'Segoe UI';
                font-weight: 600;
            }
            QPushButton {
                font-family: 'Segoe UI';
                font-weight: 600;
            }
            QComboBox {
                font-family: 'Segoe UI';
                font-weight: 600;
            }
            QLineEdit {
                font-family: 'Segoe UI';
                font-weight: 600;
            }
            QTableWidget {
                font-family: 'Segoe UI';
                font-weight: 600;
                font-size: 13px;
            }
            QHeaderView::section {
                font-family: 'Segoe UI';
                font-weight: 600;
                font-size: 14px;
            }
            QTableWidget::item {
                font-family: 'Segoe UI';
                font-weight: 600;
                font-size: 12px;
            }
            QMenu {
                font-family: 'Segoe UI';
                font-weight: 600;
            }
            QToolButton {
                font-family: 'Segoe UI';
                font-weight: 600;
            }
        """)
        self.setup_navigation()
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
        logo_path = os.path.join(os.path.dirname(__file__), "logo_without_white.png")
        pix = QPixmap(logo_path)
        pix = pix.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        logo.setPixmap(pix)
        logo.setFixedSize(32, 32)
        title_layout.addWidget(logo)
        title_label = QLabel("Mush | Farm Management System")
        title_label.setStyleSheet("color: #fff; font-size: 16px; font-weight: bold;")
        title_layout.addWidget(title_label)
        title_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        # --- Notification Bell Button ---
        self.bell_btn = QToolButton()
        self.bell_btn.setObjectName("notificationBell")
        bell_icon_path = os.path.join(os.path.dirname(__file__), "bell_icon.png")
        if os.path.exists(bell_icon_path):
            self.bell_btn.setIcon(QIcon(bell_icon_path))
        else:
            self.bell_btn.setText("🔔")
        self.bell_btn.setIconSize(QSize(24, 24))
        self.bell_btn.setStyleSheet("""
            QToolButton#notificationBell {
                background: none;
                border: none;
                color: #fff;
                font-size: 20px;
                padding: 0 8px;
            }
            QToolButton#notificationBell:hover {
                color: #f1c40f;
            }
        """)
        self.bell_btn.setCursor(Qt.PointingHandCursor)
        self.bell_btn.setPopupMode(QToolButton.InstantPopup)
        self.bell_menu = QMenu(self)
        self.bell_menu.setStyleSheet("""
            QMenu {
                background: #23272e;
                color: #fff;
                border-radius: 8px;
                padding: 8px 0;
                font-size: 15px;
                min-width: 260px;
            }
            QMenu::item {
                padding: 8px 18px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background: #353b48;
                color: #f1c40f;
            }
        """)
        self.bell_btn.setMenu(self.bell_menu)
        self.bell_btn.clicked.connect(self.refresh_alerts_menu)
        # Add bell button before minimize/max/close
        title_layout.insertWidget(title_layout.count()-3, self.bell_btn)
        # --- Red dot for new alerts ---
        self.bell_red_dot = QLabel(self.bell_btn)
        self.bell_red_dot.setFixedSize(12, 12)
        self.bell_red_dot.move(20, 2)
        self.bell_red_dot.setStyleSheet("background: #e74c3c; border-radius: 6px; border: 2px solid #23272e;")
        self.bell_red_dot.hide()
        self.refresh_alerts_menu()
        # --- End Notification Bell ---
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
        # --- Modern Header Bar ---
        header_bar = QFrame()
        header_bar.setObjectName("headerBar")
        header_bar.setStyleSheet('''
            QFrame#headerBar {
                background: #fff;
                min-height: 64px;
                max-height: 64px;
                border-bottom: 1.5px solid #f0f1f3;
                border-radius: 0 0 18px 0;
                box-shadow: 0 2px 12px rgba(44,62,80,0.04);
            }
        ''')
        header_layout = QHBoxLayout(header_bar)
        header_layout.setContentsMargins(32, 0, 32, 0)
        header_layout.setSpacing(18)
        # Welcome text
        username = self.user_data.get('username', 'Admin')
        welcome_label = QLabel(f"Welcome Back, {username} 👋")
        welcome_label.setFont(QFont("Segoe UI", 20, QFont.Bold))
        welcome_label.setStyleSheet("color: #23272e; margin-right: 8px;")
        header_layout.addWidget(welcome_label, alignment=Qt.AlignVCenter)
        # Spacer
        header_layout.addStretch(1)
        # Chat button
        chat_btn = QPushButton()
        chat_btn.setObjectName("chatBtn")
        chat_btn.setCursor(Qt.PointingHandCursor)
        chat_btn.setFixedSize(38, 38)
        chat_btn.setStyleSheet('''
            QPushButton#chatBtn {
                background: #25d366;
                border-radius: 19px;
                color: white;
                font-size: 20px;
                border: none;
            }
            QPushButton#chatBtn:hover {
                background: #128c7e;
            }
        ''')
        chat_btn.setText("💬")
        chat_btn.clicked.connect(self.open_chat)
        header_layout.addWidget(chat_btn, alignment=Qt.AlignVCenter)
        # Notification bell (reuse existing)
        self.bell_btn.setParent(header_bar)
        self.bell_btn.setStyleSheet(self.bell_btn.styleSheet() + "QToolButton { margin-left: 8px; margin-right: 8px; }")
        header_layout.addWidget(self.bell_btn, alignment=Qt.AlignVCenter)
        # Avatar + menu
        avatar_btn = QToolButton()
        avatar_btn.setObjectName("avatarBtn")
        avatar_btn.setCursor(Qt.PointingHandCursor)
        avatar_btn.setFixedSize(40, 40)
        avatar_btn.setStyleSheet('''
            QToolButton#avatarBtn {
                background: #e3f8f3;
                border-radius: 20px;
                border: 2px solid #fff;
                padding: 0;
            }
        ''')
        # Try to load user image, else initials
        avatar_pix = None
        user_img_path = os.path.join(os.path.dirname(__file__), "user_avatar.png")
        if os.path.exists(user_img_path):
            avatar_pix = QPixmap(user_img_path).scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        if avatar_pix:
            avatar_btn.setIcon(QIcon(avatar_pix))
            avatar_btn.setIconSize(QSize(40, 40))
        else:
            initials = ''.join([w[0] for w in username.split()][:2]).upper()
            avatar_btn.setText(initials)
            avatar_btn.setFont(QFont("Segoe UI", 15, QFont.Bold))
            avatar_btn.setStyleSheet(avatar_btn.styleSheet() + "color: #23272e;")
        # Menu
        avatar_menu = QMenu(self)
        avatar_menu.setStyleSheet('''
            QMenu {
                background: #fff;
                color: #23272e;
                border-radius: 10px;
                padding: 8px 0;
                font-size: 15px;
                min-width: 180px;
                box-shadow: 0 2px 12px rgba(44,62,80,0.08);
            }
            QMenu::item {
                padding: 10px 22px;
                border-radius: 6px;
            }
            QMenu::item:selected {
                background: #e3f8f3;
                color: #43d39e;
            }
        ''')
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.show_settings)
        user_mgmt_action = QAction("User Management", self)
        user_mgmt_action.triggered.connect(self.show_user_management)
        logout_action = QAction("Logout", self)
        logout_action.triggered.connect(self.handle_logout)
        avatar_menu.addAction(settings_action)
        avatar_menu.addAction(user_mgmt_action)
        avatar_menu.addSeparator()
        avatar_menu.addAction(logout_action)
        avatar_btn.setMenu(avatar_menu)
        avatar_btn.setPopupMode(QToolButton.InstantPopup)
        header_layout.addWidget(avatar_btn, alignment=Qt.AlignVCenter)
        main_layout.addWidget(header_bar)
        # Content area
        content_frame = QFrame()
        content_layout = QHBoxLayout(content_frame)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        # Sidebar
        self.sidebar = ModernSidebar(self, self.nav_callbacks)
        content_layout.addWidget(self.sidebar)
        # Main content vertical layout (header + content)
        main_content_widget = QWidget()
        main_content_layout = QVBoxLayout(main_content_widget)
        main_content_layout.setContentsMargins(0, 0, 0, 0)
        main_content_layout.setSpacing(0)
        main_content_layout.addWidget(header_bar)
        # Content area
        self.content_area = QStackedWidget()
        self.content_area.setStyleSheet("""
            QStackedWidget {
                background: #f5f6fa;
            }
        """)
        main_content_layout.addWidget(self.content_area)
        content_layout.addWidget(main_content_widget)
        main_layout.addWidget(content_frame)
        # Initialize all pages
        self.init_pages()
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

    def setup_navigation(self):
        self.nav_callbacks = {
            "dashboard": self.show_dashboard,
            "admin_dashboard": self.show_admin_dashboard,
            "orders": self.show_orders,
            "growing_beds": self.show_growing_beds,
            "customers": self.show_customers,
            "warehouse": self.show_warehouse,
            "farm_visual": self.show_farm_visual,
            "analytics": self.show_analytics,
            "user_management": self.show_user_management,
            "live_simulation": self.show_live_simulation,
            "settings": self.show_settings
        }

    def show_dashboard(self):
        self.content_area.setCurrentWidget(self.dashboard_page)
        self.update_page_title("Dashboard")

    def show_admin_dashboard(self):
        self.content_area.setCurrentWidget(self.admin_dashboard_page)
        self.update_page_title("Admin Dashboard")

    def show_orders(self):
        self.content_area.setCurrentWidget(self.orders_page)
        self.update_page_title("Orders")

    def show_growing_beds(self):
        self.content_area.setCurrentWidget(self.growing_beds_page)
        self.update_page_title("Growing Beds")

    def show_customers(self):
        self.content_area.setCurrentWidget(self.customers_page)
        self.update_page_title("Customers")

    def show_warehouse(self):
        self.content_area.setCurrentWidget(self.warehouse_page)
        self.update_page_title("Warehouse")

    def show_farm_visual(self):
        self.content_area.setCurrentWidget(self.farm_visual_page)
        self.update_page_title("Farm Visual")

    def show_analytics(self):
        self.content_area.setCurrentWidget(self.analytics_page)
        self.update_page_title("Analytics")

    def show_user_management(self):
        self.content_area.setCurrentWidget(self.user_management_page)
        self.update_page_title("User Management")

    def show_live_simulation(self):
        self.content_area.setCurrentWidget(self.live_simulation_page)
        self.update_page_title("Live Simulation")

    def show_settings(self):
        self.content_area.setCurrentWidget(self.settings_page)
        self.update_page_title("Settings")

    def update_page_title(self, title):
        self.setWindowTitle(f"Mushroom Farm Management System - {title}")

    def init_admin_dashboard(self):
        layout = QVBoxLayout(self.admin_dashboard_page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        admin_dashboard = AdminDashboard()
        layout.addWidget(admin_dashboard)

    def init_user_management_page(self):
        layout = QVBoxLayout(self.user_management_page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        user_management_widget = UserManagementGUI()
        layout.addWidget(user_management_widget)

    def add_floating_chat_button(self):
        print('[DEBUG] add_floating_chat_button called')
        if hasattr(self, 'chat_button') and self.chat_button:
            print('[DEBUG] Deleting existing chat_button')
            self.chat_button.deleteLater()
        self.chat_button = QPushButton(self)
        self.chat_button.setObjectName("floatingChatBtn")
        icon_path = os.path.join(os.path.dirname(__file__), "chat_logo.png")
        if os.path.exists(icon_path):
            print(f'[DEBUG] Found logo at {icon_path}')
            self.chat_button.setIcon(QIcon(icon_path))
            self.chat_button.setIconSize(QSize(48, 48))
        else:
            print('[DEBUG] Logo not found, using default text')
            self.chat_button.setText("💬")
        self.chat_button.setStyleSheet("""
            QPushButton#floatingChatBtn {
                background-color: #25d366;
                border-radius: 28px;
                padding: 0px;
                min-width: 56px;
                min-height: 56px;
                max-width: 56px;
                max-height: 56px;
                    color: white;
                        font-size: 32px;
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
        print('[DEBUG] chat_button.show() called')

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.position_floating_chat_button()

    def position_floating_chat_button(self):
        if hasattr(self, 'chat_button') and self.chat_button:
            margin = 32
            btn_size = 56
            x = self.width() - btn_size - margin
            y = self.height() - btn_size - margin
            print(f'[DEBUG] Moving chat_button to ({x}, {y})')
            self.chat_button.move(x, y)
            self.chat_button.raise_()
            self.chat_button.show()
            print('[DEBUG] chat_button.show() called after move')

    def open_chat(self):
        try:
            if not self.chat_gui:
                self.chat_gui = ChatGUI(self)
            self.chat_gui.show()
            self.chat_gui.raise_()
            self.chat_gui.activateWindow()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open AI Assistant: {str(e)}")
            print(f"Error opening AI Assistant: {str(e)}")

    def init_pages(self):
        # Dashboard page
        self.dashboard_page = QWidget()
        self.init_dashboard()
        self.content_area.addWidget(self.dashboard_page)

        # Admin Dashboard page
        self.admin_dashboard_page = QWidget()
        self.init_admin_dashboard()
        self.content_area.addWidget(self.admin_dashboard_page)

        # Orders page
        self.orders_page = QWidget()
        self.init_orders_page()
        self.content_area.addWidget(self.orders_page)

        # Growing Beds page
        self.growing_beds_page = QWidget()
        self.init_growing_beds_page()
        self.content_area.addWidget(self.growing_beds_page)

        # Customers page
        self.customers_page = QWidget()
        self.init_customers_page()
        self.content_area.addWidget(self.customers_page)

        # Warehouse page
        self.warehouse_page = QWidget()
        self.init_warehouse_page()
        self.content_area.addWidget(self.warehouse_page)

        # Farm Visual page
        self.farm_visual_page = QWidget()
        self.init_farm_visual_page()
        self.content_area.addWidget(self.farm_visual_page)

        # Analytics page
        self.analytics_page = QWidget()
        self.init_analytics_page()
        self.content_area.addWidget(self.analytics_page)

        # User Management page
        self.user_management_page = QWidget()
        self.init_user_management_page()
        self.content_area.addWidget(self.user_management_page)

        # Live Simulation page
        self.live_simulation_page = QWidget()
        self.init_live_simulation_page()
        self.content_area.addWidget(self.live_simulation_page)

        # Settings page
        self.settings_page = QWidget()
        self.init_settings_page()
        self.content_area.addWidget(self.settings_page)

    def init_dashboard(self):
        layout = QVBoxLayout(self.dashboard_page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.user_dashboard = DashboardWindow()
        layout.addWidget(self.user_dashboard)

    def init_orders_page(self):
        layout = QVBoxLayout(self.orders_page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Header
        header = QLabel("Orders")
        header.setStyleSheet("""
            QLabel {
                font-size: 24px;
                    font-weight: bold;
                color: #2d3436;
            }
        """)
        layout.addWidget(header)

        # Orders content
        orders = OrderGUI()
        layout.addWidget(orders)

    def init_growing_beds_page(self):
        layout = QVBoxLayout(self.growing_beds_page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Header
        header = QLabel("Growing Beds")
        header.setStyleSheet("""
                    QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #2d3436;
                    }
                """)
        layout.addWidget(header)

        # Growing beds content
        growing_beds = GrowingBedGUI()
        layout.addWidget(growing_beds)

    def init_customers_page(self):
        layout = QVBoxLayout(self.customers_page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Header
        header = QLabel("Customers")
        header.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #2d3436;
            }
        """)
        layout.addWidget(header)

        # Customers content
        customers = CustomerGUI()
        layout.addWidget(customers)

    def init_warehouse_page(self):
        layout = QVBoxLayout(self.warehouse_page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Header
        header = QLabel("Warehouse")
        header.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #2d3436;
            }
        """)
        layout.addWidget(header)

        # Warehouse content
        warehouse = WarehouseGUI()
        layout.addWidget(warehouse)

    def init_farm_visual_page(self):
        layout = QVBoxLayout(self.farm_visual_page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Header
        header = QLabel("Farm Visual")
        header.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #2d3436;
            }
        """)
        layout.addWidget(header)

        # Farm visual content
        farm_visual = FarmVisualGUI()
        layout.addWidget(farm_visual)

    def init_analytics_page(self):
        layout = QVBoxLayout(self.analytics_page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Header
        header = QLabel("Analytics")
        header.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #2d3436;
            }
        """)
        layout.addWidget(header)

        # Analytics content
        analytics = AnalyticsApp()
        layout.addWidget(analytics)

    def init_live_simulation_page(self):
        layout = QVBoxLayout(self.live_simulation_page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        title = QLabel("Live Data Simulation")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title.setAlignment(Qt.AlignHCenter)
        layout.addWidget(title)
        self.simulator = MushroomSimulator()
        self.simulation_running = False
        self.sim_btn = QPushButton("Start Simulation")
        self.sim_btn.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.sim_btn.setStyleSheet("padding: 12px 24px; border-radius: 8px; background: #43a047; color: white;")
        self.sim_btn.clicked.connect(self.toggle_simulation)
        layout.addWidget(self.sim_btn, alignment=Qt.AlignHCenter)
        self.sim_status = QLabel("Simulation is stopped.")
        self.sim_status.setFont(QFont("Segoe UI", 10))
        self.sim_status.setAlignment(Qt.AlignHCenter)
        layout.addWidget(self.sim_status)

    def toggle_simulation(self):
        if not self.simulation_running:
            self.simulator.start_simulation()
            self.simulation_running = True
            self.sim_btn.setText("Stop Simulation")
            self.sim_btn.setStyleSheet("padding: 12px 24px; border-radius: 8px; background: #e74c3c; color: white;")
            self.sim_status.setText("Simulation is running...")
        else:
            self.simulator.stop_simulation()
            self.simulation_running = False
            self.sim_btn.setText("Start Simulation")
            self.sim_btn.setStyleSheet("padding: 12px 24px; border-radius: 8px; background: #43a047; color: white;")
            self.sim_status.setText("Simulation is stopped.")

    def init_settings_page(self):
        layout = QVBoxLayout(self.settings_page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Header
        header = QLabel("Settings")
        header.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #2d3436;
            }
        """)
        layout.addWidget(header)

        # Settings content
        settings = SettingsDialog(self)
        layout.addWidget(settings)

    def handle_logout(self):
        # Show loading window
        loading_window = SimpleLoadingWindow()
        loading_window.show()
        
        # Close current window after a short delay
        QTimer.singleShot(1000, lambda: self.complete_logout(loading_window))
        
    def complete_logout(self, loading_window):
        """Complete the logout process"""
        # Close current window
        self.close()
        
        # Close loading window and show login
        loading_window.close()
        from LoginGUI import LoginGUI
        login = LoginGUI()
        login.show()

    def refresh_alerts_menu(self):
        alerts = get_alerts_from_firebase()
        self.bell_menu.clear()
        if alerts:
            for alert in alerts:
                self.bell_menu.addAction(QIcon(), alert)
            self.bell_red_dot.show()
        else:
            self.bell_menu.addAction("No alerts")
            self.bell_red_dot.hide()

    def change_theme(self, theme):
        if theme.lower() == 'dark':
            self.setStyleSheet("""
                QMainWindow { background: #001f3f; color: #fff; }
                QLabel, QPushButton, QComboBox, QLineEdit, QTableWidget, QHeaderView::section, QTableWidget::item, QMenu, QToolButton {
                    color: #fff;
                    background: #001f3f;
                    border: none;
                }
                QFrame {
                    background: #003366;
                    border-radius: 18px;
                    border: none;
                }
                QCheckBox {
                    color: #fff;
                }
            """)
        else:
            self.setStyleSheet("""
                QMainWindow { background: #f5f6fa; color: #23272e; }
                QLabel, QPushButton, QComboBox, QLineEdit, QTableWidget, QHeaderView::section, QTableWidget::item, QMenu, QToolButton {
                    color: #23272e;
                    background: #fff;
                    border: none;
                }
                QFrame {
                    background: #fff;
                    border-radius: 18px;
                    border: 1.5px solid #e0e6ed;
                }
                QCheckBox {
                    color: #23272e;
                }
            """)
    def change_language(self, lang):
        # כאן תוכל להחיל תרגום (אם יש לך QTranslator)
        pass

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # דוגמה ל-user_data בסיסי
    user_data = {"username": "admin", "role": "admin"}
    main_window = Main_gui(user_data)
    main_window.show()
    sys.exit(app.exec_())
