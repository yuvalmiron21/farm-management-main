import sys
import os
import pandas as pd
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget,
                             QPushButton, QMessageBox, QLabel, QFileDialog, QHBoxLayout,
                             QFrame, QComboBox, QRadioButton, QButtonGroup, QStackedWidget,
                             QScrollArea, QSizePolicy, QGraphicsDropShadowEffect, QLineEdit,
                             QTableWidget, QTableWidgetItem, QHeaderView, QStyledItemDelegate,
                             QToolButton, QMenu, QAction, QDialog, QSpacerItem, QGridLayout,
                             QGraphicsOpacityEffect)
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
            'Status': order.get('Status', '')
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
        # Theme-aware color map
        color_map = {
            'Total Revenue': {'light': 'rgba(76,175,80,0.1)', 'dark': 'rgba(76,175,80,0.3)', 'icon': '#4caf50'},
            'Active Orders': {'light': 'rgba(255,152,0,0.1)', 'dark': 'rgba(255,152,0,0.3)', 'icon': '#ff9800'},
            'Customers': {'light': 'rgba(33,150,243,0.1)', 'dark': 'rgba(33,150,243,0.3)', 'icon': '#2196f3'},
            'Occupancy': {'light': 'rgba(156,39,176,0.1)', 'dark': 'rgba(156,39,176,0.3)', 'icon': '#9c27b0'}
        }
        theme = 'dark' if QApplication.instance().palette().color(QPalette.Window).lightness() < 128 else 'light'
        bg_color = color_map.get(title, {'light': 'rgba(255,255,255,0.1)', 'dark': 'rgba(255,255,255,0.3)', 'icon': '#888'})[theme]
        icon_color = color_map.get(title, {'icon': '#888'})['icon']

        # Styling
        self.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                            stop:0 {bg_color}, stop:1 rgba(255,255,255,0.05));
                border-radius: 20px;
                border: 1.5px solid #fff;
                box-shadow: 0 6px 20px rgba(0,0,0,0.08);
                transition: all 0.3s ease;
            }}
            QLabel {{
                background: transparent;
                border: none;
                color: #333;
                padding: 0;
                margin: 0;
            }}
        """)
        self.setFixedSize(360, 140)

        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(16)

        # Left: icon + text
        text_col = QVBoxLayout()
        text_col.setAlignment(Qt.AlignCenter)
        icon_label = QLabel(icon)
        icon_label.setFont(QFont("FontAwesome, Segoe UI Emoji", 28))
        icon_label.setStyleSheet("background: transparent; border: none; color: %s;" % icon_color)
        icon_label.setAlignment(Qt.AlignCenter)
        value_label = QLabel(str(value))
        value_label.setFont(QFont("Inter, Segoe UI", 28, QFont.Bold))
        value_label.setStyleSheet("background: transparent; border: none; color: #1A1A1A; letter-spacing: 0.5px;")
        value_label.setAlignment(Qt.AlignCenter)
        title_label = QLabel(title)
        title_label.setFont(QFont("Inter, Segoe UI", 14, QFont.Medium))
        title_label.setStyleSheet("background: transparent; border: none; color: #666; letter-spacing: 1px;")
        title_label.setAlignment(Qt.AlignCenter)
        text_col.addWidget(icon_label)
        text_col.addWidget(value_label)
        text_col.addWidget(title_label)
        text_col.addStretch(1)
        layout.addLayout(text_col, 3)

        # Right: sparkline
        spark = self.create_sparkline(spark_data)
        layout.addWidget(spark, 2)

        # Fade-in animation
        self.setGraphicsEffect(QGraphicsOpacityEffect())
        self.animation = QPropertyAnimation(self.graphicsEffect(), b"opacity")
        self.animation.setDuration(500)
        self.animation.setStartValue(0)
        self.animation.setEndValue(1)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.animation.start()

    def create_sparkline(self, spark_data):
        # Placeholder for sparkline widget, replace with your actual implementation
        fig = Figure(figsize=(2, 0.8), dpi=60)
        ax = fig.add_subplot(111)
        ax.plot(spark_data, color='#1976d2', linewidth=2)
        ax.axis('off')
        fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
        canvas = FigureCanvas(fig)
        canvas.setFixedSize(100, 60)
        canvas.setStyleSheet("background: transparent; border: none;")
        canvas.setToolTip("Data trend over time")
        return canvas

    def enterEvent(self, event):
        self.setStyleSheet(self.styleSheet() + "box-shadow: 0 10px 24px rgba(0,0,0,0.15);")
        super().enterEvent(event)

    def leaveEvent(self, event):
        # Remove the hover shadow
        self.setStyleSheet(self.styleSheet().replace("box-shadow: 0 10px 24px rgba(0,0,0,0.15);", "box-shadow: 0 6px 20px rgba(0,0,0,0.08);"))
        super().leaveEvent(event)

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(350)
        layout = QVBoxLayout(self)
        # Language selection
        lang_label = QLabel("Language:")
        layout.addWidget(lang_label)
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["English", "עברית", "العربية"])
        # Set current language
        main_win = self.parentWidget()
        if hasattr(main_win, 'current_language'):
            lang_map = {'en': 'English', 'he': 'עברית', 'ar': 'العربية'}
            cur_lang = lang_map.get(getattr(main_win, 'current_language', 'en'), 'English')
            self.lang_combo.setCurrentText(cur_lang)
        layout.addWidget(self.lang_combo)
        # Theme selection
        theme_label = QLabel("Theme:")
        layout.addWidget(theme_label)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark"])
        if hasattr(main_win, 'current_theme'):
            self.theme_combo.setCurrentText(main_win.current_theme.capitalize())
        layout.addWidget(self.theme_combo)
        # Save button
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_btn)
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def save_settings(self):
        main_win = self.parentWidget()
        # If parent is not Main_gui, try to get the window
        if not hasattr(main_win, 'change_language') and hasattr(main_win, 'window'):
            main_win = main_win.window()
        if hasattr(main_win, 'change_language'):
            main_win.change_language(self.lang_combo.currentText())
        if hasattr(main_win, 'change_theme'):
            main_win.change_theme(self.theme_combo.currentText().lower())
        QMessageBox.information(self, "Settings", "Settings updated!")

class DashboardWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.kpi_data = get_kpi_data()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(30, 30, 30, 30)
        kpis = [
            ("Total Revenue", f"₪{self.kpi_data['total_revenue']:,.0f}", "💰", [100, 120, 90, 130, 150, 170, 160]),
            ("Active Orders", str(self.kpi_data['active_orders']), "📦", [10, 12, 8, 15, 13, 14, 16]),
            ("Customers", str(self.kpi_data['num_customers']), "👥", [200, 220, 210, 230, 250, 270, 260]),
            ("Occupancy", f"{self.kpi_data['occupancy']}%", "🌱", [60, 65, 70, 68, 72, 75, 80])
        ]
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(32)
        kpi_row.setContentsMargins(0, 30, 0, 30)
        for title, value, icon, spark_data in kpis:
            kpi_card = ModernKpiCard(title, value, icon, spark_data)
            kpi_row.addWidget(kpi_card)
        kpi_row.setAlignment(Qt.AlignHCenter)
        layout.addLayout(kpi_row)
        # Charts section
        charts_row = QHBoxLayout()
        revenue_chart = self.create_revenue_chart()
        charts_row.addWidget(revenue_chart, 2)
        occupancy_chart = self.create_occupancy_chart()
        charts_row.addWidget(occupancy_chart, 1)
        layout.addLayout(charts_row)
        # Recent orders table
        orders_label = QLabel("Recent Orders:")
        orders_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-top: 20px;")
        layout.addWidget(orders_label)
        orders_table = self.create_orders_table()
        layout.addWidget(orders_table)
        self.setLayout(layout)

    def create_revenue_chart(self):
        months, revenue = get_monthly_revenue()
        fig = Figure(figsize=(6, 4))
        ax = fig.add_subplot(111)
        line, = ax.plot(months, revenue, marker='o', color='#4CAF50', linewidth=2)
        ax.set_title('Revenue Over Time')
        ax.grid(True, linestyle='--', alpha=0.7)
        fig.tight_layout()
        canvas = FigureCanvas(fig)
        canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Add hover effect
        annot = ax.annotate("", xy=(0,0), xytext=(15,15), textcoords="offset points",
                            bbox=dict(boxstyle="round", fc="#f5f5f5", ec="#4CAF50"),
                            arrowprops=dict(arrowstyle="->", color="#4CAF50"))
        annot.set_visible(False)

        def update_annot(ind):
            x, y = line.get_data()
            idx = ind["ind"][0]
            annot.xy = (x[idx], y[idx])
            text = f"{months[idx]}: ₪{y[idx]:,.2f}"
            annot.set_text(text)
            annot.get_bbox_patch().set_facecolor("#f5f5f5")
            annot.get_bbox_patch().set_alpha(0.95)

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
        stage_counts = get_bed_occupancy()
        labels = list(stage_counts.keys())
        sizes = list(stage_counts.values())
        colors = ['#4e73df', '#f6c23e', '#1cc88a', '#e74a3b', '#858796']
        fig = Figure(figsize=(4, 4))
        ax = fig.add_subplot(111)
        wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
        ax.set_title('Bed Occupancy')
        fig.tight_layout()
        canvas = FigureCanvas(fig)
        canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Add hover effect for pie
        def on_move(event):
            found = False
            for i, wedge in enumerate(wedges):
                if wedge.contains_point([event.x, event.y], radius=1.5):
                    wedge.set_alpha(0.6)
                    percent = (sizes[i] / sum(sizes) * 100) if sum(sizes) > 0 else 0
                    ax.set_title(f"{labels[i]}: {sizes[i]} beds ({percent:.1f}%)")
                    found = True
                else:
                    wedge.set_alpha(1.0)
            if not found:
                ax.set_title('Bed Occupancy')
            canvas.draw_idle()

        canvas.mpl_connect('motion_notify_event', on_move)
        return canvas

    def create_orders_table(self):
        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Order #", "Customer", "Amount", "Status"])
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        table.setAlternatingRowColors(False)
        table.setStyleSheet("""
            QTableWidget {
                background: #f7f7f7;
                border-radius: 14px;
                border: 1px solid #e0e0e0;
                font-size: 13px;
                color: #222;
                gridline-color: #f0f0f0;
                font-family: 'Segoe UI';
                font-weight: 600;
            }
            QHeaderView::section {
                background: #e0e0e0;
                color: #222;
                font-size: 14px;
                font-weight: bold;
                border: none;
                border-bottom: 2px solid #bdbdbd;
                padding: 12px 0;
                font-family: 'Segoe UI';
                font-weight: 600;
            }
            QTableWidget::item {
                padding: 10px;
                border-bottom: 1px solid #e0e0e0;
                font-size: 12px;
                font-family: 'Segoe UI';
                font-weight: 600;
            }
            QTableWidget::item:selected {
                background: #d6e4f0;
                color: #1976d2;
            }
            QTableWidget::item:hover {
                background: #e3eafc;
            }
            QScrollBar:vertical {
                background: #f7f7f7;
                width: 12px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #bdbdbd;
                min-height: 30px;
                border-radius: 6px;
            }
        """)
        # Get real data
        data = get_recent_orders(10)
        table.setRowCount(len(data))
        status_colors = {
            "Pending": "#f1c40f",
            "Shipped": "#3498db",
            "Delivered": "#27ae60",
            "Completed": "#27ae60",
            "Cancelled": "#e74c3c",
            "Pending Shipment": "#f39c12",
            "Processing": "#e67e22"
        }
        font_family = QApplication.font().family()
        for row, order in enumerate(data):
            items = [
                str(order['OrderID']),
                str(order['Customer']),
                f"₪{order['Amount']:,.2f}",
                str(order['Status'])
            ]
            for col, item_text in enumerate(items):
                item = QTableWidgetItem(item_text)
                item.setTextAlignment(Qt.AlignCenter)
                item.setFont(QFont(font_family, 12, QFont.Bold))
                if col == 3:  # Status badge
                    # No need to set background/foreground/font, delegate will handle
                    item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
                table.setItem(row, col, item)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        # Set the custom delegate for the status column
        table.setItemDelegateForColumn(3, StatusBadgeDelegate(status_colors, table))
        return table

class ModernSidebar(QFrame):
    def __init__(self, parent=None, nav_callbacks=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setStyleSheet("""
            QFrame#sidebar {
                background: #2d3436;
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
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Logo and title
        logo_layout = QHBoxLayout()
        logo = QLabel()
        pix = QPixmap(32, 32)
        pix.fill(QColor("#43a047"))
        logo.setPixmap(pix)
        logo.setFixedSize(32, 32)
        title = QLabel("Mush")
        title.setFont(QFont("Segoe UI", 24, QFont.Bold))
        title.setStyleSheet("color: #fff;")
        logo_layout.addWidget(logo)
        logo_layout.addWidget(title)
        logo_layout.addStretch()
        layout.addLayout(logo_layout)
        layout.addSpacing(20)

        # Menu buttons
        self.buttons = []
        menu_items = [
            ("Dashboard", "dashboard", "📊"),
            ("Admin Dashboard", "admin_dashboard", "👑"),
            ("Orders", "orders", "📦"),
            ("Growing Beds", "growing_beds", "🛏️"),
            ("Customers", "customers", "👥"),
            ("Warehouse", "warehouse", "🏪"),
            ("Farm Visual", "farm_visual", "🌾"),
            ("Analytics", "analytics", "📈"),
            ("User Management", "user_management", "👤"),
            ("Live Simulation", "live_simulation", "🧪"),
            ("Settings", "settings", "⚙️")
        ]

        for text, name, icon in menu_items:
            btn = QPushButton(f"{icon}  {text}")
            btn.setCheckable(True)
            btn.setProperty("page", name)
            btn.clicked.connect(lambda checked, b=btn: self.button_clicked(b))
            layout.addWidget(btn)
            self.buttons.append(btn)

        layout.addStretch()

        # Back to Dashboard button
        back_btn = QPushButton("↩️  Back to Dashboard")
        back_btn.setStyleSheet("""
            QPushButton {
                color: #3498db;
                margin: 10px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #2d3436;
                color: #2980b9;
            }
        """)
        back_btn.clicked.connect(lambda: self.button_clicked(self.buttons[0]))
        layout.addWidget(back_btn)

        # Logout button
        logout_btn = QPushButton("🚪  Logout")
        logout_btn.setStyleSheet("""
            QPushButton {
                color: #ff7675;
                margin: 10px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #2d3436;
                color: #e74c3c;
            }
        """)
        logout_btn.clicked.connect(self.logout)
        layout.addWidget(logout_btn)

    def button_clicked(self, button):
        for btn in self.buttons:
            btn.setChecked(btn == button)
        if self.nav_callbacks and button.property("page") in self.nav_callbacks:
            self.nav_callbacks[button.property("page")]()

    def logout(self):
        self.parent().handle_logout()

class Main_gui(QMainWindow):
    def __init__(self, user_data):
        super().__init__()
        self.user_data = user_data
        self.chat_button = None
        self.chat_gui = None
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        
        # Set default font for the entire application
        self.set_font()
        
        self.init_ui()
        self.setup_navigation()
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
        # Content area
        content_frame = QFrame()
        content_layout = QHBoxLayout(content_frame)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        # Sidebar
        self.sidebar = ModernSidebar(self, self.nav_callbacks)
        content_layout.addWidget(self.sidebar)
        # Content area
        self.content_area = QStackedWidget()
        self.content_area.setStyleSheet("""
            QStackedWidget {
                background: #f5f6fa;
            }
        """)
        content_layout.addWidget(self.content_area)
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
        dashboard = DashboardWindow()
        layout.addWidget(dashboard)

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
        self.close()
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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Create Main Window
    main_window = Main_gui()
    main_window.show()

    sys.exit(app.exec_())
