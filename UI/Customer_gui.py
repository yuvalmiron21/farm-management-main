from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QHBoxLayout, QInputDialog, QHeaderView, QLineEdit, QDialog, QFormLayout, QDialogButtonBox, QSpinBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor
from firebase_admin import db
import uuid

class CustomerGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Customer Management")
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
                background-color: #9b59b6;
                color: white;
                border: none;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
                min-width: 150px;
            }
            QPushButton:hover {
                background-color: #8e44ad;
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
                background-color: #9b59b6;
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
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(20)

        # Header
        header_layout = QHBoxLayout()
        self.title = QLabel("👥 Manage Customers")
        self.title.setFont(QFont("Arial", 24, QFont.Bold))
        header_layout.addWidget(self.title)
        header_layout.addStretch()
        self.layout.addLayout(header_layout)

        # Search bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search customers...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                border: 1px solid #dcdcdc;
                border-radius: 5px;
                font-size: 14px;
            }
        """)
        self.search_input.textChanged.connect(self.filter_customers)
        search_layout.addWidget(self.search_input)
        self.layout.addLayout(search_layout)

        # Table
        self.customer_table = QTableWidget()
        self.customer_table.setColumnCount(5)
        self.customer_table.setHorizontalHeaderLabels(["ID", "Name", "Email", "Phone", "Address"])
        self.customer_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.customer_table.setAlternatingRowColors(True)
        self.customer_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.customer_table.setSelectionMode(QTableWidget.SingleSelection)
        self.customer_table.verticalHeader().setVisible(False)
        self.layout.addWidget(self.customer_table)

        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.add_customer_button = QPushButton("➕ Add Customer")
        self.add_customer_button.clicked.connect(self.add_customer)
        button_layout.addWidget(self.add_customer_button)

        self.update_customer_button = QPushButton("✏️ Update Customer")
        self.update_customer_button.clicked.connect(self.update_customer)
        button_layout.addWidget(self.update_customer_button)

        self.delete_customer_button = QPushButton("🗑️ Delete Customer")
        self.delete_customer_button.setObjectName("deleteButton")
        self.delete_customer_button.clicked.connect(self.delete_customer)
        button_layout.addWidget(self.delete_customer_button)

        self.layout.addLayout(button_layout)

        # Set main layout
        self.setLayout(self.layout)

        # Store original data for filtering
        self.all_customers = []
        
        # Load initial data
        self.load_customers()

    def filter_customers(self):
        search_text = self.search_input.text().lower()
        
        self.customer_table.setRowCount(0)
        for customer in self.all_customers:
            matches_search = (
                search_text in str(customer['id']).lower() or
                search_text in customer['name'].lower() or
                search_text in customer['email'].lower() or
                search_text in customer['phone'].lower() or
                search_text in customer['address'].lower()
            )
            
            if matches_search:
                self.add_customer_to_table({
                    'ID': customer['id'],
                    'Name': customer['name'],
                    'Email': customer['email'],
                    'Phone': customer['phone'],
                    'Address': customer['address']
                })

    def load_customers(self):
        """Load customers to table"""
        self.customer_table.setRowCount(0)
        self.all_customers = []
        try:
            ref = db.reference('Customer')
            customers_data = ref.get()

            if not customers_data:
                return

            if isinstance(customers_data, dict):
                for key, customer_data in customers_data.items():
                    if isinstance(customer_data, dict):
                        self.all_customers.append({
                            'id': customer_data.get('ID', ''),
                            'name': customer_data.get('Name', ''),
                            'email': customer_data.get('Email', ''),
                            'phone': customer_data.get('Phone', ''),
                            'address': customer_data.get('Address', '')
                        })
                        self.add_customer_to_table(customer_data)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load customers: {str(e)}")

    def add_customer_to_table(self, customer_data):
        """Add a customer to the table with styling"""
        row_position = self.customer_table.rowCount()
        self.customer_table.insertRow(row_position)
        
        # Add items with center alignment
        items = [
            str(customer_data.get("ID", "")),
            customer_data.get("Name", ""),
            customer_data.get("Email", ""),
            customer_data.get("Phone", ""),
            customer_data.get("Address", "")
        ]
        
        for col, item_text in enumerate(items):
            item = QTableWidgetItem(str(item_text))
            item.setTextAlignment(Qt.AlignCenter)
            self.customer_table.setItem(row_position, col, item)

    def add_customer(self):
        """Add a new customer with a modern form dialog and auto-generated ID"""
        try:
            dialog = AddCustomerDialog(self)
            if dialog.exec_() == QDialog.Accepted:
                data = dialog.get_data()
                ref = db.reference('Customer')
                ref.child(data["ID"]).set(data)
                QMessageBox.information(self, "Success", "Customer added successfully!")
                self.load_customers()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to add customer: {str(e)}")

    def update_customer(self):
        """Update the selected customer with improved input dialog"""
        selected_row = self.customer_table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Error", "Please select a customer to update.")
            return

        try:
            customer_id = self.customer_table.item(selected_row, 0).text()
            current_name = self.customer_table.item(selected_row, 1).text()
            current_email = self.customer_table.item(selected_row, 2).text()
            current_phone = self.customer_table.item(selected_row, 3).text()
            current_address = self.customer_table.item(selected_row, 4).text()

            name, ok = QInputDialog.getText(self, "Update Customer", "Enter Customer Name:", text=current_name)
            if not ok or not name.strip():
                return
                
            email, ok = QInputDialog.getText(self, "Update Customer", "Enter Customer Email:", text=current_email)
            if not ok or not email.strip():
                return
                
            phone, ok = QInputDialog.getText(self, "Update Customer", "Enter Customer Phone:", text=current_phone)
            if not ok or not phone.strip():
                return
                
            address, ok = QInputDialog.getText(self, "Update Customer", "Enter Customer Address:", text=current_address)
            if not ok or not address.strip():
                return

            updated_customer = {
                "ID": customer_id,
                "Name": name.strip(),
                "Email": email.strip(),
                "Phone": phone.strip(),
                "Address": address.strip()
            }

            ref = db.reference(f'Customer/{customer_id}')
            ref.update(updated_customer)
            
            QMessageBox.information(self, "Success", "Customer updated successfully!")
            self.load_customers()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to update customer: {str(e)}")

    def delete_customer(self):
        """Delete the selected customer with confirmation"""
        selected_row = self.customer_table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Error", "Please select a customer to delete.")
            return

        try:
            customer_id = self.customer_table.item(selected_row, 0).text()
            customer_name = self.customer_table.item(selected_row, 1).text()
            
            confirm = QMessageBox()
            confirm.setIcon(QMessageBox.Warning)
            confirm.setText(f"Are you sure you want to delete customer '{customer_name}'?")
            confirm.setWindowTitle("Confirm Deletion")
            confirm.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            confirm.setDefaultButton(QMessageBox.No)
            
            if confirm.exec_() == QMessageBox.Yes:
                ref = db.reference(f'Customer/{customer_id}')
                ref.delete()
                QMessageBox.information(self, "Success", "Customer deleted successfully!")
                self.load_customers()
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete customer: {str(e)}")

class AddCustomerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Customer")
        self.setMinimumWidth(400)
        self.setStyleSheet("""
            QDialog { background: #f8fafc; border-radius: 16px; }
            QLabel#titleLabel { font-size: 22px; font-weight: bold; color: #2c3e50; margin-bottom: 18px; }
            QFormLayout > QLabel { font-size: 15px; color: #222; min-width: 110px; }
            QLineEdit { font-size: 15px; padding: 7px 10px; border-radius: 7px; border: 1px solid #d0d7de; background: #fff; }
            QPushButton { min-width: 90px; min-height: 32px; font-size: 15px; border-radius: 8px; font-weight: bold; }
            QPushButton:enabled { background: #43a047; color: #fff; }
            QPushButton:enabled:hover { background: #388e3c; }
            QPushButton:disabled { background: #e0e0e0; color: #aaa; }
            QPushButton#Cancel { background: #e74c3c; color: #fff; }
            QPushButton#Cancel:hover { background: #c0392b; }
        """)
        layout = QVBoxLayout(self)
        # Title with icon
        title = QLabel("👤 Add New Customer")
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignHCenter)
        layout.addWidget(title)
        # Form
        form = QFormLayout()
        form.setSpacing(16)
        self.name = QLineEdit()
        form.addRow("Name:", self.name)
        self.email = QLineEdit()
        form.addRow("Email:", self.email)
        self.phone = QLineEdit()
        form.addRow("Phone:", self.phone)
        self.address = QLineEdit()
        form.addRow("Address:", self.address)
        layout.addLayout(form)
        # Buttons
        btns = QDialogButtonBox()
        self.ok_btn = QPushButton("OK")
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("Cancel")
        btns.addButton(self.ok_btn, QDialogButtonBox.AcceptRole)
        btns.addButton(self.cancel_btn, QDialogButtonBox.RejectRole)
        self.ok_btn.clicked.connect(self.validate_and_accept)
        self.cancel_btn.clicked.connect(self.reject)
        layout.addSpacing(10)
        layout.addWidget(btns)
    def validate_and_accept(self):
        if not self.name.text().strip() or not self.email.text().strip() or not self.phone.text().strip() or not self.address.text().strip():
            QMessageBox.warning(self, "Error", "Please fill in all fields.")
            return
        self.accept()
    def get_data(self):
        return {
            "ID": str(uuid.uuid4()),
            "Name": self.name.text().strip(),
            "Email": self.email.text().strip(),
            "Phone": self.phone.text().strip(),
            "Address": self.address.text().strip()
        }
