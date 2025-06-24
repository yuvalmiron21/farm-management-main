from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFrame, QScrollArea, QMessageBox, QDialog, QStackedWidget, QSizePolicy, QMainWindow, QSpacerItem, QToolButton, QMenu, QAction
)
from PyQt5.QtGui import QFont, QIcon, QColor, QPixmap
from PyQt5.QtCore import Qt, QSize, QPoint, QTimer
from Order_gui import OrderGUI
from Growing_bed_gui import GrowingBedGUI
from Customer_gui import CustomerGUI
from WarehouseGUI import WarehouseGUI
from FarmVisualGUI import FarmVisualGUI
from AnalyticsApp import AnalyticsApp
from firebase_admin import db
from LoadingWindow import LoadingWindow
from SimpleLoadingWindow import SimpleLoadingWindow
import os

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
        min_row.addWidget(minimize_btn, stretch=0, alignment=Qt.AlignRight)
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
            ("Orders", "orders", "Orders.png"),
            ("Growing Beds", "growing_beds", "Growing Beds.png"),
            ("Customers", "customers", "Customers.png"),
            ("Warehouse", "warehouse", "Warehouse.png"),
            ("Farm Visual", "farm_visual", "Farm Visual.png"),
            ("Analytics", "analytics", "Analytics.png")
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
                    "Orders": "📦", 
                    "Growing Beds": "🛏️",
                    "Customers": "👥",
                    "Warehouse": "🏪",
                    "Farm Visual": "🌾",
                    "Analytics": "📈"
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
                        "Orders": "📦", 
                        "Growing Beds": "🛏️",
                        "Customers": "👥",
                        "Warehouse": "🏪",
                        "Farm Visual": "🌾",
                        "Analytics": "📈"
                    }
                    text = self.menu_items[i][0]
                    btn.setText(fallback_icons.get(text, "📋"))
                    btn.setIcon(QIcon())
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
                        "Orders": "📦", 
                        "Growing Beds": "🛏️",
                        "Customers": "👥",
                        "Warehouse": "🏪",
                        "Farm Visual": "🌾",
                        "Analytics": "📈"
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
        # מצא את QMainWindow ההורה
        win = self.parent()
        while win and not hasattr(win, 'change_page'):
            win = win.parent()
        if win and hasattr(win, 'change_page'):
            win.change_page(button.property("page"))

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
        
        # Show loading window first
        self.loading_window = SimpleLoadingWindow()
        self.loading_window.show()
        
        # Initialize UI components immediately
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
        logo_path = os.path.join(os.path.dirname(__file__), "logo_without_white.png")
        if os.path.exists(logo_path):
            pix = QPixmap(logo_path)
            pix = pix.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo.setPixmap(pix)
        else:
            logo.setText("🍄")
            logo.setFont(QFont("Segoe UI Emoji", 22))
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
        username = self.username
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
        # (פשוט לא לממש אם אין)
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
        settings_action.triggered.connect(self.open_settings)
        logout_action = QAction("Logout", self)
        logout_action.triggered.connect(self.logout)
        avatar_menu.addAction(settings_action)
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
        self.sidebar = ModernSidebar(self)
        content_layout.addWidget(self.sidebar)
        # Main content vertical layout (header + content)
        main_content_widget = QWidget()
        main_content_layout = QVBoxLayout(main_content_widget)
        main_content_layout.setContentsMargins(0, 0, 0, 0)
        main_content_layout.setSpacing(0)
        main_content_layout.addWidget(header_bar)
        # Content area
        self.content = QStackedWidget()
        self.content.setStyleSheet("background: #f8fafc;")
        main_content_layout.addWidget(self.content)
        content_layout.addWidget(main_content_widget)
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

    def set_font(self):
        # Implementation of set_font method
        pass 

    def open_settings(self):
        self.change_page("settings")

    def logout(self):
        from SimpleLoadingWindow import SimpleLoadingWindow
        loading_window = SimpleLoadingWindow()
        loading_window.show()
        QTimer.singleShot(1000, lambda: self.finish_logout(loading_window))

    def finish_logout(self, loading_window):
        from user_management import UserManagement
        UserManagement.logout_user(self.username)
        self.close()
        loading_window.close()
        from LoginGUI import LoginGUI
        login = LoginGUI()
        login.show() 