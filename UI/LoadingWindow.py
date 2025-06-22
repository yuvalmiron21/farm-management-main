from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QApplication
from PyQt5.QtGui import QFont, QPixmap, QMovie
from PyQt5.QtCore import Qt, QTimer, QSize, QThread, pyqtSignal
import os

class LoadingWorker(QThread):
    """Worker thread for loading operations"""
    progress_updated = pyqtSignal(int, str)
    loading_finished = pyqtSignal()
    
    def __init__(self, loading_steps):
        super().__init__()
        self.loading_steps = loading_steps
        
    def run(self):
        total_steps = len(self.loading_steps)
        for i, (step_name, step_duration) in enumerate(self.loading_steps):
            self.progress_updated.emit(
                int((i / total_steps) * 100), 
                f"Loading {step_name}..."
            )
            self.msleep(step_duration)
        
        self.progress_updated.emit(100, "Ready!")
        self.msleep(500)  # Show "Ready!" for half a second
        self.loading_finished.emit()

class LoadingWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Loading...")
        self.setFixedSize(400, 300)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.init_ui()
        
    def init_ui(self):
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Background frame
        self.background_frame = QWidget()
        self.background_frame.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #f8fafc, stop:1 #a5d6a7);
                border-radius: 20px;
                border: 2px solid #e0e0e0;
            }
        """)
        
        frame_layout = QVBoxLayout(self.background_frame)
        frame_layout.setContentsMargins(30, 30, 30, 30)
        frame_layout.setSpacing(25)
        
        # Logo
        logo_label = QLabel()
        logo_path = os.path.join(os.path.dirname(__file__), "logo_without_white.png")
        if os.path.exists(logo_path):
            pix = QPixmap(logo_path)
            pix = pix.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(pix)
        else:
            logo_label.setText("🍄")
            logo_label.setStyleSheet("color: #2e7d32; font-size: 48px;")
        logo_label.setAlignment(Qt.AlignCenter)
        frame_layout.addWidget(logo_label)
        
        # Title
        title_label = QLabel("Mushroom Farm Management")
        title_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title_label.setStyleSheet("color: #2e7d32;")
        title_label.setAlignment(Qt.AlignCenter)
        frame_layout.addWidget(title_label)
        
        # Loading animation
        self.loading_label = QLabel()
        self.loading_label.setAlignment(Qt.AlignCenter)
        
        # Try to load the mushroom loading GIF
        gif_path = os.path.join(os.path.dirname(__file__), "mushroom_loading.gif")
        if os.path.exists(gif_path):
            self.loading_movie = QMovie(gif_path)
            self.loading_movie.setScaledSize(QSize(60, 60))
            self.loading_movie.setCacheMode(QMovie.CacheAll)
            self.loading_movie.setSpeed(100)
            self.loading_label.setMovie(self.loading_movie)
            self.loading_movie.finished.connect(self.loading_movie.start)
        else:
            # Fallback to text animation
            self.loading_label.setText("Loading...")
            self.loading_label.setStyleSheet("""
                QLabel {
                    color: #2e7d32;
                    font-size: 18px;
                    font-weight: bold;
                }
            """)
            self.dots_timer = QTimer()
            self.dots_timer.timeout.connect(self.animate_dots)
            self.dots_count = 0
            self.dots_timer.start(500)
        
        frame_layout.addWidget(self.loading_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #e0e0e0;
                border-radius: 10px;
                text-align: center;
                background: #f8f9fa;
                height: 20px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #43a047, stop:1 #66bb6a);
                border-radius: 8px;
            }
        """)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        frame_layout.addWidget(self.progress_bar)
        
        # Status text
        self.status_label = QLabel("Initializing...")
        self.status_label.setFont(QFont("Segoe UI", 10))
        self.status_label.setStyleSheet("color: #666;")
        self.status_label.setAlignment(Qt.AlignCenter)
        frame_layout.addWidget(self.status_label)
        
        layout.addWidget(self.background_frame)
        
        # Center the window
        self.center_window()
        
    def center_window(self):
        """Center the window on the screen"""
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
        
    def animate_dots(self):
        """Animate loading dots"""
        self.dots_count = (self.dots_count + 1) % 4
        dots = "." * self.dots_count
        self.loading_label.setText(f"Loading{dots}")
        
    def start_loading(self, loading_steps):
        """Start the loading process with custom steps"""
        if hasattr(self, 'loading_movie'):
            self.loading_movie.start()
        
        self.worker = LoadingWorker(loading_steps)
        self.worker.progress_updated.connect(self.update_progress)
        self.worker.loading_finished.connect(self.loading_complete)
        self.worker.start()
        
    def update_progress(self, value, status):
        """Update progress bar and status text"""
        self.progress_bar.setValue(value)
        self.status_label.setText(status)
        QApplication.processEvents()  # Keep UI responsive
        
    def loading_complete(self):
        """Called when loading is complete"""
        if hasattr(self, 'loading_movie'):
            self.loading_movie.stop()
        if hasattr(self, 'dots_timer'):
            self.dots_timer.stop()
        self.close()
        
    def closeEvent(self, event):
        """Handle window close event"""
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
        if hasattr(self, 'dots_timer'):
            self.dots_timer.stop()
        event.accept()
        
    def auto_close(self, delay_ms=3000):
        """Automatically close the window after a delay"""
        QTimer.singleShot(delay_ms, self.close) 