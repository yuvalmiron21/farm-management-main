import sys
import os
from PyQt5.QtWidgets import (
    QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel, 
    QPushButton, QScrollArea, QSplitter, QFrame, QGridLayout, 
    QApplication, QTabWidget, QProgressBar, QDialog, QTextBrowser
)
from PyQt5.QtCore import Qt, QSize, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPixmap, QIcon, QColor
import io
import base64
from datetime import datetime

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from models.insights_engine import InsightsEngine

class InsightsLoadThread(QThread):
    """Thread for loading insights in the background"""
    finished = pyqtSignal(object)
    progress = pyqtSignal(int)
    
    def __init__(self, batches, logs):
        super().__init__()
        self.batches = batches
        self.logs = logs
        
    def run(self):
        # Show progress while analyzing
        self.progress.emit(10)
        engine = InsightsEngine(self.batches, self.logs)
        self.progress.emit(40)
        
        # Generate insights
        engine.generate_insights()
        self.progress.emit(80)
        
        # Signal that we're done
        self.finished.emit(engine)
        self.progress.emit(100)

class PopupWindow(QDialog):
    """Window for displaying a larger visualization or explanation"""
    def __init__(self, content, title="Visualization", parent=None, is_text=False):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(800, 600)
        
        layout = QVBoxLayout(self)
        
        if is_text:
            text_browser = QTextBrowser()
            text_browser.setHtml(content)
            layout.addWidget(text_browser)
        else:
            # For image content
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            
            image_label = QLabel()
            image_label.setPixmap(content)
            image_label.setAlignment(Qt.AlignCenter)
            image_label.setStyleSheet("background-color: white;")
            
            scroll.setWidget(image_label)
            layout.addWidget(scroll)
        
        # Add close button at bottom
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)

class AlgorithmExplanationPopup(QDialog):
    """Dialog window for displaying algorithm explanations"""
    def __init__(self, title, algorithm_details, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"How It Works: {title}")
        self.resize(600, 400)
        
        layout = QVBoxLayout(self)
        
        # Style
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1a2e;
            }
            QLabel {
                color: white;
                font-size: 14px;
            }
            QLabel#title {
                font-size: 18px;
                font-weight: bold;
                color: #3498db;
            }
            QTextBrowser {
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
                border: 1px solid #3498db;
                border-radius: 5px;
                padding: 10px;
                font-size: 14px;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3498db, stop:1 #2980b9);
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
            }
        """)
        
        # Title
        title_label = QLabel(title)
        title_label.setObjectName("title")
        layout.addWidget(title_label)
        
        # Algorithm name
        algo_name = QLabel(f"Algorithm: {algorithm_details['name']}")
        layout.addWidget(algo_name)
        
        # Features used
        features_label = QLabel("Features Used:")
        layout.addWidget(features_label)
        
        features_text = QTextBrowser()
        features_text.setText(algorithm_details['features'])
        features_text.setMaximumHeight(60)
        layout.addWidget(features_text)
        
        # Description
        desc_label = QLabel("How It Works:")
        layout.addWidget(desc_label)
        
        desc_text = QTextBrowser()
        desc_text.setText(algorithm_details['description'])
        layout.addWidget(desc_text)
        
        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button, alignment=Qt.AlignRight)

class InsightCard(QFrame):
    """Widget for displaying a single insight with title and description"""
    def __init__(self, insight_data, parent=None):
        super().__init__(parent)
        self.insight_data = insight_data
        self.init_ui()
        
    def init_ui(self):
        # Set up card styling
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 10px;
                margin: 5px;
            }
            QLabel#title {
                font-weight: bold;
                font-size: 16px;
                color: #3498db;
                margin-bottom: 5px;
            }
            QLabel#description {
                font-size: 14px;
                color: white;
                line-height: 1.4;
            }
        """)
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Add icon based on insight type
        header_layout = QHBoxLayout()
        
        # Set icon based on type
        icon_label = QLabel()
        icon_label.setFixedSize(24, 24)
        
        icon_map = {
            'yield_factor': '🔍',
            'guidance': '⭐',
            'optimal_condition': '✅',
            'bagging': '📦',
            'harvesting': '🍄',
            'seasonal': '🌡️',
            'warning': '⚠️'
        }
        
        icon = icon_map.get(self.insight_data['type'], '💡')
        icon_label.setText(f"<span style='font-size:18px'>{icon}</span>")
        
        # Title
        title_label = QLabel(self.insight_data['title'])
        title_label.setObjectName("title")
        
        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        # Description
        description_label = QLabel(self.insight_data['description'])
        description_label.setObjectName("description")
        description_label.setWordWrap(True)
        
        layout.addLayout(header_layout)
        layout.addWidget(description_label)
        
