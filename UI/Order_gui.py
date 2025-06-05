from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QHBoxLayout, QInputDialog, QHeaderView, QFrame, QSizePolicy,
    QLineEdit, QComboBox
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor, QPalette
from firebase_admin import db

class OrderGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Order Management")
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
                background-color: #3498db;
                color: white;
                border: none;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
                min-width: 150px;
            }
            QPushButton:hover {
                background-color: #2980b9;
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
                background-color: #3498db;
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
        self.title = QLabel("📦 Manage Orders")
        self.title.setFont(QFont("Arial", 24, QFont.Bold))
        header_layout.addWidget(self.title)
        header_layout.addStretch()
        self.layout.addLayout(header_layout)

        # Search bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search orders...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                border: 1px solid #dcdcdc;
                border-radius: 5px;
                font-size: 14px;
            }
        """)
        self.search_input.textChanged.connect(self.filter_orders)
        
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All Status", "Pending", "Shipped", "Delivered", "Cancelled"])
        self.status_filter.setStyleSheet("""
            QComboBox {
                padding: 10px;
                border: 1px solid #dcdcdc;
                border-radius: 5px;
                font-size: 14px;
                min-width: 150px;
            }
        """)
        self.status_filter.currentTextChanged.connect(self.filter_orders)
        
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.status_filter)
        self.layout.addLayout(search_layout)

        # Table
        self.order_table = QTableWidget()
        self.order_table.setColumnCount(5)
        self.order_table.setHorizontalHeaderLabels(["Order Key", "Customer ID", "Order Date", "Total Amount", "Status"])
        self.order_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.order_table.setAlternatingRowColors(True)
        self.order_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.order_table.setSelectionMode(QTableWidget.SingleSelection)
        self.order_table.verticalHeader().setVisible(False)
        self.layout.addWidget(self.order_table)

        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.add_order_button = QPushButton("➕ Add New Order")
        self.add_order_button.clicked.connect(self.add_order)
        button_layout.addWidget(self.add_order_button)

        self.update_order_button = QPushButton("✏️ Update Order")
        self.update_order_button.clicked.connect(self.update_order)
        button_layout.addWidget(self.update_order_button)

        self.delete_order_button = QPushButton("🗑️ Delete Order")
        self.delete_order_button.setObjectName("deleteButton")
        self.delete_order_button.clicked.connect(self.delete_order)
        button_layout.addWidget(self.delete_order_button)

        self.layout.addLayout(button_layout)

        # Set main layout
        self.setLayout(self.layout)

        # Initialize orders storage
        self.all_orders = []
        self.filtered_orders = []

        # Load initial data
        self.load_orders()

    def load_orders(self):
        """Load orders to table"""
        self.order_table.setRowCount(0)
        self.all_orders.clear()
        self.filtered_orders.clear()
        
        try:
            ref = db.reference('Order')
            orders_data = ref.get()

            print("Raw orders data from Firebase:", orders_data)  # Debug print

            if not orders_data:
                print("No orders found in database")  # Debug print
                return

            if isinstance(orders_data, dict):
                for key, order_data in orders_data.items():
                    if isinstance(order_data, dict):
                        # Ensure status exists and is valid
                        status = order_data.get('Status', '')
                        if not status:
                            status = 'Pending'  # Default status if none exists
                        
                        # Normalize status to match our valid statuses
                        valid_statuses = ["Pending", "Shipped", "Delivered", "Cancelled"]
                        status = next((s for s in valid_statuses if s.lower() == status.lower()), status)
                        
                        order_info = {
                            'key': key,
                            'customer_id': order_data.get('CustomerID', ''),
                            'date': order_data.get('OrderDate', ''),
                            'amount': order_data.get('TotalAmount', ''),
                            'status': status
                        }
                        print(f"Processing order: {order_info}")  # Debug print
                        self.all_orders.append(order_info)
                        self.filtered_orders.append(order_info)  # Initially, filtered orders = all orders
                        
                        # Update the order in Firebase if status was normalized
                        if status != order_data.get('Status', ''):
                            try:
                                ref.child(key).update({'Status': status})
                                print(f"Updated order {key} status to {status}")  # Debug print
                            except Exception as e:
                                print(f"Failed to update order {key} status: {e}")  # Debug print
                
                # Display all orders initially
                self.display_filtered_orders()
                
        except Exception as e:
            print(f"Error loading orders: {e}")  # Debug print
            QMessageBox.critical(self, "Error", f"Failed to load orders: {str(e)}")

    def filter_orders(self):
        """Filter orders based on search text and status"""
        search_text = self.search_input.text().lower()
        status_filter = self.status_filter.currentText()
        
        print(f"\nFiltering orders:")  # Debug print
        print(f"Search text: '{search_text}'")  # Debug print
        print(f"Status filter: '{status_filter}'")  # Debug print
        print(f"Total orders available: {len(self.all_orders)}")  # Debug print
        
        # Clear filtered orders
        self.filtered_orders = []
        
        # Apply filters
        for order in self.all_orders:
            matches_search = (
                search_text in str(order['key']).lower() or
                search_text in str(order['customer_id']).lower() or
                search_text in str(order['date']).lower() or
                search_text in str(order['amount']).lower() or
                search_text in str(order['status']).lower()
            )
            
            matches_status = (
                status_filter == "All Status" or
                status_filter.lower() == str(order['status']).lower()
            )
            
            print(f"Order {order['key']}:")  # Debug print
            print(f"  Status: '{order['status']}'")  # Debug print
            print(f"  Matches search: {matches_search}")  # Debug print
            print(f"  Matches status: {matches_status}")  # Debug print
            
            if matches_search and matches_status:
                print(f"  -> Adding to filtered list")  # Debug print
                self.filtered_orders.append(order)
        
        # Display filtered orders
        self.display_filtered_orders()

    def display_filtered_orders(self):
        """Display the filtered orders in the table"""
        self.order_table.setRowCount(0)
        for order in self.filtered_orders:
            self.add_order_to_table(order['key'], {
                'CustomerID': order['customer_id'],
                'OrderDate': order['date'],
                'TotalAmount': order['amount'],
                'Status': order['status']
            })

    def add_order_to_table(self, order_key, order_data):
        """Add an order to the table with styling"""
        row_position = self.order_table.rowCount()
        self.order_table.insertRow(row_position)
        
        # Add items with center alignment
        items = [
            order_key,
            str(order_data.get("CustomerID", "")),
            order_data.get("OrderDate", ""),
            f"₪{float(order_data.get('TotalAmount', 0)):.2f}",
            order_data.get("Status", "")
        ]
        
        for col, item_text in enumerate(items):
            item = QTableWidgetItem(str(item_text))
            item.setTextAlignment(Qt.AlignCenter)
            
            # Color-code the status
            if col == 4:  # Status column
                status_colors = {
                    "Pending": "#f1c40f",    # Yellow
                    "Shipped": "#3498db",    # Blue
                    "Delivered": "#2ecc71",  # Green
                    "Cancelled": "#e74c3c"   # Red
                }
                color = status_colors.get(item_text, "#95a5a6")
                item.setBackground(QColor(color))
                item.setForeground(QColor("white"))
                item.setFont(QFont("Arial", weight=QFont.Bold))
            
            self.order_table.setItem(row_position, col, item)

    def add_order(self):
        """Add a new order with improved input dialog"""
        try:
            customer_id, ok = QInputDialog.getInt(self, "Add Order", "Enter Customer ID:", min=1)
            if not ok:
                return
                
            order_date, ok = QInputDialog.getText(self, "Add Order", "Enter Order Date (YYYY-MM-DD):")
            if not ok:
                return
                
            total_amount, ok = QInputDialog.getDouble(self, "Add Order", "Enter Total Amount (₪):", min=0.01)
            if not ok:
                return
                
            status_dialog = QInputDialog(self)
            status_dialog.setComboBoxItems(["Pending", "Shipped", "Delivered", "Cancelled"])
            status_dialog.setWindowTitle("Add Order")
            status_dialog.setLabelText("Select Status:")
            if status_dialog.exec_() != QInputDialog.Accepted:
                return
            status = status_dialog.textValue()

            new_order = {
                "CustomerID": customer_id,
                "OrderDate": order_date,
                "TotalAmount": total_amount,
                "Status": status
            }

            ref = db.reference('Order')
            new_order_ref = ref.push(new_order)
            
            QMessageBox.information(self, "Success", "Order added successfully!")
            self.load_orders()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to add order: {str(e)}")

    def update_order(self):
        """Update the selected order with improved input dialog"""
        selected_row = self.order_table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Error", "Please select an order to update.")
            return

        try:
            order_key = self.order_table.item(selected_row, 0).text()
            current_customer_id = int(self.order_table.item(selected_row, 1).text())
            current_date = self.order_table.item(selected_row, 2).text()
            current_amount = float(self.order_table.item(selected_row, 3).text().replace('₪', ''))
            current_status = self.order_table.item(selected_row, 4).text()

            customer_id, ok = QInputDialog.getInt(self, "Update Order", "Enter Customer ID:", value=current_customer_id, min=1)
            if not ok:
                return
                
            order_date, ok = QInputDialog.getText(self, "Update Order", "Enter Order Date:", text=current_date)
            if not ok:
                return
                
            total_amount, ok = QInputDialog.getDouble(self, "Update Order", "Enter Total Amount (₪):", value=current_amount, min=0.01)
            if not ok:
                return
                
            status_dialog = QInputDialog(self)
            status_dialog.setComboBoxItems(["Pending", "Shipped", "Delivered", "Cancelled"])
            status_dialog.setWindowTitle("Update Order")
            status_dialog.setLabelText("Select Status:")
            status_dialog.setTextValue(current_status)
            if status_dialog.exec_() != QInputDialog.Accepted:
                return
            status = status_dialog.textValue()

            updated_order = {
                "CustomerID": customer_id,
                "OrderDate": order_date,
                "TotalAmount": total_amount,
                "Status": status
            }

            ref = db.reference(f'Order/{order_key}')
            ref.update(updated_order)
            
            QMessageBox.information(self, "Success", "Order updated successfully!")
            self.load_orders()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to update order: {str(e)}")

    def delete_order(self):
        """Delete the selected order with confirmation"""
        selected_row = self.order_table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Error", "Please select an order to delete.")
            return

        try:
            order_key = self.order_table.item(selected_row, 0).text()
            
            confirm = QMessageBox()
            confirm.setIcon(QMessageBox.Warning)
            confirm.setText("Are you sure you want to delete this order?")
            confirm.setWindowTitle("Confirm Deletion")
            confirm.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            confirm.setDefaultButton(QMessageBox.No)
            
            if confirm.exec_() == QMessageBox.Yes:
                ref = db.reference(f'Order/{order_key}')
                ref.delete()
                QMessageBox.information(self, "Success", "Order deleted successfully!")
                self.load_orders()
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete order: {str(e)}")
