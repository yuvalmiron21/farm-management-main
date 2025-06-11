from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit, QComboBox, QMessageBox, QDialog)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from user_management import UserManagement

class UserManagementGUI(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QWidget {
                background: #f5f6fa;
            }
            QTableWidget {
                background: #fff;
                border-radius: 12px;
                border: 1px solid #e0e0e0;
                font-size: 15px;
                color: #222;
                gridline-color: #f0f0f0;
                alternate-background-color: #ececec;
            }
            QHeaderView::section {
                background: #e0e0e0;
                color: #222;
                font-size: 16px;
                font-weight: bold;
                border: none;
                border-bottom: 2px solid #bdbdbd;
                padding: 10px 0;
            }
            QPushButton {
                background: #43a047;
                color: #fff;
                border-radius: 8px;
                padding: 6px 16px;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #388e3c;
            }
        """)
        self.init_ui()
        self.load_users()

    def init_ui(self):
        layout = QVBoxLayout(self)
        header = QLabel("User Management")
        header.setFont(QFont("Segoe UI", 20, QFont.Bold))
        header.setStyleSheet("color: #23272e; margin-bottom: 10px;")
        layout.addWidget(header)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Username", "Role", "Edit", "Delete"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        # Add user section
        add_layout = QHBoxLayout()
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.role_combo = QComboBox()
        self.role_combo.addItems(["user", "admin"])
        add_btn = QPushButton("Add User")
        add_btn.clicked.connect(self.add_user)
        add_layout.addWidget(self.username_input)
        add_layout.addWidget(self.password_input)
        add_layout.addWidget(self.role_combo)
        add_layout.addWidget(add_btn)
        layout.addLayout(add_layout)

    def load_users(self):
        users = UserManagement.get_all_users()
        self.table.setRowCount(len(users))
        for row, (uid, username, role) in enumerate(users):
            self.table.setItem(row, 0, QTableWidgetItem(username))
            self.table.setItem(row, 1, QTableWidgetItem(role))
            # Edit button
            edit_btn = QPushButton("Edit")
            edit_btn.clicked.connect(lambda _, u=uid, n=username, r=role: self.edit_user(u, n, r))
            self.table.setCellWidget(row, 2, edit_btn)
            # Delete button
            del_btn = QPushButton("Delete")
            del_btn.setStyleSheet("background: #e74c3c; color: #fff; border-radius: 8px;")
            del_btn.clicked.connect(lambda _, u=uid: self.delete_user(u))
            self.table.setCellWidget(row, 3, del_btn)

    def add_user(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        role = self.role_combo.currentText()
        if not username or not password:
            QMessageBox.warning(self, "Error", "Please enter username and password.")
            return
        success, msg = UserManagement.add_user(username, password, role)
        if success:
            QMessageBox.information(self, "Success", msg)
            self.username_input.clear()
            self.password_input.clear()
            self.load_users()
        else:
            QMessageBox.warning(self, "Error", msg)

    def delete_user(self, uid):
        reply = QMessageBox.question(self, "Delete User", "Are you sure you want to delete this user?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            UserManagement.delete_user(uid)
            self.load_users()

    def edit_user(self, uid, username, role):
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit User")
        layout = QVBoxLayout(dialog)
        username_edit = QLineEdit(username)
        role_combo = QComboBox()
        role_combo.addItems(["user", "admin"])
        role_combo.setCurrentText(role)
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(lambda: self.save_edit_user(dialog, uid, username_edit.text(), role_combo.currentText()))
        layout.addWidget(QLabel("Username:"))
        layout.addWidget(username_edit)
        layout.addWidget(QLabel("Role:"))
        layout.addWidget(role_combo)
        layout.addWidget(save_btn)
        dialog.exec_()

    def save_edit_user(self, dialog, uid, username, role):
        if not username:
            QMessageBox.warning(self, "Error", "Username cannot be empty.")
            return
        UserManagement.update_user(uid, username, role)
        dialog.accept()
        self.load_users() 