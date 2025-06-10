import sys
import os
import pandas as pd
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget,
                             QPushButton, QMessageBox, QLabel, QFileDialog, QHBoxLayout,
                             QFrame, QComboBox, QRadioButton, QButtonGroup, QStackedWidget,
                             QScrollArea, QSizePolicy, QGraphicsDropShadowEffect, QLineEdit,
                             QTableWidget, QTableWidgetItem, QHeaderView, QStyledItemDelegate,
                             QToolButton, QMenu, QAction, QDialog)
from PyQt5.QtGui import QFont, QIcon, QColor, QPalette, QBrush, QPen, QPixmap
from PyQt5.QtCore import Qt, QSettings, QTranslator, QLocale
from firebase_admin import db, credentials, initialize_app
import firebase_admin
from Order_gui import OrderGUI
from Growing_bed_gui import GrowingBedGUI
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
    ref = db.reference('GrowingBed')
    beds = ref.get() or {}
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
    orders_ref = db.reference('Order')
    orders = orders_ref.get() or {}
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
    customers_ref = db.reference('Customer')
    customers = customers_ref.get() or {}
    num_customers = len(customers) if isinstance(customers, dict) else 0

    # Beds
    beds_ref = db.reference('GrowingBed')
    beds = beds_ref.get() or {}
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
    ref = db.reference('Order')
    orders = ref.get() or {}
    # Sort by date descending
    def parse_date(order):
        try:
            return datetime.strptime(order.get('OrderDate', ''), '%Y-%m-%d')
        except Exception:
            return datetime.min
    sorted_orders = sorted(orders.values(), key=parse_date, reverse=True)
    # Get customer names if possible
    customers_ref = db.reference('Customer')
    customers = customers_ref.get() or {}
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
    ref = db.reference("Users")
    users = ref.get() or {}
    for user in users.values():
        if user.get("LoggedIn", False):
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
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        # Alerts section
        alerts_layout = QHBoxLayout()
        alerts_layout.setAlignment(Qt.AlignLeft)
        self.alerts_btn = QToolButton()
        self.alerts_btn.setText("🔔")
        self.alerts_btn.setToolTip("Alerts")
        self.alerts_btn.setPopupMode(QToolButton.InstantPopup)
        self.alerts_btn.setStyleSheet("font-size: 22px; color: #856404; background: transparent; border: none;")
        # Badge for number of alerts
        alerts = get_alerts_from_firebase()
        if alerts:
            self.alerts_btn.setText(f"🔔 {len(alerts)}")
        # Dropdown menu
        menu = QMenu()
        if alerts:
            for alert in alerts:
                action = QAction(alert, self)
                menu.addAction(action)
        else:
            menu.addAction(QAction("No alerts", self))
        self.alerts_btn.setMenu(menu)
        alerts_layout.addWidget(self.alerts_btn)
        layout.addLayout(alerts_layout)

        # KPI Cards
        kpi_layout = QHBoxLayout()
        kpis = [
            ("💰 Total Revenue", f"₪{self.kpi_data['total_revenue']:,.0f}", "#e0ffe0"),
            ("📦 Active Orders", str(self.kpi_data['active_orders']), "#e0f7fa"),
            ("👤 Customers", str(self.kpi_data['num_customers']), "#f3e9ff"),
            ("🌱 Occupancy", f"{self.kpi_data['occupancy']}%", "#fff3e0"),
        ]
        for title, value, color in kpis:
            card = self.create_kpi_card(title, value, color)
            kpi_layout.addWidget(card)
        layout.addLayout(kpi_layout)

        # Charts section
        charts_layout = QHBoxLayout()
        # Revenue chart
        revenue_chart = self.create_revenue_chart()
        charts_layout.addWidget(revenue_chart, 2)
        # Occupancy chart
        occupancy_chart = self.create_occupancy_chart()
        charts_layout.addWidget(occupancy_chart, 1)
        layout.addLayout(charts_layout)

        # Recent orders table
        orders_label = QLabel("Recent Orders:")
        orders_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-top: 20px;")
        layout.addWidget(orders_label)

        orders_table = self.create_orders_table()
        layout.addWidget(orders_table)

        self.setLayout(layout)

    def create_kpi_card(self, title, value, color):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {color};
                border-radius: 12px;
                padding: 15px;
            }}
        """)
        layout = QVBoxLayout(card)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        value_label = QLabel(value)
        value_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        return card

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
        table.setAlternatingRowColors(True)
        table.setStyleSheet("""
            QTableWidget {
                background: #f7f7f7;
                border-radius: 14px;
                border: 1px solid #e0e0e0;
                font-size: 16px;
                color: #222;
                gridline-color: #f0f0f0;
                alternate-background-color: #ececec;
            }
            QHeaderView::section {
                background: #e0e0e0;
                color: #222;
                font-size: 17px;
                font-weight: bold;
                border: none;
                border-bottom: 2px solid #bdbdbd;
                padding: 12px 0;
            }
            QTableWidget::item {
                padding: 10px;
                border-bottom: 1px solid #e0e0e0;
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
                if col == 3:  # Status badge
                    # No need to set background/foreground/font, delegate will handle
                    item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
                table.setItem(row, col, item)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        # Set the custom delegate for the status column
        table.setItemDelegateForColumn(3, StatusBadgeDelegate(status_colors, table))
        return table

class Sidebar(QFrame):
    def __init__(self, parent=None, nav_callbacks=None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(220)
        self.expanded = True
        self.nav_callbacks = nav_callbacks or {}
        self.menu_items = [
            ("📊", "Dashboard", self.nav_callbacks.get("dashboard")),
            ("🏡", "Farm Visual", self.nav_callbacks.get("farm_visual")),
            ("📦", "Orders", self.nav_callbacks.get("orders")),
            ("🛏️", "Growing Beds", self.nav_callbacks.get("growing_beds")),
            ("🏭", "Warehouse", self.nav_callbacks.get("warehouse")),
            ("📊", "View Analytics", self.nav_callbacks.get("analytics")),
            ("👤", "Customers", self.nav_callbacks.get("customers")),
            ("📤", "Upload Excel", self.nav_callbacks.get("upload_excel")),
            ("🚪", "Logout", self.nav_callbacks.get("logout")),
        ]
        self.setStyleSheet("""
            QFrame#Sidebar {
                background-color: #181c24;
                border: none;
                border-radius: 16px;
            }
            QPushButton.menuBtn {
                background: transparent;
                color: #fff;
                border: none;
                font-size: 17px;
                text-align: left;
                padding: 12px 0 12px 10px;
                border-radius: 8px;
                margin: 5px 10px;
                font-weight: 500;
                transition: all 0.15s;
            }
            QPushButton.menuBtn:hover, QPushButton.menuBtn:checked {
                background-color: #232a36;
                color: #7ed6df;
                font-weight: bold;
                transform: scale(1.06);
            }
            QPushButton#toggleBtn {
                background: transparent;
                color: #fff;
                border: none;
                font-size: 20px;
                margin: 0 0 10px 0;
                padding: 8px 0 8px 10px;
                border-radius: 8px;
            }
            QPushButton#toggleBtn:hover {
                background-color: #232a36;
            }
            QLabel#SidebarTitle {
                background: transparent;
                color: #fff;
                font-size: 22px;
                font-weight: bold;
                margin: 18px 0 18px 10px;
            }
            QFrame#ProfileFrame {
                background: transparent;
                border: none;
                border-top: 1px solid #232a36;
                margin-top: 10px;
                padding-top: 16px;
                padding-bottom: 0px;
            }
            QLabel#ProfileName {
                color: #fff;
                font-size: 16px;
                font-weight: bold;
                background: transparent;
                padding-left: 0px;
            }
            QLabel#ProfilePic {
                border-radius: 18px;
                background: #232a36;
                min-width: 36px;
                min-height: 36px;
                max-width: 36px;
                max-height: 36px;
                font-size: 22px;
                qproperty-alignment: AlignCenter;
            }
            QPushButton#ProfileMenuBtn {
                background: transparent;
                color: #fff;
                border: none;
                font-size: 20px;
                padding: 0 6px;
            }
            QPushButton#ProfileMenuBtn:hover {
                color: #7ed6df;
            }
            QPushButton#SettingsBtn {
                background: transparent;
                color: #b0b0b0;
                border: none;
                font-size: 16px;
                text-align: left;
                padding: 10px 0 10px 10px;
                border-radius: 8px;
                margin: 8px 10px 0 10px;
                font-weight: 500;
                transition: all 0.15s;
            }
            QPushButton#SettingsBtn:hover {
                background-color: #232a36;
                color: #7ed6df;
            }
        """)
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 20, 0, 20)
        # Toggle button
        self.toggle_btn = QPushButton("⬅️", self)
        self.toggle_btn.setObjectName("toggleBtn")
        self.toggle_btn.clicked.connect(self.toggle_sidebar)
        self.layout.addWidget(self.toggle_btn)
        # Title
        self.title = QLabel("⚙️ Settings")
        self.title.setObjectName("SidebarTitle")
        self.layout.addWidget(self.title)
        # Menu
        self.menu_btns = []
        for icon, text, callback in self.menu_items:
            btn = QPushButton(f"{icon}  {text}")
            btn.setProperty('class', 'menuBtn')
            btn.setCursor(Qt.PointingHandCursor)
            if callback:
                btn.clicked.connect(callback)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.layout.addWidget(btn)
            self.menu_btns.append((btn, icon, text))
        self.layout.addStretch()
        # Profile section
        user = get_logged_in_user() or {}
        name = user.get("Name") or user.get("Username") or "Itay"
        photo = user.get("PhotoURL") or user.get("photo")
        profile_frame = QFrame()
        profile_frame.setObjectName("ProfileFrame")
        profile_layout = QHBoxLayout(profile_frame)
        profile_layout.setContentsMargins(16, 0, 16, 0)
        profile_layout.setSpacing(10)
        # Profile pic
        profile_pic = QLabel()
        profile_pic.setObjectName("ProfilePic")
        if photo:
            pixmap = QPixmap()
            pixmap.loadFromData(requests.get(photo).content) if photo.startswith('http') else pixmap.load(photo)
            pixmap = pixmap.scaled(36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            profile_pic.setPixmap(pixmap)
        else:
            profile_pic.setText("🦁")
        profile_layout.addWidget(profile_pic)
        # Name
        profile_name = QLabel(name)
        profile_name.setObjectName("ProfileName")
        profile_layout.addWidget(profile_name)
        # Menu button
        profile_menu_btn = QPushButton("⋮")
        profile_menu_btn.setObjectName("ProfileMenuBtn")
        profile_menu_btn.setCursor(Qt.PointingHandCursor)
        profile_menu_btn.setFixedWidth(28)
        profile_layout.addWidget(profile_menu_btn)
        profile_layout.addStretch()
        self.layout.addWidget(profile_frame)
        # Settings button
        self.settings_btn = QPushButton("⚙️  Settings")
        self.settings_btn.setObjectName("SettingsBtn")
        self.settings_btn.setCursor(Qt.PointingHandCursor)
        self.settings_btn.clicked.connect(self.open_settings)
        self.layout.addWidget(self.settings_btn)
        self.update_sidebar()

    def toggle_sidebar(self):
        self.expanded = not self.expanded
        self.setFixedWidth(60 if not self.expanded else 220)
        self.toggle_btn.setText("➡️" if not self.expanded else "⬅️")
        self.title.setVisible(self.expanded)
        for btn, icon, text in self.menu_btns:
            if self.expanded:
                btn.setText(f"{icon}  {text}")
                btn.setStyleSheet("")
            else:
                btn.setText(icon)
                btn.setStyleSheet("font-size: 22px; text-align: center; padding-left: 0px; padding-right: 0px;")

    def update_sidebar(self):
        self.toggle_sidebar()  # To set initial state
        self.toggle_sidebar()  # And back to expanded

    def open_settings(self):
        dlg = SettingsDialog(self.window())
        dlg.exec_()

class Main_gui(QMainWindow):
    def __init__(self, username=None, role=None):
        super().__init__()
        # Initialize window attributes
        self.order_gui = None
        self.customer_gui = None
        self.growing_bed_gui = None
        self.warehouse_gui = None
        self.farm_visual = None
        self.analytics_gui = None
        self.dashboard = None
        self.simulator = None

        self.settings = QSettings('MushroomFarm', 'Main_gui')
        self.translator = QTranslator()
        self.current_language = self.settings.value('language', 'en')  # Default to English
        self.current_theme = self.settings.value('theme', 'light')

        # Initialize translations before creating UI
        self.current_translations = TRANSLATIONS[self.current_language]

        # שמור את המשתמש וה-role
        self.current_user = username
        self.current_role = role

        self.init_ui()
        self.apply_theme(self.current_theme)

        # Make window fullscreen
        self.showMaximized()

    def init_ui(self):
        self.setWindowTitle(self.tr('title'))
        self.setLayoutDirection(Qt.LeftToRight)
        self.main_layout = QHBoxLayout()
        self.main_layout.setSpacing(20)
        self.main_layout.setContentsMargins(20, 20, 20, 20)

        # Sidebar navigation callbacks
        nav_callbacks = {
            "dashboard": self.open_dashboard,
            "farm_visual": self.open_farm_visual,
            "orders": self.open_order_gui,
            "growing_beds": self.open_growing_bed_gui,
            "warehouse": self.open_warehouse_gui,
            "analytics": self.open_analytics_gui,
            "customers": self.open_customer_gui,
            "upload_excel": self.upload_excel_logs,
            "logout": self.handle_logout,
        }
        sidebar = Sidebar(nav_callbacks=nav_callbacks)
        self.main_layout.addWidget(sidebar)

        # כפתור ניהול משתמשים (רק לאדמין)
        if self.current_role == 'admin':
            self.admin_btn = QPushButton('User Management')
            self.admin_btn.setStyleSheet("background-color: #1976d2; color: white; font-weight: bold; border-radius: 8px; padding: 8px 16px;")
            self.admin_btn.clicked.connect(self.open_admin_panel)
            sidebar.layout.addWidget(self.admin_btn)

        # Add simulation control button
        simulation_btn = QPushButton("🎮 Start Simulation")
        simulation_btn.setObjectName("simulationBtn")
        simulation_btn.clicked.connect(self.toggle_simulation)
        simulation_btn.setStyleSheet("""
            QPushButton#simulationBtn {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton#simulationBtn:hover {
                background-color: #45a049;
            }
            QPushButton#simulationBtn:checked {
                background-color: #f44336;
            }
        """)
        sidebar.layout.addWidget(simulation_btn)

        # Main content area with stacked widget
        self.content_stack = QStackedWidget()
        self.dashboard = DashboardWindow()
        self.content_stack.addWidget(self.dashboard)
        self.placeholder = QWidget()
        self.content_stack.addWidget(self.placeholder)
        self.main_layout.addWidget(self.content_stack, stretch=2)

        container = QWidget()
        container.setLayout(self.main_layout)
        self.setCentralWidget(container)

    def change_language(self, language_text):
        language_map = {
            'עברית': 'he',
            'English': 'en',
            'العربية': 'ar'
        }
        language_code = language_map.get(language_text, 'en')
        if language_code != self.current_language:
            self.current_language = language_code
            self.settings.setValue('language', language_code)
            self.current_translations = TRANSLATIONS[language_code]
            self.init_ui()

    def tr(self, text):
        return self.current_translations.get(text.lower(), text)

    def change_theme(self, theme):
        self.current_theme = theme
        self.settings.setValue('theme', theme)
        self.apply_theme(theme)

    def apply_theme(self, theme):
        if theme == 'dark':
            dark_style = """
                QMainWindow, QWidget {
                    background-color: #1a1a1a;
                    color: #ffffff;
                }
                QLabel {
                    color: #ffffff;
                }
                QPushButton {
                    color: white;
                    border: none;
                }
                QFrame#settingsPanel {
                    background-color: #2d2d2d;
                    border: 1px solid #404040;
                    border-radius: 10px;
                }
                QComboBox, QRadioButton {
                    background-color: #333333;
                    color: #ffffff;
                    border: 1px solid #404040;
                    padding: 8px;
                }
                QComboBox:hover, QRadioButton:hover {
                    border-color: #666666;
                    background-color: #404040;
                }
                QTableView {
                    background-color: #2d2d2d;
                    alternate-background-color: #333333;
                    color: #ffffff;
                    gridline-color: #404040;
                    border: 1px solid #404040;
                    selection-background-color: #2980b9;
                    selection-color: #ffffff;
                }
                QTableView::item {
                    padding: 8px;
                    border-bottom: 1px solid #404040;
                }
                QTableView::item:selected {
                    background-color: #2980b9;
                    color: #ffffff;
                }
                QTableView::item:hover {
                    background-color: #34495e;
                }
                QHeaderView::section {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    padding: 10px;
                    border: 1px solid #404040;
                    font-weight: bold;
                }
                QScrollBar:vertical {
                    background-color: #2d2d2d;
                    width: 14px;
                    margin: 0px;
                }
                QScrollBar::handle:vertical {
                    background-color: #404040;
                    min-height: 30px;
                    border-radius: 7px;
                }
                QScrollBar::handle:vertical:hover {
                    background-color: #4a4a4a;
                }
                QScrollBar:horizontal {
                    background-color: #2d2d2d;
                    height: 14px;
                    margin: 0px;
                }
                QScrollBar::handle:horizontal {
                    background-color: #404040;
                    min-width: 30px;
                    border-radius: 7px;
                }
                QScrollBar::handle:horizontal:hover {
                    background-color: #4a4a4a;
                }
                QLineEdit {
                    background-color: #333333;
                    color: #ffffff;
                    border: 1px solid #404040;
                    padding: 8px;
                    border-radius: 5px;
                }
                QLineEdit:focus {
                    border-color: #2980b9;
                }
            """
            self.setStyleSheet(dark_style)

            # Update the title label style for dark mode
            title_label = self.findChild(QLabel, "title_label")
            if title_label:
                title_label.setStyleSheet("""
                    QLabel {
                        font-size: 32px;
                        color: #ffffff;
                        padding: 20px;
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                            stop:0 #2d2d2d, stop:1 transparent);
                        border-radius: 15px;
                    }
                """)

            # Apply dark theme to child windows if they exist
            if hasattr(self, 'order_gui') and self.order_gui is not None:
                self.order_gui.setStyleSheet(dark_style)
            if hasattr(self, 'customer_gui') and self.customer_gui is not None:
                self.customer_gui.setStyleSheet(dark_style)
            if hasattr(self, 'growing_bed_gui') and self.growing_bed_gui is not None:
                self.growing_bed_gui.setStyleSheet(dark_style)
            if hasattr(self, 'warehouse_gui') and self.warehouse_gui is not None:
                self.warehouse_gui.setStyleSheet(dark_style)
            if hasattr(self, 'farm_visual') and self.farm_visual is not None:
                self.farm_visual.setStyleSheet(dark_style)
            if hasattr(self, 'analytics_gui') and self.analytics_gui is not None:
                self.analytics_gui.setStyleSheet(dark_style)
        else:
            # Light theme
            light_style = """
                QMainWindow, QWidget {
                    background-color: #f5f5f5;
                    color: #333333;
                }
                QLabel {
                    color: #333333;
                }
                QPushButton {
                    color: white;
                    border: none;
                }
                QFrame#settingsPanel {
                    background-color: #ffffff;
                    border: 1px solid #dee2e6;
                    border-radius: 10px;
                }
                QComboBox, QRadioButton {
                    background-color: white;
                    color: #333333;
                    border: 1px solid #ced4da;
                    padding: 8px;
                }
                QComboBox:hover, QRadioButton:hover {
                    border-color: #80bdff;
                }
                QTableView {
                    background-color: #ffffff;
                    alternate-background-color: #f8f9fa;
                    color: #333333;
                    gridline-color: #dee2e6;
                    border: 1px solid #dee2e6;
                    selection-background-color: #007bff;
                    selection-color: #ffffff;
                }
                QTableView::item {
                    padding: 8px;
                    border-bottom: 1px solid #dee2e6;
                }
                QTableView::item:selected {
                    background-color: #007bff;
                    color: #ffffff;
                }
                QTableView::item:hover {
                    background-color: #e9ecef;
                }
                QHeaderView::section {
                    background-color: #f8f9fa;
                    color: #333333;
            padding: 10px;
                    border: 1px solid #dee2e6;
                    font-weight: bold;
                }
                QScrollBar:vertical {
                    background-color: #f8f9fa;
                    width: 14px;
                    margin: 0px;
                }
                QScrollBar::handle:vertical {
                    background-color: #dee2e6;
                    min-height: 30px;
                    border-radius: 7px;
                }
                QScrollBar::handle:vertical:hover {
                    background-color: #ced4da;
                }
                QScrollBar:horizontal {
                    background-color: #f8f9fa;
                    height: 14px;
                    margin: 0px;
                }
                QScrollBar::handle:horizontal {
                    background-color: #dee2e6;
                    min-width: 30px;
                    border-radius: 7px;
                }
                QScrollBar::handle:horizontal:hover {
                    background-color: #ced4da;
                }
                QLineEdit {
                    background-color: #ffffff;
                    color: #333333;
                    border: 1px solid #ced4da;
                    padding: 8px;
                    border-radius: 5px;
                }
                QLineEdit:focus {
                    border-color: #80bdff;
                }
            """
            self.setStyleSheet(light_style)

            # Update the title label style for light mode
            title_label = self.findChild(QLabel, "title_label")
            if title_label:
                title_label.setStyleSheet("""
                    QLabel {
                        font-size: 32px;
                        color: #2c3e50;
                        padding: 20px;
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                            stop:0 #f5f5f5, stop:1 transparent);
                        border-radius: 15px;
                    }
                """)

    def open_dashboard(self):
        try:
            # Create new dashboard window
            self.dashboard = AdminDashboard()
            self.dashboard.setWindowModality(Qt.ApplicationModal)  # Make it modal
            self.dashboard.show()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open Dashboard: {str(e)}")
            print(f"Error opening Dashboard: {str(e)}")

    def open_order_gui(self):
        try:
            self.order_gui = OrderGUI()
            self.order_gui.show()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open Order Management: {str(e)}")
            print(f"Error opening Order Management: {str(e)}")

    def open_growing_bed_gui(self):
        try:
            self.growing_bed_gui = GrowingBedGUI()
            self.growing_bed_gui.show()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open Growing Beds: {str(e)}")
            print(f"Error opening Growing Beds: {str(e)}")

    def open_warehouse_gui(self):
        try:
            self.warehouse_gui = WarehouseGUI()
            self.warehouse_gui.show()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open Warehouse: {str(e)}")
            print(f"Error opening Warehouse: {str(e)}")

    def open_customer_gui(self):
        try:
            self.customer_gui = CustomerGUI()
            self.customer_gui.show()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open Customer Management: {str(e)}")
            print(f"Error opening Customer Management: {str(e)}")

    def open_analytics_gui(self):
        try:
            self.analytics_gui = AnalyticsApp()
            self.analytics_gui.show()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open Analytics: {str(e)}")
            print(f"Error opening Analytics: {str(e)}")

    def open_farm_visual(self):
        try:
            self.farm_visual = FarmVisualGUI()
            self.farm_visual.show()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open Farm Visual: {str(e)}")
            print(f"Error opening Farm Visual: {str(e)}")

    def upload_excel_logs(self):
        try:
            file_name, _ = QFileDialog.getOpenFileName(self, "Select Excel File", "", "Excel Files (*.xlsx *.xls)")
            if file_name:
                # TODO: Implement Excel upload logic
                QMessageBox.information(self, "Success", "Excel file uploaded successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to upload Excel file: {str(e)}")
            print(f"Error uploading Excel file: {str(e)}")

    def generate_dummy_data(self):
        try:
            from generate_dummy_data import upload_dummy_data
            if upload_dummy_data():
                QMessageBox.information(self, "Success", "Dummy data generated successfully!")
            else:
                QMessageBox.warning(self, "Warning", "Failed to generate dummy data.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate dummy data: {str(e)}")
            print(f"Error generating dummy data: {str(e)}")

    def handle_logout(self):
        reply = QMessageBox.question(self, 'Logout', 'Are you sure you want to logout?',
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.close()

    @staticmethod
    def delete_table(table_name):
        ref = db.reference(table_name)  # Reference to the table (node)
        ref.delete()  # Deletes the node

    # delete_table("Batches")
    # delete_table("Logs")

    # Deletes the "Logs" table

    def toggle_simulation(self):
        """Toggle the live simulation on/off"""
        if not self.simulator:
            try:
                from live_simulation import start_live_simulation
                self.simulator = start_live_simulation()
                self.sender().setText("🎮 Stop Simulation")
                self.sender().setChecked(True)
                QMessageBox.information(self, "Simulation", "Live simulation started!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to start simulation: {str(e)}")
        else:
            try:
                self.simulator.stop_simulation()
                self.simulator = None
                self.sender().setText("🎮 Start Simulation")
                self.sender().setChecked(False)
                QMessageBox.information(self, "Simulation", "Live simulation stopped!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to stop simulation: {str(e)}")

    def open_admin_panel(self):
        # כאן תוכל לייבא ולפתוח את AdminPanel (בהמשך)
        try:
            from AdminPanel import AdminPanel
            self.admin_panel = AdminPanel()
            self.admin_panel.show()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open Admin Panel: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Create Main Window
    main_window = Main_gui()
    main_window.show()

    sys.exit(app.exec_())
