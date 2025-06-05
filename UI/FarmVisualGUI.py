from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QGraphicsView, QGraphicsScene, QGraphicsItem, QFrame, QToolTip,
    QSizePolicy, QSpacerItem, QScrollArea, QMenu, QInputDialog, QMessageBox,
    QGraphicsDropShadowEffect, QGraphicsOpacityEffect
)
from PyQt5.QtCore import Qt, QRectF, QPointF, QSizeF, pyqtSignal, QPropertyAnimation, QEasingCurve, QTimer
from PyQt5.QtGui import (
    QPainter, QBrush, QPen, QColor, QLinearGradient, QFont,
    QPainterPath, QPolygonF, QRadialGradient, QPainterPath
)
from firebase_admin import db
from datetime import datetime
import random

class MushroomBlock(QGraphicsItem):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.width = 25
        self.height = 35
        self.growth_level = random.random()  # 0 to 1
        self.has_alert = random.random() < 0.1  # 10% chance of alert

    def boundingRect(self):
        return QRectF(0, 0, self.width, self.height)

    def paint(self, painter, option, widget):
        # Draw substrate block
        gradient = QLinearGradient(0, 0, 0, self.height)
        gradient.setColorAt(0, QColor("#e0e0e0"))
        gradient.setColorAt(1, QColor("#bdbdbd"))
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(Qt.gray, 1))
        painter.drawRoundedRect(0, 0, self.width, self.height, 5, 5)

        # Draw mushrooms based on growth level
        if self.growth_level > 0.3:
            mushroom_color = QColor("#8bc34a")
            if self.has_alert:
                mushroom_color = QColor("#e74c3c")  # Red for alert
            
            painter.setBrush(QBrush(mushroom_color))
            painter.setPen(QPen(mushroom_color.darker(120), 1))
            
            # Draw multiple mushrooms based on growth level
            num_mushrooms = int(self.growth_level * 3) + 1
            for i in range(num_mushrooms):
                x_offset = (self.width / (num_mushrooms + 1)) * (i + 1)
                y_offset = self.height * (0.2 + (self.growth_level * 0.3))
                
                # Cap
                cap_width = 8 * self.growth_level
                painter.drawEllipse(QPointF(x_offset, y_offset), cap_width, cap_width * 0.7)
                
                # Stem
                stem_height = 10 * self.growth_level
                painter.drawRect(x_offset - 2, y_offset, 4, stem_height)

