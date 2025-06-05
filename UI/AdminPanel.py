from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QHBoxLayout, QLineEdit, QComboBox, QMessageBox
from user_db import get_all_users, add_user, delete_user, update_user

class AdminPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Admin Panel")
        layout = QVBoxLayout(self)
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Username", "Role", "Actions"])
        layout.addWidget(self.table)
        self.refresh_table()

        # Add user form
        form = QHBoxLayout()
        self.new_username = QLineEdit()
        self.new_username.setPlaceholderText("Username")
        self.new_password = QLineEdit()
        self.new_password.setPlaceholderText("Password")
        self.new_password.setEchoMode(QLineEdit.Password)
        self.new_role = QComboBox()
        self.new_role.addItems(["user", "admin"])
        add_btn = QPushButton("Add User")
        add_btn.clicked.connect(self.add_user)
        form.addWidget(self.new_username)
        form.addWidget(self.new_password)
        form.addWidget(self.new_role)
        form.addWidget(add_btn)
        layout.addLayout(form)

    def refresh_table(self):
        users = get_all_users()
        self.table.setRowCount(len(users))
        for i, (uid, uname, role) in enumerate(users):
            self.table.setItem(i, 0, QTableWidgetItem(str(uid)))
            self.table.setItem(i, 1, QTableWidgetItem(uname))
            self.table.setItem(i, 2, QTableWidgetItem(role))
            del_btn = QPushButton("Delete")
            del_btn.clicked.connect(lambda _, uid=uid: self.delete_user(uid))
            self.table.setCellWidget(i, 3, del_btn)

    def add_user(self):
        uname = self.new_username.text()
        pwd = self.new_password.text()
        role = self.new_role.currentText()
        if not uname or not pwd:
            QMessageBox.warning(self, "Error", "Username and password required")
            return
        ok, msg = add_user(uname, pwd, role)
        if ok:
            QMessageBox.information(self, "Success", msg)
            self.refresh_table()
        else:
            QMessageBox.warning(self, "Error", msg)

    def delete_user(self, uid):
        delete_user(uid)
        self.refresh_table() 