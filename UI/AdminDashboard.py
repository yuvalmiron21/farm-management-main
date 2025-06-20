import sys
import firebase_admin
from firebase_admin import credentials, db
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGridLayout, QScrollArea, QPushButton, QSizePolicy,
    QProgressBar, QMessageBox, QToolTip, QComboBox, QDateEdit,
    QToolButton, QStyle, QDialog, QGroupBox, QFormLayout, QLineEdit
)
from PyQt5.QtCore import Qt, QTimer, QDate
from PyQt5.QtGui import QPainter, QColor, QFont, QCursor, QPixmap
from PyQt5.QtChart import QChart, QChartView, QPieSeries, QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis, QLineSeries
from datetime import datetime, timedelta
import calendar
import os
from prediction_utils import (
    get_order_history,
    get_unique_customers_and_statuses,
    filter_orders,
    prophet_forecast,
    prophet_revenue_forecast,
    prophet_profit_forecast,
    prophet_returning_customers_forecast,
    prophet_product_forecast,
    get_product_list
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from prophet import Prophet
import pandas as pd
import io
from user_management import UserManagement
from db.cache_manager import CacheManager
import numpy as np

_cache_manager = CacheManager()

class MetricCard(QFrame):
    def __init__(self, title, value, icon, color="#4CAF50", show_progress=False, progress_value=0):
        super().__init__()
        self.setObjectName("metricCard")
        self.setStyleSheet(f"""
            #metricCard {{
                background: white;
                border-radius: 10px;
                padding: 15px;
                margin: 5px;
                border: 1px solid #e0e0e0;
            }}
            QLabel {{
                color: #333;
            }}
            QProgressBar {{
                border: 1px solid #e0e0e0;
                border-radius: 5px;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 5px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        
        # Header with icon and title
        header = QHBoxLayout()
        iconLabel = QLabel(icon)
        iconLabel.setStyleSheet(f"color: {color}; font-size: 24px;")
        titleLabel = QLabel(title)
        titleLabel.setStyleSheet("font-weight: bold; font-size: 14px;")
        header.addWidget(iconLabel)
        header.addWidget(titleLabel)
        header.addStretch()
        
        # Value
        self.valueLabel = QLabel(str(value))
        self.valueLabel.setStyleSheet(f"font-size: 24px; color: {color}; font-weight: bold;")
        
        layout.addLayout(header)
        layout.addWidget(self.valueLabel)
        
        # Progress bar (optional)
        if show_progress:
            self.progressBar = QProgressBar()
            self.progressBar.setMaximum(100)
            self.progressBar.setValue(int(progress_value))
            layout.addWidget(self.progressBar)
        
    def update_value(self, value, progress_value=None):
        self.valueLabel.setText(str(value))
        if hasattr(self, 'progressBar') and progress_value is not None:
            self.progressBar.setValue(int(progress_value))

class ForecastDetailDialog(QDialog):
    def __init__(self, title, fig, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(600, 400)
        layout = QVBoxLayout(self)
        canvas = FigureCanvas(fig)
        layout.addWidget(canvas)

class SparklineLabel(QLabel):
    def __init__(self, series, index_to_label, tooltip_fmt, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.series = series
        self.index_to_label = index_to_label
        self.tooltip_fmt = tooltip_fmt
        self.setMouseTracking(True)
    def mouseMoveEvent(self, event):
        x = event.pos().x()
        width = self.width()
        idx = int(x / width * (len(self.series)-1))
        idx = max(0, min(idx, len(self.series)-1))
        val = self.series.iloc[idx] if hasattr(self.series, 'iloc') else self.series[idx]
        label_str = self.index_to_label[idx] if self.index_to_label else str(idx)
        QToolTip.showText(event.globalPos(), self.tooltip_fmt.format(label=label_str, value=val))
    def leaveEvent(self, event):
        QToolTip.hideText()
        super().leaveEvent(event)

class AdminDashboard(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Admin Dashboard")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create main layout with scroll area
        main_layout = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        
        # Dashboard title
        title = QLabel("🍄 Dashboard - Revenue and Orders")
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin: 20px 0;")
        scroll_layout.addWidget(title)

        # Create grid for metric cards
        metrics_grid = QGridLayout()
        
        # Initialize metric cards with new KPIs
        self.monthly_revenue_card = MetricCard("Monthly Revenue", "₪0", "💰", "#E91E63")
        self.monthly_profit_card = MetricCard("Monthly Profit", "₪0", "💵", "#4CAF50")
        self.yearly_revenue_card = MetricCard("Yearly Revenue", "₪0", "📊", "#2196F3")
        self.yearly_profit_card = MetricCard("Yearly Profit", "₪0", "📈", "#9C27B0")
        self.avg_order_value = MetricCard("Avg. Order Value", "₪0", "🛒", "#FF9800")
        self.total_orders = MetricCard("Total Orders", "0", "📦", "#00BCD4")
        self.active_beds_card = MetricCard("Active Beds", "0", "🌱", "#4CAF50", True, 0)
        self.harvest_ready_card = MetricCard("Ready for Harvest", "0", "🍄", "#FF9800", True, 0)
        
        # Add cards to grid (3x3 layout)
        metrics_grid.addWidget(self.monthly_revenue_card, 0, 0)
        metrics_grid.addWidget(self.monthly_profit_card, 0, 1)
        metrics_grid.addWidget(self.yearly_revenue_card, 0, 2)
        metrics_grid.addWidget(self.yearly_profit_card, 1, 0)
        metrics_grid.addWidget(self.avg_order_value, 1, 1)
        metrics_grid.addWidget(self.total_orders, 1, 2)
        metrics_grid.addWidget(self.active_beds_card, 2, 0)
        metrics_grid.addWidget(self.harvest_ready_card, 2, 1)
        
        scroll_layout.addLayout(metrics_grid)
        
        # Add charts section
        charts_layout = QGridLayout()
        
        # Revenue and profit trend chart
        self.profit_chart = QChartView()
        self.profit_chart.setMinimumHeight(300)
        charts_layout.addWidget(self.profit_chart, 0, 0)
        
        # Growing beds status chart
        self.beds_chart = QChartView()
        self.beds_chart.setMinimumHeight(300)
        charts_layout.addWidget(self.beds_chart, 0, 1)
        
        # Order value distribution chart
        self.orders_chart = QChartView()
        self.orders_chart.setMinimumHeight(300)
        charts_layout.addWidget(self.orders_chart, 1, 0, 1, 2)
        
        scroll_layout.addLayout(charts_layout)
        
        # --- Filters Section ---
        filter_group = QGroupBox("📊 Filters")
        filter_group.setObjectName("filterGroup")
        filter_group.setStyleSheet("""
            QGroupBox#filterGroup {
                background-color: #ffffff;
                border: 1px solid #e0e6ed;
                border-radius: 12px;
                font-size: 16px;
                font-weight: bold;
                color: #34495e;
                margin-top: 20px;
                padding: 20px;
                padding-top: 35px; /* Space for the title */
            }
            QGroupBox#filterGroup::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 5px 15px;
                margin-left: 15px;
                background-color: #3498db;
                border-radius: 8px;
                color: white;
            }
            QLabel#filterLabel {
                font-size: 12px;
                font-weight: bold;
                color: #566573;
            }
            QComboBox, QDateEdit {
                border: 1px solid #dcdfe6;
                border-radius: 6px;
                padding: 8px 12px;
                min-width: 140px;
                background-color: #fdfdfd;
                font-size: 12px;
                color: #333;
            }
            QComboBox:hover, QDateEdit:hover {
                border-color: #3498db;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 25px;
                border-left-width: 1px;
                border-left-color: #dcdfe6;
                border-left-style: solid;
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
            }
        """)
        filter_layout = QHBoxLayout(filter_group)
        filter_layout.setSpacing(15)
        filter_layout.setAlignment(Qt.AlignLeft)

        # Helper to create styled filter widgets
        def create_filter_widget(icon, text, widget):
            item_layout = QHBoxLayout()
            item_layout.setSpacing(8)
            
            label = QLabel(f"{icon} {text}")
            label.setObjectName("filterLabel")
            item_layout.addWidget(label)
            item_layout.addWidget(widget)
            
            # Use a container widget to hold the layout
            container = QWidget()
            container.setLayout(item_layout)
            return container

        # Time range filter
        self.time_range_combo = QComboBox()
        self.time_range_combo.addItems(['Last 4 Weeks', 'Last 3 Months', 'Last Year', 'Custom Range'])
        filter_layout.addWidget(create_filter_widget("🕒", "Time Range:", self.time_range_combo))

        # Customer filter
        customer_name_map = self.get_customer_name_map()
        self.customer_combo = QComboBox()
        self.customer_combo.addItem('All Customers', None)
        for cid, name in customer_name_map.items():
            self.customer_combo.addItem(name, cid)
        filter_layout.addWidget(create_filter_widget("👤", "Customer:", self.customer_combo))
        
        # Status filter
        _, statuses = get_unique_customers_and_statuses()
        self.status_combo = QComboBox()
        self.status_combo.addItem('All Statuses')
        self.status_combo.addItems([str(s) for s in statuses])
        filter_layout.addWidget(create_filter_widget("🏷️", "Status:", self.status_combo))

        # Custom date range widgets (initially hidden)
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDate(QDate.currentDate().addMonths(-1))
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDate(QDate.currentDate())
        
        self.from_widget = create_filter_widget("➡️", "From:", self.start_date_edit)
        self.to_widget = create_filter_widget("⬅️", "To:", self.end_date_edit)
        filter_layout.addWidget(self.from_widget)
        filter_layout.addWidget(self.to_widget)
        self.from_widget.hide()
        self.to_widget.hide()

        # Product filter
        product_name_map = self.get_product_name_map()
        self.product_combo = QComboBox()
        self.product_combo.addItem('All Products', None)
        for pid, name in product_name_map.items():
            self.product_combo.addItem(name, pid)
        filter_layout.addWidget(create_filter_widget("🍄", "Product:", self.product_combo))
        self.product_combo.currentIndexChanged.connect(self.update_prediction_section)
        
        filter_layout.addStretch() # Push model selector to the right

        # Forecast model selector
        self.model_combo = QComboBox()
        self.model_combo.addItems(["Prophet", "ARIMA"])
        filter_layout.addWidget(create_filter_widget("🤖", "Model:", self.model_combo))
        self.model_combo.currentIndexChanged.connect(self.update_prediction_section)

        scroll_layout.addWidget(filter_group)

        # Ensure explanation and prediction_label are initialized before use
        self.explanation = QLabel()
        self.explanation.setWordWrap(True)
        self.explanation.setStyleSheet("font-size: 15px; color: #333; margin-top: 30px; margin-bottom: 10px;")
        scroll_layout.addWidget(self.explanation)
        self.prediction_label = QLabel()
        self.prediction_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50; margin-bottom: 10px;")
        scroll_layout.addWidget(self.prediction_label)

        self.graph_canvas = None
        self.forecast_cards_layout = QGridLayout()
        scroll_layout.addLayout(self.forecast_cards_layout)

        # Insights section (below forecast cards, above recent activity)
        self.insights_label = QLabel("Insights")
        self.insights_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-top: 20px;")
        scroll_layout.addWidget(self.insights_label)
        self.insights_text = QLabel()
        self.insights_text.setWordWrap(True)
        self.insights_text.setStyleSheet("font-size: 15px; color: #2c3e50; margin-bottom: 10px;")
        scroll_layout.addWidget(self.insights_text)

        # Add User Section
        add_user_group = QGroupBox("Add New User")
        add_user_layout = QFormLayout()
        self.new_username = QLineEdit()
        self.new_password = QLineEdit()
        self.new_password.setEchoMode(QLineEdit.Password)
        self.new_role = QComboBox()
        self.new_role.addItems(["user", "admin"])
        add_user_layout.addRow("Username:", self.new_username)
        add_user_layout.addRow("Password:", self.new_password)
        add_user_layout.addRow("Role:", self.new_role)
        add_user_button = QPushButton("Add User")
        add_user_button.clicked.connect(self.add_new_user)
        add_user_layout.addRow(add_user_button)
        add_user_group.setLayout(add_user_layout)
        scroll_layout.addWidget(add_user_group)

        # Connect filter signals
        self.time_range_combo.currentIndexChanged.connect(self.update_prediction_section)
        self.customer_combo.currentIndexChanged.connect(self.update_prediction_section)
        self.status_combo.currentIndexChanged.connect(self.update_prediction_section)
        self.start_date_edit.dateChanged.connect(self.update_prediction_section)
        self.end_date_edit.dateChanged.connect(self.update_prediction_section)
        self.time_range_combo.currentTextChanged.connect(self.toggle_custom_date_range)
        if self.product_combo:
            self.product_combo.currentIndexChanged.connect(self.update_prediction_section)
        self.model_combo.currentIndexChanged.connect(self.update_prediction_section)

        # Initial update
        self.update_prediction_section()

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
        
        # Recent Activity Section (now after predictions)
        activity_label = QLabel("Recent Activity")
        activity_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-top: 20px;")
        scroll_layout.addWidget(activity_label)
        self.activity_frame = QFrame()
        self.activity_frame.setStyleSheet("""
            QFrame {
                background: white;
                border-radius: 10px;
                padding: 15px;
                border: 1px solid #e0e0e0;
            }
        """)
        self.activity_layout = QVBoxLayout(self.activity_frame)
        scroll_layout.addWidget(self.activity_frame)

        # Set up update timer
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_dashboard_data)
        self.update_timer.start(300000)  # Update every 5 minutes

        # Initial data load
        self.update_dashboard_data()

    def toggle_custom_date_range(self):
        is_custom = self.time_range_combo.currentText() == 'Custom Range'
        self.from_widget.setVisible(is_custom)
        self.to_widget.setVisible(is_custom)

    def update_prediction_section(self):
        # Get filter values
        time_range = self.time_range_combo.currentText()
        customer = self.customer_combo.currentData() if self.customer_combo else None
        if customer is None:
            customer = None
        status = self.status_combo.currentText()
        product = self.product_combo.currentData() if self.product_combo else None
        if status == 'All Statuses':
            status = None
        # Time range logic
        end_date = datetime.now()
        if time_range == 'Last 4 Weeks':
            start_date = end_date - timedelta(weeks=4)
        elif time_range == 'Last 3 Months':
            start_date = end_date - timedelta(days=90)
        elif time_range == 'Last Year':
            start_date = end_date - timedelta(days=365)
        elif time_range == 'Custom Range':
            start_date = self.start_date_edit.date().toPyDate()
            end_date = self.end_date_edit.date().toPyDate()
        else:
            start_date = None
        # Get and filter data
        df = get_order_history()
        
        # --- דיבאג ראשוני: בדיקת ה-DataFrame הגולמי ---
        print("--- Initial DataFrame from get_order_history() ---")
        if df.empty:
            print("DataFrame is EMPTY.")
        else:
            print(f"DataFrame has {len(df)} rows.")
            print(df.head())
            print("Columns:", df.columns)
            print("Data types:\n", df.dtypes)
        print("-------------------------------------------------")

        # --- סינון לפי פילטרים ---
        df_filtered = df.copy()
        if not df_filtered.empty:
            if customer:
                df_filtered = df_filtered[df_filtered['customer_id'] == customer]
            if status:
                df_filtered = df_filtered[df_filtered['status'] == status]
            if start_date and end_date and 'date' in df_filtered.columns:
                df_filtered = df_filtered[(df_filtered['date'] >= pd.to_datetime(start_date)) & (df_filtered['date'] <= pd.to_datetime(end_date))]
        
        # --- דיבאג: כמה דאטה נשאר? ---
        print(f"Filtered orders: {len(df_filtered)} rows (after filters)")
        
        # Add profit column if possible (assuming 'cost' might come from somewhere else in the future)
        if 'amount' in df_filtered.columns and 'cost' in df_filtered.columns:
            df_filtered['profit'] = df_filtered['amount'] - df_filtered['cost']
        
        # Explanation
        self.explanation.setText("""