class InsightCardWithDetails(InsightCard):
    """Extended insight card with 'How it works' button"""
    def __init__(self, insight_data, parent=None, insights_engine=None, main_view=None):
        super().__init__(insight_data, parent)
        self.insights_engine = insights_engine
        self.insight_data = insight_data
        self.main_view = main_view
        
        # Create button layout
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # Add visualization button for relevant insights
        if main_view and hasattr(main_view, 'tabs'):
            # Map insight types to visualization tabs
            viz_mapping = {
                'yield_factor': self.show_feature_importance,
                'optimal_condition': self.show_feature_importance,
                'harvesting': self.show_harvest_timeline,
                'seasonal': self.show_seasonal_patterns,
                'bagging': self.show_decision_tree
            }
            
            if insight_data['type'] in viz_mapping:
                viz_button = QPushButton("See Visualization")
                viz_button.setFixedWidth(140)
                viz_button.setStyleSheet("""
                    QPushButton {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                            stop:0 #9b59b6, stop:1 #8e44ad);
                        color: white;
                        border: none;
                        border-radius: 4px;
                        padding: 5px;
                        font-size: 12px;
                    }
                """)
                viz_button.clicked.connect(viz_mapping[insight_data['type']])
                button_layout.addWidget(viz_button)
        
        # Add 'How it works' button
        if insights_engine and hasattr(insights_engine, 'get_algorithm_details'):
            info_button = QPushButton("How it works")
            info_button.setFixedWidth(120)
            info_button.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #16a085, stop:1 #1abc9c);
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 5px;
                    font-size: 12px;
                }
            """)
            info_button.clicked.connect(self.show_algorithm_details)
            button_layout.addWidget(info_button)
        
        # Add to layout
        self.layout().addLayout(button_layout)
    
    def show_algorithm_details(self):
        """Show popup with algorithm details"""
        if not self.insights_engine:
            return
            
        algo_details = self.insights_engine.get_algorithm_details(self.insight_data['type'])
        if not algo_details:
            algo_details = self.insights_engine.get_algorithm_details('yield_factor')  # Fallback
        
        popup = AlgorithmExplanationPopup(self.insight_data['title'], algo_details, self)
        popup.exec_()
        
    def show_feature_importance(self):
        """Jump to feature importance visualization"""
        if self.main_view and hasattr(self.main_view, 'tabs'):
            self.main_view.tabs.setCurrentIndex(3)  # Visualizations tab
            # Scroll to feature importance section
            self.main_view.scroll_to_section("feature_importance")
    
    def show_harvest_timeline(self):
        """Jump to harvest timeline visualization"""
        if self.main_view and hasattr(self.main_view, 'tabs'):
            self.main_view.tabs.setCurrentIndex(3)  # Visualizations tab
            # Scroll to harvest timeline section
            self.main_view.scroll_to_section("harvest_timeline")
    
    def show_seasonal_patterns(self):
        """Jump to seasonal patterns visualization"""
        if self.main_view and hasattr(self.main_view, 'tabs'):
            self.main_view.tabs.setCurrentIndex(3)  # Visualizations tab
            # Scroll to seasonal patterns section
            self.main_view.scroll_to_section("seasonal")
    
    def show_decision_tree(self):
        """Jump to decision tree visualization"""
        if self.main_view and hasattr(self.main_view, 'tabs'):
            self.main_view.tabs.setCurrentIndex(3)  # Visualizations tab
            # Scroll to decision tree section
            self.main_view.scroll_to_section("decision_tree")

class InsightsView(QMainWindow):
    """Main window for displaying farm analytics insights"""
    def __init__(self, batches, logs):
        super().__init__()
        self.batches = batches
        self.logs = logs
        self.insights_engine = None
        self.setWindowTitle("MUSH - Farm Insights")
        self.setMinimumSize(1200, 800)
        
        # Set dark theme
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #1a1a2e;
                color: #ffffff;
            }
            QLabel {
                font-size: 14px;
                color: #ffffff;
            }
            QLabel#title {
                font-size: 28px;
                font-weight: bold;
                color: #ffffff;
                padding: 20px 0;
            }
            QLabel#summary {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #2c3e50, stop:1 #3498db);
                border-radius: 10px;
                padding: 20px;
                margin: 10px;
                font-size: 16px;
                line-height: 1.4;
            }
            QLabel#section_title {
                font-size: 20px;
                font-weight: bold;
                color: #3498db;
                padding: 10px 0;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3498db, stop:1 #2980b9);
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
                min-width: 120px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3498db, stop:1 #2475a8);
            }
            QPushButton#backButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #e74c3c, stop:1 #c0392b);
            }
            QPushButton#backButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #c0392b, stop:1 #a93226);
            }
            QProgressBar {
                border: 1px solid #3498db;
                border-radius: 5px;
                text-align: center;
                background-color: #1a1a2e;
                min-height: 20px;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                width: 10px;
                margin: 0.5px;
            }
            QTabWidget::pane {
                border: 1px solid #3498db;
                background-color: #1a1a2e;
                border-radius: 5px;
            }
            QTabBar::tab {
                background: rgba(52, 152, 219, 0.2);
                color: white;
                padding: 10px 15px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: #3498db;
                color: white;
            }
            QTabBar::tab:hover {
                background: rgba(52, 152, 219, 0.5);
            }
        """)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)
        
        # Header with back button and title
        header_layout = QHBoxLayout()
        
        # Back button
        back_button = QPushButton("← Back to Analytics")
        back_button.setObjectName("backButton")
        back_button.clicked.connect(self.close)
        back_button.setFixedWidth(200)
        header_layout.addWidget(back_button)
        
        # Title
        title_label = QLabel("🔮 Farm Insights & Recommendations")
        title_label.setObjectName("title")
        title_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(title_label)
        
        # Add stretch to keep title centered
        header_layout.insertStretch(0)
        header_layout.addStretch()
        
        main_layout.addLayout(header_layout)
        
        # Loading indicators
        self.loading_layout = QVBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        
        loading_label = QLabel("Analyzing your farm data to generate insights...")
        loading_label.setAlignment(Qt.AlignCenter)
        
        self.loading_layout.addWidget(loading_label)
        self.loading_layout.addWidget(self.progress_bar)
        
        main_layout.addLayout(self.loading_layout)
        
        # Content layout (hidden until insights are loaded)
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setSpacing(20)
        
        # Summary section
        self.summary_label = QLabel()
        self.summary_label.setObjectName("summary")
        self.summary_label.setWordWrap(True)
        self.content_layout.addWidget(self.summary_label)
        
        # Tabs for different types of insights
        self.tabs = QTabWidget()
        
        # Create tab for each section
        self.yield_factors_tab = QWidget()
        self.optimal_conditions_tab = QWidget()
        self.timelines_tab = QWidget()
        self.visualizations_tab = QWidget()
        
        # Set up tab layouts
        self.setup_yield_factors_tab()
        self.setup_optimal_conditions_tab()
        self.setup_timelines_tab()
        self.setup_visualizations_tab()
        
        # Add tabs to widget
        self.tabs.addTab(self.yield_factors_tab, "Yield Factors")
        self.tabs.addTab(self.optimal_conditions_tab, "Optimal Conditions")
        self.tabs.addTab(self.timelines_tab, "Growth Timelines")
        self.tabs.addTab(self.visualizations_tab, "Visualizations")
        
        self.content_layout.addWidget(self.tabs)
        
        # Add last updated time
        self.update_time_label = QLabel()
        self.update_time_label.setAlignment(Qt.AlignRight)
        self.content_layout.addWidget(self.update_time_label)
        
        # Add content widget to main layout but hide it initially
        main_layout.addWidget(self.content_widget)
        self.content_widget.hide()
        
        # Start insight generation in background
        self.load_insights()
    
    def setup_yield_factors_tab(self):
        """Set up the yield factors tab"""
        layout = QVBoxLayout(self.yield_factors_tab)
        
        # Scrollable area for cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        
        # Container for cards
        self.yield_factors_container = QWidget()
        self.yield_factors_layout = QVBoxLayout(self.yield_factors_container)
        self.yield_factors_layout.setAlignment(Qt.AlignTop)
        self.yield_factors_layout.setSpacing(15)
        
        # Add to scroll area
        scroll.setWidget(self.yield_factors_container)
        layout.addWidget(scroll)
    
    def setup_optimal_conditions_tab(self):
        """Set up the optimal conditions tab"""
        layout = QVBoxLayout(self.optimal_conditions_tab)
        
        # Scrollable area for cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        
        # Container for cards
        self.optimal_conditions_container = QWidget()
        self.optimal_conditions_layout = QVBoxLayout(self.optimal_conditions_container)
        self.optimal_conditions_layout.setAlignment(Qt.AlignTop)
        self.optimal_conditions_layout.setSpacing(15)
        
        # Add to scroll area
        scroll.setWidget(self.optimal_conditions_container)
        layout.addWidget(scroll)
    
    def setup_timelines_tab(self):
        """Set up the growth timelines tab"""
        layout = QVBoxLayout(self.timelines_tab)
        
        # Scrollable area for cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        
        # Container for cards
        self.timelines_container = QWidget()
        self.timelines_layout = QVBoxLayout(self.timelines_container)
        self.timelines_layout.setAlignment(Qt.AlignTop)
        self.timelines_layout.setSpacing(15)
        
        # Add to scroll area
        scroll.setWidget(self.timelines_container)
        layout.addWidget(scroll)
    
    def setup_visualizations_tab(self):
        """Set up visualizations tab with all data visualizations"""
        # Create scrollable area for visualizations
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(20)
        
        # Feature importance section
        self.feature_importance_label = QLabel("📊 Feature Importance")
        self.feature_importance_label.setObjectName("section_title")
        layout.addWidget(self.feature_importance_label)
        
        self.feature_importance_desc = QLabel("This chart shows which factors have the greatest impact on your mushroom yields.")
        self.feature_importance_desc.setWordWrap(True)
        layout.addWidget(self.feature_importance_desc)
        
        # Container for feature importance chart
        self.feature_importance_container = QWidget()
        self.feature_importance_container.setStyleSheet("padding: 10px; margin: 5px;")
        fi_layout = QVBoxLayout(self.feature_importance_container)
        
        self.feature_importance_image = QLabel("Loading feature importance analysis...")
        self.feature_importance_image.setAlignment(Qt.AlignCenter)
        fi_layout.addWidget(self.feature_importance_image)
        
        # Button for opening detailed view
        self.feature_importance_button = QPushButton("View Feature Importance Details")
        self.feature_importance_button.setVisible(False)
        self.feature_importance_button.clicked.connect(self.show_feature_importance_popup)
        fi_layout.addWidget(self.feature_importance_button, alignment=Qt.AlignCenter)
        
        layout.addWidget(self.feature_importance_container)
        
        # Seasonal analysis section
        self.seasonal_label = QLabel("🌡️ Seasonal Impact Analysis")
        self.seasonal_label.setObjectName("section_title")
        layout.addWidget(self.seasonal_label)
        
        self.seasonal_desc = QLabel("This visualization shows how seasonal factors affect your mushroom growing outcomes.")
        self.seasonal_desc.setWordWrap(True)
        layout.addWidget(self.seasonal_desc)
        
        # Container for seasonal chart
        self.seasonal_container = QWidget()
        self.seasonal_container.setStyleSheet("padding: 10px; margin: 5px;")
        seasonal_layout = QVBoxLayout(self.seasonal_container)
        
        self.seasonal_image = QLabel("Loading seasonal analysis...")
        self.seasonal_image.setAlignment(Qt.AlignCenter)
        seasonal_layout.addWidget(self.seasonal_image)
        
        # Button for opening detailed view
        self.seasonal_button = QPushButton("View Seasonal Analysis Details")
        self.seasonal_button.setVisible(False)
        self.seasonal_button.clicked.connect(self.show_seasonal_popup)
        seasonal_layout.addWidget(self.seasonal_button, alignment=Qt.AlignCenter)
        
        layout.addWidget(self.seasonal_container)
        
        # Decision tree section
        self.decision_tree_label = QLabel("🌳 Decision Tree Analysis")
        self.decision_tree_label.setObjectName("section_title")
        layout.addWidget(self.decision_tree_label)
        
        self.decision_tree_desc = QLabel("This decision tree shows what factors most influence your mushroom yields.")
        self.decision_tree_desc.setWordWrap(True)
        layout.addWidget(self.decision_tree_desc)
        
        # Container for decision tree
        self.decision_tree_container = QWidget()
        self.decision_tree_container.setStyleSheet("padding: 10px; margin: 5px;")
        dt_layout = QVBoxLayout(self.decision_tree_container)
        
        self.decision_tree_image = QLabel("Loading decision tree analysis...")
        self.decision_tree_image.setAlignment(Qt.AlignCenter)
        dt_layout.addWidget(self.decision_tree_image)
        
        # Add multiple buttons in a row
        buttons_layout = QHBoxLayout()
        
        # Button for opening popup
        self.decision_tree_button = QPushButton("View Decision Tree Details")
        self.decision_tree_button.setVisible(False)
        self.decision_tree_button.clicked.connect(self.show_decision_tree_popup)
        buttons_layout.addWidget(self.decision_tree_button)
        
        # New button for opening detailed Decision Tree Insights tool
        from UI.DecisionTreeInsightsGUI import DecisionTreeInsightsGUI
        self.detailed_dt_button = QPushButton("Open Advanced Decision Tree Tool")
        self.detailed_dt_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #795548, stop:1 #5D4037);
                color: white;
                font-weight: bold;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6D4C41, stop:1 #5D4037);
            }
        """)
        self.detailed_dt_button.clicked.connect(self.open_decision_tree_insights)
        buttons_layout.addWidget(self.detailed_dt_button)
        
        dt_layout.addLayout(buttons_layout)
        
        # Algorithm info button
        self.decision_tree_info_button = QPushButton("How This Analysis Works")
        self.decision_tree_info_button.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #3498db;
                border: 1px solid #3498db;
                font-size: 12px;
                padding: 5px 10px;
            }
        """)
        self.decision_tree_info_button.clicked.connect(lambda: self.show_algorithm_explanation('decision_tree'))
        dt_layout.addWidget(self.decision_tree_info_button, alignment=Qt.AlignCenter)
        
        layout.addWidget(self.decision_tree_container)
        
        scroll.setWidget(container)
        
        # Add to the tab
        tab_layout = QVBoxLayout(self.visualizations_tab)
        tab_layout.addWidget(scroll)
    
    def load_insights(self):
        """Load insights in a background thread"""
        self.loading_thread = InsightsLoadThread(self.batches, self.logs)
        self.loading_thread.finished.connect(self.on_insights_loaded)
        self.loading_thread.progress.connect(self.progress_bar.setValue)
        self.loading_thread.start()
    
    def on_insights_loaded(self, insights_engine):
        """Handle when insights are finished loading"""
        try:
            self.insights_engine = insights_engine
            
            # Hide loading indicators
            self.loading_layout.itemAt(0).widget().hide()
            self.loading_layout.itemAt(1).widget().hide()
            
            # Show content
            self.content_widget.show()
            
            # Update summary
            summary_text = "Analysis complete. Explore the tabs below for insights."
            try:
                summary_text = insights_engine.get_summary_text()
            except Exception as e:
                print(f"Error getting summary text: {str(e)}")
            self.summary_label.setText(summary_text)
            
            # Update last refreshed time
            self.update_time_label.setText(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            
            # Populate tabs
            self.populate_tabs()
            
            # Load visualizations and make the tab visible
            self.load_visualizations()
            
            # Make visualizations tab more prominent
            self.tabs.setCurrentIndex(3)  # Switch to visualizations tab (index 3)
            
            # Add a notification about visualizations
            notification = QLabel("✨ Check out the Visualizations tab for interactive graphs and decision trees!")
            notification.setStyleSheet("""
                background-color: rgba(52, 152, 219, 0.3);
                border-radius: 5px;
                padding: 10px;
                color: white;
                font-weight: bold;
            """)
            self.content_layout.insertWidget(1, notification)
            
        except Exception as e:
            print(f"Error loading insights: {str(e)}")
            self.loading_layout.itemAt(0).widget().setText(f"Error loading insights. Please try again.")
            self.progress_bar.setValue(0)
    
    def populate_tabs(self):
        """Populate all tabs with insights"""
        try:
            # Populate yield factors tab
            yield_insights = self.insights_engine.get_insights(insight_type='yield_factor')
            guidance_insights = self.insights_engine.get_insights(insight_type='guidance')
            
            for insight in yield_insights + guidance_insights:
                card = InsightCardWithDetails(insight, insights_engine=self.insights_engine, main_view=self)
                self.yield_factors_layout.addWidget(card)
                
            if not yield_insights and not guidance_insights:
                empty_label = QLabel("Not enough data to determine yield factors yet.")
                empty_label.setAlignment(Qt.AlignCenter)
                self.yield_factors_layout.addWidget(empty_label)
            
            # Populate optimal conditions tab
            optimal_insights = self.insights_engine.get_insights(insight_type='optimal_condition')
            
            for insight in optimal_insights:
                card = InsightCardWithDetails(insight, insights_engine=self.insights_engine, main_view=self)
                self.optimal_conditions_layout.addWidget(card)
                
            if not optimal_insights:
                empty_label = QLabel("Not enough data to determine optimal conditions yet.")
                empty_label.setAlignment(Qt.AlignCenter)
                self.optimal_conditions_layout.addWidget(empty_label)
            
            # Populate timelines tab
            bagging_insights = self.insights_engine.get_insights(insight_type='bagging')
            harvesting_insights = self.insights_engine.get_insights(insight_type='harvesting')
            seasonal_insights = self.insights_engine.get_insights(insight_type='seasonal')
            warning_insights = self.insights_engine.get_insights(insight_type='warning')
            
            for insight in bagging_insights + harvesting_insights + seasonal_insights + warning_insights:
                card = InsightCardWithDetails(insight, insights_engine=self.insights_engine, main_view=self)
                self.timelines_layout.addWidget(card)
                
            if not bagging_insights and not harvesting_insights and not seasonal_insights:
                empty_label = QLabel("Not enough data to determine growth timelines yet.")
                empty_label.setAlignment(Qt.AlignCenter)
                self.timelines_layout.addWidget(empty_label)
        except Exception as e:
            print(f"Error populating tabs: {str(e)}")
            # Add error message to each tab
            for layout in [self.yield_factors_layout, self.optimal_conditions_layout, self.timelines_layout]:
                error_label = QLabel("Error loading insights. Please try again later.")
                error_label.setAlignment(Qt.AlignCenter)
                layout.addWidget(error_label)
    
    def load_visualizations(self):
        """Load visualizations from the insights engine"""
        try:
            if not self.insights_engine:
                return
                
            # Load decision tree plot
            try:
                decision_tree_data = self.insights_engine.generate_decision_tree_plot()
                if decision_tree_data:
                    if 'image' in decision_tree_data:
                        pixmap = self.base64_to_pixmap(decision_tree_data['image'])
                        self.decision_tree_image.setPixmap(pixmap)
                        self.decision_tree_button.setVisible(True)
                    
                    if 'explanation' in decision_tree_data:
                        self.decision_tree_desc.setText(decision_tree_data['explanation'])
                        
                    # If HTML content is available (text fallback), use it
                    if 'html_content' in decision_tree_data:
                        # Create a text browser to display the HTML
                        from PyQt5.QtWidgets import QTextBrowser
                        html_browser = QTextBrowser()
                        html_browser.setHtml(decision_tree_data['html_content'])
                        html_browser.setMinimumHeight(300)
                        html_browser.setStyleSheet("background-color: white; color: black; border-radius: 5px;")
                        
                        # Replace the image with the HTML browser
                        layout = self.decision_tree_container.layout()
                        layout.replaceWidget(self.decision_tree_image, html_browser)
                        self.decision_tree_image.hide()
                        
                        # Update button text
                        self.decision_tree_button.setText("Open Feature Importance Details")
                        
                        # Store HTML content for popup
                        self.decision_tree_html = decision_tree_data['html_content']
                else:
                    self.decision_tree_image.setText("Not enough data for decision tree analysis.")
            except Exception as e:
                print(f"Error loading decision tree plot: {str(e)}")
                self.decision_tree_image.setText("Error loading decision tree visualization.")
                
            # Load feature importance plot
            try:
                features_plot = self.insights_engine.get_features_plot()
                if features_plot:
                    pixmap = self.base64_to_pixmap(features_plot)
                    self.feature_importance_image.setPixmap(pixmap)
                    self.feature_importance_button.setVisible(True)
                else:
                    self.feature_importance_image.setText("Not enough data for feature importance visualization.")
            except Exception as e:
                print(f"Error loading feature importance plot: {str(e)}")
                self.feature_importance_image.setText("Error loading visualization.")
                
            # Load seasonal plot
            try:
                seasonal_plot = self.insights_engine.get_seasonal_plot()
                if seasonal_plot:
                    pixmap = self.base64_to_pixmap(seasonal_plot)
                    self.seasonal_image.setPixmap(pixmap)
                    self.seasonal_button.setVisible(True)
                else:
                    self.seasonal_image.setText("Not enough seasonal data for visualization.")
            except Exception as e:
                print(f"Error loading seasonal plot: {str(e)}")
                self.seasonal_image.setText("Error loading visualization.")
                
            # Load harvest timeline plot
            try:
                harvest_plot = self.insights_engine.get_harvest_timeline_plot()
                if harvest_plot:
                    pixmap = self.base64_to_pixmap(harvest_plot)
                    self.harvest_timeline_image.setPixmap(pixmap)
                    self.harvest_btn.setVisible(True)
                else:
                    self.harvest_timeline_image.setText("Not enough harvest data for timeline visualization.")
            except Exception as e:
                print(f"Error loading harvest timeline plot: {str(e)}")
                self.harvest_timeline_image.setText("Error loading visualization.")
        except Exception as e:
            print(f"Error loading visualizations: {str(e)}")
            
    def show_feature_importance_popup(self):
        """Show feature importance plot in a popup window"""
        if hasattr(self, 'feature_importance_image') and self.feature_importance_image.pixmap():
            popup = PopupWindow(self.feature_importance_image.pixmap(), "Feature Importance", self)
            popup.exec_()
            
    def show_seasonal_popup(self):
        """Show seasonal plot in a popup window"""
        if hasattr(self, 'seasonal_image') and self.seasonal_image.pixmap():
            popup = PopupWindow(self.seasonal_image.pixmap(), "Seasonal Yield Patterns", self)
            popup.exec_()
            
    def show_harvest_popup(self):
        """Show harvest timeline plot in a popup window"""
        if hasattr(self, 'harvest_timeline_image') and self.harvest_timeline_image.pixmap():
            popup = PopupWindow(self.harvest_timeline_image.pixmap(), "Harvest Timeline", self)
            popup.exec_()
            
    def show_decision_tree_popup(self):
        """Show decision tree plot in a popup window"""
        if hasattr(self, 'decision_tree_html'):
            # If we have HTML content, show that instead
            popup = PopupWindow(self.decision_tree_html, "Decision Tree Analysis", self, is_text=True)
            popup.exec_()
        elif hasattr(self, 'decision_tree_image') and self.decision_tree_image.pixmap():
            popup = PopupWindow(self.decision_tree_image.pixmap(), "Decision Tree Analysis", self)
            popup.exec_()
            
    def show_algorithm_explanation(self, algorithm_type):
        """Show explanation of how an algorithm works"""
        if not self.insights_engine or not hasattr(self.insights_engine, 'get_algorithm_details'):
            return
            
        algorithm_details = self.insights_engine.get_algorithm_details(algorithm_type)
        if not algorithm_details:
            return
            
        titles = {
            'yield_factor': 'Yield Factor Analysis',
            'optimal_condition': 'Optimal Conditions Analysis', 
            'harvesting': 'Harvest Timeline Analysis',
            'seasonal': 'Seasonal Pattern Analysis',
            'decision_tree': 'Decision Tree Analysis'
        }
        
        title = titles.get(algorithm_type, 'Algorithm Explanation')
        
        popup = AlgorithmExplanationPopup(title, algorithm_details, self)
        popup.exec_()
    
    def base64_to_pixmap(self, base64_data):
        """Convert base64 image data to QPixmap"""
        image_data = base64.b64decode(base64_data)
        pixmap = QPixmap()
        pixmap.loadFromData(image_data)
        return pixmap

    def scroll_to_section(self, section_name):
        """Scroll to a specific section in the visualizations tab"""
        # Map section names to their widgets
        section_map = {
            "feature_importance": self.feature_importance_container,
            "seasonal": self.seasonal_container,
            "harvest_timeline": self.harvest_container,
            "decision_tree": self.decision_tree_container
        }
        
        if section_name in section_map:
            # Find the scroll area in the visualizations tab
            scroll_area = None
            for i in range(self.visualizations_tab.layout().count()):
                item = self.visualizations_tab.layout().itemAt(i)
                if item and item.widget() and isinstance(item.widget(), QScrollArea):
                    scroll_area = item.widget()
                    break
            
            # If we found the scroll area, scroll to the widget
            if scroll_area and section_map[section_name]:
                # This is a simplified approach - for more complex scrolling you'd need
                # to calculate the exact position
                section_map[section_name].setFocus()
                
            # Flash the section to make it more noticeable
            if section_map[section_name]:
                orig_style = section_map[section_name].styleSheet()
                highlight_style = "border: 2px solid #e74c3c; border-radius: 8px;"
                
                # Briefly highlight the section
                section_map[section_name].setStyleSheet(highlight_style)
                
                # Reset after a short delay using a QTimer
                QTimer.singleShot(1500, lambda: section_map[section_name].setStyleSheet(orig_style))

    def open_decision_tree_insights(self):
        """Open the detailed decision tree insights tool"""
        try:
            from UI.DecisionTreeInsightsGUI import DecisionTreeInsightsGUI
            self.decision_tree_insights = DecisionTreeInsightsGUI()
            self.decision_tree_insights.show()
        except Exception as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to open Decision Tree Insights: {str(e)}")
            print(f"Error opening Decision Tree Insights: {str(e)}")

if __name__ == "__main__":
    # For testing
    from models.Log import run_example
    
    app = QApplication(sys.argv)
    batches, logs = run_example()
    insights_view = InsightsView(batches, logs)
    insights_view.show()
    sys.exit(app.exec_()) 