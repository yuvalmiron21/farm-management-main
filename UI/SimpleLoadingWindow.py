from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QGraphicsDropShadowEffect
from PyQt5.QtGui import QMovie, QPixmap, QColor, QFontDatabase, QFont
from PyQt5.QtCore import Qt, QTimer, QSize
import os

class SimpleLoadingWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Loading...")
        self.setFixedSize(450, 300)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)  # Enable transparency for shadow

        # Font
        font_path = os.path.join(os.path.dirname(__file__), "fonts", "Outfit-VariableFont_wght.ttf")
        if os.path.exists(font_path):
            font_id = QFontDatabase.addApplicationFont(font_path)
            if font_id != -1:
                font_families = QFontDatabase.applicationFontFamilies(font_id)
                if font_families:
                    self.outfit_font = QFont(font_families[0])

        # Main background widget
        self.background_widget = QWidget(self)
        self.background_widget.setGeometry(10, 10, self.width() - 20, self.height() - 20)
        
        self.background_widget.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #f0f4f0, stop:1 #e0e8e0); /* Softer, elegant gradient */
                border-radius: 15px;
            }
        """)

        # Drop Shadow Effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(5)
        shadow.setColor(QColor(0, 0, 0, 50))
        self.background_widget.setGraphicsEffect(shadow)
        
        # Layout for content
        content_layout = QVBoxLayout(self.background_widget)
        content_layout.setContentsMargins(30, 30, 30, 30)
        content_layout.setSpacing(20)
        content_layout.setAlignment(Qt.AlignCenter)

        # Logo
        logo_label = QLabel()
        logo_label.setStyleSheet("border: none; background: transparent;")
        logo_path = os.path.join(os.path.dirname(__file__), "logo_without_white.png")
        if os.path.exists(logo_path):
            pix = QPixmap(logo_path)
            pix = pix.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(pix)
        else:
            logo_label.setText("🍄")
        logo_label.setAlignment(Qt.AlignCenter)
        
        # Loading GIF
        self.movie_label = QLabel()
        self.movie_label.setStyleSheet("border: none; background: transparent;")
        self.movie_label.setAlignment(Qt.AlignCenter)
        gif_path = os.path.join(os.path.dirname(__file__), "mushroom_loading.gif")
        if os.path.exists(gif_path):
            self.movie = QMovie(gif_path)
            self.movie.setScaledSize(QSize(80, 80))  # Use a fixed size for the GIF
            self.movie_label.setMovie(self.movie)
            self.movie.start()
            self.movie.finished.connect(self.movie.start) # Loop the GIF
        else:
            self.movie_label.setText("Loading...")
        
        # Loading Text
        text_label = QLabel("Loading System...")
        text_label.setStyleSheet("color: #333; border: none; background: transparent;")
        if hasattr(self, 'outfit_font'):
            self.outfit_font.setPointSize(18)
            text_label.setFont(self.outfit_font)
        text_label.setAlignment(Qt.AlignCenter)
        
        content_layout.addWidget(logo_label)
        content_layout.addWidget(self.movie_label)
        content_layout.addWidget(text_label)

        # Auto-close timer
        QTimer.singleShot(5000, self.close)

    def closeEvent(self, event):
        if hasattr(self, 'movie') and self.movie.state() == QMovie.Running:
            self.movie.stop()
        super().closeEvent(event)