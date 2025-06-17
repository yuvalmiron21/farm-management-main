from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit
from PyQt5.QtCore import Qt

class DecisionTreeInsightsGUI(QWidget):
    def __init__(self, batches=None, logs=None, parent=None):
        super().__init__(parent)
        self.batches = batches
        self.logs = logs
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        title = QLabel("Decision Tree Insights")
        title.setAlignment(Qt.AlignHCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 12px;")
        layout.addWidget(title)

        # Placeholder for future decision tree visualization
        info = QTextEdit()
        info.setReadOnly(True)
        info.setStyleSheet("background: #f7f7f7; border-radius: 8px; font-size: 14px;")
        info.setText("""
This section will display insights from a Decision Tree model based on your batches and logs data.

- Number of batches: {}
- Number of logs: {}

(Visualization and detailed insights coming soon!)
""".format(len(self.batches) if self.batches else 0, len(self.logs) if self.logs else 0))
        layout.addWidget(info)
        layout.addStretch() 