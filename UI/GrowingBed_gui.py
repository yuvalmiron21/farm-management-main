from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QTableWidget, QTableWidgetItem, QPushButton,
                             QMessageBox, QDialog, QDialogButtonBox, QInputDialog,
                             QHeaderView, QComboBox, QDateEdit, QFormLayout)
from PyQt5.QtCore import Qt, QDate, QEvent
from PyQt5.QtGui import QFont, QColor, QDoubleValidator
from firebase_admin import db
import uuid

class GrowingBedGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Growing Beds Management")
        self.setStyleSheet("""
            QWidget {
                background-color: #f5f5f5;
                font-family: Arial;
            }
            QPushButton {
                padding: 10px;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QTableWidget {
                border: 1px solid #dcdcdc;
                border-radius: 5px;
                background-color: white;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 5px;
                border: 1px solid #dcdcdc;
                font-weight: bold;
            }
        """)

        # Main layout with margins
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(20)

        # Header
        header_layout = QHBoxLayout()
        self.title = QLabel("🌱 Manage Growing Beds")
        self.title.setFont(QFont("Arial", 24, QFont.Bold))
        header_layout.addWidget(self.title)
        header_layout.addStretch()
        self.layout.addLayout(header_layout)

        # Search bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search growing beds...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                border: 1px solid #dcdcdc;
                border-radius: 5px;
                font-size: 14px;
            }
        """)
        self.search_input.textChanged.connect(self.filter_beds)
        
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All Status", "Available", "Occupied", "Maintenance"])
        self.status_filter.setStyleSheet("""
            QComboBox {
                padding: 10px;
                border: 1px solid #dcdcdc;
                border-radius: 5px;
                font-size: 14px;
                min-width: 150px;
            }
        """)
        self.status_filter.currentTextChanged.connect(self.filter_beds)
        
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.status_filter)
        self.layout.addLayout(search_layout)

        # Table
        self.bed_table = QTableWidget()
        self.bed_table.setColumnCount(8)
        self.bed_table.setHorizontalHeaderLabels([
            "ID", "Name", "Location", "Size (m²)", "Status", 
            "Crop Type", "Planting Date", "Harvest Date"
        ])
        self.bed_table.viewport().installEventFilter(self)
        self.bed_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.bed_table.setAlternatingRowColors(True)
        self.bed_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.bed_table.setSelectionMode(QTableWidget.SingleSelection)
        self.bed_table.verticalHeader().setVisible(False)
        self.bed_table.setStyleSheet("""
            QTableWidget {
                background: #fff;
                border: 1px solid #dcdcdc;
                border-radius: 8px;
                font-size: 15px;
            }
            QHeaderView::section {
                background: #f0f0f0;
                font-weight: bold;
                font-size: 16px;
                border: 1px solid #dcdcdc;
                padding: 8px;
            }
            QTableWidget::item:selected {
                background: #3498db;
                color: #fff;
            }
        """)
        self.bed_table.setRowHeight(0, 38)  # Default for first row, rest set dynamically
        self.layout.addWidget(self.bed_table)

        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        self.add_bed_button = QPushButton("➕ Add Bed")
        self.add_bed_button.setStyleSheet("padding: 10px; border-radius: 5px; background: #27ae60; color: white; font-weight: bold;")
        self.add_bed_button.clicked.connect(self.add_bed)
        button_layout.addWidget(self.add_bed_button)
        self.update_bed_button = QPushButton("✏️ Update Bed")
        self.update_bed_button.setStyleSheet("padding: 10px; border-radius: 5px; background: #f1c40f; color: #222; font-weight: bold;")
        self.update_bed_button.clicked.connect(self.update_bed)
        button_layout.addWidget(self.update_bed_button)
        self.delete_bed_button = QPushButton("🗑️ Delete Bed")
        self.delete_bed_button.setObjectName("deleteButton")
        self.delete_bed_button.setStyleSheet("padding: 10px; border-radius: 5px; background: #e74c3c; color: white; font-weight: bold;")
        self.delete_bed_button.clicked.connect(self.delete_bed)
        button_layout.addWidget(self.delete_bed_button)
        self.layout.addLayout(button_layout)

        # Set main layout
        self.setLayout(self.layout)

        # Store original data for filtering
        self.all_beds = []
        self.filtered_beds = []
        
        # Load initial data
        self.load_beds()

    def filter_beds(self):
        """Filter beds based on search text and status"""
        search_text = self.search_input.text().lower()
        status_filter = self.status_filter.currentText()
        
        self.filtered_beds = []
        
        for bed in self.all_beds:
            matches_search = (
                search_text in str(bed['id']).lower() or
                search_text in bed['name'].lower() or
                search_text in bed['location'].lower() or
                search_text in str(bed['size']).lower() or
                search_text in bed['status'].lower() or
                search_text in str(bed.get('crop_type', '')).lower()
            )
            
            matches_status = (
                status_filter == "All Status" or
                status_filter.lower() == bed['status'].lower()
            )
            
            if matches_search and matches_status:
                self.filtered_beds.append(bed)
        
        self.display_filtered_beds()

    def display_filtered_beds(self):
        """Display the filtered beds in the table"""
        self.bed_table.setRowCount(0)
        for bed in self.filtered_beds:
            self.add_bed_to_table(bed)

    def load_beds(self):
        """Load beds to table"""
        self.bed_table.setRowCount(0)
        self.all_beds = []
        self.filtered_beds = []
        
        try:
            ref = db.reference('GrowingBed')
            beds_data = ref.get()

            if not beds_data:
                return

            if isinstance(beds_data, dict):
                for key, bed_data in beds_data.items():
                    if isinstance(bed_data, dict):
                        # Map Firebase fields to table fields
                        bed_info = {
                            'id': key, # Use Firebase key as ID
                            'name': bed_data.get('Name', f"Bed {key.replace('BED', '')}"),
                            'location': bed_data.get('Location', 'N/A'),
                            'size': bed_data.get('Size', 0.0), # Assuming size is stored directly
                            'status': bed_data.get('CurrentGrowthStage', 'Unknown'), # Map from CurrentGrowthStage
                            'crop_type': bed_data.get('MushroomType', ''), # Map from MushroomType
                            'planting_date': bed_data.get('Start_date', ''), # Map from Start_date
                            'harvest_date': bed_data.get('HarvestDate', '') # Assuming this field exists
                        }
                        self.all_beds.append(bed_info)
                        self.filtered_beds.append(bed_info)
                        self.add_bed_to_table(bed_info)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load growing beds: {str(e)}")

    def add_bed_to_table(self, bed_data):
        """Add a bed to the table with styling"""
        row_position = self.bed_table.rowCount()
        self.bed_table.insertRow(row_position)
        
        # Ensure size is float for formatting
        size_value = bed_data['size']
        try:
            size_value = float(size_value)
        except (ValueError, TypeError):
            size_value = 0.0

        # Add items with center alignment
        items = [
            str(bed_data['id']),
            bed_data['name'],
            bed_data['location'],
            f"{size_value:.2f}",
            bed_data['status'],
            bed_data.get('crop_type', ''),
            bed_data.get('planting_date', ''),
            bed_data.get('harvest_date', '')
        ]
        
        for col, item_text in enumerate(items):
            item = QTableWidgetItem(str(item_text))
            item.setTextAlignment(Qt.AlignCenter)
            
            # Color-code the status
            if col == 4:  # Status column
                status_colors = {
                    "Active": "#2ecc71",
                    "Available": "#2ecc71",
                    "Inactive": "#e74c3c",
                    "Maintenance": "#f39c12",
                    "Spawn Run": "#3498db",
                    "Pinning": "#9b59b6",
                    "Fruiting": "#1abc9c",
                    "Harvesting": "#27ae60",
                    "Empty": "#bdc3c7",
                    "Unknown": "#7f8c8d"
                }
                
                status_text = item.text()
                color_hex = status_colors.get(status_text, "#7f8c8d")
                item.setBackground(QColor(color_hex))
                item.setForeground(QColor("white"))
                item.setFont(QFont("Arial", weight=QFont.Bold))
            
            self.bed_table.setItem(row_position, col, item)

    def add_bed(self):
        """Add a new growing bed with a modern form dialog"""
        try:
            dialog = AddGrowingBedDialog(self)
            if dialog.exec_() == QDialog.Accepted:
                data = dialog.get_data()
                ref = db.reference('GrowingBed')
                ref.child(data["ID"]).set(data)
                QMessageBox.information(self, "Success", "Growing bed added successfully!")
                self.load_beds()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to add growing bed: {str(e)}")

    def update_bed(self):
        """Update the selected growing bed"""
        selected_row = self.bed_table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Error", "Please select a growing bed to update.")
            return

        try:
            bed_id = self.bed_table.item(selected_row, 0).text()
            current_data = {
                "ID": bed_id,
                "Name": self.bed_table.item(selected_row, 1).text(),
                "Location": self.bed_table.item(selected_row, 2).text(),
                "Size": float(self.bed_table.item(selected_row, 3).text()),
                "Status": self.bed_table.item(selected_row, 4).text(),
                "CropType": self.bed_table.item(selected_row, 5).text(),
                "PlantingDate": self.bed_table.item(selected_row, 6).text(),
                "HarvestDate": self.bed_table.item(selected_row, 7).text()
            }

            dialog = UpdateGrowingBedDialog(self, current_data)
            if dialog.exec_() == QDialog.Accepted:
                updated_data = dialog.get_data()
                ref = db.reference(f'GrowingBed/{bed_id}')
                ref.update(updated_data)
                QMessageBox.information(self, "Success", "Growing bed updated successfully!")
                self.load_beds()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to update growing bed: {str(e)}")

    def delete_bed(self):
        """Delete the selected growing bed with confirmation"""
        selected_row = self.bed_table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Error", "Please select a growing bed to delete.")
            return

        try:
            bed_id = self.bed_table.item(selected_row, 0).text()
            bed_name = self.bed_table.item(selected_row, 1).text()
            
            confirm = QMessageBox()
            confirm.setIcon(QMessageBox.Warning)
            confirm.setText(f"Are you sure you want to delete growing bed '{bed_name}'?")
            confirm.setWindowTitle("Confirm Deletion")
            confirm.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            confirm.setDefaultButton(QMessageBox.No)
            
            if confirm.exec_() == QMessageBox.Yes:
                ref = db.reference(f'GrowingBed/{bed_id}')
                ref.delete()
                QMessageBox.information(self, "Success", "Growing bed deleted successfully!")
                self.load_beds()
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete growing bed: {str(e)}")

    def eventFilter(self, source, event):
        if source == self.bed_table.viewport() and event.type() == QEvent.Wheel and event.modifiers() & Qt.ControlModifier:
            current_font = self.bed_table.font()
            point_size = current_font.pointSize()
            
            if event.angleDelta().y() > 0:
                point_size += 1
            else:
                point_size = max(6, point_size - 1)
            
            current_font.setPointSize(point_size)
            self.bed_table.setFont(current_font)
            
            # Adjust header font and row height
            header_font = self.bed_table.horizontalHeader().font()
            header_font.setPointSize(point_size)
            self.bed_table.horizontalHeader().setFont(header_font)
            self.bed_table.horizontalHeader().setMinimumHeight(point_size + 22)

            for i in range(self.bed_table.rowCount()):
                self.bed_table.setRowHeight(i, point_size + 20)

            return True

        return super().eventFilter(source, event)

class AddGrowingBedDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Growing Bed")
        self.setMinimumWidth(420)
        self.setStyleSheet("""
            QDialog {
                background: #f8f9fa;
            }
            QLabel {
                font-size: 15px;
            }
            QLineEdit, QComboBox, QDateEdit {
                padding: 8px;
                border-radius: 5px;
                border: 1px solid #dcdcdc;
                font-size: 14px;
            }
            QPushButton {
                padding: 10px;
                border-radius: 5px;
                background: #3498db;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #2980b9;
            }
        """)
        layout = QVBoxLayout()
        title = QLabel("🌱 Add Growing Bed")
        title.setFont(QFont("Arial", 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        form = QFormLayout()
        self.name = QLineEdit()
        form.addRow("Name:", self.name)
        self.location = QLineEdit()
        form.addRow("Location:", self.location)
        self.size = QLineEdit()
        self.size.setValidator(QDoubleValidator(0.0, 1000.0, 2))
        form.addRow("Size (m²):", self.size)
        self.status = QComboBox()
        self.status.addItems(["Available", "Occupied", "Maintenance"])
        form.addRow("Status:", self.status)
        self.crop_type = QLineEdit()
        form.addRow("Crop Type:", self.crop_type)
        self.planting_date = QDateEdit()
        self.planting_date.setCalendarPopup(True)
        form.addRow("Planting Date:", self.planting_date)
        self.harvest_date = QDateEdit()
        self.harvest_date.setCalendarPopup(True)
        form.addRow("Harvest Date:", self.harvest_date)
        layout.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        btns.accepted.connect(self.validate_and_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)
        self.setLayout(layout)
    def validate_and_accept(self):
        if not self.name.text().strip() or not self.location.text().strip() or not self.size.text().strip():
            QMessageBox.warning(self, "Error", "Please fill in all required fields.")
            return
        self.accept()
    def get_data(self):
        return {
            "ID": str(uuid.uuid4()),
            "Name": self.name.text().strip(),
            "Location": self.location.text().strip(),
            "Size": float(self.size.text().strip()),
            "Status": self.status.currentText(),
            "CropType": self.crop_type.text().strip(),
            "PlantingDate": self.planting_date.date().toString("yyyy-MM-dd"),
            "HarvestDate": self.harvest_date.date().toString("yyyy-MM-dd")
        }

class UpdateGrowingBedDialog(QDialog):
    def __init__(self, parent=None, current_data=None):
        super().__init__(parent)
        self.setWindowTitle("Update Growing Bed")
        self.setMinimumWidth(400)
        self.current_data = current_data or {}
        
        layout = QVBoxLayout()
        
        # Name
        layout.addWidget(QLabel("Name:"))
        self.name = QLineEdit(self.current_data.get("Name", ""))
        layout.addWidget(self.name)
        
        # Location
        layout.addWidget(QLabel("Location:"))
        self.location = QLineEdit(self.current_data.get("Location", ""))
        layout.addWidget(self.location)
        
        # Size
        layout.addWidget(QLabel("Size (m²):"))
        self.size = QLineEdit(str(self.current_data.get("Size", 0)))
        self.size.setValidator(QDoubleValidator(0.0, 1000.0, 2))
        layout.addWidget(self.size)
        
        # Status
        layout.addWidget(QLabel("Status:"))
        self.status = QComboBox()
        self.status.addItems(["Available", "Occupied", "Maintenance"])
        self.status.setCurrentText(self.current_data.get("Status", "Available"))
        layout.addWidget(self.status)
        
        # Crop Type
        layout.addWidget(QLabel("Crop Type:"))
        self.crop_type = QLineEdit(self.current_data.get("CropType", ""))
        layout.addWidget(self.crop_type)
        
        # Planting Date
        layout.addWidget(QLabel("Planting Date:"))
        self.planting_date = QDateEdit()
        self.planting_date.setCalendarPopup(True)
        if self.current_data.get("PlantingDate"):
            self.planting_date.setDate(QDate.fromString(self.current_data["PlantingDate"], "yyyy-MM-dd"))
        layout.addWidget(self.planting_date)
        
        # Harvest Date
        layout.addWidget(QLabel("Harvest Date:"))
        self.harvest_date = QDateEdit()
        self.harvest_date.setCalendarPopup(True)
        if self.current_data.get("HarvestDate"):
            self.harvest_date.setDate(QDate.fromString(self.current_data["HarvestDate"], "yyyy-MM-dd"))
        layout.addWidget(self.harvest_date)
        
        # Buttons
        btns = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self)
        btns.accepted.connect(self.validate_and_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)
        
        self.setLayout(layout)

    def validate_and_accept(self):
        if not self.name.text().strip() or not self.location.text().strip() or not self.size.text().strip():
            QMessageBox.warning(self, "Error", "Please fill in all required fields.")
            return
        self.accept()

    def get_data(self):
        return {
            "Name": self.name.text().strip(),
            "Location": self.location.text().strip(),
            "Size": float(self.size.text().strip()),
            "Status": self.status.currentText(),
            "CropType": self.crop_type.text().strip(),
            "PlantingDate": self.planting_date.date().toString("yyyy-MM-dd"),
            "HarvestDate": self.harvest_date.date().toString("yyyy-MM-dd")
        } 