from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QGraphicsView, QGraphicsScene, QGraphicsItem, QGraphicsRectItem, QGraphicsTextItem, QFrame, QToolTip,
    QSizePolicy, QSpacerItem, QScrollArea, QMenu, QInputDialog, QDialog, QLineEdit, QSpinBox, QDialogButtonBox, QComboBox, QDateEdit, QFormLayout, QMessageBox, QStackedWidget, QGraphicsObject, QColorDialog
)
from PyQt5.QtCore import (
    Qt, QRectF, QPointF, QSizeF, pyqtSignal, QPropertyAnimation, QEasingCurve, 
    pyqtProperty, pyqtSlot, QLineF, QEvent, QPoint
)
from PyQt5.QtGui import (
    QPainter, QBrush, QPen, QColor, QLinearGradient, QFont,
    QPainterPath, QCursor, QDoubleValidator
)
from firebase_admin import db
import json
import os
from datetime import datetime

class CustomGraphicsScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.grid_size = 20
        self.background_color = QColor("#eceff1")
        self.light_pen = QPen(QColor("#dcdcdc"), 1)
        self.dark_pen = QPen(QColor("#c0c0c0"), 1.5)

    def drawBackground(self, painter, rect):
        painter.fillRect(rect, self.background_color)
        left = int(rect.left()) - (int(rect.left()) % self.grid_size)
        top = int(rect.top()) - (int(rect.top()) % self.grid_size)
        lines_light, lines_dark = [], []
        for x in range(left, int(rect.right()), self.grid_size):
            lines = lines_dark if x % (self.grid_size * 5) == 0 else lines_light
            lines.append(QLineF(x, rect.top(), x, rect.bottom()))
        for y in range(top, int(rect.bottom()), self.grid_size):
            lines = lines_dark if y % (self.grid_size * 5) == 0 else lines_light
            lines.append(QLineF(rect.left(), y, rect.right(), y))
        painter.setPen(self.light_pen)
        painter.drawLines(lines_light)
        painter.setPen(self.dark_pen)
        painter.drawLines(lines_dark)

