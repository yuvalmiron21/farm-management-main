import sys
import os
import pandas as pd
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QComboBox,
    QPushButton, QDateEdit, QGridLayout, QDialog, QMessageBox, QFrame, QSpacerItem, QSizePolicy, QScrollArea,
    QLineEdit
)
from PyQt5.QtChart import QChart, QChartView, QLineSeries, QDateTimeAxis, QValueAxis, QSplineSeries
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QLinearGradient, QGradient, QPalette
from PyQt5.QtCore import Qt, QDateTime, QPoint, QPointF, QRectF, QSize, QMargins, QTimer
from babel.plural import value_node

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from models.analytics_backend import AnalyticsBackend
import numpy as np

# Import the new insights view
from UI.InsightsView import InsightsView


class CustomChartView(QChartView):
    def __init__(self, chart, y_label):
        super().__init__(chart)
        self.y_label = y_label
        
        # Create a modern tooltip
        self.tooltip = QFrame(self)
        self.tooltip.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #2c3e50, stop:1 #3498db);
                color: white;
                border-radius: 8px;
                padding: 12px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
        """)
        
        self.tooltip_label = QLabel(self.tooltip)
        self.tooltip_label.setStyleSheet("""
            color: white;
            font-size: 13px;
            font-weight: bold;
        """)
        
        layout = QVBoxLayout(self.tooltip)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.tooltip_label)
        self.tooltip.hide()

        # Store the current closest point for hover detection
        self.current_closest_point = None
        self.hover_threshold = 20  # pixels
        
    def mouseMoveEvent(self, event):
        pos = event.pos()
        series = self.chart().series()[0]  # Get the first series
        
        # Convert screen coordinates to chart coordinates
        chart_pos = self.chart().mapToValue(QPointF(pos))
        
        # Find the closest data point and its distance
        closest_point = None
        min_distance = float('inf')
        closest_screen_point = None
        
        for point in series.pointsVector():
            # Convert data point to screen coordinates
            screen_point = self.chart().mapToPosition(point)
            
            # Calculate Euclidean distance in screen coordinates
            dx = screen_point.x() - pos.x()
            dy = screen_point.y() - pos.y()
            distance = (dx * dx + dy * dy) ** 0.5
            
            if distance < min_distance:
                min_distance = distance
                closest_point = point
                closest_screen_point = screen_point
        
        # Only show tooltip if cursor is within threshold distance of a point
        if closest_point and min_distance <= self.hover_threshold:
            self.current_closest_point = closest_point
            
            # Convert timestamp to datetime
            dt = QDateTime.fromMSecsSinceEpoch(int(closest_point.x())).toString("yyyy-MM-dd hh:mm")
            value = closest_point.y()
            
            # Update tooltip text
            self.tooltip_label.setText(f"Date: {dt}\nValue: {value:.2f} {self.y_label}")
            
            # Position tooltip near the data point
            tooltip_x = closest_screen_point.x() + 10
            tooltip_y = closest_screen_point.y() - self.tooltip.height() - 10
            
            # Adjust if tooltip would go off screen
            if tooltip_x + self.tooltip.width() > self.width():
                tooltip_x = closest_screen_point.x() - self.tooltip.width() - 10
            if tooltip_y < 0:
                tooltip_y = closest_screen_point.y() + 10
            
            self.tooltip.move(int(tooltip_x), int(tooltip_y))
            self.tooltip.show()
            
            # Optional: Add visual indicator of selected point
            self.update()  # Trigger repaint for custom point highlighting
        else:
            self.current_closest_point = None
            self.tooltip.hide()
            self.update()
            
    def paintEvent(self, event):
        super().paintEvent(event)
        
        # Draw highlight for the closest point if it exists
        if self.current_closest_point:
            painter = QPainter(self.viewport())
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Convert data point to screen coordinates
            screen_point = self.chart().mapToPosition(self.current_closest_point)
            
            # Draw point highlight
            painter.setPen(QPen(QColor("#ffffff"), 2))
            painter.setBrush(QColor("#3498db"))
            painter.drawEllipse(screen_point, 6, 6)
            
    def leaveEvent(self, event):
        self.current_closest_point = None
        self.tooltip.hide()
        self.update()


class AnalyticsApp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Initialize backend with error handling
        try:
            self.backend = AnalyticsBackend()
        except Exception as e:
            print(f"🚨 Error initializing AnalyticsBackend: {str(e)}")
            # Show error message to user
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Analytics Error", 
                               f"Failed to load analytics data:\n{str(e)}\n\nThe analytics dashboard will show with limited functionality.")
            # Create a dummy backend with empty data
            self.backend = None

        self.setWindowTitle("MUSH - Analytics Dashboard")
        # Set a fixed size instead of fullscreen for better control
        self.setMinimumSize(1600, 900)
        
        # Create a scroll area for the main content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #1a1a2e;
            }
            QScrollBar:vertical {
                background: #1a1a2e;
                width: 12px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #3498db;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #2980b9;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: rgba(255, 255, 255, 0.1);
                border-radius: 6px;
            }
        """)
        self.setCentralWidget(scroll_area)
        
        # Create main widget with a dark theme
        main_widget = QWidget()
        scroll_area.setWidget(main_widget)
        
        # Modern color palette
        main_widget.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #1a1a2e;
                color: #ffffff;
            }
            QLabel {
                font-size: 14px;
                color: #ffffff;
                padding: 5px;
            }
            QLabel#title {
                font-size: 28px;
                font-weight: bold;
                color: #ffffff;
                padding: 20px 0;
            }
            QLabel#stats {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2c3e50, stop:1 #3498db);
                border-radius: 10px;
                padding: 15px;
                margin: 10px;
                font-size: 15px;
            }
            QLabel#details {
                background: rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                padding: 15px;
                margin: 10px;
                font-size: 14px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
            QComboBox, QDateEdit {
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
                padding: 8px;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 6px;
                font-size: 14px;
                min-width: 150px;
            }
            QComboBox:hover, QDateEdit:hover {
                background-color: rgba(255, 255, 255, 0.15);
                border: 1px solid rgba(255, 255, 255, 0.3);
            }
            QComboBox::drop-down, QDateEdit::drop-down {
                border: none;
                padding-right: 10px;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3498db, stop:1 #2980b9);
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
                min-width: 120px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3498db, stop:1 #2475a8);
            }
            QPushButton#backButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #e74c3c, stop:1 #c0392b);
                position: fixed;
                top: 20px;
                left: 20px;
            }
            QPushButton#backButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #c0392b, stop:1 #a93226);
            }
            QChart {
                background-color: transparent;
                color: white;
            }
        """)

        # Main layout with proper spacing
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        main_widget.setLayout(layout)

        # Create insight notification banner (initially hidden)
        self.insight_banner = QFrame()
        self.insight_banner.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2c3e50, stop:1 #3498db);
                color: white;
                border-radius: 10px;
                padding: 15px;
                margin: 10px;
            }
            QLabel {
                color: white;
                font-size: 14px;
            }
            QPushButton#insightButton {
                background: rgba(255, 255, 255, 0.2);
                border-radius: 5px;
                padding: 8px 15px;
                color: white;
                font-weight: bold;
            }
            QPushButton#insightButton:hover {
                background: rgba(255, 255, 255, 0.3);
            }
            QPushButton#closeButton {
                background: transparent;
                color: rgba(255, 255, 255, 0.7);
                font-size: 16px;
                font-weight: bold;
                padding: 0;
                margin: 0;
                border: none;
                min-width: 20px;
            }
            QPushButton#closeButton:hover {
                color: white;
            }
        """)
        self.insight_banner.hide()  # Hide initially

        # Create the insights window (but don't show it yet)
        self.insights_view = None

        # Header section with back button and title
        header_layout = QHBoxLayout()
        
        # Back button
        back_button = QPushButton("← Back to Main Menu")
        back_button.setObjectName("backButton")
        back_button.clicked.connect(self.close)
        back_button.setFixedWidth(200)
        header_layout.addWidget(back_button)
        
        # Title
        title_label = QLabel("🌱 Farm Analytics Dashboard")
        title_label.setObjectName("title")
        title_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(title_label)
        
        # Add insights button
        insights_button = QPushButton("✨ View Insights")
        insights_button.setObjectName("insightsButton")
        insights_button.setStyleSheet("""
            QPushButton#insightsButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #9b59b6, stop:1 #8e44ad);
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
                min-width: 150px;
            }
            QPushButton#insightsButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #8e44ad, stop:1 #762d93);
            }
        """)
        insights_button.clicked.connect(self.show_insights)
        insights_button.setFixedWidth(200)
        header_layout.addWidget(insights_button)
        
        # Add stretch to keep title centered
        header_layout.insertStretch(0)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)

        # Create a container for stats and details
        info_container = QHBoxLayout()
        info_container.setSpacing(20)
        
        # Stats card
        self.stats_label = QLabel(self.backend.generate_statistics())
        self.stats_label.setObjectName("stats")
        info_container.addWidget(self.stats_label)
        
        # Batch details card
        self.batch_details_label = QLabel("Batch Details:\nSelect a batch to see details.")
        self.batch_details_label.setObjectName("details")
        info_container.addWidget(self.batch_details_label)
        
        layout.addLayout(info_container)

        # Filters container
        filters_container = QHBoxLayout()
        filters_container.setSpacing(20)
        
        # Left side filters
        left_filters = QHBoxLayout()
        left_filters.setSpacing(15)

        # Batch filter
        batch_section = QVBoxLayout()
        batch_label = QLabel("Batch ID:")
        self.batch_filter = QLineEdit()
        self.batch_filter.setPlaceholderText("Enter batch ID or leave empty for all")
        batch_section.addWidget(batch_label)
        batch_section.addWidget(self.batch_filter)
        left_filters.addLayout(batch_section)

        # Mushroom type filter
        mushroom_section = QVBoxLayout()
        mushroom_label = QLabel("Mushroom Type:")
        self.mushroom_filter = QComboBox()
        self.mushroom_filter.addItem("All Types")
        self.mushroom_filter.addItems(sorted(set(map(str, self.backend.get_mushroom_types()))))
        mushroom_section.addWidget(mushroom_label)
        mushroom_section.addWidget(self.mushroom_filter)
        left_filters.addLayout(mushroom_section)

        filters_container.addLayout(left_filters)

        # Date range filters
        date_section = QVBoxLayout()
        date_label = QLabel("Date Range:")
        dates_layout = QHBoxLayout()
        
        self.start_date_filter = QDateEdit()
        self.start_date_filter.setCalendarPopup(True)
        self.start_date_filter.setDate(pd.Timestamp(self.backend.get_earliest_date()).to_pydatetime().date())
        
        self.end_date_filter = QDateEdit()
        self.end_date_filter.setCalendarPopup(True)
        self.end_date_filter.setDate(pd.Timestamp(self.backend.get_latest_date()).to_pydatetime().date())
        
        dates_layout.addWidget(self.start_date_filter)
        dates_layout.addWidget(QLabel("to"))
        dates_layout.addWidget(self.end_date_filter)
        
        date_section.addWidget(date_label)
        date_section.addLayout(dates_layout)
        filters_container.addLayout(date_section)

        # Apply filters button
        apply_filter_button = QPushButton("Apply Filters")
        apply_filter_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2ecc71, stop:1 #27ae60);
                color: white;
                padding: 12px 24px;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
                min-width: 150px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #27ae60, stop:1 #219a52);
            }
        """)
        apply_filter_button.clicked.connect(self.update_graphs)
        filters_container.addWidget(apply_filter_button)
        
        # Add stretch to push everything to the left
        filters_container.addStretch()
        
        layout.addLayout(filters_container)

        # Yield percentage
        self.yield_percentage_label = QLabel("Yield Percentage: N/A")
        self.yield_percentage_label.setObjectName("stats")
        layout.addWidget(self.yield_percentage_label)

        # Charts container with fixed size
        charts_container = QWidget()
        charts_layout = QGridLayout(charts_container)
        charts_layout.setSpacing(20)

        # Create and style charts with fixed sizes
        self.air_temp_chart = self.create_chart("Air Temperature", "°C")
        self.humidity_chart = self.create_chart("Humidity", "%")
        self.co2_chart = self.create_chart("CO₂ Levels", "ppm")
        self.substrate_temp_chart = self.create_chart("Substrate Temperature", "°C")

        # Add charts to grid with proper sizing
        charts_layout.addWidget(self.air_temp_chart, 0, 0)
        charts_layout.addWidget(self.humidity_chart, 0, 1)
        charts_layout.addWidget(self.co2_chart, 1, 0)
        charts_layout.addWidget(self.substrate_temp_chart, 1, 1)

        # Set column and row stretching
        charts_layout.setColumnStretch(0, 1)
        charts_layout.setColumnStretch(1, 1)
        charts_layout.setRowStretch(0, 1)
        charts_layout.setRowStretch(1, 1)

        # Set fixed height for charts container based on window size
        charts_container.setMinimumHeight(600)  # Increased minimum height
        
        layout.addWidget(charts_container)
        
        # Setup the insight banner
        self.setup_insight_banner()
        layout.addWidget(self.insight_banner)
        
        # Show the insight banner after a delay
        QTimer.singleShot(1500, self.show_insight_banner)
        
        # Add stretch at the bottom to ensure proper spacing
        layout.addStretch()
        
        # Update the graphs initially
        self.update_graphs()

        # Remove the automatic update on text change
        # self.batch_filter.textChanged.disconnect(self.update_batch_details)  # Remove this line
        # Only update batch details (not graphs) on text change
        self.batch_filter.textChanged.connect(self.update_batch_details)  # Keep this connection

        # Make the batch filter red when invalid
        self.batch_filter.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
                padding: 8px;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 6px;
                font-size: 14px;
                min-width: 150px;
            }
            QLineEdit:hover {
                background-color: rgba(255, 255, 255, 0.15);
                border: 1px solid rgba(255, 255, 255, 0.3);
            }
            QLineEdit[invalid="true"] {
                border: 1px solid #e74c3c;
                background-color: rgba(231, 76, 60, 0.1);
            }
        """)
        self.batch_filter.setProperty("invalid", False)

    def update_graphs(self):
        batch_id = self.batch_filter.text().strip()  # Add strip() to remove whitespace
        mushroom_type = self.mushroom_filter.currentText()
        start_date = pd.Timestamp(self.start_date_filter.date().toPyDate())
        end_date = pd.Timestamp(self.end_date_filter.date().toPyDate())

        # Convert batch_id to int only if it's not empty
        batch_id_param = int(batch_id) if batch_id and batch_id.isdigit() else "All Batches"

        # Update charts
        self.update_chart(self.air_temp_chart, self.backend.get_air_temp_data(batch_id_param, mushroom_type, start_date, end_date))
        self.update_chart(self.humidity_chart, self.backend.get_humidity_data(batch_id_param, mushroom_type, start_date, end_date))
        self.update_chart(self.co2_chart, self.backend.get_co2_data(batch_id_param, mushroom_type, start_date, end_date))
        self.update_chart(self.substrate_temp_chart, self.backend.get_substrate_temp_data(batch_id_param, mushroom_type, start_date, end_date))

        # Update Yield Percentage
        if batch_id and batch_id.isdigit():
            try:
                yield_percentage = self.backend.calculate_yield_percentage(int(batch_id))
                self.yield_percentage_label.setText(f"Yield Percentage: {yield_percentage:.2f}%")
            except Exception:
                self.yield_percentage_label.setText("Yield Percentage: N/A")
        elif batch_id_param == "All Batches":
            try:
                # Calculate average yield percentage for all batches
                all_yields = []
                for batch in self.backend.batches:
                    try:
                        yield_percentage = self.backend.calculate_yield_percentage(batch.batch_id)
                        if yield_percentage is not None:
                            all_yields.append(yield_percentage)
                    except Exception:
                        continue
                
                if all_yields:
                    avg_yield = sum(all_yields) / len(all_yields)
                    self.yield_percentage_label.setText(f"Average Yield Percentage (All Batches): {avg_yield:.2f}%")
                else:
                    self.yield_percentage_label.setText("Yield Percentage: N/A")
            except Exception:
                self.yield_percentage_label.setText("Yield Percentage: N/A")
        else:
            self.yield_percentage_label.setText("Yield Percentage: N/A")

    def create_chart(self, title, y_label):
        chart = QChart()
        chart.setTitle(title)
        chart.setAnimationOptions(QChart.SeriesAnimations)
        chart.setBackgroundVisible(False)
        chart.setDropShadowEnabled(True)
        chart.setMargins(QMargins(10, 10, 10, 10))
        
        # Style the chart
        chart.setTitleFont(QFont("Arial", 12, QFont.Bold))
        chart.setTitleBrush(QColor("#ffffff"))
        
        # Create series with modern styling
        series = QSplineSeries()
        gradient = QLinearGradient(QPointF(0, 0), QPointF(1, 1))
        gradient.setColorAt(0.0, QColor("#3498db"))
        gradient.setColorAt(1.0, QColor("#2ecc71"))
        gradient.setCoordinateMode(QGradient.ObjectBoundingMode)
        
        pen = QPen(QColor("#3498db"), 2.5)
        series.setPen(pen)
        chart.addSeries(series)

        # Style axes
        axis_x = QDateTimeAxis()
        axis_x.setFormat("dd-MM-yyyy")
        axis_x.setTitleText("Date")
        axis_x.setLabelsColor(QColor("#ffffff"))
        axis_x.setTitleBrush(QColor("#ffffff"))
        chart.addAxis(axis_x, Qt.AlignBottom)
        series.attachAxis(axis_x)

        axis_y = QValueAxis()
        axis_y.setTitleText(y_label)
        axis_y.setLabelsColor(QColor("#ffffff"))
        axis_y.setTitleBrush(QColor("#ffffff"))
        chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_y)

        # Use custom chart view with tooltips
        chart_view = CustomChartView(chart, y_label)
        chart_view.setRenderHint(QPainter.Antialiasing)
        
        # Set fixed size for better layout
        chart_view.setMinimumSize(QSize(700, 350))  # Increased size for better visibility
        
        return chart_view

    def update_chart(self, chart_view, data):
        """Helper function to update a line chart with new data and display statistics."""
        # Use QSplineSeries for smoother lines
        series = QSplineSeries()
        series.setPen(QPen(QColor("#3498db"), 2))
        values = []

        # Always apply smoothing for better performance, with different intervals based on data size
        if data:  # Only process if we have data
            try:
                # Sort data by timestamp
                data.sort(key=lambda x: x[0])
                
                # Determine interval size based on data length
                if len(data) > 1000:
                    interval_size = 86400  # 24 hours in seconds for very large datasets
                elif len(data) > 500:
                    interval_size = 43200  # 12 hours in seconds for large datasets
                elif len(data) > 100:
                    interval_size = 21600  # 6 hours in seconds for medium datasets
                else:
                    interval_size = 3600   # 1 hour in seconds for small datasets
                
                # Group data points into intervals
                grouped_data = {}
                
                for timestamp, value in data:
                    if value is not None and not pd.isna(value):
                        interval = timestamp // interval_size
                        if interval not in grouped_data:
                            grouped_data[interval] = []
                        grouped_data[interval].append(value)
                
                # Calculate average for each interval
                smoothed_data = []
                for interval, interval_values in sorted(grouped_data.items()):
                    if interval_values:  # Only add intervals that have values
                        avg_value = sum(interval_values) / len(interval_values)
                        smoothed_data.append((interval * interval_size, avg_value))
                
                data = smoothed_data
            except Exception:
                # Silently fall back to original data if smoothing fails
                pass

        # Add data points to series
        for timestamp, value in data:
            if value is not None and not pd.isna(value):  # Only add non-null values
                dt = QDateTime.fromSecsSinceEpoch(timestamp)
                series.append(dt.toMSecsSinceEpoch(), value)
                values.append(value)

        chart = chart_view.chart()
        chart.removeAllSeries()
        chart.addSeries(series)

        # Remove existing axes before adding new ones
        for axis in chart.axes():
            chart.removeAxis(axis)

        # Create new X-axis
        axis_x = QDateTimeAxis()
        axis_x.setFormat("dd-MM-yyyy")
        axis_x.setTitleText("Date")
        chart.addAxis(axis_x, Qt.AlignBottom)
        series.attachAxis(axis_x)

        # Create new Y-axis
        axis_y = QValueAxis()
        axis_y.setTitleText(chart.title())
        chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_y)

        # Calculate statistics and set axis range
        if values:
            valid_values = [v for v in values if v is not None and not pd.isna(v)]
            if valid_values:
                min_val = min(valid_values)
                max_val = max(valid_values)
                padding = (max_val - min_val) * 0.1 if max_val != min_val else max_val * 0.1
                axis_y.setRange(min_val - padding, max_val + padding)

    def update_batch_details(self):
        batch_id = self.batch_filter.text().strip()  # Add strip() to remove whitespace
        
        # Reset the invalid state
        self.batch_filter.setProperty("invalid", False)
        self.batch_filter.style().unpolish(self.batch_filter)
        self.batch_filter.style().polish(self.batch_filter)
        
        if not batch_id:
            self.batch_details_label.setText("Batch Details:\nEnter a batch ID to see details.")
            return

        if not batch_id.isdigit():
            self.batch_filter.setProperty("invalid", True)
            self.batch_filter.style().unpolish(self.batch_filter)
            self.batch_filter.style().polish(self.batch_filter)
            self.batch_details_label.setText("Batch Details:\nPlease enter a valid batch ID number.")
            return

        try:
            batch_id = int(batch_id)
            batch = next((b for b in self.backend.batches if b.batch_id == batch_id), None)
            if batch:
                mushroom_map = {
                    1 : "Erinji",
                    2 : "Shiitake",
                    3 : "Maitake",
                    4 : "Hericium",
                    5 : "Tiger Sawgill",
                    6 : "Nebrodensis"
                }
                details = (f"Batch Details:\n"
                          f"Batch ID: {batch.batch_id}\n"
                          f"Mushroom Type: {mushroom_map[batch.mushroom_type]}\n"
                          f"Iteration ID: {batch.iteration_id}\n"
                          f"Start Date: {batch.start_date.strftime('%Y-%m-%d')}\n"
                          f"Room Number: {batch.room_number}\n"
                          f"Substrate: {batch.substrate} kg")
                self.batch_details_label.setText(details)
                # Reset invalid state if batch is found
                self.batch_filter.setProperty("invalid", False)
                self.batch_filter.style().unpolish(self.batch_filter)
                self.batch_filter.style().polish(self.batch_filter)
            else:
                self.batch_filter.setProperty("invalid", True)
                self.batch_filter.style().unpolish(self.batch_filter)
                self.batch_filter.style().polish(self.batch_filter)
                self.batch_details_label.setText(f"Batch Details:\nBatch ID {batch_id} not found.")
        except ValueError:
            self.batch_filter.setProperty("invalid", True)
            self.batch_filter.style().unpolish(self.batch_filter)
            self.batch_filter.style().polish(self.batch_filter)
            self.batch_details_label.setText("Batch Details:\nPlease enter a valid batch ID number.")

    def setup_insight_banner(self):
        """Set up the insight banner that shows at the bottom of the screen"""
        banner_layout = QHBoxLayout(self.insight_banner)
        banner_layout.setContentsMargins(15, 10, 15, 10)
        
        # Icon
        icon_label = QLabel("🔮")
        icon_label.setFixedWidth(30)
        banner_layout.addWidget(icon_label)
        
        # Message
        message_label = QLabel("New insights about your farm are available! Discover optimal growing conditions and yield factors.")
        message_label.setWordWrap(True)
        banner_layout.addWidget(message_label)
        
        # View button
        view_button = QPushButton("View Insights")
        view_button.setObjectName("insightButton")
        view_button.clicked.connect(self.show_insights)
        banner_layout.addWidget(view_button)
        
        # Close button
        close_button = QPushButton("×")
        close_button.setObjectName("closeButton")
        close_button.clicked.connect(self.insight_banner.hide)
        close_button.setFixedWidth(20)
        banner_layout.addWidget(close_button)
    
    def show_insight_banner(self):
        """Show the insight banner with animation"""
        self.insight_banner.show()
    
    def show_insights(self):
        """Open the insights window"""
        if not self.insights_view:
            self.insights_view = InsightsView(self.backend.batches, self.backend.logs)
        
        self.insights_view.show()
        self.insight_banner.hide()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    analytics_gui = AnalyticsApp()
    analytics_gui.show()
    sys.exit(app.exec_())