<b>ML-based Forecasts for Next Period</b><br>
All predictions below use Facebook Prophet (time series ML model) on your filtered data.<br>
<b>Filters:</b> Time Range, Customer, Status, Product
""")
        # --- ML Forecasts ---
        model = self.model_combo.currentText() if hasattr(self, 'model_combo') else 'Prophet'
        # פונקציה פנימית ליצירת sparkline
        def create_sparkline(series, color='#2196F3', tooltip_fmt=None, index_to_label=None):
            if series is None or len(series) < 2:
                return None
            fig = Figure(figsize=(2.5, 0.6), dpi=100)
            ax = fig.add_subplot(111)
            ax.plot(series, color=color, linewidth=2, marker='o')
            ax.set_xticks([])
            ax.set_yticks([])
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_visible(False)
            ax.spines['bottom'].set_visible(False)
            fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
            buf = io.BytesIO()
            fig.savefig(buf, format='png', bbox_inches='tight', pad_inches=0)
            buf.seek(0)
            pixmap = QPixmap()
            pixmap.loadFromData(buf.getvalue())
            buf.close()
            if tooltip_fmt is not None and index_to_label is not None:
                label = SparklineLabel(series, index_to_label, tooltip_fmt)
                label.setPixmap(pixmap)
                return label
            else:
                label = QLabel()
                label.setPixmap(pixmap)
                return label
        # 1. Order Forecast
        order_text = "Not enough data"
        order_spark = None
        order_fallback_msg = ""
        if not df_filtered.empty:
            if model == 'Prophet':
                order_ml = prophet_forecast(df_filtered, periods=1, freq='W')
            else:
                from prediction_utils import arima_forecast
                order_ml = arima_forecast(df_filtered, periods=1)
            if order_ml is not None:
                if model == 'Prophet':
                    row = order_ml.iloc[-1]
                    if row['yhat'] < 0:
                        order_text = "0 (model predicted negative value, fallback to 0)"
                        order_fallback_msg = "Model predicted a negative value. This usually means there is no recent data or a sharp decline. Fallback to 0."
                    else:
                        order_text = f"₪{row['yhat']:.0f} (range: ₪{row['yhat_lower']:.0f} - ₪{row['yhat_upper']:.0f})"
                else:
                    val = order_ml.iloc[-1]
                    if val < 0:
                        order_text = "0 (model predicted negative value, fallback to 0)"
                        order_fallback_msg = "Model predicted a negative value. This usually means there is no recent data or a sharp decline. Fallback to 0."
                    else:
                        order_text = f"₪{val:,.0f} (ARIMA)"
            else:
                # fallback: Linear Regression
                try:
                    from sklearn.linear_model import LinearRegression
                    df_lr = df_filtered.copy()
                    df_lr = df_lr.dropna(subset=['date', 'amount'])
                    df_lr['date_ordinal'] = df_lr['date'].map(lambda x: x.toordinal())
                    X = df_lr['date_ordinal'].values.reshape(-1, 1)
                    y = df_lr['amount'].values
                    if len(X) > 2:
                        model_lr = LinearRegression().fit(X, y)
                        next_week = [[df_lr['date_ordinal'].max() + 7]]
                        pred = model_lr.predict(next_week)[0]
                        order_text = f"₪{pred:.0f} (LR)"
                        order_fallback_msg = "Fallback: Linear Regression used due to limited data."
                    elif len(X) > 0:
                        avg = df_lr['amount'].mean()
                        order_text = f"₪{avg:.0f} (avg)"
                        order_fallback_msg = "Fallback: Average of available data used due to insufficient data for ML."
                    else:
                        order_text = "No data available"
                        order_fallback_msg = "No data available for prediction."
                except Exception as e:
                    order_text = "No data available"
                    order_fallback_msg = f"Error in fallback: {e}"
            # sparkline - מגמת הזמנות שבועית
            try:
                weekly = df_filtered.set_index('date').resample('W').sum()
                order_spark = create_sparkline(weekly['amount'], color='#2196F3', tooltip_fmt='Week: {label}\nAmount: ₪{value:,.0f}', index_to_label=[str(d.date()) for d in weekly.index])
            except Exception as e:
                order_spark = None
        else:
            # Fallback: ממוצע אחרון
            if 'amount' in df.columns and len(df['amount'].dropna()) > 0:
                avg = df['amount'].dropna().mean()
                order_text = f"₪{avg:.0f} (avg, low confidence)"
                order_fallback_msg = "Fallback: Average of all available data used due to insufficient data."
            else:
                order_text = "No data available"
                order_fallback_msg = "No data available for prediction."

        # 2. Revenue Forecast
        revenue_text = "Not enough data"
        revenue_spark = None
        revenue_fallback_msg = ""
        if not df_filtered.empty:
            revenue_ml = prophet_revenue_forecast(df_filtered, periods=1, freq='W')
            if revenue_ml is not None:
                row = revenue_ml.iloc[-1]
                if row['yhat'] < 0:
                    revenue_text = "0 (model predicted negative value, fallback to 0)"
                    revenue_fallback_msg = "Model predicted a negative value. This usually means there is no recent data or a sharp decline. Fallback to 0."
                else:
                    revenue_text = f"₪{row['yhat']:.0f} (range: ₪{row['yhat_lower']:.0f} - ₪{row['yhat_upper']:.0f})"
            else:
                try:
                    from sklearn.linear_model import LinearRegression
                    df_lr = df_filtered.copy()
                    df_lr = df_lr.dropna(subset=['date', 'amount'])
                    df_lr['date_ordinal'] = df_lr['date'].map(lambda x: x.toordinal())
                    X = df_lr['date_ordinal'].values.reshape(-1, 1)
                    y = df_lr['amount'].values
                    if len(X) > 2:
                        model_lr = LinearRegression().fit(X, y)
                        next_week = [[df_lr['date_ordinal'].max() + 7]]
                        pred = model_lr.predict(next_week)[0]
                        revenue_text = f"₪{pred:.0f} (LR)"
                        revenue_fallback_msg = "Fallback: Linear Regression used due to limited data."
                    elif len(X) > 0:
                        avg = df_lr['amount'].mean()
                        revenue_text = f"₪{avg:.0f} (avg)"
                        revenue_fallback_msg = "Fallback: Average of available data used due to insufficient data for ML."
                    else:
                        revenue_text = "No data available"
                        revenue_fallback_msg = "No data available for prediction."
                except Exception as e:
                    revenue_text = "No data available"
                    revenue_fallback_msg = f"Error in fallback: {e}"
            try:
                weekly = df_filtered.set_index('date').resample('W').sum()
                revenue_spark = create_sparkline(weekly['amount'], color='#4CAF50', tooltip_fmt='Week: {label}\nAmount: ₪{value:,.0f}', index_to_label=[str(d.date()) for d in weekly.index])
            except Exception as e:
                revenue_spark = None
        else:
            if 'amount' in df.columns and len(df['amount'].dropna()) > 0:
                avg = df['amount'].dropna().mean()
                revenue_text = f"₪{avg:.0f} (avg, low confidence)"
                revenue_fallback_msg = "Fallback: Average of all available data used due to insufficient data."
            else:
                revenue_text = "No data available"
                revenue_fallback_msg = "No data available for prediction."

        # 3. Total Number of Orders Forecast (instead of Profit)
        orders_count_text = "Not enough data"
        orders_count_spark = None
        orders_count_fallback_msg = ""
        if not df_filtered.empty and 'date' in df_filtered.columns:
            weekly_orders = df_filtered.set_index('date').resample('W').size().reset_index(name='orders_count')
            orders_count_ml = prophet_forecast(weekly_orders.rename(columns={'orders_count': 'amount'}), periods=1, freq='W')
            if orders_count_ml is not None:
                row = orders_count_ml.iloc[-1]
                if row['yhat'] < 0:
                    orders_count_text = "0 (model predicted negative value, fallback to 0)"
                    orders_count_fallback_msg = "Model predicted a negative value. This usually means there is no recent data or a sharp decline. Fallback to 0."
                else:
                    orders_count_text = f"{row['yhat']:.0f} (range: {row['yhat_lower']:.0f} - {row['yhat_upper']:.0f})"
            else:
                # fallback: ממוצע
                avg = weekly_orders['orders_count'].mean() if not weekly_orders.empty else 0
                orders_count_text = f"{avg:.0f} (avg, low confidence)"
                orders_count_fallback_msg = "Fallback: Average of weekly order counts used due to insufficient data."
            # sparkline - מגמת כמות הזמנות שבועית
            try:
                orders_count_spark = create_sparkline(weekly_orders['orders_count'], color='#FF9800', tooltip_fmt='Week: {label}\nOrders: {value}', index_to_label=[str(d.date()) for d in weekly_orders['date']])
            except Exception as e:
                orders_count_spark = None
        else:
            orders_count_text = "No data available"
            orders_count_fallback_msg = "No data available for prediction."

        # 4. Returning Customers Forecast
        returning_text = "Not enough data"
        returning_spark = None
        returning_fallback_msg = ""
        if 'customer_id' in df_filtered.columns and not df_filtered.empty:
            returning_ml = prophet_returning_customers_forecast(df_filtered, periods=1, freq='W')
            if returning_ml is not None:
                row = returning_ml.iloc[-1]
                if row['yhat'] < 0:
                    returning_text = "0 (model predicted negative value, fallback to 0)"
                    returning_fallback_msg = "Model predicted a negative value. This usually means there is no recent data or a sharp decline. Fallback to 0."
                else:
                    returning_text = f"{row['yhat']:.0f} (range: {row['yhat_lower']:.0f} - {row['yhat_upper']:.0f})"
            else:
                try:
                    df_ret = df_filtered.copy()
                    df_ret['week'] = df_ret['date'].dt.to_period('W').apply(lambda r: r.start_time)
                    weekly = df_ret.groupby('week')['customer_id'].apply(lambda x: x.duplicated().sum()).reset_index()
                    if not weekly.empty:
                        avg = weekly['customer_id'].mean()
                        returning_text = f"{avg:.0f} (avg)"
                        returning_fallback_msg = "Fallback: Average of weekly returning customers used due to insufficient data for ML."
                    else:
                        returning_text = "No data available"
                        returning_fallback_msg = "No data available for prediction."
                except Exception as e:
                    returning_text = "No data available"
                    returning_fallback_msg = f"Error in fallback: {e}"
            try:
                df_ret = df_filtered.copy()
                df_ret['week'] = df_ret['date'].dt.to_period('W').apply(lambda r: r.start_time)
                weekly = df_ret.groupby('week')['customer_id'].apply(lambda x: x.duplicated().sum()).reset_index()
                returning_spark = create_sparkline(weekly['customer_id'], color='#9C27B0', tooltip_fmt='Week: {label}\nAmount: {value}', index_to_label=[str(d.date()) for d in weekly['week']])
            except Exception as e:
                returning_spark = None
        else:
            returning_text = "No data available"
            returning_fallback_msg = "No data available for prediction."

        # 5. Product Forecast (if product selected)
        product_id = self.product_combo.currentData() if self.product_combo else None
        product_text = "Not enough data"
        product_spark = None
        product_fallback_msg = ""
        if product_id:
            product_ml = prophet_product_forecast(df_filtered, product_id, periods=1, freq='W')
            if product_ml is not None:
                row = product_ml.iloc[-1]
                if row['yhat'] < 0:
                    product_text = "0 (model predicted negative value, fallback to 0)"
                    product_fallback_msg = "Model predicted a negative value. This usually means there is no recent data or a sharp decline. Fallback to 0."
                else:
                    product_text = f"₪{row['yhat']:.0f} (range: ₪{row['yhat_lower']:.0f} - ₪{row['yhat_upper']:.0f})"
            else:
                try:
                    from sklearn.linear_model import LinearRegression
                    df_lr = df_filtered[df_filtered['product_id'] == product_id].copy()
                    df_lr = df_lr.dropna(subset=['date', 'amount'])
                    df_lr['date_ordinal'] = df_lr['date'].map(lambda x: x.toordinal())
                    X = df_lr['date_ordinal'].values.reshape(-1, 1)
                    y = df_lr['amount'].values
                    if len(X) > 2:
                        model_lr = LinearRegression().fit(X, y)
                        next_week = [[df_lr['date_ordinal'].max() + 7]]
                        pred = model_lr.predict(next_week)[0]
                        product_text = f"₪{pred:.0f} (LR)"
                        product_fallback_msg = "Fallback: Linear Regression used due to limited data."
                    elif len(X) > 0:
                        avg = df_lr['amount'].mean()
                        product_text = f"₪{avg:.0f} (avg)"
                        product_fallback_msg = "Fallback: Average of available product data used due to insufficient data for ML."
                    else:
                        product_text = "No data available"
                        product_fallback_msg = "No data available for prediction."
                except Exception as e:
                    product_text = "No data available"
                    product_fallback_msg = f"Error in fallback: {e}"
            try:
                df_prod = df_filtered[df_filtered['product_id'] == product_id].copy()
                weekly = df_prod.set_index('date').resample('W').sum()
                product_spark = create_sparkline(weekly['amount'], color='#E91E63', tooltip_fmt='Week: {label}\nAmount: ₪{value:,.0f}', index_to_label=[str(d.date()) for d in weekly.index])
            except Exception as e:
                product_spark = None
        else:
            product_text = "בחר מוצר"
            product_fallback_msg = "No product selected."

        # 6. New Customers Forecast
        new_customers_text = "Not enough data"
        new_customers_spark = None
        new_customers_fallback_msg = ""
        try:
            if not df_filtered.empty and 'customer_id' in df_filtered.columns and 'date' in df_filtered.columns:
                df_new = df_filtered.copy()
                df_new['date'] = pd.to_datetime(df_new['date'])
                df_new = df_new.sort_values('date')
                # Find first order date for each customer
                first_orders = df_new.groupby('customer_id')['date'].min().reset_index()
                # Count new customers per week
                new_customers_per_week = first_orders.groupby(first_orders['date'].dt.to_period('W')).size().reset_index(name='new_customers')
                new_customers_per_week['date'] = new_customers_per_week['date'].dt.start_time
                # Prophet
                if model == 'Prophet':
                    from prophet import Prophet
                    df_prophet = new_customers_per_week.rename(columns={'date': 'ds', 'new_customers': 'y'})
                    m = Prophet()
                    m.fit(df_prophet)
                    future = m.make_future_dataframe(periods=1, freq='W')
                    forecast = m.predict(future)
                    row = forecast.iloc[-1]
                    if row['yhat'] < 0:
                        new_customers_text = "0 (model predicted negative value, fallback to 0)"
                        new_customers_fallback_msg = "Model predicted a negative value. This usually means there is no recent data or a sharp decline. Fallback to 0."
                    else:
                        new_customers_text = f"{row['yhat']:.0f} (range: {row['yhat_lower']:.0f} - {row['yhat_upper']:.0f})"
                else:
                    from statsmodels.tsa.arima.model import ARIMA
                    y = new_customers_per_week['new_customers']
                    if len(y) > 2:
                        model_arima = ARIMA(y, order=(1,1,1))
                        model_fit = model_arima.fit()
                        pred = model_fit.forecast(steps=1)
                        if pred[0] < 0:
                            new_customers_text = "0 (model predicted negative value, fallback to 0)"
                            new_customers_fallback_msg = "Model predicted a negative value. This usually means there is no recent data or a sharp decline. Fallback to 0."
                        else:
                            new_customers_text = f"{pred[0]:.0f} (ARIMA)"
                    elif len(y) > 0:
                        avg = y.mean()
                        if avg < 0:
                            new_customers_text = "0 (model predicted negative value, fallback to 0)"
                            new_customers_fallback_msg = "Model predicted a negative value. This usually means there is no recent data or a sharp decline. Fallback to 0."
                        else:
                            new_customers_text = f"{avg:.0f} (avg)"
                    else:
                        new_customers_text = "No data available"
                        new_customers_fallback_msg = "No data available for prediction."
                # sparkline - מגמת לקוחות חדשים
                try:
                    new_customers_spark = create_sparkline(new_customers_per_week['new_customers'], color='#00BCD4', tooltip_fmt='Week: {label}\nAmount: {value}', index_to_label=[str(d.date()) for d in new_customers_per_week['date']])
                except Exception as e:
                    new_customers_spark = None
        except Exception as e:
            new_customers_text = "No data available"
            new_customers_fallback_msg = f"Error in fallback: {e}"

        # Remove old forecast cards
        while self.forecast_cards_layout.count():
            item = self.forecast_cards_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)

        # Define new ML forecast cards with updated emojis and colors
        cards = [
            ("📈", "Order Forecast", order_text, order_spark, "#3498db", "Predicted total order value for next week.", order_fallback_msg),
            ("💰", "Revenue Forecast", revenue_text, revenue_spark, "#2ecc71", "Predicted total revenue for next week.", revenue_fallback_msg),
            ("📦", "Total Orders Forecast", orders_count_text, orders_count_spark, "#f39c12", "Predicted number of distinct orders for next week.", orders_count_fallback_msg),
            ("👥", "Returning Customers", returning_text, returning_spark, "#9b59b6", "Predicted number of customers who have ordered before.", returning_fallback_msg),
            ("🍄", "Product Forecast", product_text, product_spark, "#e74c3c", "Predicted order value for the selected product.", product_fallback_msg),
            ("✨", "New Customers", new_customers_text, new_customers_spark, "#1abc9c", "Predicted number of customers making their first order.", new_customers_fallback_msg),
        ]
        
        # Create new, redesigned cards
        self.card_widgets = []
        for i, (icon, title, value, spark, color, desc, fallback_msg) in enumerate(cards):
            card = QFrame()
            card.setObjectName("forecastCard")
            card.setCursor(QCursor(Qt.PointingHandCursor))
            card.setStyleSheet(f"""
                #forecastCard {{
                    background-color: #ffffff;
                    border-radius: 12px;
                    border: 1px solid #e9eef2;
                    padding: 20px;
                    margin: 10px;
                }}
                #forecastCard:hover {{
                    border: 1px solid {color};
                }}
                QLabel {{
                    background-color: transparent;
                    border: none;
                }}
                QToolButton {{
                    border: none;
                    background-color: transparent;
                    color: #95a5a6;
                }}
                QToolButton:hover {{
                    color: {color};
                }}
            """)

            vbox = QVBoxLayout(card)
            vbox.setSpacing(10)
            vbox.setContentsMargins(0, 0, 0, 0)

            # --- Header ---
            header = QHBoxLayout()
            header.setSpacing(12)
            icon_label = QLabel(icon)
            icon_label.setStyleSheet(f"font-size: 28px; color: {color};")
            
            title_layout = QVBoxLayout()
            title_layout.setSpacing(0)
            title_label = QLabel(title)
            title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50;")
            desc_label = QLabel(desc)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("font-size: 11px; color: #7f8c8d;")
            title_layout.addWidget(title_label)
            title_layout.addWidget(desc_label)

            info_btn = QToolButton()
            info_btn.setIcon(self.style().standardIcon(QStyle.SP_MessageBoxInformation))
            info_btn.setCursor(QCursor(Qt.PointingHandCursor))
            info_text = fallback_msg if fallback_msg else "This forecast is generated using an ML model based on historical data."
            info_btn.setToolTip(f"Click for more info.")
            
            def make_info_callback(text, t):
                return lambda: QMessageBox.information(self, f"{t} Info", text)
            info_btn.clicked.connect(make_info_callback(info_text, title))

            header.addWidget(icon_label, alignment=Qt.AlignTop)
            header.addLayout(title_layout)
            header.addStretch()
            header.addWidget(info_btn, alignment=Qt.AlignTop)
            vbox.addLayout(header)

            vbox.addStretch(1)

            # --- Value ---
            value_label = QLabel(value)
            value_label.setAlignment(Qt.AlignCenter)
            value_label.setStyleSheet("font-size: 26px; font-weight: bold; color: #34495e; margin-top: 5px;")
            value_label.setWordWrap(True)
            vbox.addWidget(value_label)
            
            # --- High Uncertainty Warning ---
            if 'range:' in value:
                import re
                match = re.search(r'range:.*?([\d,.-]+).*?([\d,.-]+)', value)
                if match:
                    try:
                        lower = float(match.group(1).replace(',', ''))
                        upper = float(match.group(2).replace(',', ''))
                        if upper > 0 and (upper - lower) / upper > 0.75: # High uncertainty if range is >75% of upper bound
                            warn_label = QLabel("⚠️ High uncertainty in forecast")
                            warn_label.setStyleSheet("font-size: 11px; color: #e67e22; font-weight: bold;")
                            warn_label.setAlignment(Qt.AlignCenter)
                            vbox.addWidget(warn_label)
                    except (ValueError, IndexError):
                        pass # Ignore if parsing fails

            vbox.addStretch(1)

            # --- Sparkline ---
            if spark is not None:
                spark_container = QWidget()
                spark_layout = QVBoxLayout(spark_container)
                spark_layout.setContentsMargins(0,5,0,5)
                spark_layout.addWidget(spark, alignment=Qt.AlignCenter)
                vbox.addWidget(spark_container)
            else:
                placeholder = QLabel() # Placeholder to maintain height
                placeholder.setMinimumHeight(30)
                vbox.addWidget(placeholder)

            # --- Fallback/Info Message ---
            if fallback_msg:
                fallback_label = QLabel(f"ℹ️ {fallback_msg}")
                fallback_label.setWordWrap(True)
                fallback_label.setStyleSheet("font-size: 10px; color: #7f8c8d; border-top: 1px solid #f2f2f2; padding-top: 8px; margin-top: 8px;")
                vbox.addWidget(fallback_label)

            self.forecast_cards_layout.addWidget(card, i // 3, i % 3)
            self.card_widgets.append(card)

        # Update insights section
        self.insights_text.setText(self.generate_insights(df_filtered))

    def show_forecast_detail(self, title, df):
        # Prepare the relevant figure for each card
        fig = Figure(figsize=(6, 4))
        ax = fig.add_subplot(111)
        if title == "Total Order Forecast":
            # Weekly trend
            if not df.empty:
                weekly = df.set_index('date').resample('W').sum()
                ax.plot(weekly.index, weekly['amount'], marker='o', color='#43A047')
                ax.set_title('Weekly Order Trend')
                ax.set_xlabel('Week')
                ax.set_ylabel('Total Orders (₪)')
            else:
                ax.text(0.5, 0.5, 'No data available', ha='center', va='center')
        elif title == "Avg. Order Value":
            # Distribution
            if not df.empty:
                ax.hist(df['amount'], bins=10, color='#66BB6A', edgecolor='black')
                ax.set_title('Order Value Distribution')
                ax.set_xlabel('Order Value (₪)')
                ax.set_ylabel('Count')
            else:
                ax.text(0.5, 0.5, 'No data available', ha='center', va='center')
        elif title == "Top Customer":
            # Orders for top customer
            if not df.empty and df['customer_id'].notnull().any():
                top_customer = df['customer_id'].mode()[0]
                cust_df = df[df['customer_id'] == top_customer]
                if not cust_df.empty:
                    ax.plot(cust_df['date'], cust_df['amount'], marker='o', color='#8BC34A')
                    ax.set_title(f'Order History for Customer: {top_customer}')
                    ax.set_xlabel('Date')
                    ax.set_ylabel('Order Value (₪)')
                else:
                    ax.text(0.5, 0.5, 'No data for top customer', ha='center', va='center')
            else:
                ax.text(0.5, 0.5, 'No customer data', ha='center', va='center')
        fig.tight_layout()
        dlg = ForecastDetailDialog(title, fig, self)
        dlg.exec_()

    def update_dashboard_data(self):
        try:
            print("Starting dashboard data update...")
            
            # Get current date for monthly calculations
            now = datetime.now()
            current_month = now.month
            current_year = now.year
            
            # Fetch all necessary data
            print("Fetching data from Firebase...")
            orders_data = _cache_manager.get_data('Order') or {}
            beds_data = _cache_manager.get_data('GrowingBed') or {}
            harvests_data = _cache_manager.get_data('Harvests') or {}
            
            print(f"Retrieved data: Orders: {type(orders_data)}, Beds: {type(beds_data)}, Harvests: {type(harvests_data)}")
            
            # Initialize metrics
            monthly_revenue = 0
            monthly_profit = 0
            yearly_revenue = 0
            yearly_profit = 0
            total_orders_count = 0
            total_order_value = 0
            total_beds = 0
            active_beds = 0
            harvest_ready = 0
            bed_stages = {
                'Spawn Run': 0,
                'Pinning': 0,
                'Fruiting': 0,
                'Harvesting': 0,
                'Empty': 0
            }
            
            # Process orders
            print("Processing orders...")
            if isinstance(orders_data, dict):
                total_orders_count = len(orders_data)
                for order_id, order in orders_data.items():
                    try:
                        if isinstance(order, dict):
                            order_date = order.get('OrderDate', '')
                            if order_date:
                                order_date = datetime.strptime(order_date, '%Y-%m-%d')
                                total_amount = float(order.get('TotalAmount', 0))
                                cost = float(order.get('Cost', 0))  # Assuming we have a Cost field
                                profit = total_amount - cost
                                
                                total_order_value += total_amount
                                
                                if order_date.year == current_year:
                                    yearly_revenue += total_amount
                                    yearly_profit += profit
                                    if order_date.month == current_month:
                                        monthly_revenue += total_amount
                                        monthly_profit += profit
                    except (ValueError, TypeError) as e:
                        print(f"Error processing order {order_id}: {str(e)}")
                        continue
            
            # Calculate average order value
            avg_order_value = total_order_value / total_orders_count if total_orders_count > 0 else 0
            
            # Process beds
            print("Processing beds...")
            if isinstance(beds_data, dict):
                total_beds = len(beds_data)
                for bed_id, bed in beds_data.items():
                    try:
                        if isinstance(bed, dict):
                            stage = bed.get('CurrentGrowthStage', 'Empty')
                            if stage in bed_stages:
                                bed_stages[stage] += 1
                                if stage != 'Empty':
                                    active_beds += 1
                                if stage == 'Harvesting':
                                    harvest_ready += 1
                    except Exception as e:
                        print(f"Error processing bed {bed_id}: {str(e)}")
                        continue
            
            # Calculate percentages
            active_beds_percentage = round((active_beds / total_beds * 100)) if total_beds > 0 else 0
            harvest_ready_percentage = round((harvest_ready / total_beds * 100)) if total_beds > 0 else 0
            
            # Update metric cards
            print("Updating metric cards...")
            self.monthly_revenue_card.update_value(f"₪{monthly_revenue:,.2f}")
            self.monthly_profit_card.update_value(f"₪{monthly_profit:,.2f}")
            self.yearly_revenue_card.update_value(f"₪{yearly_revenue:,.2f}")
            self.yearly_profit_card.update_value(f"₪{yearly_profit:,.2f}")
            self.avg_order_value.update_value(f"₪{avg_order_value:,.2f}")
            self.total_orders.update_value(str(total_orders_count))
            self.active_beds_card.update_value(f"{active_beds}/{total_beds}", active_beds_percentage)
            self.harvest_ready_card.update_value(f"{harvest_ready}/{total_beds}", harvest_ready_percentage)
            
            # Update charts
            print("Updating charts...")
            self.update_profit_chart(orders_data)
            self.update_order_status_pie_chart(orders_data)
            self.update_orders_chart(orders_data)
            
            # Update recent activity
            print("Updating recent activity...")
            self.update_recent_activity(orders_data, beds_data, harvests_data)
            
            print("Dashboard update completed successfully")
            
        except Exception as e:
            print(f"Error updating dashboard: {str(e)}")
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "Error", f"Failed to update dashboard: {str(e)}")
    
    def update_profit_chart(self, orders_data):
        chart = QChart()
        chart.setTitle("Profit and Revenue Trend")
        # Create series for revenue and profit
        revenue_series = QLineSeries()
        revenue_series.setName("Revenue")
        profit_series = QLineSeries()
        profit_series.setName("Profit")
        # Get last 6 months
        months = []
        revenues = []
        profits = []
        now = datetime.now()
        for i in range(5, -1, -1):
            date = now - timedelta(days=i*30)
            month_name = calendar.month_abbr[date.month]
            months.append(month_name)
            # Calculate revenue and profit for this month
            monthly_revenue = 0
            monthly_profit = 0
            if isinstance(orders_data, dict):
                for order in orders_data.values():
                    try:
                        if isinstance(order, dict):
                            order_date = datetime.strptime(order.get('OrderDate', ''), '%Y-%m-%d')
                            if order_date.month == date.month and order_date.year == date.year:
                                total_amount = float(order.get('TotalAmount', 0))
                                cost = float(order.get('Cost', 0))
                                monthly_revenue += total_amount
                                monthly_profit += (total_amount - cost)
                    except (ValueError, TypeError):
                        continue
            revenues.append(monthly_revenue)
            profits.append(monthly_profit)
        # Add data to series
        for i, (rev, prof) in enumerate(zip(revenues, profits)):
            revenue_series.append(i, rev)
            profit_series.append(i, prof)
        chart.addSeries(revenue_series)
        chart.addSeries(profit_series)
        # Set up axes
        axis_x = QValueAxis()
        axis_x.setRange(0, 5)
        axis_x.setTickCount(6)
        axis_x.setLabelFormat("%s")
        axis_x.setLabelsAngle(-45)
        chart.addAxis(axis_x, Qt.AlignBottom)
        revenue_series.attachAxis(axis_x)
        profit_series.attachAxis(axis_x)
        axis_y = QValueAxis()
        chart.addAxis(axis_y, Qt.AlignLeft)
        revenue_series.attachAxis(axis_y)
        profit_series.attachAxis(axis_y)
        # Enable hover effects only (no always-on labels)
        chart.setAcceptHoverEvents(True)
        chart.setCursor(Qt.PointingHandCursor)
        # Add hover tooltips only
        def hover_changed(point, state):
            if state:
                idx = int(point.x())
                if 0 <= idx < len(months):
                    tooltip = f"Month: {months[idx]}\n"
                    tooltip += f"Revenue: ₪{revenues[idx]:,.0f}\n"
                    tooltip += f"Profit: ₪{profits[idx]:,.0f}"
                    QToolTip.showText(QCursor.pos(), tooltip)
            else:
                QToolTip.hideText()
        revenue_series.hovered.connect(hover_changed)
        profit_series.hovered.connect(hover_changed)
        # Reduce font size for axes
        font = QFont()
        font.setPointSize(9)
        axis_x.setLabelsFont(font)
        axis_y.setLabelsFont(font)
        chart.legend().setFont(font)
        chart.legend().setAlignment(Qt.AlignBottom)
        self.profit_chart.setChart(chart)
    
    def update_order_status_pie_chart(self, orders_data):
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
        # Prepare data
        status_labels = ["Pending", "Processing", "Shipped", "Delivered", "Cancelled"]
        colors = ['#f1c40f', '#e67e22', '#3498db', '#2ecc71', '#e74c3c']
        status_counts = {k: 0 for k in status_labels}
        total_orders = 0
        if isinstance(orders_data, dict):
            for order in orders_data.values():
                if isinstance(order, dict):
                    status = order.get("Status", "Pending")
                    for valid in status_labels:
                        if status.lower() == valid.lower():
                            status = valid
                            break
                    if status in status_counts:
                        status_counts[status] += 1
                        total_orders += 1
        sizes = [status_counts[k] for k in status_labels]
        # Remove previous chart widget if exists
        if self.beds_chart.layout() is not None:
            while self.beds_chart.layout().count():
                item = self.beds_chart.layout().takeAt(0)
                widget = item.widget()
                if widget:
                    widget.setParent(None)
        else:
            self.beds_chart.setLayout(QVBoxLayout())
        # Create matplotlib pie chart
        fig = Figure(figsize=(4, 4))
        ax = fig.add_subplot(111)
        wedges, texts, autotexts = ax.pie(
            sizes,
            labels=status_labels,
            colors=colors,
            autopct=lambda pct: f'{pct:.1f}%' if pct > 0 else '',
            startangle=90
        )
        ax.set_title('Order Status Distribution')
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
                    ax.set_title(f"{status_labels[i]}: {sizes[i]} orders ({percent:.1f}%)")
                    found = True
                else:
                    wedge.set_alpha(1.0)
            if not found:
                ax.set_title('Order Status Distribution')
            canvas.draw_idle()
        canvas.mpl_connect('motion_notify_event', on_move)
        self.beds_chart.layout().addWidget(canvas)
    
    def update_orders_chart(self, orders_data):
        chart = QChart()
        chart.setTitle("Order Value Distribution")
        
        # Create bar series
        series = QBarSeries()
        order_set = QBarSet("Order Value")
        
        # Define value ranges
        ranges = [
            (0, 1000),
            (1000, 2000),
            (2000, 5000),
            (5000, 10000),
            (10000, float('inf'))
        ]
        
        # Count orders in each range
        counts = [0] * len(ranges)
        if isinstance(orders_data, dict):
            for order in orders_data.values():
                try:
                    if isinstance(order, dict):
                        amount = float(order.get('TotalAmount', 0))
                        for i, (min_val, max_val) in enumerate(ranges):
                            if min_val <= amount < max_val:
                                counts[i] += 1
                                break
                except (ValueError, TypeError):
                    continue
        
        # Add data to bar set
        order_set.append(counts)
        series.append(order_set)
        chart.addSeries(series)
        
        # Add tooltips to bars
        for i, count in enumerate(counts):
            order_set.setLabel(f"{count} Orders")
        
        # Set up axes
        axis_x = QBarCategoryAxis()
        axis_x.append(["0-1,000", "1,000-2,000", "2,000-5,000", "5,000-10,000", "10,000+"])
        chart.addAxis(axis_x, Qt.AlignBottom)
        series.attachAxis(axis_x)
        
        axis_y = QValueAxis()
        chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_y)
        
        # Enable hover effects
        chart.setAcceptHoverEvents(True)
        chart.setCursor(Qt.PointingHandCursor)
        
        # Add hover tooltips
        def hover_changed(status, index, barset):
            if status:
                range_text = ["0-1,000", "1,000-2,000", "2,000-5,000", "5,000-10,000", "10,000+"][index]
                tooltip = f"Range: {range_text}\n"
                tooltip += f"Number of Orders: {counts[index]}"
                QToolTip.showText(QCursor.pos(), tooltip)
            else:
                QToolTip.hideText()
        
        series.hovered.connect(hover_changed)
        
        self.orders_chart.setChart(chart)
    
    def handle_slice_hover(self, state, slice, label=None):
        """Handle hover events for pie chart slices"""
        if state:
            # Increase explosion factor on hover
            slice.setExplodeDistanceFactor(0.15)
            percentage = (slice.percentage() * 100)
            # Tooltip מפורט
            if label is None:
                label = slice.label()
            tooltip = f"{label}\nאחוז: {percentage:.1f}%"
            QToolTip.showText(QCursor.pos(), tooltip)
        else:
            # Reset explosion factor
            slice.setExplodeDistanceFactor(0.05)
            QToolTip.hideText()
    
    def update_recent_activity(self, orders_data, beds_data, harvests_data):
        # Clear existing activity items
        for i in reversed(range(self.activity_layout.count())): 
            self.activity_layout.itemAt(i).widget().setParent(None)
        
        activities = []
        
        # Add recent orders
        if isinstance(orders_data, dict):
            try:
                for order_id, order in orders_data.items():
                    if isinstance(order, dict):
                        try:
                            order_date = order.get('OrderDate', '')
                            if order_date:
                                activities.append((
                                    order_date,
                                    f"📦 Order #{order_id}: ₪{float(order.get('TotalAmount', 0)):,.2f}"
                                ))
                        except (ValueError, TypeError) as e:
                            print(f"Error processing order activity {order_id}: {str(e)}")
            except Exception as e:
                print(f"Error processing orders for activity: {str(e)}")
        
        # Add bed status changes
        if isinstance(beds_data, dict):
            for bed_id, bed in beds_data.items():
                if isinstance(bed, dict):
                    try:
                        stage = bed.get('CurrentGrowthStage', '')
                        last_updated = bed.get('LastUpdated', '')
                        if stage and last_updated:
                            if stage == 'Harvesting':
                                activities.append((
                                    last_updated,
                                    f"🍄 Bed #{bed_id} ready for harvest!"
                                ))
                            elif stage == 'Fruiting':
                                activities.append((
                                    last_updated,
                                    f"🌱 Bed #{bed_id} in fruiting phase"
                                ))
                    except Exception as e:
                        print(f"Error processing bed activity {bed_id}: {str(e)}")
        
        # Add recent harvests
        if isinstance(harvests_data, dict):
            try:
                for harvest_id, harvest in harvests_data.items():
                    if isinstance(harvest, dict):
                        try:
                            harvest_date = harvest.get('date', '')
                            if harvest_date:
                                activities.append((
                                    harvest_date,
                                    f"⚖️ Harvest #{harvest_id}: {harvest.get('quantity', 0)}kg"
                                ))
                        except (ValueError, TypeError) as e:
                            print(f"Error processing harvest activity {harvest_id}: {str(e)}")
            except Exception as e:
                print(f"Error processing harvests for activity: {str(e)}")
        
        # Sort activities by date and display
        activities.sort(key=lambda x: x[0], reverse=True)
        for date, message in activities[:10]:
            activity = QLabel(f"{date}: {message}")
            activity.setStyleSheet("color: #333; padding: 5px 0;")
            self.activity_layout.addWidget(activity)

    def generate_insights(self, df):
        # Example insights: monthly growth, best product, returning customers
        if df.empty or 'amount' not in df.columns:
            return "Not enough data for insights."
        try:
            # Monthly growth
            df_month = df.set_index('date').resample('M').sum()
            if len(df_month) >= 2:
                last, prev = df_month['amount'].iloc[-1], df_month['amount'].iloc[-2]
                growth = ((last - prev) / prev) * 100 if prev else 0
                if growth > 0:
                    growth_text = f"This month saw a <b>{growth:.1f}% increase</b> in orders."
                elif growth < 0:
                    growth_text = f"This month saw a <b>{abs(growth):.1f}% decrease</b> in orders."
                else:
                    growth_text = "No change in orders this month."
            else:
                growth_text = "Not enough data for monthly growth."
            # Best-selling product
            if 'product_id' in df.columns and df['product_id'].notnull().any():
                best_product = df.groupby('product_id')['amount'].sum().idxmax()
                best_text = f"Best-selling product: <b>{best_product}</b>."
            else:
                best_text = "No product data available."
            # Returning customers
            if 'customer_id' in df.columns:
                returning = df.duplicated(subset=['customer_id']).sum()
                returning_text = f"Returning customers this period: <b>{returning}</b>."
            else:
                returning_text = "No customer data available."
            return f"{growth_text}<br>{best_text}<br>{returning_text}"
        except Exception as e:
            return f"Error generating insights: {e}"

    def get_product_name_map(self):
        ref = db.reference('Products')
        products = ref.get() or {}
        return {pid: prod.get('Name', pid) for pid, prod in products.items()}

    def get_customer_name_map(self):
        ref = db.reference('Customer')
        customers = ref.get() or {}
        return {cid: cust.get('Name', cid) for cid, cust in customers.items()}

    def add_new_user(self):
        username = self.new_username.text()
        password = self.new_password.text()
        role = self.new_role.currentText()
        if not username or not password:
            QMessageBox.warning(self, "Error", "Please fill in all fields.")
            return
        success, message = UserManagement.add_user(username, password, role)
        if success:
            QMessageBox.information(self, "Success", message)
            self.new_username.clear()
            self.new_password.clear()
        else:
            QMessageBox.warning(self, "Error", message)

if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    
    # Apply style to the entire application
    app.setStyleSheet("""
        QWidget {
            font-family: Arial, sans-serif;
            background-color: #f5f5f5;
        }
    """)
    
    dashboard = AdminDashboard()
    dashboard.show()
    sys.exit(app.exec_()) 