class StorageUnitItem(QGraphicsObject):
    edit_requested = pyqtSignal(str, str)

    def __init__(self, unit_id, unit_data, unit_type="supply", parent=None):
        super().__init__(parent)
        self.unit_id = unit_id
        self.unit_data = unit_data
        self.unit_type = unit_type
        
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemSendsScenePositionChanges)
        self.setAcceptHoverEvents(True)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setZValue(1)

        self._scale = 1.0
        self._is_hovered = False
        self.width = 150
        self.height = 100
        self.detailed_panel_width = 250
        self.detailed_panel_height = 210
        
        self.type_colors = {
            "supply": ("#78909c", "#546e7a"),
            "harvest": ("#66bb6a", "#43a047")
        }
        self.title_font = QFont("Arial", 10, QFont.Bold)
        self.label_font = QFont("Arial", 8)

    def get_view(self):
        if self.scene() and self.scene().views():
            return self.scene().views()[0]
        return None

    def _get_panel_x_position(self):
        """Determines the panel's x position relative to the item's origin."""
        panel_x = self.width + 10  # Default to the right
        view = self.get_view()
        if view:
            visible_rect = view.mapToScene(view.viewport().rect()).boundingRect()
            panel_abs_right = self.scenePos().x() + panel_x + self.detailed_panel_width
            if panel_abs_right > visible_rect.right():
                panel_x = -self.detailed_panel_width - 10
        return panel_x

    @pyqtProperty(float)
    def scale(self): return self._scale

    @scale.setter
    def scale(self, value):
        self._scale = value
        self.prepareGeometryChange()
        self.update()
        
    def boundingRect(self):
        base_rect = QRectF(-5, -5, self.width + 10, self.height + 10)
        if self._is_hovered or self.isSelected():
            panel_x = self._get_panel_x_position()
            panel_rect = QRectF(panel_x, 0, self.detailed_panel_width, self.detailed_panel_height)
            return base_rect.united(panel_rect.adjusted(-5, -5, 5, 5))
        return base_rect
        
    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.Antialiasing)
        transform = painter.transform()
        painter.scale(self._scale, self._scale)
        
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width, self.height, 10, 10)
        
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 15))
        painter.drawPath(path.translated(2, 2))

        color1, color2 = self.type_colors.get(self.unit_type, ("#9E9E9E", "#616161"))
        gradient = QLinearGradient(0, 0, 0, self.height)
        gradient.setColorAt(0, QColor(color1))
        gradient.setColorAt(1, QColor(color2))
        painter.setBrush(gradient)
        painter.setPen(QPen(QColor(0,0,0,40), 1))
        painter.drawPath(path)

        painter.setPen(Qt.white)
        painter.setFont(self.title_font)
        name = self.unit_data.get('name', 'Unknown')
        painter.drawText(QRectF(10, 5, self.width - 20, 25), name)
        
        quantity = self.unit_data.get('quantity', 0)
        max_quantity = self.unit_data.get('max_quantity', 100)
        
        painter.setFont(self.label_font)
        painter.setPen(QColor(255,255,255,180))
        painter.drawText(QRectF(10, 25, self.width-20, 20), f"{quantity} / {max_quantity}")

        # Show category/subcategory if available
        category = self.unit_data.get('category', '')
        subcategory = self.unit_data.get('subcategory', '')
        if category and subcategory:
            painter.drawText(QRectF(10, 45, self.width-20, 15), f"{category}")
            painter.drawText(QRectF(10, 60, self.width-20, 15), f"{subcategory}")

        fill_percentage = min(1.0, quantity / max_quantity) if max_quantity > 0 else 0
        
        # Draw background of progress bar
        painter.setBrush(QColor(0,0,0, 20))
        painter.drawRoundedRect(10, self.height - 30, self.width - 20, 15, 7, 7)
        
        # Draw filled part of progress bar
        fill_color = QColor("#4CAF50") if fill_percentage > 0.6 else (QColor("#FFC107") if fill_percentage > 0.2 else QColor("#F44336"))
        painter.setBrush(fill_color)
        painter.drawRoundedRect(10, self.height - 30, int((self.width - 20) * fill_percentage), 15, 7, 7)
        
        painter.setTransform(transform)
        
        # Show detailed info panel when selected or hovered
        if self._is_hovered or self.isSelected():
            self.paint_detailed_panel(painter)

    def paint_detailed_panel(self, painter):
        panel_width = self.detailed_panel_width
        panel_height = self.detailed_panel_height
        panel_x = self._get_panel_x_position()
        
        path = QPainterPath()
        path.addRoundedRect(panel_x, 0, panel_width, panel_height, 8, 8)
            
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 15))
        painter.drawPath(path.translated(1, 1))

        painter.setBrush(QColor(255, 255, 255, 250))
        painter.setPen(QPen(QColor("#e0e0e0"), 1))
        painter.drawPath(path)
        
        data = self.unit_data
        y_offset = 20
        
        # Basic info
        painter.setFont(QFont("Arial", 12, QFont.Bold))
        painter.setPen(Qt.black)
        painter.drawText(panel_x + 15, y_offset, "📦 Item Details")
        y_offset += 25
        
        painter.setFont(QFont("Arial", 10))
        painter.setPen(QColor("#555"))
        
        # Category and subcategory
        if data.get('category'):
            painter.drawText(panel_x + 15, y_offset, f"Category: {data.get('category', 'N/A')}")
            y_offset += 20
        if data.get('subcategory'):
            painter.drawText(panel_x + 15, y_offset, f"Type: {data.get('subcategory', 'N/A')}")
            y_offset += 20
        
        # Description
        if data.get('description'):
            painter.drawText(panel_x + 15, y_offset, f"Description: {data.get('description', 'N/A')}")
            y_offset += 20
        
        # Price
        if data.get('unit_price'):
            painter.drawText(panel_x + 15, y_offset, f"Price: ${data.get('unit_price', 0):.2f}")
            y_offset += 20
        
        # Supplier
        if data.get('supplier'):
            painter.drawText(panel_x + 15, y_offset, f"Supplier: {data.get('supplier', 'N/A')}")
            y_offset += 20
        
        # Quality grade
        if data.get('quality_grade'):
            quality_color = QColor("#4CAF50") if data.get('quality_grade') == "Premium" else (QColor("#FFC107") if data.get('quality_grade') == "Standard" else QColor("#F44336"))
            painter.setPen(quality_color)
            painter.drawText(panel_x + 15, y_offset, f"Quality: {data.get('quality_grade', 'N/A')}")
            painter.setPen(QColor("#555"))
            y_offset += 20
        
        # Expiry date
        if data.get('expiry_date'):
            painter.drawText(panel_x + 15, y_offset, f"Expires: {data.get('expiry_date', 'N/A')}")
            y_offset += 20
        
        # Last updated
        if data.get('last_updated'):
            painter.drawText(panel_x + 15, y_offset, f"Updated: {data.get('last_updated', 'N/A').split(' ')[0]}")
                
    def hoverEnterEvent(self, event):
        self.prepareGeometryChange()
        self._is_hovered = True
        self.setZValue(100)
        self.anim = QPropertyAnimation(self, b"scale")
        self.anim.setEndValue(1.1)
        self.anim.setDuration(200)
        self.anim.start()
        super().hoverEnterEvent(event)
        
    def hoverLeaveEvent(self, event):
        self.prepareGeometryChange()
        self._is_hovered = False
        self.setZValue(1)
        self.anim = QPropertyAnimation(self, b"scale")
        self.anim.setEndValue(1.0)
        self.anim.setDuration(200)
        self.anim.start()
        super().hoverLeaveEvent(event)

    def mouseDoubleClickEvent(self, event):
        self.edit_requested.emit(self.unit_id, self.unit_type)
        super().mouseDoubleClickEvent(event)
    
    def _clear_guides(self):
        if hasattr(self, 'guide_lines'):
            for line in self.guide_lines:
                if line.scene():
                    self.scene().removeItem(line)
            self.guide_lines.clear()

    def mouseReleaseEvent(self, event):
        self._clear_guides()
        super().mouseReleaseEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedChange:
            self.prepareGeometryChange() # Recalculate bounding rect on selection change
        
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            self._clear_guides()
            new_pos = value
            snap_threshold = 10
            grid_size = self.scene().grid_size

            final_x = round(new_pos.x() / grid_size) * grid_size
            final_y = round(new_pos.y() / grid_size) * grid_size
            
            other_items = [item for item in self.scene().items() if isinstance(item, StorageUnitItem) and item != self]
            my_rect_future = QRectF(new_pos, self.boundingRect().size())
            
            for other in other_items:
                other_rect = other.sceneBoundingRect()
                
                alignments_x = {other_rect.left(): my_rect_future.left(), other_rect.right(): my_rect_future.right(), other_rect.center().x(): my_rect_future.center().x()}
                for target_x, my_x in alignments_x.items():
                    if abs(target_x - my_x) < snap_threshold:
                        final_x = new_pos.x() - (my_x - target_x)
                        self._draw_guide(QLineF(target_x, other_rect.top(), target_x, my_rect_future.bottom()))
                        break
                
                alignments_y = {other_rect.top(): my_rect_future.top(), other_rect.bottom(): my_rect_future.bottom(), other_rect.center().y(): my_rect_future.center().y()}
                for target_y, my_y in alignments_y.items():
                    if abs(target_y - my_y) < snap_threshold:
                        final_y = new_pos.y() - (my_y - target_y)
                        self._draw_guide(QLineF(other_rect.left(), target_y, my_rect_future.right(), target_y))
                        break

            return QPointF(final_x, final_y)

        return super().itemChange(change, value)

    def _draw_guide(self, line):
        if not hasattr(self, 'guide_lines'): self.guide_lines = []
        pen = QPen(QColor("#1abc9c"), 1.5, Qt.DashLine)
        guide = self.scene().addLine(line, pen)
        guide.setZValue(200)
        self.guide_lines.append(guide)

