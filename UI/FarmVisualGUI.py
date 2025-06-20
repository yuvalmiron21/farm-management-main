from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QGraphicsView, QGraphicsScene, QGraphicsItem, QFrame, QToolTip,
    QSizePolicy, QSpacerItem, QScrollArea, QMenu, QInputDialog, QMessageBox,
    QGraphicsDropShadowEffect, QGraphicsOpacityEffect, QDialog, QFormLayout,
    QDialogButtonBox, QLineEdit, QComboBox, QGraphicsLineItem, QGraphicsTextItem,
    QGraphicsRectItem, QGraphicsObject, QColorDialog
)
from PyQt5.QtCore import (
    Qt, QRectF, QPointF, QSizeF, pyqtSignal, QPropertyAnimation, QEasingCurve, 
    QTimer, pyqtProperty, pyqtSlot, QLineF, QEvent, QPoint
)
from PyQt5.QtGui import (
    QPainter, QBrush, QPen, QColor, QLinearGradient, QFont,
    QPainterPath, QPolygonF, QRadialGradient, QFontDatabase, QCursor
)
from firebase_admin import db
from datetime import datetime
import random
import json
import os

class CustomGraphicsScene(QGraphicsScene):
    """A custom scene with a grid background."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.grid_size = 20
        self.background_color = QColor("#f0f4f8")
        self.light_pen = QPen(QColor("#e3eaf0"), 1)
        self.dark_pen = QPen(QColor("#d8dde2"), 1.5)

    def drawBackground(self, painter, rect):
        painter.fillRect(rect, self.background_color)
        
        left = int(rect.left()) - (int(rect.left()) % self.grid_size)
        top = int(rect.top()) - (int(rect.top()) % self.grid_size)
        
        lines_light, lines_dark = [], []
        for x in range(left, int(rect.right()), self.grid_size):
            if x % (self.grid_size * 5) == 0:
                lines_dark.append(QLineF(x, rect.top(), x, rect.bottom()))
            else:
                lines_light.append(QLineF(x, rect.top(), x, rect.bottom()))
                
        for y in range(top, int(rect.bottom()), self.grid_size):
            if y % (self.grid_size * 5) == 0:
                lines_dark.append(QLineF(rect.left(), y, rect.right(), y))
            else:
                lines_light.append(QLineF(rect.left(), y, rect.right(), y))
                
        painter.setPen(self.light_pen)
        painter.drawLines(lines_light)
        painter.setPen(self.dark_pen)
        painter.drawLines(lines_dark)

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

class GrowingBedItem(QGraphicsObject):
    bed_moved = pyqtSignal(str, QPointF)
    edit_requested = pyqtSignal(str)

    def __init__(self, bed_id, bed_data, parent=None):
        super().__init__(parent)
        self.bed_id = bed_id
        self.bed_data = bed_data
        
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemSendsScenePositionChanges)
        self.setAcceptHoverEvents(True)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setZValue(1)

        self._scale = 1.0
        self._is_hovered = False
        self.width = 180
        self.height = 130
        self.detailed_panel_width = 220
        self.detailed_panel_height = 150
        
        self.stage_colors = {
            "Spawn Run": ("#78909c", "#546e7a"),
            "Pinning": ("#ffd54f", "#ffc107"),
            "Fruiting": ("#66bb6a", "#43a047"),
            "Harvesting": ("#7e57c2", "#5e35b1"),
            "Empty": ("#ef5350", "#e53935")
        }

        self.title_font = QFont("Arial", 11, QFont.Bold)
        self.label_font = QFont("Arial", 8)
        self.value_font = QFont("Arial", 9, QFont.Bold)

    def get_view(self):
        if self.scene() and self.scene().views():
            return self.scene().views()[0]
        return None

    def _get_panel_x_position(self):
        """Determines the panel's x position relative to the item's origin."""
        panel_x = self.width + 10
        view = self.get_view()
        if view:
            visible_rect = view.mapToScene(view.viewport().rect()).boundingRect()
            panel_abs_right = self.scenePos().x() + panel_x + self.detailed_panel_width
            if panel_abs_right > visible_rect.right():
                panel_x = -self.detailed_panel_width - 10
        return panel_x

    @pyqtProperty(float)
    def scale(self):
        return self._scale

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

    def shape(self):
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width, self.height, 10, 10)
        return path

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)
        
        transform = painter.transform()
        painter.scale(self._scale, self._scale)
        
        path = self.shape()
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 20 if self.isSelected() else 15))
        painter.drawPath(path.translated(2, 2))
        
        stage = self.bed_data.get('CurrentGrowthStage', 'Empty')
        color1_hex, color2_hex = self.stage_colors.get(stage, self.stage_colors["Empty"])
        gradient = QLinearGradient(0, 0, 0, self.height)
        gradient.setColorAt(0, QColor(color1_hex))
        gradient.setColorAt(1, QColor(color2_hex))
        painter.setBrush(gradient)
        painter.setPen(QPen(QColor(0,0,0, 40), 1))
        painter.drawPath(path)

        painter.setPen(Qt.white)
        painter.setFont(self.title_font)
        painter.drawText(QRectF(15, 10, self.width - 30, 25), f"Bed {self.bed_id}")
        
        painter.setFont(self.label_font)
        painter.setPen(QColor(255, 255, 255, 180))
        painter.drawText(QRectF(15, 30, self.width - 30, 20), stage)

        progress = (list(self.stage_colors.keys()).index(stage) + 1) / len(self.stage_colors) if stage in self.stage_colors else 0
        painter.setBrush(QColor(255, 255, 255, 50))
        painter.drawRoundedRect(15, self.height - 25, self.width - 30, 10, 5, 5)
        painter.setBrush(QColor(255, 255, 255, 150))
        painter.drawRoundedRect(15, self.height - 25, int((self.width - 30) * progress), 10, 5, 5)

        painter.setTransform(transform)
        
        if self.isSelected() or self._is_hovered:
            self.paint_data_panel(painter)

    def paint_data_panel(self, painter):
        panel_x = self._get_panel_x_position()
        panel_width = self.detailed_panel_width
        panel_height = self.detailed_panel_height
        
        path = QPainterPath()
        path.addRoundedRect(panel_x, 0, panel_width, panel_height, 8, 8)
        
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 15))
        painter.drawPath(path.translated(1, 1))

        painter.setBrush(QColor(255, 255, 255, 250))
        painter.setPen(QPen(QColor("#e0e0e0"), 1))
        painter.drawPath(path)
        
        data = self.bed_data
        data_items = [
            ("🌡️", "Temperature", f"{data.get('Temperature', 0)}°C"),
            ("💧", "Humidity", f"{data.get('Humidity', 0)}%"),
            ("☁️", "CO2 Level", f"{data.get('CO2Level', 0)} ppm"),
            ("🕒", "Last Update", f"{data.get('LastUpdated', 'N/A').split(' ')[0]}")
        ]
        
        y_offset = 20
        for icon, label, value in data_items:
            painter.setFont(QFont("Arial", 12))
            painter.setPen(Qt.black)
            painter.drawText(panel_x + 15, y_offset, icon)
            
            painter.setFont(self.label_font)
            painter.setPen(QColor("#555"))
            painter.drawText(panel_x + 40, y_offset, label)
            
            painter.setFont(self.value_font)
            painter.setPen(QColor("#111"))
            painter.drawText(QRectF(panel_x + 100, y_offset - 10, panel_width - 115, 20), Qt.AlignRight | Qt.AlignVCenter, value)
            y_offset += 30

    def hoverEnterEvent(self, event):
        self.prepareGeometryChange()
        self._is_hovered = True
        self.setZValue(100)
        self.anim = QPropertyAnimation(self, b"scale")
        self.anim.setEndValue(1.1)
        self.anim.setDuration(200)
        self.anim.setEasingCurve(QEasingCurve.OutQuad)
        self.anim.start()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.prepareGeometryChange()
        self._is_hovered = False
        self.setZValue(1)
        self.anim = QPropertyAnimation(self, b"scale")
        self.anim.setEndValue(1.0)
        self.anim.setDuration(200)
        self.anim.setEasingCurve(QEasingCurve.OutQuad)
        self.anim.start()
        super().hoverLeaveEvent(event)

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
            self.prepareGeometryChange()

        if change == QGraphicsItem.ItemPositionChange and self.scene():
            self._clear_guides()
            new_pos = value
            snap_threshold = 10
            grid_size = self.scene().grid_size

            final_x = round(new_pos.x() / grid_size) * grid_size
            final_y = round(new_pos.y() / grid_size) * grid_size
            
            other_beds = [item for item in self.scene().items() if isinstance(item, GrowingBedItem) and item != self]

            my_rect_future = QRectF(new_pos, self.boundingRect().size())
            
            for other in other_beds:
                other_rect = other.sceneBoundingRect()
                
                # --- Vertical Snapping (X axis) ---
                alignments_x = {
                    other_rect.left(): my_rect_future.left(),
                    other_rect.right(): my_rect_future.right(),
                    other_rect.center().x(): my_rect_future.center().x()
                }
                for target_x, my_x in alignments_x.items():
                    if abs(target_x - my_x) < snap_threshold:
                        final_x = new_pos.x() - (my_x - target_x)
                        self._draw_guide(QLineF(target_x, other_rect.top(), target_x, my_rect_future.bottom()))
                        break
                
                # --- Horizontal Snapping (Y axis) ---
                alignments_y = {
                    other_rect.top(): my_rect_future.top(),
                    other_rect.bottom(): my_rect_future.bottom(),
                    other_rect.center().y(): my_rect_future.center().y()
                }
                for target_y, my_y in alignments_y.items():
                    if abs(target_y - my_y) < snap_threshold:
                        final_y = new_pos.y() - (my_y - target_y)
                        self._draw_guide(QLineF(other_rect.left(), target_y, my_rect_future.right(), target_y))
                        break

            return QPointF(final_x, final_y)

        return super().itemChange(change, value)

    def _draw_guide(self, line):
        if not hasattr(self, 'guide_lines'):
            self.guide_lines = []
        pen = QPen(QColor("#1abc9c"), 1.5, Qt.DashLine)
        guide = self.scene().addLine(line, pen)
        guide.setZValue(200)
        self.guide_lines.append(guide)

    def mouseDoubleClickEvent(self, event):
        self.edit_requested.emit(self.bed_id)
        super().mouseDoubleClickEvent(event)

class ResizableRectItem(QGraphicsRectItem):
    """A resizable rectangle for defining rooms."""
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
        if self.isSelected():
            pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        
        brush_color = QColor("#3498db")
        brush_color.setAlpha(20)
        painter.setBrush(brush_color)
        painter.drawRoundedRect(self.rect(), 5, 5)

        if self.isSelected():
            painter.setBrush(QColor("#2980b9"))
            for handle in self.handles.values():
                painter.drawRect(handle)

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
            if self.resizing_handle == 1:
                rect.setTopLeft(event.pos())
            elif self.resizing_handle == 2:
                rect.setTopRight(event.pos())
            elif self.resizing_handle == 3:
                rect.setBottomLeft(event.pos())
            elif self.resizing_handle == 4:
                rect.setBottomRight(event.pos())
            self.setRect(rect)
            self.update_handles()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.resizing_handle = None
        super().mouseReleaseEvent(event)

class EditBedDialog(QDialog):
    def __init__(self, bed_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Edit Bed {bed_data.get('id', '')}")
        self.setMinimumWidth(350)
        self.setStyleSheet("""
            QDialog { background-color: #f8f9fa; }
            QLabel { font-size: 13px; }
            QLineEdit, QComboBox { 
                padding: 8px; border: 1px solid #ced4da; border-radius: 4px; 
                background-color: white; font-size: 13px;
            }
            QPushButton { 
                padding: 8px 16px; border-radius: 4px; font-weight: bold;
                background-color: #007bff; color: white; border: none;
            }
            QPushButton:hover { background-color: #0056b3; }
            QPushButton#cancelButton { background-color: #6c757d; }
            QPushButton#cancelButton:hover { background-color: #5a6268; }
        """)

        self.layout = QFormLayout(self)
        
        self.stage_combo = QComboBox()
        stages = ["Spawn Run", "Pinning", "Fruiting", "Harvesting", "Empty"]
        self.stage_combo.addItems(stages)
        self.stage_combo.setCurrentText(bed_data.get('CurrentGrowthStage', 'Empty'))
        self.layout.addRow("Growth Stage:", self.stage_combo)

        self.temp_input = QLineEdit(str(bed_data.get('Temperature', 0)))
        self.layout.addRow("Temperature (°C):", self.temp_input)
        
        self.humidity_input = QLineEdit(str(bed_data.get('Humidity', 0)))
        self.layout.addRow("Humidity (%):", self.humidity_input)

        self.co2_input = QLineEdit(str(bed_data.get('CO2Level', 0)))
        self.layout.addRow("CO2 Level (ppm):", self.co2_input)

        self.buttons = QDialogButtonBox()
        ok_button = self.buttons.addButton(QDialogButtonBox.Ok)
        cancel_button = self.buttons.addButton(QDialogButtonBox.Cancel)
        cancel_button.setObjectName("cancelButton")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.layout.addWidget(self.buttons)

    def get_data(self):
        try:
            return {
                "CurrentGrowthStage": self.stage_combo.currentText(),
                "Temperature": float(self.temp_input.text()),
                "Humidity": float(self.humidity_input.text()),
                "CO2Level": int(self.co2_input.text()),
                "LastUpdated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please ensure all numeric fields are valid numbers.")
            return None

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

class FarmVisualGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mushroom Farm Visual Management")
        self.setGeometry(100, 100, 1400, 900)
        self.bed_positions = {}
        self.room_design_file = os.path.join(os.path.dirname(__file__), "farm_layout.json")
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
        
        self.load_design()
        self.load_farm_data()

    def setup_toolbar(self):
        toolbar_container = QWidget()
        toolbar_container.setStyleSheet("background-color: #2c3e50;")
        toolbar_layout = QVBoxLayout(toolbar_container)
        toolbar_layout.setContentsMargins(10, 10, 10, 10)

        title_label = QLabel("Farm Layout & Management")
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
        
        add_bed_btn = QPushButton("🛏️ Add Bed")
        add_bed_btn.setStyleSheet(btn_style)
        add_bed_btn.clicked.connect(self.add_growing_bed)
        toolbar.addWidget(add_bed_btn)

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
        save_btn.clicked.connect(self.save_design)
        toolbar.addWidget(save_btn)
        
        toolbar_layout.addWidget(toolbar_frame)
        self.layout.addWidget(toolbar_container)

    def set_adding_mode(self, mode, button):
        self.adding_mode = mode
        if mode:
            self.view.setCursor(Qt.CrossCursor)
            for btn in self.findChildren(QPushButton):
                if isinstance(btn, QPushButton) and btn.isCheckable() and btn != button:
                    btn.setChecked(False)
        else:
            self.view.setCursor(Qt.ArrowCursor)

    def zoom_in(self):
        self.view.scale(1.2, 1.2)

    def zoom_out(self):
        self.view.scale(1/1.2, 1/1.2)
    
    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_in()
            else:
                self.zoom_out()
        else:
            super().wheelEvent(event)

    def change_background_color(self):
        color = QColorDialog.getColor(self.scene.background_color, self, "Select Background Color", QColorDialog.ShowAlphaChannel)
        if color.isValid():
            self.scene.background_color = color
            self.scene.update()

    @pyqtSlot(str, QPointF)
    def on_bed_moved(self, bed_id, pos):
        self.bed_positions[bed_id] = {'x': pos.x(), 'y': pos.y()}

    def load_farm_data(self):
        try:
            for item in self.scene.items():
                if isinstance(item, GrowingBedItem):
                    self.scene.removeItem(item)
            
            ref = db.reference('GrowingBed')
            beds_data = ref.get() or {}
            
            for bed_id, bed_data in beds_data.items():
                bed_item = GrowingBedItem(bed_id, bed_data)
                bed_item.bed_moved.connect(self.on_bed_moved)
                bed_item.edit_requested.connect(self.open_bed_editor)
                
                if bed_id in self.bed_positions:
                    pos_data = self.bed_positions[bed_id]
                    bed_item.setPos(pos_data['x'], pos_data['y'])
                else:
                    row = len(beds_data) // 5
                    col = len(beds_data) % 5
                    bed_item.setPos(col * 220, 500 + row * 160)
                self.scene.addItem(bed_item)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load farm data: {str(e)}")

    @pyqtSlot(str)
    def open_bed_editor(self, bed_id):
        try:
            bed_ref = db.reference(f'GrowingBed/{bed_id}')
            bed_data = bed_ref.get()
            if not bed_data:
                QMessageBox.warning(self, "Error", f"Could not find data for bed {bed_id}.")
                return
            
            bed_data['id'] = bed_id
            self.dialog = EditBedDialog(bed_data, self)
            
            if self.dialog.exec_() == QDialog.Accepted:
                new_data = self.dialog.get_data()
                if new_data:
                    bed_ref.update(new_data)
                    self.load_farm_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open editor: {e}")

    def save_design(self):
        design = {
            "beds": self.bed_positions, 
            "rects": [], 
            "texts": [],
            "background_color": self.scene.background_color.name(QColor.HexArgb)
        }
        for item in self.scene.items():
            if isinstance(item, ResizableRectItem):
                r = item.rect()
                design["rects"].append({"x": r.x(), "y": r.y(), "w": r.width(), "h": r.height()})
            elif isinstance(item, QGraphicsTextItem):
                 design["texts"].append({"x": item.x(), "y": item.y(), "text": item.toPlainText()})
        
        try:
            with open(self.room_design_file, "w") as f:
                json.dump(design, f, indent=4)
            QMessageBox.information(self, "Success", "Farm layout saved!")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not save layout: {e}")

    def load_design(self):
        for item in self.scene.items():
            if not isinstance(item, GrowingBedItem):
                self.scene.removeItem(item)

        if not os.path.exists(self.room_design_file):
            return
            
        try:
            with open(self.room_design_file, "r") as f:
                design = json.load(f)
            
            self.bed_positions = design.get("beds", {})
            bg_color = design.get("background_color", "#f0f4f8")
            self.scene.background_color = QColor(bg_color)
            
            for r_data in design.get("rects", []):
                rect = ResizableRectItem(r_data['x'], r_data['y'], r_data['w'], r_data['h'])
                self.scene.addItem(rect)
            for t_data in design.get("texts", []):
                text = QGraphicsTextItem(t_data['text'])
                text.setPos(t_data['x'], t_data['y'])
                text.setDefaultTextColor(QColor("#34495e"))
                text.setFont(QFont("Arial", 14, QFont.Bold))
                text.setFlags(QGraphicsTextItem.ItemIsMovable | QGraphicsTextItem.ItemIsSelectable)
                text.setZValue(0)
                self.scene.addItem(text)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not load layout: {e}")
    
    def add_growing_bed(self):
        bed_id, ok = QInputDialog.getText(self, 'Add Growing Bed', 'Enter new bed ID:')
        if ok and bed_id:
            try:
                ref = db.reference(f'GrowingBed/{bed_id}')
                ref.set({
                    "CurrentGrowthStage": "Empty",
                    "Humidity": 0,
                    "Temperature": 0,
                    "CO2Level": 0,
                "LastUpdated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
                self.load_farm_data()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to add bed: {e}")

    def eventFilter(self, source, event):
        if source != self.view.viewport():
            return super().eventFilter(source, event)

        if self.adding_mode == 'text' and event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            text, ok = QInputDialog.getText(self, "Add Label", "Enter text for the label:")
            if ok and text:
                pos = self.view.mapToScene(event.pos())
                text_item = QGraphicsTextItem(text)
                text_item.setDefaultTextColor(QColor("#34495e"))
                text_item.setFont(QFont("Arial", 14, QFont.Bold))
                text_item.setPos(pos)
                text_item.setFlags(QGraphicsTextItem.ItemIsMovable | QGraphicsTextItem.ItemIsSelectable)
                text_item.setZValue(0)
                self.scene.addItem(text_item)
            self.set_adding_mode(None, None)
            for btn in self.findChildren(QPushButton):
                if isinstance(btn, QPushButton) and btn.isCheckable():
                    btn.setChecked(False)
            return True
        
        elif self.adding_mode == 'rect':
            if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
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
            elif event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton and self.current_drawing_item:
                self.current_drawing_item.setPen(QPen(QColor("#3498db"), 2))
                self.current_drawing_item = None
                self.drawing_start_pos = None
                self.set_adding_mode(None, None)
                for btn in self.findChildren(QPushButton):
                    if isinstance(btn, QPushButton) and btn.isCheckable():
                        btn.setChecked(False)
                return True

        return super().eventFilter(source, event)

    def closeEvent(self, event):
        reply = QMessageBox.question(self, 'Save Changes', 
                                     "Do you want to save the layout changes before closing?",
                                     QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                                     QMessageBox.Cancel)
        if reply == QMessageBox.Yes:
            self.save_design()
            event.accept()
        elif reply == QMessageBox.No:
            event.accept()
        else:
            event.ignore() 