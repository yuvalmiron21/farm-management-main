import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QHBoxLayout, QInputDialog, QHeaderView, QFrame, QSizePolicy,
    QLineEdit, QComboBox, QDialog, QFormLayout, QDialogButtonBox, QDateEdit, QDoubleSpinBox, QSpinBox,
    QCompleter
)
from PyQt5.QtCore import Qt, QTimer, QDate
from PyQt5.QtGui import QFont, QColor, QPalette
from firebase_admin import db
from db.cache_manager import CacheManager

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

        # --- Date range filter ---
        self.from_date = QDateEdit()
        self.from_date.setCalendarPopup(True)
        self.from_date.setDisplayFormat("yyyy-MM-dd")
        self.from_date.setDate(QDate(2000, 1, 1))
        self.from_date.setStyleSheet("padding: 8px; border-radius: 5px; border: 1px solid #dcdcdc; font-size: 14px;")
        self.from_date.dateChanged.connect(self.filter_orders)
        self.to_date = QDateEdit()
        self.to_date.setCalendarPopup(True)
        self.to_date.setDisplayFormat("yyyy-MM-dd")
        self.to_date.setDate(QDate.currentDate())
        self.to_date.setStyleSheet("padding: 8px; border-radius: 5px; border: 1px solid #dcdcdc; font-size: 14px;")
        self.to_date.dateChanged.connect(self.filter_orders)
        search_layout.addWidget(QLabel("From:"))
        search_layout.addWidget(self.from_date)
        search_layout.addWidget(QLabel("To:"))
        search_layout.addWidget(self.to_date)
        # --- End date range filter ---

        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.status_filter)
        self.layout.addLayout(search_layout)

        # Table
        self.order_table = QTableWidget()
        self.order_table.setColumnCount(5)
        self.order_table.setHorizontalHeaderLabels(["Order Key", "Customer ID", "Customer Name", "Order Date", "Total Amount", "Status"])
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
        self._cache_manager = CacheManager()
        self.load_orders()

    def load_orders(self):
        """Load orders to table"""
        self.order_table.setRowCount(0)
        self.all_orders.clear()
        self.filtered_orders.clear()
        
        try:
            orders_data = self._cache_manager.get_data('Order')
            print("Raw orders data from cache/Firebase:", orders_data)  # Debug print

            customers_data = self._cache_manager.get_data('Customer') or {}
            def get_customer_name(cid):
                for cust in customers_data.values():
                    if str(cust.get('ID', '')) == str(cid) or str(cust.get('CustomerID', '')) == str(cid):
                        return cust.get('Name', cust.get('FullName', ''))
                return ""

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
                        
                        customer_id = order_data.get('CustomerID', '')
                        customer_name = get_customer_name(customer_id)
                        
                        order_info = {
                            'key': key,
                            'customer_id': customer_id,
                            'customer_name': customer_name,
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
                                ref = db.reference('Order')
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
        """Filter orders based on search text, status, and date range"""
        search_text = self.search_input.text().lower()
        status_filter = self.status_filter.currentText()
        from_date = self.from_date.date().toString("yyyy-MM-dd")
        to_date = self.to_date.date().toString("yyyy-MM-dd")
        print(f"\nFiltering orders:")  # Debug print
        print(f"Search text: '{search_text}'")  # Debug print
        print(f"Status filter: '{status_filter}'")  # Debug print
        print(f"Date range: {from_date} to {to_date}")  # Debug print
        print(f"Total orders available: {len(self.all_orders)}")  # Debug print
        # Clear filtered orders
        self.filtered_orders = []
        # Apply filters
        for order in self.all_orders:
            matches_search = (
                search_text in str(order['key']).lower() or
                search_text in str(order['customer_id']).lower() or
                search_text in str(order.get('customer_name', '')).lower() or
                search_text in str(order['date']).lower() or
                search_text in str(order['amount']).lower() or
                search_text in str(order['status']).lower()
            )
            # חיפוש מתקדם: חיפוש תאריך מדויק או חלקי
            if search_text:
                if '-' in search_text and len(search_text) >= 8:
                    matches_search = matches_search or search_text in str(order['date']).lower()
            matches_status = (
                status_filter == "All Status" or
                status_filter.lower() == str(order['status']).lower()
            )
            # --- Date range filter ---
            order_date = order['date']
            in_date_range = True
            if order_date:
                in_date_range = (from_date <= order_date <= to_date)
            # --- End date range filter ---
            if matches_search and matches_status and in_date_range:
                self.filtered_orders.append(order)
        # Display filtered orders
        self.display_filtered_orders()

    def display_filtered_orders(self):
        """Display the filtered orders in the table"""
        self.order_table.setRowCount(0)
        for order in self.filtered_orders:
            self.add_order_to_table(order['key'], {
                'CustomerID': order['customer_id'],
                'CustomerName': order['customer_name'],
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
            order_data.get("CustomerName", ""),
            order_data.get("OrderDate", ""),
            f"₪{float(order_data.get('TotalAmount', 0)):.2f}",
            order_data.get("Status", "")
        ]
        
        for col, item_text in enumerate(items):
            item = QTableWidgetItem(str(item_text))
            item.setTextAlignment(Qt.AlignCenter)
            
            # Color-code the status
            if col == 5:  # Status column
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

    class AddOrderDialog(QDialog):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setWindowTitle("Add New Order")
            self.setMinimumWidth(500)
            self.setStyleSheet("""
                QDialog { background: #f8fafc; border-radius: 16px; }
                QLabel#titleLabel { font-size: 22px; font-weight: bold; color: #2c3e50; margin-bottom: 18px; }
                QFormLayout > QLabel { font-size: 15px; color: #222; min-width: 110px; }
                QSpinBox, QDateEdit, QDoubleSpinBox, QComboBox { font-size: 15px; padding: 7px 10px; border-radius: 7px; border: 1px solid #d0d7de; background: #fff; }
                QPushButton { min-width: 90px; min-height: 32px; font-size: 15px; border-radius: 8px; font-weight: bold; }
                QPushButton:enabled { background: #43a047; color: #fff; }
                QPushButton:enabled:hover { background: #388e3c; }
                QPushButton:disabled { background: #e0e0e0; color: #aaa; }
                QPushButton#Cancel { background: #e74c3c; color: #fff; }
                QPushButton#Cancel:hover { background: #c0392b; }
            """)
            layout = QVBoxLayout(self)
            # Title with icon
            title = QLabel("📦 Add New Order")
            title.setObjectName("titleLabel")
            title.setAlignment(Qt.AlignHCenter)
            layout.addWidget(title)
            # Fetch customers and products
            self.customers = self.fetch_customers()
            self.products = self.fetch_products()
            # Form
            form = QFormLayout()
            form.setSpacing(16)
            # Customer ComboBox
            self.customer_combo = QComboBox()
            self.customer_combo.setEditable(True)
            self.customer_combo.completer().setFilterMode(Qt.MatchContains)
            self.customer_combo.completer().setCompletionMode(QCompleter.PopupCompletion)
            if not self.customers:
                self.customer_combo.addItem("No customers found", None)
                self.customer_combo.setEnabled(False)
            else:
                for cid, name in self.customers.items():
                    self.customer_combo.addItem(f"{name} (ID: {cid})", cid)
            # --- כפתור הוסף לקוח חדש ---
            add_customer_btn = QPushButton("+ Add New Customer")
            add_customer_btn.setStyleSheet("padding: 7px 12px; border-radius: 7px; background: #43a047; color: #fff; font-size: 13px;")
            add_customer_btn.clicked.connect(self.add_new_customer_dialog)
            customer_row = QHBoxLayout()
            customer_row.addWidget(self.customer_combo)
            customer_row.addWidget(add_customer_btn)
            form.addRow("Customer:", customer_row)
            # Order Date
            self.order_date = QDateEdit()
            self.order_date.setCalendarPopup(True)
            self.order_date.setDate(QDate.currentDate())
            form.addRow("Order Date:", self.order_date)
            # Status
            self.status = QComboBox()
            self.status.addItems(["Pending", "Shipped", "Delivered", "Cancelled"])
            form.addRow("Status:", self.status)
            layout.addLayout(form)
            # Products Table
            prod_label = QLabel("Products:")
            prod_label.setStyleSheet("font-size: 15px; font-weight: bold; margin-top: 10px;")
            layout.addWidget(prod_label)
            self.product_table = QTableWidget(0, 3)
            self.product_table.setHorizontalHeaderLabels(["Product", "Quantity", "Unit Price"])
            self.product_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            self.product_table.verticalHeader().setVisible(False)
            layout.addWidget(self.product_table)
            # Add Product Button
            add_prod_btn = QPushButton("+ Add Product")
            add_prod_btn.clicked.connect(self.add_product_row)
            layout.addWidget(add_prod_btn)
            # Order Summary
            self.summary_label = QLabel()
            self.summary_label.setStyleSheet("font-size: 15px; margin-top: 10px; color: #2c3e50;")
            layout.addWidget(self.summary_label)
            self.product_table.cellChanged.connect(self.update_summary)
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
            self.add_product_row()  # Start with one row
            self.update_summary()
        def fetch_customers(self):
            ref = db.reference('Customer')
            customers = ref.get() or {}
            return {str(cid): cust.get('Name', str(cid)) for cid, cust in customers.items()}
        def fetch_products(self):
            ref = db.reference('Products')
            products = ref.get() or {}
            return {str(pid): prod.get('Name', str(pid)) for pid, prod in products.items()}
        def add_product_row(self):
            row = self.product_table.rowCount()
            self.product_table.insertRow(row)
            # Product ComboBox
            prod_combo = QComboBox()
            for pid, name in self.products.items():
                prod_combo.addItem(name, pid)
            self.product_table.setCellWidget(row, 0, prod_combo)
            # Quantity
            qty = QSpinBox()
            qty.setMinimum(1)
            qty.setMaximum(10000)
            qty.valueChanged.connect(self.update_summary)
            self.product_table.setCellWidget(row, 1, qty)
            # Unit Price
            price = QDoubleSpinBox()
            price.setMinimum(0.01)
            price.setMaximum(100000)
            price.setPrefix("₪")
            price.valueChanged.connect(self.update_summary)
            self.product_table.setCellWidget(row, 2, price)
        def update_summary(self):
            total = 0
            summary = []
            for row in range(self.product_table.rowCount()):
                prod_combo = self.product_table.cellWidget(row, 0)
                qty = self.product_table.cellWidget(row, 1)
                price = self.product_table.cellWidget(row, 2)
                if prod_combo and qty and price:
                    name = prod_combo.currentText()
                    q = qty.value()
                    p = price.value()
                    if q > 0 and p > 0:
                        total += q * p
                        summary.append(f"{name} x{q} @ ₪{p:.2f}")
            self.summary_label.setText(f"<b>Order Summary:</b> {'; '.join(summary)}<br><b>Total: ₪{total:.2f}</b>")
        def validate_and_accept(self):
            try:
                # בדוק שנבחר לקוח קיים
                if not self.customer_combo.isEnabled() or self.customer_combo.currentData() is None:
                    QMessageBox.warning(self, "Error", "Please select a valid customer.")
                    return
                # בדוק שיש לפחות מוצר אחד
                if self.product_table.rowCount() == 0:
                    QMessageBox.warning(self, "Error", "Please add at least one product.")
                    return
                found_valid_product = False
                for row in range(self.product_table.rowCount()):
                    prod_combo = self.product_table.cellWidget(row, 0)
                    qty = self.product_table.cellWidget(row, 1)
                    price = self.product_table.cellWidget(row, 2)
                    if not prod_combo or not qty or not price:
                        QMessageBox.warning(self, "Error", "Please fill all product details correctly.")
                        return
                    if qty.value() > 0 and price.value() > 0:
                        found_valid_product = True
                if not found_valid_product:
                    QMessageBox.warning(self, "Error", "Please enter valid quantity and price for at least one product.")
                    return
                # בדוק שהתאריך תקין
                if not self.order_date.date().isValid():
                    QMessageBox.warning(self, "Error", "Please select a valid order date.")
                    return
                # בדוק שסכום ההזמנה חיובי
                total = 0
                for row in range(self.product_table.rowCount()):
                    qty = self.product_table.cellWidget(row, 1)
                    price = self.product_table.cellWidget(row, 2)
                    if qty and price:
                        total += qty.value() * price.value()
                if total <= 0:
                    QMessageBox.warning(self, "Error", "Order total must be positive.")
                    return
                self.accept()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Validation error: {str(e)}")
                return
        def get_data(self):
            # Collect products
            products = []
            total = 0
            for row in range(self.product_table.rowCount()):
                prod_combo = self.product_table.cellWidget(row, 0)
                qty = self.product_table.cellWidget(row, 1)
                price = self.product_table.cellWidget(row, 2)
                pid = prod_combo.currentData()
                name = prod_combo.currentText()
                q = qty.value()
                p = price.value()
                products.append({"ProductID": pid, "Name": name, "Quantity": q, "UnitPrice": p})
                total += q * p
            return {
                "CustomerID": self.customer_combo.currentData(),
                "OrderDate": self.order_date.date().toString("yyyy-MM-dd"),
                "Status": self.status.currentText(),
                "Products": products,
                "TotalAmount": total
            }
        def add_new_customer_dialog(self):
            from Customer_gui import AddCustomerDialog
            dialog = AddCustomerDialog(self)
            if dialog.exec_() == QDialog.Accepted:
                data = dialog.get_data()
                try:
                    ref = db.reference('Customer')
                    ref.child(data["ID"]).set(data)
                    QMessageBox.information(self, "Success", "Customer added successfully!")
                    # טען מחדש את רשימת הלקוחות
                    self.customers = self.fetch_customers()
                    self.customer_combo.clear()
                    for cid, name in self.customers.items():
                        self.customer_combo.addItem(f"{name} (ID: {cid})", cid)
                    # בחר את הלקוח החדש
                    idx = self.customer_combo.findData(data["ID"])
                    if idx != -1:
                        self.customer_combo.setCurrentIndex(idx)
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to add customer: {str(e)}")

    def add_order(self):
        """Add a new order with a modern form dialog"""
        try:
            dialog = self.AddOrderDialog(self)
            if dialog.exec_() == QDialog.Accepted:
                data = dialog.get_data()
                # Validation
                if not data["CustomerID"] or not data["OrderDate"] or data["TotalAmount"] <= 0 or not data["Status"]:
                    QMessageBox.warning(self, "Error", "Please fill in all fields correctly.")
                    return
                ref = db.reference('Order')
                ref.push(data)
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
            current_customer_name = self.order_table.item(selected_row, 2).text()
            current_date = self.order_table.item(selected_row, 3).text()
            current_amount = float(self.order_table.item(selected_row, 4).text().replace('₪', ''))
            current_status = self.order_table.item(selected_row, 5).text()

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
                "CustomerName": current_customer_name,
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
