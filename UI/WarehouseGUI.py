from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QGraphicsView, QGraphicsScene, QGraphicsItem, QFrame, QToolTip,
    QSizePolicy, QSpacerItem, QScrollArea, QMenu, QInputDialog
)
from PyQt5.QtCore import Qt, QRectF, QPointF, QSizeF
from PyQt5.QtGui import QPainter, QBrush, QPen, QColor, QLinearGradient, QFont
from firebase_admin import db

class StorageUnitItem(QGraphicsItem):
    def __init__(self, unit_id, unit_data, unit_type="supply", parent=None):
        super().__init__(parent)
        self.unit_id = unit_id
        self.unit_data = unit_data
        self.unit_type = unit_type  # "supply" or "harvest"
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        
        # Visual properties
        self.width = 100
        self.height = 80
        self.hover = False
        
    def boundingRect(self):
        return QRectF(-10, -10, self.width + 120, self.height + 20)
        
    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw storage unit
        if self.unit_type == "supply":
            gradient = QLinearGradient(0, 0, 0, self.height)
            gradient.setColorAt(0, QColor("#90a4ae"))
            gradient.setColorAt(1, QColor("#78909c"))
        else:  # harvest
            gradient = QLinearGradient(0, 0, 0, self.height)
            gradient.setColorAt(0, QColor("#81c784"))
            gradient.setColorAt(1, QColor("#66bb6a"))
            
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(Qt.black, 2))
        painter.drawRoundedRect(0, 0, self.width, self.height, 10, 10)
        
        # Draw label
        font = QFont("Arial", 8, QFont.Bold)
        painter.setFont(font)
        painter.setPen(QPen(Qt.white))
        name = self.unit_data.get('name', 'Unknown')
        painter.drawText(5, 20, name)
        
        # Draw quantity indicator
        quantity = self.unit_data.get('quantity', 0)
        max_quantity = self.unit_data.get('max_quantity', 100)
        fill_percentage = min(1.0, quantity / max_quantity)
        fill_height = int(self.height * fill_percentage)  # Convert to integer
        
        # Determine fill color based on percentage
        if fill_percentage > 0.8:
            fill_color = QColor("#4CAF50")  # Green
        elif fill_percentage > 0.4:
            fill_color = QColor("#FFC107")  # Yellow
        else:
            fill_color = QColor("#F44336")  # Red
            
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(fill_color))
        painter.drawRoundedRect(10, self.height - fill_height - 5,  
                              self.width - 20, fill_height, 5, 5)
        
        # Draw quantity text
        painter.setPen(QPen(Qt.white))
        painter.drawText(5, self.height - 10, f"{quantity}/{max_quantity}")
        
        # Show details on hover
        if self.hover or self.isSelected():
            # Draw details panel
            panel_x = self.width + 10
            panel_y = 0
            panel_width = 100
            panel_height = self.height
            
            painter.setBrush(QBrush(QColor(255, 255, 255, 240)))
            painter.setPen(QPen(Qt.lightGray, 1))
            painter.drawRoundedRect(panel_x, panel_y, panel_width, panel_height, 5, 5)
            
            # Draw details
            painter.setPen(QPen(Qt.black))
            font = QFont("Arial", 8)
            painter.setFont(font)
            
            details = [
                f"ID: {self.unit_id[:8]}",
                f"Type: {self.unit_type}",
                f"Qty: {quantity}",
                f"Max: {max_quantity}",
                f"Used: {quantity/max_quantity*100:.1f}%"
            ]
            
            y = 15
            for detail in details:
                painter.drawText(panel_x + 5, y, detail)
                y += 15
                
    def hoverEnterEvent(self, event):
        self.hover = True
        self.update()
        
    def hoverLeaveEvent(self, event):
        self.hover = False
        self.update()

class WarehouseGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Warehouse Management")
        self.setGeometry(100, 100, 1200, 800)
        
        # Main layout
        self.layout = QVBoxLayout()
        self.layout.setSpacing(10)
        self.layout.setContentsMargins(10, 10, 10, 10)
        
        # Top toolbar
        toolbar = QHBoxLayout()
        
        add_supply_btn = QPushButton("➕ Add Supply Storage")
        add_supply_btn.clicked.connect(lambda: self.add_storage_unit("supply"))
        toolbar.addWidget(add_supply_btn)
        
        add_harvest_btn = QPushButton("🍄 Add Harvest Storage")
        add_harvest_btn.clicked.connect(lambda: self.add_storage_unit("harvest"))
        toolbar.addWidget(add_harvest_btn)
        
        # Add zoom buttons
        zoom_in_btn = QPushButton("🔍+")
        zoom_in_btn.clicked.connect(self.zoom_in)
        toolbar.addWidget(zoom_in_btn)
        
        zoom_out_btn = QPushButton("🔍-")
        zoom_out_btn.clicked.connect(self.zoom_out)
        toolbar.addWidget(zoom_out_btn)
        
        toolbar.addStretch()
        
        self.layout.addLayout(toolbar)
        
        # Warehouse view
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.view.setBackgroundBrush(QBrush(QColor("#eceff1")))
        
        # Enable mouse wheel zoom
        self.view.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.view.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.view.setDragMode(QGraphicsView.ScrollHandDrag)
        
        self.layout.addWidget(self.view)
        
        self.setLayout(self.layout)
        
        # Initialize zoom factor
        self.zoom_factor = 1.0
        
        # Load initial data
        self.load_warehouse_data()
        
    def load_warehouse_data(self):
        try:
            # Load supplies
            supplies_ref = db.reference('Supplies')
            supplies_data = supplies_ref.get()
            if supplies_data:
                for unit_id, unit_data in supplies_data.items():
                    self.add_storage_unit_to_scene("supply", unit_id, unit_data)
            
            # Load harvests
            harvests_ref = db.reference('Harvests')
            harvests_data = harvests_ref.get()
            if harvests_data:
                for unit_id, unit_data in harvests_data.items():
                    self.add_storage_unit_to_scene("harvest", unit_id, unit_data)
                    
            # Update scene size
            self.scene.setSceneRect(self.scene.itemsBoundingRect().adjusted(-50, -50, 50, 50))
            
        except Exception as e:
            print(f"Error loading warehouse data: {e}")
            
    def add_storage_unit_to_scene(self, unit_type, unit_id, unit_data):
        unit_item = StorageUnitItem(unit_id, unit_data, unit_type)
        
        # Position units in a grid layout
        items_count = len(self.scene.items())
        row = items_count // 6
        col = items_count % 6
        
        # Separate supplies and harvests into two sections
        if unit_type == "harvest":
            row += 4  # Start harvest storage 4 rows below supplies
            
        x = col * 120
        y = row * 100
        
        unit_item.setPos(x, y)
        self.scene.addItem(unit_item)
        
    def add_storage_unit(self, unit_type):
        try:
            # Get unit details
            name, ok = QInputDialog.getText(self, "Add Storage Unit", 
                                          "Enter storage unit name:")
            if not ok or not name:
                return
                
            quantity, ok = QInputDialog.getInt(self, "Add Storage Unit",
                                             "Enter initial quantity:",
                                             0, 0, 10000, 1)
            if not ok:
                return
                
            max_quantity, ok = QInputDialog.getInt(self, "Add Storage Unit",
                                                 "Enter maximum capacity:",
                                                 100, quantity, 10000, 100)
            if not ok:
                return
            
            # Create new unit in database
            unit_data = {
                'name': name,
                'quantity': quantity,
                'max_quantity': max_quantity
            }
            
            ref = db.reference('Supplies' if unit_type == "supply" else 'Harvests')
            new_unit_ref = ref.push(unit_data)
            
            # Add to scene
            self.add_storage_unit_to_scene(unit_type, new_unit_ref.key, unit_data)
            
            # Update scene size
            self.scene.setSceneRect(self.scene.itemsBoundingRect().adjusted(-50, -50, 50, 50))
            
        except Exception as e:
            print(f"Error adding storage unit: {e}") 

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