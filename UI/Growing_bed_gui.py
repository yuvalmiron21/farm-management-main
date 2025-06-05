from PyQt5.QtWidgets import (
    QMainWindow, QVBoxLayout, QWidget, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QMessageBox, QHBoxLayout, QInputDialog, QHeaderView,
    QLineEdit, QComboBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor
from firebase_admin import db
from datetime import datetime

class GrowingBedGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Growing Beds Management")
        self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet("""
            QWidget {
                background-color: #f5f5f5;
                color: #333;
            }
            QLabel {
                font-size: 24px;
                color: #2c3e50;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
                min-width: 150px;
            }
            QPushButton:hover {
                background-color: #219a52;
            }
            QPushButton#deleteButton {
                background-color: #e74c3c;
            }
            QPushButton#deleteButton:hover {
                background-color: #c0392b;
            }
            QTableWidget {
                background-color: white;
                alternate-background-color: #f9f9f9;
                border: 1px solid #dcdcdc;
                border-radius: 5px;
                padding: 5px;
                gridline-color: #e0e0e0;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QTableWidget::item:selected {
                background-color: #27ae60;
                color: white;
            }
            QHeaderView::section {
                background-color: #2c3e50;
                color: white;
                padding: 10px;
                border: none;
                font-weight: bold;
            }
            QScrollBar:vertical {
                border: none;
                background: #f5f5f5;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #bdc3c7;
                border-radius: 5px;
            }
        """)

        # Main layout with margins
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(20)

        # Header
        header_layout = QHBoxLayout()
        self.title = QLabel("🌱 Growing Beds Management")
        self.title.setFont(QFont("Arial", 24, QFont.Bold))
        header_layout.addWidget(self.title)
        header_layout.addStretch()
        self.main_layout.addLayout(header_layout)

        # Define valid growth stages
        self.valid_stages = ["Spawn Run", "Pinning", "Fruiting", "Harvesting", "Empty"]
        
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
        
        self.stage_filter = QComboBox()
        self.stage_filter.addItems(["All Stages"] + self.valid_stages)
        self.stage_filter.setStyleSheet("""
            QComboBox {
                padding: 10px;
                border: 1px solid #dcdcdc;
                border-radius: 5px;
                font-size: 14px;
                min-width: 150px;
            }
        """)
        self.stage_filter.currentTextChanged.connect(self.filter_beds)
        
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.stage_filter)
        self.main_layout.addLayout(search_layout)

        # Table
        self.growing_bed_table = QTableWidget()
        self.growing_bed_table.setColumnCount(6)
        self.growing_bed_table.setHorizontalHeaderLabels([
            "Bed ID", "Farm ID", "CO₂ Level", "Humidity", "Growth Stage", "Last Updated"
        ])
        self.growing_bed_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.growing_bed_table.setAlternatingRowColors(True)
        self.growing_bed_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.growing_bed_table.setSelectionMode(QTableWidget.SingleSelection)
        self.growing_bed_table.verticalHeader().setVisible(False)
        self.main_layout.addWidget(self.growing_bed_table)

        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.add_button = QPushButton("➕ Add Growing Bed")
        self.add_button.clicked.connect(self.add_growing_bed)
        button_layout.addWidget(self.add_button)

        self.update_button = QPushButton("✏️ Update Bed")
        self.update_button.clicked.connect(self.update_growing_bed)
        button_layout.addWidget(self.update_button)

        self.delete_button = QPushButton("🗑️ Delete Bed")
        self.delete_button.setObjectName("deleteButton")
        self.delete_button.clicked.connect(self.delete_growing_bed)
        button_layout.addWidget(self.delete_button)

        self.main_layout.addLayout(button_layout)

        # Set main layout
        container = QWidget()
        container.setLayout(self.main_layout)
        self.setCentralWidget(container)

        # Store original data for filtering
        self.all_beds = []
        
        # Load initial data
        self.load_growing_beds()

    def filter_beds(self):
        """Filter growing beds based on search text and stage"""
        search_text = self.search_input.text().lower()
        stage_filter = self.stage_filter.currentText()
        
        print(f"Filtering beds - Search: '{search_text}', Stage: '{stage_filter}'")  # Debug print
        print(f"Available beds: {len(self.all_beds)}")  # Debug print
        
        self.growing_bed_table.setRowCount(0)
        for bed in self.all_beds:
            matches_search = (
                search_text in str(bed['bed_id']).lower() or
                search_text in str(bed['farm_id']).lower() or
                search_text in str(bed['co2']).lower() or
                search_text in str(bed['humidity']).lower() or
                search_text in str(bed['stage']).lower()
            )
            
            matches_stage = (
                stage_filter == "All Stages" or
                stage_filter.lower() == str(bed['stage']).lower()
            )
            
            print(f"Bed {bed['bed_id']} - Stage: {bed['stage']}, Matches search: {matches_search}, Matches stage: {matches_stage}")  # Debug print
            
            if matches_search and matches_stage:
                self.add_bed_to_table({
                    'BedID': bed['bed_id'],
                    'FarmID': bed['farm_id'],
                    'CO2Level': bed['co2'],
                    'Humidity': bed['humidity'],
                    'CurrentGrowthStage': bed['stage'],
                    'LastUpdated': bed['updated']
                })

    def load_growing_beds(self):
        """Load growing beds to table"""
        self.growing_bed_table.setRowCount(0)
        self.all_beds = []
        try:
            ref = db.reference("GrowingBed")
            growing_beds_data = ref.get()

            if not growing_beds_data:
                return

            if isinstance(growing_beds_data, dict):
                for key, bed_data in growing_beds_data.items():
                    if isinstance(bed_data, dict):
                        self.all_beds.append({
                            'bed_id': bed_data.get('BedID', ''),
                            'farm_id': bed_data.get('FarmID', ''),
                            'co2': bed_data.get('CO2Level', ''),
                            'humidity': bed_data.get('Humidity', ''),
                            'stage': bed_data.get('CurrentGrowthStage', ''),
                            'updated': bed_data.get('LastUpdated', '')
                        })
                        self.add_bed_to_table(bed_data)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load growing beds: {str(e)}")

    def add_bed_to_table(self, bed_data):
        """Add a growing bed to the table with styling"""
        row_position = self.growing_bed_table.rowCount()
        self.growing_bed_table.insertRow(row_position)
        
        # Add items with center alignment
        items = [
            str(bed_data.get("BedID", "")),
            str(bed_data.get("FarmID", "")),
            f"{bed_data.get('CO2Level', '')} ppm",
            f"{bed_data.get('Humidity', '')}%",
            bed_data.get("CurrentGrowthStage", ""),
            bed_data.get("LastUpdated", "")
        ]
        
        for col, item_text in enumerate(items):
            item = QTableWidgetItem(str(item_text))
            item.setTextAlignment(Qt.AlignCenter)
            
            # Color-code the growth stage
            if col == 4:  # Growth Stage column
                stage_colors = {
                    "Spawn Run": "#95a5a6",    # Gray
                    "Pinning": "#f1c40f",      # Yellow
                    "Fruiting": "#27ae60",     # Green
                    "Harvesting": "#8e44ad",   # Purple
                    "Empty": "#e74c3c"         # Red
                }
                color = stage_colors.get(item_text, "#95a5a6")
                item.setBackground(QColor(color))
                item.setForeground(QColor("white"))
                item.setFont(QFont("Arial", weight=QFont.Bold))
            
            self.growing_bed_table.setItem(row_position, col, item)

    def add_growing_bed(self):
        """Add a new growing bed with improved input dialog"""
        try:
            bed_id, ok = QInputDialog.getInt(self, "Add Growing Bed", "Enter Bed ID:", min=1)
            if not ok:
                return
                
            farm_id, ok = QInputDialog.getInt(self, "Add Growing Bed", "Enter Farm ID:", min=1)
            if not ok:
                return
                
            co2_level, ok = QInputDialog.getInt(self, "Add Growing Bed", "Enter CO₂ Level (ppm):", min=0, max=10000)
            if not ok:
                return
                
            humidity, ok = QInputDialog.getInt(self, "Add Growing Bed", "Enter Humidity Level (%):", min=0, max=100)
            if not ok:
                return
                
            stage_dialog = QInputDialog(self)
            stage_dialog.setComboBoxItems(self.valid_stages)
            stage_dialog.setWindowTitle("Add Growing Bed")
            stage_dialog.setLabelText("Select Growth Stage:")
            if stage_dialog.exec_() != QInputDialog.Accepted:
                return
            growth_stage = stage_dialog.textValue()

            new_bed = {
                "BedID": bed_id,
                "FarmID": farm_id,
                "CO2Level": co2_level,
                "Humidity": humidity,
                "CurrentGrowthStage": growth_stage,
                "LastUpdated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            ref = db.reference("GrowingBed")
            ref.child(str(bed_id)).set(new_bed)
            
            QMessageBox.information(self, "Success", "Growing bed added successfully!")
            self.load_growing_beds()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to add growing bed: {str(e)}")

    def update_growing_bed(self):
        """Update the selected growing bed with improved input dialog"""
        selected_row = self.growing_bed_table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Error", "Please select a growing bed to update.")
            return

        try:
            bed_id = self.growing_bed_table.item(selected_row, 0).text()
            current_farm_id = int(self.growing_bed_table.item(selected_row, 1).text())
            current_co2 = int(self.growing_bed_table.item(selected_row, 2).text().replace(" ppm", ""))
            current_humidity = int(self.growing_bed_table.item(selected_row, 3).text().replace("%", ""))
            current_stage = self.growing_bed_table.item(selected_row, 4).text()

            farm_id, ok = QInputDialog.getInt(self, "Update Growing Bed", "Enter Farm ID:", value=current_farm_id, min=1)
            if not ok:
                return
                
            co2_level, ok = QInputDialog.getInt(self, "Update Growing Bed", "Enter CO₂ Level (ppm):", value=current_co2, min=0, max=10000)
            if not ok:
                return
                
            humidity, ok = QInputDialog.getInt(self, "Update Growing Bed", "Enter Humidity Level (%):", value=current_humidity, min=0, max=100)
            if not ok:
                return
                
            stage_dialog = QInputDialog(self)
            stage_dialog.setComboBoxItems(self.valid_stages)
            stage_dialog.setWindowTitle("Update Growing Bed")
            stage_dialog.setLabelText("Select Growth Stage:")
            stage_dialog.setTextValue(current_stage)
            if stage_dialog.exec_() != QInputDialog.Accepted:
                return
            growth_stage = stage_dialog.textValue()

            updated_bed = {
                "BedID": bed_id,
                "FarmID": farm_id,
                "CO2Level": co2_level,
                "Humidity": humidity,
                "CurrentGrowthStage": growth_stage,
                "LastUpdated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            ref = db.reference(f"GrowingBed/{bed_id}")
            ref.update(updated_bed)
            
            QMessageBox.information(self, "Success", "Growing bed updated successfully!")
            self.load_growing_beds()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to update growing bed: {str(e)}")

    def delete_growing_bed(self):
        """Delete the selected growing bed with confirmation"""
        selected_row = self.growing_bed_table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Error", "Please select a growing bed to delete.")
            return

        try:
            bed_id = self.growing_bed_table.item(selected_row, 0).text()
            
            confirm = QMessageBox()
            confirm.setIcon(QMessageBox.Warning)
            confirm.setText("Are you sure you want to delete this growing bed?")
            confirm.setWindowTitle("Confirm Deletion")
            confirm.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            confirm.setDefaultButton(QMessageBox.No)
            
            if confirm.exec_() == QMessageBox.Yes:
                ref = db.reference(f"GrowingBed/{bed_id}")
                ref.delete()
                QMessageBox.information(self, "Success", "Growing bed deleted successfully!")
                self.load_growing_beds()
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete growing bed: {str(e)}")