class PannableGraphicsView(QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self._panning = False
        self._last_mouse_pos = QPoint()
        self.setDragMode(QGraphicsView.NoDrag)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and not self.itemAt(event.pos()):
            self._panning = True
            self._last_mouse_pos = event.pos()
            self.viewport().setCursor(Qt.ClosedHandCursor)
            event.accept()
        else:
            self._panning = False
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._panning:
            delta = event.pos() - self._last_mouse_pos
            self._last_mouse_pos = event.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._panning:
            self._panning = False
            self.viewport().setCursor(Qt.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

class ResizableRectItem(QGraphicsRectItem):
    def __init__(self, x, y, w, h):
        super().__init__(x, y, w, h)
        self.setFlags(QGraphicsRectItem.ItemIsMovable | QGraphicsRectItem.ItemIsSelectable | QGraphicsRectItem.ItemSendsScenePositionChanges)
        self.setAcceptHoverEvents(True)
        self.setZValue(-1)
        self.handle_size = 10
        self.handles = {}
        self.update_handles()
        self.resizing_handle = None

    def update_handles(self):
        rect = self.rect()
        self.handles[1] = QRectF(rect.left(), rect.top(), self.handle_size, self.handle_size)
        self.handles[2] = QRectF(rect.right() - self.handle_size, rect.top(), self.handle_size, self.handle_size)
        self.handles[3] = QRectF(rect.left(), rect.bottom() - self.handle_size, self.handle_size, self.handle_size)
        self.handles[4] = QRectF(rect.right() - self.handle_size, rect.bottom() - self.handle_size, self.handle_size, self.handle_size)

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor("#3498db"), 2, Qt.SolidLine)
        if self.isSelected(): pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        brush_color = QColor("#3498db"); brush_color.setAlpha(20)
        painter.setBrush(brush_color)
        painter.drawRoundedRect(self.rect(), 5, 5)
        if self.isSelected():
            painter.setBrush(QColor("#2980b9"))
            for handle in self.handles.values(): painter.drawRect(handle)

    def hoverMoveEvent(self, event):
        for handle_pos, handle_rect in self.handles.items():
            if handle_rect.contains(event.pos()):
                self.setCursor(Qt.SizeFDiagCursor)
                return
        self.setCursor(Qt.OpenHandCursor)
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
        for handle_pos, handle_rect in self.handles.items():
            if handle_rect.contains(event.pos()):
                self.resizing_handle = handle_pos
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.resizing_handle:
            self.prepareGeometryChange()
            rect = self.rect()
            if self.resizing_handle == 1: rect.setTopLeft(event.pos())
            elif self.resizing_handle == 2: rect.setTopRight(event.pos())
            elif self.resizing_handle == 3: rect.setBottomLeft(event.pos())
            elif self.resizing_handle == 4: rect.setBottomRight(event.pos())
            self.setRect(rect)
            self.update_handles()
        else:
            super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        self.resizing_handle = None
        super().mouseReleaseEvent(event)

class EditStorageUnitDialog(QDialog):
    def __init__(self, unit_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Warehouse Item")
        self.setMinimumWidth(400)
        self.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel {
                font-size: 13px;
                font-weight: bold;
                color: #495057;
                padding: 3px;
            }
            QLineEdit, QComboBox, QSpinBox, QDateEdit {
                padding: 8px;
                border-radius: 4px;
                border: 1px solid #ced4da;
                background-color: white;
                color: #495057;
                font-size: 12px;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDateEdit:focus {
                border: 2px solid #007bff;
            }
            QPushButton {
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
                background-color: #007bff;
                color: white;
                border: none;
                margin: 3px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # Header
        header_label = QLabel("✏️ Edit Warehouse Item")
        header_label.setStyleSheet("font-size: 18px; font-weight: bold; padding: 8px; color: #343a40;")
        header_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(header_label)

        # Basic Information
        self.name_input = QLineEdit(unit_data.get('name', ''))
        self.name_input.setPlaceholderText("Item name...")
        layout.addWidget(QLabel("Name:"))
        layout.addWidget(self.name_input)

        # Description
        self.description_input = QLineEdit(unit_data.get('description', ''))
        self.description_input.setPlaceholderText("Enter item description (optional)...")
        layout.addWidget(QLabel("Description:"))
        layout.addWidget(self.description_input)

        # Category and Subcategory
        self.category_combo = QComboBox()
        categories = ["Growing Supplies", "Harvested Mushrooms", "Equipment & Tools", "Packaging Materials", "Environmental Control"]
        self.category_combo.addItems(categories)
        current_category = unit_data.get('category', 'Growing Supplies')
        if current_category in categories:
            self.category_combo.setCurrentText(current_category)
        self.category_combo.currentIndexChanged.connect(self.update_subcategories_edit)
        layout.addWidget(QLabel("Category:"))
        layout.addWidget(self.category_combo)

        self.subcategory_combo = QComboBox()
        self.update_subcategories_edit(self.category_combo.currentIndex())
        current_subcategory = unit_data.get('subcategory', '')
        if current_subcategory:
            self.subcategory_combo.setCurrentText(current_subcategory)
        layout.addWidget(QLabel("Subcategory:"))
        layout.addWidget(self.subcategory_combo)

        # Quantity Information
        quantity_layout = QHBoxLayout()
        
        self.quantity_input = QSpinBox()
        self.quantity_input.setRange(0, 100000)
        self.quantity_input.setSuffix(" units")
        self.quantity_input.setValue(unit_data.get('quantity', 0))
        quantity_layout.addWidget(QLabel("Current Quantity:"))
        quantity_layout.addWidget(self.quantity_input)
        
        self.max_quantity_input = QSpinBox()
        self.max_quantity_input.setRange(1, 100000)
        self.max_quantity_input.setSuffix(" units")
        self.max_quantity_input.setValue(unit_data.get('max_quantity', 100))
        quantity_layout.addWidget(QLabel("Max Capacity:"))
        quantity_layout.addWidget(self.max_quantity_input)
        
        layout.addLayout(quantity_layout)

        # Additional Fields
        self.price_input = QLineEdit(str(unit_data.get('unit_price', '')))
        self.price_input.setPlaceholderText("0.00")
        self.price_input.setValidator(QDoubleValidator(0.0, 100000.0, 2))
        layout.addWidget(QLabel("Unit Price ($):"))
        layout.addWidget(self.price_input)

        self.supplier_input = QLineEdit(unit_data.get('supplier', ''))
        self.supplier_input.setPlaceholderText("Supplier name...")
        layout.addWidget(QLabel("Supplier:"))
        layout.addWidget(self.supplier_input)

        self.expiry_input = QDateEdit()
        self.expiry_input.setCalendarPopup(True)
        expiry_date = unit_data.get('expiry_date', '')
        if expiry_date:
            try:
                self.expiry_input.setDate(datetime.strptime(expiry_date, "%Y-%m-%d").date())
            except:
                self.expiry_input.setDate(self.expiry_input.date().addDays(30))
        else:
            self.expiry_input.setDate(self.expiry_input.date().addDays(30))
        layout.addWidget(QLabel("Expiry Date:"))
        layout.addWidget(self.expiry_input)

        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["Premium", "Standard", "Economy"])
        quality = unit_data.get('quality_grade', 'Standard')
        if quality in ["Premium", "Standard", "Economy"]:
            self.quality_combo.setCurrentText(quality)
        layout.addWidget(QLabel("Quality Grade:"))
        layout.addWidget(self.quality_combo)

        # Buttons
        button_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        button_layout.addStretch()
        
        save_btn = QPushButton("Save Changes")
        save_btn.clicked.connect(self.accept)
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)

    def update_subcategories_edit(self, index):
        self.subcategory_combo.clear()
        
        categories = {
            0: ["Substrate Materials", "Spawn/Mycelium", "Nutrient Supplements", "pH Adjusters", "Growth Hormones"],
            1: ["White Button Mushrooms", "Portobello Mushrooms", "Shiitake Mushrooms", "Oyster Mushrooms", "Chanterelle Mushrooms", "Morel Mushrooms", "Crimini Mushrooms"],
            2: ["Growing Trays", "Humidity Controllers", "Temperature Sensors", "CO2 Monitors", "Air Circulation Fans", "Lighting Systems", "Harvesting Tools"],
            3: ["Plastic Containers", "Paper Bags", "Vacuum Seal Bags", "Labels & Stickers", "Shipping Boxes", "Insulation Materials"],
            4: ["Heating Systems", "Cooling Systems", "Humidifiers", "Dehumidifiers", "Air Filters", "Water Systems"]
        }
        
        self.subcategory_combo.addItems(categories.get(index, []))

    def get_data(self):
        data = {
            "name": self.name_input.text().strip(),
            "description": self.description_input.text().strip(),
            "category": self.category_combo.currentText(),
            "subcategory": self.subcategory_combo.currentText(),
            "quantity": self.quantity_input.value(),
            "max_quantity": self.max_quantity_input.value(),
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Add optional fields
        price_text = self.price_input.text().strip()
        if price_text:
            data["unit_price"] = float(price_text)
        
        supplier_text = self.supplier_input.text().strip()
        if supplier_text:
            data["supplier"] = supplier_text
        
        data["expiry_date"] = self.expiry_input.date().toString("yyyy-MM-dd")
        data["quality_grade"] = self.quality_combo.currentText()
        
        return data

class AddWarehouseItemDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Warehouse Item")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        self.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #495057;
                padding: 5px;
            }
            QLineEdit, QComboBox, QSpinBox, QDateEdit {
                padding: 10px;
                border-radius: 4px;
                border: 1px solid #ced4da;
                background-color: white;
                color: #495057;
                font-size: 13px;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDateEdit:focus {
                border: 2px solid #007bff;
            }
            QLineEdit::placeholder {
                color: #6c757d;
            }
            QPushButton {
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
                background-color: #007bff;
                color: white;
                border: none;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header_label = QLabel("📦 Add New Warehouse Item")
        header_label.setStyleSheet("font-size: 20px; font-weight: bold; padding: 10px; color: #343a40;")
        header_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(header_label)

        # Category Selection
        category_label = QLabel("Select Category:")
        layout.addWidget(category_label)
        
        self.category_combo = QComboBox()
        self.category_combo.addItems([
            "Growing Supplies",
            "Harvested Mushrooms", 
            "Equipment & Tools",
            "Packaging Materials",
            "Environmental Control"
        ])
        self.category_combo.currentIndexChanged.connect(self.update_subcategories)
        layout.addWidget(self.category_combo)

        # Subcategory Selection
        subcategory_label = QLabel("Select Subcategory:")
        layout.addWidget(subcategory_label)
        
        self.subcategory_combo = QComboBox()
        layout.addWidget(self.subcategory_combo)

        # Item Details
        details_label = QLabel("Item Details:")
        layout.addWidget(details_label)

        # Name
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter item name...")
        layout.addWidget(self.name_input)

        # Description
        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText("Enter item description (optional)...")
        layout.addWidget(self.description_input)

        # Quantity and Capacity
        quantity_layout = QHBoxLayout()
        
        self.quantity_input = QSpinBox()
        self.quantity_input.setRange(0, 100000)
        self.quantity_input.setSuffix(" units")
        quantity_layout.addWidget(QLabel("Current Quantity:"))
        quantity_layout.addWidget(self.quantity_input)
        
        self.max_quantity_input = QSpinBox()
        self.max_quantity_input.setRange(1, 100000)
        self.max_quantity_input.setSuffix(" units")
        quantity_layout.addWidget(QLabel("Max Capacity:"))
        quantity_layout.addWidget(self.max_quantity_input)
        
        layout.addLayout(quantity_layout)

        # Additional Fields (will be shown/hidden based on category)
        self.additional_widgets = {}
        
        # Price field
        self.price_input = QLineEdit()
        self.price_input.setPlaceholderText("0.00")
        self.price_input.setValidator(QDoubleValidator(0.0, 100000.0, 2))
        self.additional_widgets['price'] = (QLabel("Unit Price ($):"), self.price_input)
        
        # Supplier field
        self.supplier_input = QLineEdit()
        self.supplier_input.setPlaceholderText("Supplier name...")
        self.additional_widgets['supplier'] = (QLabel("Supplier:"), self.supplier_input)
        
        # Expiry date field
        self.expiry_input = QDateEdit()
        self.expiry_input.setCalendarPopup(True)
        self.expiry_input.setDate(self.expiry_input.date().addDays(30))
        self.additional_widgets['expiry'] = (QLabel("Expiry Date:"), self.expiry_input)
        
        # Quality field
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["Premium", "Standard", "Economy"])
        self.additional_widgets['quality'] = (QLabel("Quality Grade:"), self.quality_combo)

        # Buttons
        button_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        button_layout.addStretch()
        
        add_btn = QPushButton("Add Item")
        add_btn.clicked.connect(self.validate_and_accept)
        button_layout.addWidget(add_btn)
        
        layout.addLayout(button_layout)
        
        # Initialize subcategories
        self.update_subcategories(0)
        
    def update_subcategories(self, index):
        self.subcategory_combo.clear()
        
        categories = {
            0: [  # Growing Supplies
                "Substrate Materials",
                "Spawn/Mycelium", 
                "Nutrient Supplements",
                "pH Adjusters",
                "Growth Hormones"
            ],
            1: [  # Harvested Mushrooms
                "White Button Mushrooms",
                "Portobello Mushrooms", 
                "Shiitake Mushrooms",
                "Oyster Mushrooms",
                "Chanterelle Mushrooms",
                "Morel Mushrooms",
                "Crimini Mushrooms"
            ],
            2: [  # Equipment & Tools
                "Growing Trays",
                "Humidity Controllers",
                "Temperature Sensors",
                "CO2 Monitors",
                "Air Circulation Fans",
                "Lighting Systems",
                "Harvesting Tools"
            ],
            3: [  # Packaging Materials
                "Plastic Containers",
                "Paper Bags",
                "Vacuum Seal Bags",
                "Labels & Stickers",
                "Shipping Boxes",
                "Insulation Materials"
            ],
            4: [  # Environmental Control
                "Heating Systems",
                "Cooling Systems",
                "Humidifiers",
                "Dehumidifiers",
                "Air Filters",
                "Water Systems"
            ]
        }
        
        self.subcategory_combo.addItems(categories.get(index, []))
        self.update_additional_fields(index)
    
    def update_additional_fields(self, category_index):
        # Hide all additional fields first
        for widget in self.additional_widgets.values():
            if hasattr(widget[0], 'setVisible'):
                widget[0].setVisible(False)
            if hasattr(widget[1], 'setVisible'):
                widget[1].setVisible(False)
        
        # Show relevant fields based on category
        if category_index == 0:  # Growing Supplies
            self.additional_widgets['price'][0].setVisible(True)
            self.additional_widgets['price'][1].setVisible(True)
            self.additional_widgets['supplier'][0].setVisible(True)
            self.additional_widgets['supplier'][1].setVisible(True)
            self.additional_widgets['expiry'][0].setVisible(True)
            self.additional_widgets['expiry'][1].setVisible(True)
            
        elif category_index == 1:  # Harvested Mushrooms
            self.additional_widgets['price'][0].setVisible(True)
            self.additional_widgets['price'][1].setVisible(True)
            self.additional_widgets['quality'][0].setVisible(True)
            self.additional_widgets['quality'][1].setVisible(True)
            self.additional_widgets['expiry'][0].setVisible(True)
            self.additional_widgets['expiry'][1].setVisible(True)
            
        elif category_index == 2:  # Equipment & Tools
            self.additional_widgets['price'][0].setVisible(True)
            self.additional_widgets['price'][1].setVisible(True)
            self.additional_widgets['supplier'][0].setVisible(True)
            self.additional_widgets['supplier'][1].setVisible(True)
            
        elif category_index == 3:  # Packaging Materials
            self.additional_widgets['price'][0].setVisible(True)
            self.additional_widgets['price'][1].setVisible(True)
            self.additional_widgets['supplier'][0].setVisible(True)
            self.additional_widgets['supplier'][1].setVisible(True)
            
        elif category_index == 4:  # Environmental Control
            self.additional_widgets['price'][0].setVisible(True)
            self.additional_widgets['price'][1].setVisible(True)
            self.additional_widgets['supplier'][0].setVisible(True)
            self.additional_widgets['supplier'][1].setVisible(True)
    
    def validate_and_accept(self):
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please enter an item name.")
            return
        
        if self.quantity_input.value() > self.max_quantity_input.value():
            QMessageBox.warning(self, "Validation Error", "Current quantity cannot exceed maximum capacity.")
            return
        
        self.accept()
    
    def get_data(self):
        category = self.category_combo.currentText()
        subcategory = self.subcategory_combo.currentText()
        
        data = {
            "name": self.name_input.text().strip(),
            "description": self.description_input.text().strip(),
            "category": category,
            "subcategory": subcategory,
            "quantity": self.quantity_input.value(),
            "max_quantity": self.max_quantity_input.value(),
            "type": "supply" if category in ["Growing Supplies", "Equipment & Tools", "Packaging Materials", "Environmental Control"] else "harvest"
        }
        
        # Add additional fields if they're visible
        if self.additional_widgets['price'][1].isVisible():
            data["unit_price"] = float(self.price_input.text() or "0.0")
        
        if self.additional_widgets['supplier'][1].isVisible():
            data["supplier"] = self.supplier_input.text().strip()
        
        if self.additional_widgets['expiry'][1].isVisible():
            data["expiry_date"] = self.expiry_input.date().toString("yyyy-MM-dd")
        
        if self.additional_widgets['quality'][1].isVisible():
            data["quality_grade"] = self.quality_combo.currentText()
        
        return data

class WarehouseGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Warehouse Management")
        self.setGeometry(100, 100, 1400, 900)
        self.positions = {}
        self.layout_file = os.path.join(os.path.dirname(__file__), "warehouse_layout.json")
        self.adding_mode = None
        self.current_drawing_item = None
        self.drawing_start_pos = None

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0,0,0,0)
        self.layout.setSpacing(0)
        
        self.setup_toolbar()
        
        self.scene = CustomGraphicsScene(self)
        self.view = PannableGraphicsView(self.scene, self)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setViewportUpdateMode(QGraphicsView.BoundingRectViewportUpdate)
        self.view.setStyleSheet("border: none;")
        self.view.viewport().installEventFilter(self)
        
        self.layout.addWidget(self.view)
        
        self.load_layout()
        self.load_warehouse_data()

    def setup_toolbar(self):
        toolbar_container = QWidget()
        toolbar_container.setStyleSheet("background-color: #2c3e50;")
        toolbar_layout = QVBoxLayout(toolbar_container)
        toolbar_layout.setContentsMargins(10, 10, 10, 10)

        title_label = QLabel("Warehouse Management")
        title_label.setStyleSheet("font-size: 20px; color: white; font-weight: bold; padding-bottom: 10px;")
        toolbar_layout.addWidget(title_label)

        toolbar_frame = QFrame()
        toolbar = QHBoxLayout(toolbar_frame)
        toolbar.setContentsMargins(0,0,0,0)
        toolbar.setSpacing(10)
        
        btn_style = """
            QPushButton {
                background-color: #34495e; color: white; border: none; padding: 8px 16px;
                font-size: 13px; border-radius: 4px;
            }
            QPushButton:hover { background-color: #4a627a; }
            QPushButton:checked { background-color: #1abc9c; color: white; }
        """
        
        add_item_btn = QPushButton("📦 Add Item")
        add_item_btn.setStyleSheet(btn_style)
        add_item_btn.clicked.connect(self.add_item)
        toolbar.addWidget(add_item_btn)

        add_rect_btn = QPushButton("⬜ Add Area")
        add_rect_btn.setCheckable(True)
        add_rect_btn.setStyleSheet(btn_style)
        add_rect_btn.clicked.connect(lambda checked: self.set_adding_mode('rect' if checked else None, add_rect_btn))
        toolbar.addWidget(add_rect_btn)
        
        add_text_btn = QPushButton("✍️ Add Label")
        add_text_btn.setCheckable(True)
        add_text_btn.setStyleSheet(btn_style)
        add_text_btn.clicked.connect(lambda checked: self.set_adding_mode('text' if checked else None, add_text_btn))
        toolbar.addWidget(add_text_btn)
        
        toolbar.addStretch()

        zoom_in_btn = QPushButton("➕ Zoom In")
        zoom_in_btn.setStyleSheet(btn_style)
        zoom_in_btn.clicked.connect(self.zoom_in)
        toolbar.addWidget(zoom_in_btn)
        
        zoom_out_btn = QPushButton("➖ Zoom Out")
        zoom_out_btn.setStyleSheet(btn_style)
        zoom_out_btn.clicked.connect(self.zoom_out)
        toolbar.addWidget(zoom_out_btn)
        
        change_bg_btn = QPushButton("🎨 Background")
        change_bg_btn.setStyleSheet(btn_style)
        change_bg_btn.clicked.connect(self.change_background_color)
        toolbar.addWidget(change_bg_btn)

        save_btn = QPushButton("💾 Save Layout")
        save_btn.setStyleSheet(btn_style.replace("#34495e", "#27ae60").replace("#4a627a", "#2ecc71"))
        save_btn.clicked.connect(self.save_layout)
        toolbar.addWidget(save_btn)
        
        toolbar_layout.addWidget(toolbar_frame)
        self.layout.addWidget(toolbar_container)

    def set_adding_mode(self, mode, button=None):
        self.adding_mode = mode
        self.view.setCursor(Qt.CrossCursor if mode else Qt.ArrowCursor)
        if mode:
            for btn in self.findChildren(QPushButton):
                if btn.isCheckable() and btn != button: btn.setChecked(False)

    def zoom_in(self): self.view.scale(1.2, 1.2)
    def zoom_out(self): self.view.scale(1/1.2, 1/1.2)
    
    def change_background_color(self):
        color = QColorDialog.getColor(self.scene.background_color, self, "Select Background Color", QColorDialog.ShowAlphaChannel)
        if color.isValid():
            self.scene.background_color = color
            self.scene.update()
    
    def add_item(self):
        dialog = AddWarehouseItemDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            ref_name = "Supplies" if data['type'] == 'supply' else 'Harvests'
            
            # Create the complete item data
            item_data = {
                "name": data['name'],
                "description": data['description'],
                "category": data['category'],
                "subcategory": data['subcategory'],
                "quantity": data['quantity'],
                "max_quantity": data['max_quantity'],
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Add optional fields if they exist
            if 'unit_price' in data:
                item_data["unit_price"] = data['unit_price']
            if 'supplier' in data:
                item_data["supplier"] = data['supplier']
            if 'expiry_date' in data:
                item_data["expiry_date"] = data['expiry_date']
            if 'quality_grade' in data:
                item_data["quality_grade"] = data['quality_grade']
            
            db.reference(ref_name).push().set(item_data)
        self.load_warehouse_data()
        
    def load_warehouse_data(self):
        for item in self.scene.items():
            if isinstance(item, StorageUnitItem): self.scene.removeItem(item)
        
        current_x = 20
        current_y = 20
        
        for unit_type in ["supply", "harvest"]:
            ref_name = "Supplies" if unit_type == "supply" else "Harvests"
            data = db.reference(ref_name).get() or {}
            for unit_id, unit_data in data.items():
                item = StorageUnitItem(unit_id, unit_data, unit_type)
                item.edit_requested.connect(self.open_editor)
                if unit_id in self.positions:
                    item.setPos(self.positions[unit_id]['x'], self.positions[unit_id]['y'])
                else:
                    item.setPos(current_x, current_y)
                    current_x += item.width + 20
                    if current_x > self.view.width() - 200:
                        current_x = 20
                        current_y += item.height + 20

                self.scene.addItem(item)

    @pyqtSlot(str, str)
    def open_editor(self, unit_id, unit_type):
        ref_name = "Supplies" if unit_type == "supply" else "Harvests"
        ref = db.reference(f'{ref_name}/{unit_id}')
        data = ref.get()
        if not data: return
        dialog = EditStorageUnitDialog(data, self)
        if dialog.exec_() == QDialog.Accepted:
            ref.update(dialog.get_data())
            self.load_warehouse_data()

    def save_layout(self):
        design = {"positions": {}, "rects": [], "texts": [], "background_color": self.scene.background_color.name(QColor.HexArgb)}
        for item in self.scene.items():
            if isinstance(item, StorageUnitItem):
                design["positions"][item.unit_id] = {'x': item.x(), 'y': item.y()}
            elif isinstance(item, ResizableRectItem):
                r = item.rect()
                design["rects"].append({"x": r.x(), "y": r.y(), "w": r.width(), "h": r.height()})
            elif isinstance(item, QGraphicsTextItem):
                 design["texts"].append({"x": item.x(), "y": item.y(), "text": item.toPlainText()})
        with open(self.layout_file, "w") as f: json.dump(design, f, indent=4)
        QMessageBox.information(self, "Success", "Layout saved!")

    def load_layout(self):
        for item in self.scene.items():
            if not isinstance(item, StorageUnitItem): self.scene.removeItem(item)
        if not os.path.exists(self.layout_file): return
        try:
            with open(self.layout_file, "r") as f: design = json.load(f)
            self.positions = design.get("positions", {})
            self.scene.background_color = QColor(design.get("background_color", "#eceff1"))
            for r_data in design.get("rects", []): self.scene.addItem(ResizableRectItem(r_data['x'], r_data['y'], r_data['w'], r_data['h']))
            for t_data in design.get("texts", []):
                text = QGraphicsTextItem(t_data['text'])
                text.setPos(t_data['x'], t_data['y'])
                text.setDefaultTextColor(QColor("#34495e")); text.setFont(QFont("Arial", 14, QFont.Bold))
                text.setFlags(QGraphicsTextItem.ItemIsMovable | QGraphicsTextItem.ItemIsSelectable); text.setZValue(0)
                self.scene.addItem(text)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not load layout: {e}")

    def eventFilter(self, source, event):
        if source == self.view.viewport():
            if event.type() == QEvent.Wheel and event.modifiers() & Qt.ControlModifier:
                if event.angleDelta().y() > 0:
                    self.zoom_in()
                else:
                    self.zoom_out()
                return True

            if self.adding_mode == 'text' and event.type() == QEvent.MouseButtonPress:
                text, ok = QInputDialog.getText(self, "Add Label", "Enter text for the label:")
                if ok and text:
                    pos = self.view.mapToScene(event.pos())
                    text_item = QGraphicsTextItem(text)
                    text_item.setDefaultTextColor(QColor("#34495e")); text_item.setFont(QFont("Arial", 14, QFont.Bold))
                    text_item.setPos(pos); text_item.setFlags(QGraphicsTextItem.ItemIsMovable | QGraphicsTextItem.ItemIsSelectable); text_item.setZValue(0)
                    self.scene.addItem(text_item)
                self.set_adding_mode(None)
                return True
            elif self.adding_mode == 'rect':
                if event.type() == QEvent.MouseButtonPress:
                    self.drawing_start_pos = self.view.mapToScene(event.pos())
                    rect = QRectF(self.drawing_start_pos, self.drawing_start_pos)
                    self.current_drawing_item = ResizableRectItem(rect.x(), rect.y(), rect.width(), rect.height())
                    self.current_drawing_item.setPen(QPen(QColor("#3498db"), 2, Qt.DashLine))
                    self.scene.addItem(self.current_drawing_item)
                    return True
                elif event.type() == QEvent.MouseMove and self.drawing_start_pos:
                    current_pos = self.view.mapToScene(event.pos())
                    rect = QRectF(self.drawing_start_pos, current_pos).normalized()
                    self.current_drawing_item.setRect(rect)
                    return True
                elif event.type() == QEvent.MouseButtonRelease and self.current_drawing_item:
                    self.current_drawing_item.setPen(QPen(QColor("#3498db"), 2))
                    self.current_drawing_item = None
                    self.drawing_start_pos = None
                    self.set_adding_mode(None)
                    return True
        return super().eventFilter(source, event)

from PyQt5.QtWidgets import QApplication
import sys
if __name__ == '__main__':
    # You need a running Firebase app for this to work
    # from firebase_admin import credentials, initialize_app
    # cred = credentials.Certificate("path/to/your/credentials.json")
    # initialize_app(cred, {'databaseURL': 'your-db-url'})
    
    app = QApplication(sys.argv)
    gui = WarehouseGUI()
    gui.show()
    sys.exit(app.exec_()) 