class GrowingBedItem(QGraphicsItem):
    def __init__(self, bed_id, bed_data, parent=None):
        super().__init__(parent)
        self.bed_id = bed_id
        self.bed_data = bed_data
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        
        # Visual properties
        self.width = 200
        self.height = 150
        self.hover = False
        self.selected = False
        self.hover_scale = 1.0
        self.hover_animation = None
        
        # Process bed data
        self.environmental_data = {
            'temperature': bed_data.get('Temperature', 22),
            'humidity': bed_data.get('Humidity', 85),
            'co2': bed_data.get('CO2Level', 500),
            'stage': bed_data.get('CurrentGrowthStage', 'Empty'),
            'last_updated': bed_data.get('LastUpdated', datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            'farm_id': bed_data.get('FarmID', 'N/A')
        }

    def boundingRect(self):
        # Adjust bounding rect for hover scaling
        scale_factor = self.hover_scale
        width = (self.width + 220) * scale_factor
        height = (self.height + 20) * scale_factor
        return QRectF(-10 * scale_factor, -10 * scale_factor, width, height)

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Apply hover scale
        if self.hover or self.isSelected():
            painter.scale(self.hover_scale, self.hover_scale)
        
        # Main bed container
        stage_colors = {
            "Spawn Run": QColor("#78909c"),    # Blue-gray
            "Pinning": QColor("#ffd54f"),      # Amber
            "Fruiting": QColor("#66bb6a"),     # Light green
            "Harvesting": QColor("#7e57c2"),   # Deep purple
            "Empty": QColor("#e57373")         # Light red
        }
        
        stage = self.environmental_data['stage']
        bed_color = stage_colors.get(stage, QColor("#78909c"))
        
        # Create shadow path
        shadow_path = QPainterPath()
        shadow_path.addRoundedRect(2, 2, self.width, self.height, 10, 10)
        
        # Draw shadow
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 30))
        painter.drawPath(shadow_path)
        
        # Draw main container with gradient
        gradient = QLinearGradient(0, 0, 0, self.height)
        if self.hover or self.isSelected():
            gradient.setColorAt(0, bed_color.lighter(120))
            gradient.setColorAt(1, bed_color.lighter(80))
        else:
            gradient.setColorAt(0, bed_color)
            gradient.setColorAt(1, bed_color.darker(120))
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(Qt.black, 2))
        painter.drawRoundedRect(0, 0, self.width, self.height, 10, 10)
        
        # Draw header background
        header_gradient = QLinearGradient(0, 0, 0, 40)
        header_gradient.setColorAt(0, QColor(0, 0, 0, 60))
        header_gradient.setColorAt(1, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(header_gradient))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, self.width, 40, 10, 10)
        
        # Draw bed ID and stage with improved text visibility
        font = QFont("Arial", 11, QFont.Bold)
        painter.setFont(font)
        
        # Draw text shadow
        painter.setPen(QPen(QColor(0, 0, 0, 100)))
        painter.drawText(11, 26, f"Bed {self.bed_id}")
        painter.drawText(11, 46, stage)
        
        # Draw main text
        painter.setPen(QPen(Qt.white))
        painter.drawText(10, 25, f"Bed {self.bed_id}")
        painter.drawText(10, 45, stage)
        
        # If bed is selected or hovered, show environmental data
        if self.hover or self.isSelected():
            self.paint_data_panel(painter)

    def paint_data_panel(self, painter):
        panel_x = self.width + 10
        panel_y = 0
        panel_width = 220
        panel_height = self.height
        
        # Draw panel shadow
        shadow_path = QPainterPath()
        shadow_path.addRoundedRect(panel_x + 2, panel_y + 2, panel_width, panel_height, 8, 8)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 30))
        painter.drawPath(shadow_path)
        
        # Draw panel background with gradient
        gradient = QLinearGradient(panel_x, 0, panel_x + panel_width, 0)
        gradient.setColorAt(0, QColor(255, 255, 255, 250))
        gradient.setColorAt(1, QColor(245, 245, 245, 250))
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(QColor("#e0e0e0")))
        painter.drawRoundedRect(panel_x, panel_y, panel_width, panel_height, 8, 8)
        
        # Draw data with improved visibility
        title_font = QFont("Arial", 10, QFont.Bold)
        value_font = QFont("Arial", 9)
        
        y_offset = 20
        line_height = 28
        
        data_items = [
            ("🌡️", "Temperature", f"{self.environmental_data['temperature']}°C"),
            ("💧", "Humidity", f"{self.environmental_data['humidity']}%"),
            ("☁️", "CO2 Level", f"{self.environmental_data['co2']} ppm"),
            ("🌱", "Growth Stage", f"{self.environmental_data['stage']}")
        ]
        
        for icon, label, value in data_items:
            # Draw icon
            painter.setFont(title_font)
            painter.setPen(QPen(QColor("#666666")))
            painter.drawText(panel_x + 15, y_offset, icon)
            
            # Draw label
            painter.setFont(value_font)
            painter.setPen(QPen(QColor("#333333")))
            painter.drawText(panel_x + 40, y_offset, label)
            
            # Draw value with background highlight
            value_rect = QRectF(panel_x + 130, y_offset - 15, 80, 20)
            painter.setBrush(QColor(245, 245, 245))
            painter.setPen(QPen(QColor("#e0e0e0")))
            painter.drawRoundedRect(value_rect, 4, 4)
            
            painter.setFont(title_font)
            painter.setPen(QPen(QColor("#2c3e50")))
            painter.drawText(value_rect, Qt.AlignCenter, value)
            
            y_offset += line_height

    def hoverEnterEvent(self, event):
        self.hover = True
        self.hover_scale = 1.05
        self.update()

    def hoverLeaveEvent(self, event):
        self.hover = False
        self.hover_scale = 1.0
        self.update()

class FarmVisualGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mushroom Farm Visual Management")
        self.setGeometry(100, 100, 1200, 800)
        
        # Main layout
        self.layout = QVBoxLayout()
        self.layout.setSpacing(15)
        self.layout.setContentsMargins(20, 20, 20, 20)
        
        # Title with shadow effect
        title_label = QLabel("🌾 Mushroom Farm Management")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 28px;
                color: #2c3e50;
                padding: 15px 20px;
                font-weight: bold;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #f5f5f5, stop:1 transparent);
                border-radius: 10px;
            }
        """)
        
        # Add shadow to title
        title_shadow = QGraphicsDropShadowEffect()
        title_shadow.setBlurRadius(15)
        title_shadow.setColor(QColor(0, 0, 0, 30))
        title_shadow.setOffset(0, 2)
        title_label.setGraphicsEffect(title_shadow)
        
        self.layout.addWidget(title_label)
        
        # Toolbar with enhanced styling
        toolbar = QHBoxLayout()
        
        button_style = """
            QPushButton {
                background-color: #2ecc71;
                color: white;
                border: none;
                padding: 12px 25px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 8px;
                min-width: 150px;
            }
            QPushButton:hover {
                background-color: #27ae60;
                transform: scale(1.05);
                transition: all 0.2s ease-in-out;
            }
            QPushButton:pressed {
                background-color: #219a52;
                transform: scale(0.95);
            }
        """
        
        add_bed_btn = QPushButton("🛏️ Add Growing Bed")
        add_bed_btn.setStyleSheet(button_style)
        add_bed_btn.setCursor(Qt.PointingHandCursor)
        
        # Add shadow to button
        btn_shadow = QGraphicsDropShadowEffect()
        btn_shadow.setBlurRadius(10)
        btn_shadow.setColor(QColor(0, 0, 0, 50))
        btn_shadow.setOffset(0, 2)
        add_bed_btn.setGraphicsEffect(btn_shadow)
        
        add_bed_btn.clicked.connect(self.add_growing_bed)
        toolbar.addWidget(add_bed_btn)
        
        # Add zoom buttons
        zoom_in_btn = QPushButton("🔍+")
        zoom_in_btn.setStyleSheet(button_style.replace("#2ecc71", "#3498db"))
        zoom_in_btn.setCursor(Qt.PointingHandCursor)
        zoom_in_btn.clicked.connect(self.zoom_in)
        toolbar.addWidget(zoom_in_btn)
        
        zoom_out_btn = QPushButton("🔍-")
        zoom_out_btn.setStyleSheet(button_style.replace("#2ecc71", "#3498db"))
        zoom_out_btn.setCursor(Qt.PointingHandCursor)
        zoom_out_btn.clicked.connect(self.zoom_out)
        toolbar.addWidget(zoom_out_btn)
        
        toolbar.addStretch()
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setStyleSheet(button_style.replace("#2ecc71", "#3498db"))
        refresh_btn.setCursor(Qt.PointingHandCursor)
        
        # Add shadow to refresh button
        refresh_shadow = QGraphicsDropShadowEffect()
        refresh_shadow.setBlurRadius(10)
        refresh_shadow.setColor(QColor(0, 0, 0, 50))
        refresh_shadow.setOffset(0, 2)
        refresh_btn.setGraphicsEffect(refresh_shadow)
        
        refresh_btn.clicked.connect(self.load_farm_data)
        toolbar.addWidget(refresh_btn)
        
        self.layout.addLayout(toolbar)
        
        # Farm view with enhanced styling
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Enable mouse wheel zoom
        self.view.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.view.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.view.setDragMode(QGraphicsView.ScrollHandDrag)
        
        # Create gradient background
        bg_gradient = QLinearGradient(0, 0, 0, 800)
        bg_gradient.setColorAt(0, QColor("#f0f4c3"))
        bg_gradient.setColorAt(1, QColor("#dcedc8"))
        self.view.setBackgroundBrush(QBrush(bg_gradient))
        
        # Add shadow to view
        view_shadow = QGraphicsDropShadowEffect()
        view_shadow.setBlurRadius(20)
        view_shadow.setColor(QColor(0, 0, 0, 40))
        view_shadow.setOffset(0, 0)
        self.view.setGraphicsEffect(view_shadow)
        
        self.layout.addWidget(self.view)
        
        self.setLayout(self.layout)
        
        # Load initial data
        self.load_farm_data()
        
        # Initialize zoom factor
        self.zoom_factor = 1.0

    def load_farm_data(self):
        """Load growing beds from the database"""
        try:
            self.scene.clear()
            
            ref = db.reference('GrowingBed')
            beds_data = ref.get()
            
            if not beds_data:
                return
            
            if isinstance(beds_data, dict):
                for bed_id, bed_data in beds_data.items():
                    if isinstance(bed_data, dict):
                        bed_item = GrowingBedItem(bed_id, bed_data)
                        
                        # Position beds in a grid layout
                        row = len(self.scene.items()) // 3
                        col = len(self.scene.items()) % 3
                        x = col * 450  # Increased spacing
                        y = row * 200  # Increased spacing
                        bed_item.setPos(x, y)
                        
                        self.scene.addItem(bed_item)
            
            # Update scene rectangle with padding
            rect = self.scene.itemsBoundingRect()
            self.scene.setSceneRect(rect.adjusted(-50, -50, 50, 50))
            
            # Fit view to scene
            self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load farm data: {str(e)}")

    def add_growing_bed(self):
        """Add a new growing bed"""
        try:
            ref = db.reference('GrowingBed')
            existing_beds = ref.get() or {}
            next_bed_id = max([int(bid) for bid in existing_beds.keys()] + [500]) + 1
            
            new_bed_data = {
                "BedID": next_bed_id,
                "FarmID": 1,
                "CO2Level": 500,
                "Humidity": 85,
                "Temperature": 22,
                "CurrentGrowthStage": "Empty",
                "LastUpdated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            ref.child(str(next_bed_id)).set(new_bed_data)
            self.load_farm_data()
            
            QMessageBox.information(self, "Success", f"Added new growing bed with ID: {next_bed_id}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to add growing bed: {str(e)}")

    def resizeEvent(self, event):
        """Handle window resize events"""
        super().resizeEvent(event)
        self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)

    def zoom_in(self):
        self.zoom_factor *= 1.2
        self.view.scale(1.2, 1.2)

    def zoom_out(self):
        self.zoom_factor /= 1.2
        self.view.scale(1/1.2, 1/1.2)

    def wheelEvent(self, event):
        # Zoom with mouse wheel
        if event.angleDelta().y() > 0:
            self.zoom_in()
        else:
            self.zoom_out() 