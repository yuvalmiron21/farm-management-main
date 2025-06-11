from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QGraphicsView, QGraphicsScene, QGraphicsItem, QFrame, QToolTip,
    QSizePolicy, QSpacerItem, QScrollArea, QMenu, QInputDialog, QDialog, QLineEdit, QSpinBox, QDialogButtonBox, QComboBox, QDateEdit, QFormLayout, QMessageBox, QStackedWidget
)
from PyQt5.QtCore import Qt, QRectF, QPointF, QSizeF
from PyQt5.QtGui import QPainter, QBrush, QPen, QColor, QLinearGradient, QFont, QDoubleValidator, QIcon
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

class AddWarehouseItemDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add to Warehouse")
        self.setMinimumWidth(480)
        self.setStyleSheet("""
            QDialog {
                background: #f8f9fa;
            }
            QLabel {
                font-size: 15px;
            }
            QLineEdit, QComboBox, QDateEdit, QSpinBox {
                padding: 8px;
                border-radius: 5px;
                border: 1px solid #dcdcdc;
                font-size: 14px;
            }
            QPushButton {
                padding: 10px;
                border-radius: 5px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #27ae60, stop:1 #2980b9);
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #219150;
            }
        """)
        layout = QVBoxLayout()
        title = QLabel("📦 Add to Warehouse")
        title.setFont(QFont("Arial", 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        # Type selection
        self.type_combo = QComboBox()
        self.type_combo.addItem("Product", "product")
        self.type_combo.addItem("Supply Storage", "supply")
        self.type_combo.addItem("Harvest Storage", "harvest")
        self.type_combo.currentIndexChanged.connect(self.switch_form)
        layout.addWidget(self.type_combo)
        # Stacked widget for forms
        self.forms = QStackedWidget()
        # Product form
        self.product_form = QFormLayout()
        self.product_name = QLineEdit()
        self.product_name.setPlaceholderText("Product name...")
        self.product_form.addRow("Name:", self.product_name)
        self.product_category = QLineEdit()
        self.product_category.setPlaceholderText("e.g. Substrate, Packaging...")
        self.product_form.addRow("Category:", self.product_category)
        self.product_quantity = QSpinBox()
        self.product_quantity.setRange(0, 100000)
        self.product_form.addRow("Quantity:", self.product_quantity)
        self.product_unit_price = QLineEdit()
        self.product_unit_price.setValidator(QDoubleValidator(0.0, 100000.0, 2))
        self.product_unit_price.setPlaceholderText("₪0.00")
        self.product_form.addRow("Unit Price:", self.product_unit_price)
        self.product_supplier = QLineEdit()
        self.product_supplier.setPlaceholderText("Supplier name...")
        self.product_form.addRow("Supplier:", self.product_supplier)
        self.product_expiry = QDateEdit()
        self.product_expiry.setCalendarPopup(True)
        self.product_form.addRow("Expiry Date:", self.product_expiry)
        product_form_widget = QWidget()
        product_form_widget.setLayout(self.product_form)
        self.forms.addWidget(product_form_widget)
        # Supply Storage form
        self.supply_form = QFormLayout()
        self.supply_name = QLineEdit()
        self.supply_form.addRow("Name:", self.supply_name)
        self.supply_quantity = QSpinBox()
        self.supply_quantity.setRange(0, 10000)
        self.supply_form.addRow("Initial Quantity:", self.supply_quantity)
        self.supply_max_quantity = QSpinBox()
        self.supply_max_quantity.setRange(1, 10000)
        self.supply_max_quantity.setValue(100)
        self.supply_form.addRow("Maximum Capacity:", self.supply_max_quantity)
        supply_form_widget = QWidget()
        supply_form_widget.setLayout(self.supply_form)
        self.forms.addWidget(supply_form_widget)
        # Harvest Storage form
        self.harvest_form = QFormLayout()
        self.harvest_name = QLineEdit()
        self.harvest_form.addRow("Name:", self.harvest_name)
        self.harvest_quantity = QSpinBox()
        self.harvest_quantity.setRange(0, 10000)
        self.harvest_form.addRow("Initial Quantity:", self.harvest_quantity)
        self.harvest_max_quantity = QSpinBox()
        self.harvest_max_quantity.setRange(1, 10000)
        self.harvest_max_quantity.setValue(100)
        self.harvest_form.addRow("Maximum Capacity:", self.harvest_max_quantity)
        harvest_form_widget = QWidget()
        harvest_form_widget.setLayout(self.harvest_form)
        self.forms.addWidget(harvest_form_widget)
        layout.addWidget(self.forms)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        btns.accepted.connect(self.validate_and_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)
        self.setLayout(layout)
        self.switch_form(0)
    def switch_form(self, idx):
        self.forms.setCurrentIndex(idx)
    def validate_and_accept(self):
        idx = self.forms.currentIndex()
        if idx == 0:  # Product
            if not self.product_name.text().strip() or not self.product_category.text().strip() or not self.product_unit_price.text().strip() or not self.product_supplier.text().strip():
                QMessageBox.warning(self, "Error", "Please fill in all required fields.")
                return
        elif idx == 1:  # Supply
            if not self.supply_name.text().strip():
                QMessageBox.warning(self, "Error", "Please fill in all required fields.")
                return
        elif idx == 2:  # Harvest
            if not self.harvest_name.text().strip():
                QMessageBox.warning(self, "Error", "Please fill in all required fields.")
                return
        self.accept()
    def get_data(self):
        idx = self.forms.currentIndex()
        if idx == 0:  # Product
            return {
                "type": "product",
                "name": self.product_name.text().strip(),
                "category": self.product_category.text().strip(),
                "quantity": self.product_quantity.value(),
                "unit_price": float(self.product_unit_price.text().strip()),
                "supplier": self.product_supplier.text().strip(),
                "expiry": self.product_expiry.date().toString("yyyy-MM-dd")
            }
        elif idx == 1:  # Supply
            return {
                "type": "supply",
                "name": self.supply_name.text().strip(),
                "quantity": self.supply_quantity.value(),
                "max_quantity": self.supply_max_quantity.value()
            }
        elif idx == 2:  # Harvest
            return {
                "type": "harvest",
                "name": self.harvest_name.text().strip(),
                "quantity": self.harvest_quantity.value(),
                "max_quantity": self.harvest_max_quantity.value()
            }

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
        
        add_item_btn = QPushButton("➕ Add to Warehouse")
        add_item_btn.clicked.connect(self.add_warehouse_item)
        toolbar.addWidget(add_item_btn)
        
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
        
    def add_warehouse_item(self):
        try:
            dialog = AddWarehouseItemDialog(self)
            if dialog.exec_() == QDialog.Accepted:
                data = dialog.get_data()
                if data["type"] == "product":
                    ref = db.reference('Products')
                    ref.push(data)
                    QMessageBox.information(self, "Success", "Product added to warehouse!")
                elif data["type"] == "supply":
                    ref = db.reference('Supplies')
                    ref.push({"name": data["name"], "quantity": data["quantity"], "max_quantity": data["max_quantity"]})
                    QMessageBox.information(self, "Success", "Supply storage added!")
                elif data["type"] == "harvest":
                    ref = db.reference('Harvests')
                    ref.push({"name": data["name"], "quantity": data["quantity"], "max_quantity": data["max_quantity"]})
                    QMessageBox.information(self, "Success", "Harvest storage added!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to add item: {str(e)}")

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

    def add_product(self):
        try:
            dialog = AddProductDialog(self)
            if dialog.exec_() == QDialog.Accepted:
                product_data = dialog.get_data()
                ref = db.reference('Products')
                ref.push(product_data)
                QMessageBox.information(self, "Success", "Product added to warehouse!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to add product: {str(e)}") 