# SPDX-License-Identifier: GPL-3.0-or-later
# Holophonix PySide Window - Advanced Control Interface

import bpy
import sys
from threading import Thread

# Try to import PySide
try:
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QLabel, QSlider, QGroupBox, QTextEdit,
        QProgressBar, QSplitter, QFrame, QComboBox, QGridLayout,
        QTabWidget, QScrollArea, QToolButton, QSizePolicy, QSpacerItem,
        QGraphicsView, QGraphicsScene, QGraphicsEllipseItem, QGraphicsLineItem
    )
    from PySide6.QtCore import QTimer, Qt, Signal, QObject, QPropertyAnimation, QEasingCurve, QRect
    from PySide6.QtGui import QFont, QIcon, QPixmap, QPalette, QColor, QPainter, QLinearGradient, QPen
    
    PYSIDE_AVAILABLE = True
except ImportError:
    PYSIDE_AVAILABLE = False


class BlenderBridge(QObject):
    """Bridge between PySide UI and Blender context."""
    update_osc_status = Signal(bool, str)
    update_transport_status = Signal(int)
    update_track_list = Signal(list)
    update_model_info = Signal(str)
    
    def __init__(self):
        super().__init__()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_from_blender)
        self.timer.start(100)  # Update every 100ms
    
    def update_from_blender(self):
        """Update UI from Blender state."""
        try:
            # OSC Status
            osc = bpy.context.scene.holo_osc_settings
            self.update_osc_status.emit(osc.connected, osc.ip_out)
            
            # Transport Status
            from ..core import playback as pb
            active = pb.get_active_animations()
            self.update_transport_status.emit(len(active))
            
            # Track List
            tracks = bpy.context.scene.holo_tracks.tracks
            track_info = [(t.track_id, t.track_name) for t in tracks]
            self.update_track_list.emit(track_info)
            
            # Model Info
            params_pg = getattr(bpy.context.scene, 'holo_anim_params', None)
            if params_pg:
                from ..core import animation as anim_core
                model = anim_core.get_model(params_pg.model_id)
                model_label = model.get('label', params_pg.model_id) if model else params_pg.model_id
                self.update_model_info.emit(model_label)
        except Exception as e:
            print(f"[Holophonix] Bridge update error: {e}")


class ModernButton(QPushButton):
    """Modern styled button with animations."""
    def __init__(self, text, icon_name=None):
        super().__init__(text)
        self.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                       stop:0 #2d2d30, stop:1 #3e3e42);
                border: 1px solid #555;
                border-radius: 6px;
                padding: 8px 16px;
                color: white;
                font-weight: bold;
                font-size: 12px;
                min-width: 80px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                       stop:0 #404045, stop:1 #55555a);
                border-color: #0078d4;
                box-shadow: 0 2px 8px rgba(0, 120, 212, 0.3);
            }
            QPushButton:pressed {
                background: #0078d4;
                transform: translateY(1px);
            }
            QPushButton:disabled {
                background: #2a2a2a;
                color: #666;
                border-color: #444;
            }
        """)


class ModernSlider(QSlider):
    """Modern styled slider with real-time value display."""
    def __init__(self, orientation=Qt.Horizontal):
        super().__init__(orientation)
        self.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #444;
                height: 8px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                         stop:0 #2d2d30, stop:1 #3e3e42);
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                         stop:0 #0078d4, stop:1 #005a9e);
                border: 2px solid #0099ff;
                width: 18px;
                height: 18px;
                margin: -7px 0;
                border-radius: 9px;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
            }
            QSlider::handle:horizontal:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                         stop:0 #0099ff, stop:1 #0078d4);
                border-color: #00ccff;
                box-shadow: 0 0 8px rgba(0, 153, 255, 0.5);
            }
        """)


class ModernCard(QFrame):
    """Material Design card with elevation."""
    def __init__(self):
        super().__init__()
        self.setFrameStyle(QFrame.NoFrame)
        self.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                       stop:0 #3a3a3d, stop:1 #2d2d30);
                border: 1px solid #444;
                border-radius: 8px;
                margin: 4px;
            }
        """)


class TrajectoryWidget(QGraphicsView):
    """Real-time trajectory visualization."""
    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setStyleSheet("""
            QGraphicsView {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                       stop:0 #1a1a1c, stop:1 #2d2d30);
                border: 1px solid #444;
                border-radius: 4px;
            }
        """)
        self.setMinimumHeight(200)
        self.trajectory_items = []
        
    def update_trajectory(self, points):
        """Update trajectory visualization."""
        # Clear previous trajectory
        for item in self.trajectory_items:
            self.scene.removeItem(item)
        self.trajectory_items.clear()
        
        if not points:
            return
            
        # Draw trajectory
        pen = QPen(QColor(0, 153, 255), 2)
        pen.setCosmetic(True)
        
        for i in range(len(points) - 1):
            line = QGraphicsLineItem(
                points[i][0] * 50, -points[i][1] * 50,
                points[i+1][0] * 50, -points[i+1][1] * 50
            )
            line.setPen(pen)
            self.scene.addItem(line)
            self.trajectory_items.append(line)
        
        # Add points
        for point in points:
            ellipse = QGraphicsEllipseItem(
                point[0] * 50 - 3, -point[1] * 50 - 3, 6, 6
            )
            ellipse.setBrush(QColor(255, 100, 100))
            ellipse.setPen(QPen(QColor(255, 150, 150), 1))
            self.scene.addItem(ellipse)
            self.trajectory_items.append(ellipse)
        
        # Center view
        self.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)


class HolophonixWindow(QMainWindow):
    """Main PySide window for Holophonix advanced control."""
    
    def __init__(self):
        super().__init__()
        self.bridge = BlenderBridge()
        self.setWindowTitle("🎵 Holophonix Animator - Advanced Control")
        self.setGeometry(100, 100, 1000, 700)
        
        # Apply dark theme
        self.setup_dark_theme()
        
        # Setup UI
        self.setup_ui()
        self.setup_connections()
        
        # Set window flags
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        
        # Setup animations
        self.setup_animations()
    
    def setup_dark_theme(self):
        """Apply modern dark theme."""
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(45, 45, 48))
        palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
        palette.setColor(QPalette.Base, QColor(30, 30, 30))
        palette.setColor(QPalette.AlternateBase, QColor(40, 40, 40))
        palette.setColor(QPalette.ToolTipBase, QColor(0, 120, 212))
        palette.setColor(QPalette.ToolTipText, QColor(255, 255, 255))
        palette.setColor(QPalette.Text, QColor(255, 255, 255))
        palette.setColor(QPalette.Button, QColor(61, 61, 64))
        palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
        palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.Link, QColor(0, 153, 255))
        palette.setColor(QPalette.Highlight, QColor(0, 120, 212))
        palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
        self.setPalette(palette)
    
    def setup_animations(self):
        """Setup UI animations."""
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(300)
        self.fade_animation.setEasingCurve(QEasingCurve.OutCubic)
    
    def setup_ui(self):
        """Create the modern UI layout with tabs."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main vertical layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)
        
        # Header with status
        header_card = ModernCard()
        header_layout = QHBoxLayout(header_card)
        header_layout.setContentsMargins(12, 8, 12, 8)
        
        # OSC Status
        self.osc_status_label = QLabel("🔴 OSC: Disconnected")
        self.osc_status_label.setStyleSheet("""
            QLabel {
                color: #ff4444;
                font-weight: bold;
                font-size: 14px;
                padding: 4px 8px;
                background: rgba(255, 68, 68, 0.1);
                border-radius: 4px;
            }
        """)
        header_layout.addWidget(self.osc_status_label)
        
        header_layout.addStretch()
        
        # Transport status
        self.transport_status_label = QLabel("⏹ Stopped")
        self.transport_status_label.setStyleSheet("""
            QLabel {
                color: #888;
                font-weight: bold;
                font-size: 14px;
                padding: 4px 8px;
                background: rgba(136, 136, 136, 0.1);
                border-radius: 4px;
            }
        """)
        header_layout.addWidget(self.transport_status_label)
        
        main_layout.addWidget(header_card)
        
        # Tab widget for organized content
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #444;
                background: #2d2d30;
                border-radius: 4px;
            }
            QTabBar::tab {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                       stop:0 #3a3a3d, stop:1 #2d2d30);
                border: 1px solid #444;
                border-bottom: none;
                border-radius: 4px 4px 0 0;
                padding: 8px 16px;
                margin-right: 2px;
                color: #ccc;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                       stop:0 #0078d4, stop:1 #005a9e);
                color: white;
                border-color: #0078d4;
            }
            QTabBar::tab:hover:!selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                       stop:0 #404045, stop:1 #55555a);
                color: white;
            }
        """)
        
        # Tab 1: Transport & Models
        transport_tab = self.create_transport_tab()
        self.tab_widget.addTab(transport_tab, "🎮 Transport")
        
        # Tab 2: Parameters
        params_tab = self.create_parameters_tab()
        self.tab_widget.addTab(params_tab, "⚙️ Parameters")
        
        # Tab 3: Visualization
        viz_tab = self.create_visualization_tab()
        self.tab_widget.addTab(viz_tab, "📊 Visualization")
        
        # Tab 4: Tracks & OSC
        tracks_tab = self.create_tracks_tab()
        self.tab_widget.addTab(tracks_tab, "🎵 Tracks")
        
        # Tab 5: Logger (for debugging)
        logger_tab = self.create_logger_tab()
        self.tab_widget.addTab(logger_tab, "📝 Logger")
        
        main_layout.addWidget(self.tab_widget)
    
    def create_transport_tab(self):
        """Create transport and models tab."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setSpacing(12)
        
        # Left: Transport controls
        transport_card = ModernCard()
        transport_layout = QVBoxLayout(transport_card)
        transport_layout.setContentsMargins(12, 12, 12, 12)
        
        # Title
        title = QLabel("🎬 Transport Controls")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0078d4; margin-bottom: 8px;")
        transport_layout.addWidget(title)
        
        # Play/Stop buttons
        btn_layout = QHBoxLayout()
        self.play_btn = ModernButton("▶ Play")
        self.play_btn.clicked.connect(self.play_selected)
        btn_layout.addWidget(self.play_btn)
        
        self.stop_btn = ModernButton("⏹ Stop")
        self.stop_btn.clicked.connect(self.stop_all)
        btn_layout.addWidget(self.stop_btn)
        
        transport_layout.addLayout(btn_layout)
        
        # Loop mode
        loop_layout = QHBoxLayout()
        loop_layout.addWidget(QLabel("Loop:"))
        self.loop_combo = QComboBox()
        self.loop_combo.addItems(["Once", "Loop", "Ping-Pong"])
        self.loop_combo.setStyleSheet("""
            QComboBox {
                background: #3a3a3d;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px 8px;
                color: white;
                min-width: 100px;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid #888;
                margin-right: 4px;
            }
        """)
        self.loop_combo.currentTextChanged.connect(self.update_loop_mode)
        loop_layout.addWidget(self.loop_combo)
        transport_layout.addLayout(loop_layout)
        
        # Duration
        self.duration_slider = ModernSlider()
        self.duration_slider.setRange(10, 600)
        self.duration_slider.setValue(40)
        self.duration_label = QLabel("Duration: 4.0s")
        self.duration_label.setStyleSheet("color: #ccc; font-size: 12px;")
        self.duration_slider.valueChanged.connect(self.update_duration)
        transport_layout.addWidget(self.duration_label)
        transport_layout.addWidget(self.duration_slider)
        
        layout.addWidget(transport_card)
        
        # Right: Model selector
        model_card = ModernCard()
        model_layout = QVBoxLayout(model_card)
        model_layout.setContentsMargins(12, 12, 12, 12)
        
        # Model title
        model_title = QLabel("🎭 Animation Models")
        model_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0078d4; margin-bottom: 8px;")
        model_layout.addWidget(model_title)
        
        # Current model display
        self.model_label = QLabel("Model: ---")
        self.model_label.setStyleSheet("""
            QLabel {
                background: rgba(0, 120, 212, 0.1);
                border: 1px solid #0078d4;
                border-radius: 4px;
                padding: 8px;
                color: #00ccff;
                font-weight: bold;
                margin-bottom: 12px;
            }
        """)
        model_layout.addWidget(self.model_label)
        
        # Model grid
        model_grid = QGridLayout()
        models = ["circular", "linear", "figure8", "spiral", "pendulum", "random_walk"]
        icons = ["⭕", "➖", "∞", "🌀", "🔄", "🎲"]
        
        for i, (model_id, icon) in enumerate(zip(models, icons)):
            row, col = i // 3, i % 3
            btn = ModernButton(f"{icon} {model_id.replace('_', ' ').title()}")
            btn.clicked.connect(lambda checked, m=model_id: self.set_model(m))
            model_grid.addWidget(btn, row, col)
        
        model_layout.addLayout(model_grid)
        layout.addWidget(model_card)
        
        return widget
    
    def create_parameters_tab(self):
        """Create advanced parameters tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Parameters card
        params_card = ModernCard()
        params_layout = QVBoxLayout(params_card)
        params_layout.setContentsMargins(12, 12, 12, 12)
        
        # Title
        title = QLabel("⚙️ Advanced Parameters")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0078d4; margin-bottom: 12px;")
        params_layout.addWidget(title)
        
        # Parameter sliders with enhanced styling
        sliders = [
            ("radius", "Radius", "2.0", 20, 200),
            ("height", "Height", "0.0", -100, 100),
            ("speed", "Speed", "1.0", 1, 200),
            ("turns", "Turns", "5.0", 1, 100)
        ]
        
        for param_id, label, default_val, min_val, max_val in sliders:
            param_label = QLabel(f"{label}: {default_val}")
            param_label.setStyleSheet("color: #ccc; font-size: 13px; margin: 4px 0;")
            params_layout.addWidget(param_label)
            
            slider = ModernSlider()
            slider.setRange(min_val, max_val)
            slider.setValue(float(default_val) * 10 if '.' in default_val else int(default_val))
            slider.valueChanged.connect(
                lambda v, pid=param_id, pl=param_label: self.update_parameter(pid, v, pl)
            )
            params_layout.addWidget(slider)
            
            # Store reference
            setattr(self, f"{param_id}_slider", slider)
            setattr(self, f"{param_id}_label", param_label)
        
        layout.addWidget(params_card)
        layout.addStretch()
        
        return widget
    
    def create_visualization_tab(self):
        """Create visualization tab with trajectory display."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Trajectory visualization
        viz_card = ModernCard()
        viz_layout = QVBoxLayout(viz_card)
        viz_layout.setContentsMargins(12, 12, 12, 12)
        
        title = QLabel("📊 Trajectory Visualization")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0078d4; margin-bottom: 8px;")
        viz_layout.addWidget(title)
        
        # Trajectory widget
        self.trajectory_widget = TrajectoryWidget()
        viz_layout.addWidget(self.trajectory_widget)
        
        # Quick actions
        actions_layout = QHBoxLayout()
        refresh_btn = ModernButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh_preview)
        actions_layout.addWidget(refresh_btn)
        
        focus_btn = ModernButton("🎯 Focus View")
        focus_btn.clicked.connect(self.focus_view)
        actions_layout.addWidget(focus_btn)
        
        actions_layout.addStretch()
        viz_layout.addLayout(actions_layout)
        
        layout.addWidget(viz_card)
        
        return widget
    
    def create_tracks_tab(self):
        """Create tracks and OSC management tab."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setSpacing(12)
        
        # Tracks list
        tracks_card = ModernCard()
        tracks_layout = QVBoxLayout(tracks_card)
        tracks_layout.setContentsMargins(12, 12, 12, 12)
        
        title = QLabel("🎵 Active Tracks")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0078d4; margin-bottom: 8px;")
        tracks_layout.addWidget(title)
        
        self.track_list = QTextEdit()
        self.track_list.setStyleSheet("""
            QTextEdit {
                background: #1a1a1c;
                border: 1px solid #444;
                border-radius: 4px;
                color: #ccc;
                font-family: 'Consolas', monospace;
                font-size: 12px;
            }
        """)
        self.track_list.setReadOnly(True)
        self.track_list.setMaximumHeight(150)
        tracks_layout.addWidget(self.track_list)
        
        layout.addWidget(tracks_card)
        
        # OSC controls
        osc_card = ModernCard()
        osc_layout = QVBoxLayout(osc_card)
        osc_layout.setContentsMargins(12, 12, 12, 12)
        
        osc_title = QLabel("📡 OSC Connection")
        osc_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0078d4; margin-bottom: 8px;")
        osc_layout.addWidget(osc_title)
        
        # OSC IP display
        self.osc_ip_label = QLabel("IP: ---")
        self.osc_ip_label.setStyleSheet("color: #ccc; margin: 4px 0;")
        osc_layout.addWidget(self.osc_ip_label)
        
        # OSC buttons
        osc_btn_layout = QHBoxLayout()
        connect_btn = ModernButton("🔗 Connect")
        connect_btn.clicked.connect(self.toggle_osc)
        osc_btn_layout.addWidget(connect_btn)
        
        dump_btn = ModernButton("💾 Dump")
        dump_btn.clicked.connect(self.osc_dump)
        osc_btn_layout.addWidget(dump_btn)
        
        osc_layout.addLayout(osc_btn_layout)
        
        # Import button
        import_btn = ModernButton("📁 Import .hol")
        import_btn.clicked.connect(self.import_hol)
        osc_layout.addWidget(import_btn)
        
        layout.addWidget(osc_card)
        
        return widget
    
    def create_logger_tab(self):
        """Create debug logger tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Logger card
        logger_card = ModernCard()
        logger_layout = QVBoxLayout(logger_card)
        logger_layout.setContentsMargins(12, 12, 12, 12)
        
        # Title
        title = QLabel("📝 Activity Logger")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0078d4; margin-bottom: 8px;")
        logger_layout.addWidget(title)
        
        # Logger text area
        self.log_text = QTextEdit()
        self.log_text.setStyleSheet("""
            QTextEdit {
                background: #1a1a1c;
                border: 1px solid #444;
                border-radius: 4px;
                color: #ccc;
                font-family: 'Consolas', monospace;
                font-size: 12px;
            }
        """)
        self.log_text.setReadOnly(True)
        logger_layout.addWidget(self.log_text)
        
        # Clear button
        clear_btn = ModernButton("🗑️ Clear Log")
        clear_btn.clicked.connect(self.log_text.clear)
        logger_layout.addWidget(clear_btn)
        
        layout.addWidget(logger_card)
        
        # Add initial message
        self.log_text.append("🎵 Holophonix Advanced Control Window initialized")
        self.log_text.append("📝 Ready for debugging...")
        
        return widget
    
    def create_control_panel(self):
        """Create the advanced control panel."""
        panel = QFrame()
        panel.setFrameStyle(QFrame.StyledPanel)
        layout = QVBoxLayout(panel)
        
        # OSC Status Group
        osc_group = QGroupBox("OSC Connection")
        osc_layout = QVBoxLayout()
        
        self.osc_status_label = QLabel("Disconnected")
        self.osc_status_label.setStyleSheet("color: red; font-weight: bold;")
        osc_layout.addWidget(self.osc_status_label)
        
        self.osc_ip_label = QLabel("IP: ---")
        osc_layout.addWidget(self.osc_ip_label)
        
        osc_btn_layout = QHBoxLayout()
        osc_connect_btn = QPushButton("Connect")
        osc_connect_btn.clicked.connect(self.toggle_osc)
        osc_btn_layout.addWidget(osc_connect_btn)
        
        osc_dump_btn = QPushButton("Dump")
        osc_dump_btn.clicked.connect(self.osc_dump)
        osc_btn_layout.addWidget(osc_dump_btn)
        
        osc_layout.addLayout(osc_btn_layout)
        osc_group.setLayout(osc_layout)
        layout.addWidget(osc_group)
        
        # Transport Group
        transport_group = QGroupBox("Transport")
        transport_layout = QVBoxLayout()
        
        self.transport_status_label = QLabel("Stopped")
        self.transport_status_label.setStyleSheet("color: gray; font-weight: bold;")
        transport_layout.addWidget(self.transport_status_label)
        
        # Transport buttons with more options
        btn_layout = QHBoxLayout()
        
        self.play_btn = QPushButton("Play")
        self.play_btn.clicked.connect(self.play_selected)
        btn_layout.addWidget(self.play_btn)
        
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_all)
        btn_layout.addWidget(self.stop_btn)
        
        transport_layout.addLayout(btn_layout)
        
        # Loop mode selector
        loop_layout = QHBoxLayout()
        loop_layout.addWidget(QLabel("Loop:"))
        self.loop_combo = QComboBox()
        self.loop_combo.addItems(["Once", "Loop", "Ping-Pong"])
        self.loop_combo.currentTextChanged.connect(self.update_loop_mode)
        loop_layout.addWidget(self.loop_combo)
        transport_layout.addLayout(loop_layout)
        
        # Duration slider
        self.duration_slider = QSlider(Qt.Horizontal)
        self.duration_slider.setRange(10, 600)  # 0.1 to 60 seconds
        self.duration_slider.setValue(40)  # 4 seconds
        self.duration_label = QLabel("Duration: 4.0s")
        self.duration_slider.valueChanged.connect(self.update_duration)
        transport_layout.addWidget(self.duration_label)
        transport_layout.addWidget(self.duration_slider)
        
        transport_group.setLayout(transport_layout)
        layout.addWidget(transport_group)
        
        # Model Group
        model_group = QGroupBox("Animation Model")
        model_layout = QVBoxLayout()
        
        self.model_label = QLabel("Model: ---")
        model_layout.addWidget(self.model_label)
        
        # Model selector buttons in grid
        model_grid_layout = QGridLayout()
        models = ["circular", "linear", "figure8", "spiral", "pendulum", "random_walk"]
        for i, model_id in enumerate(models):
            row, col = i // 3, i % 3
            btn = QPushButton(model_id.replace("_", " ").title())
            btn.clicked.connect(lambda checked, m=model_id: self.set_model(m))
            btn.setStyleSheet("QPushButton { padding: 8px; }")
            model_grid_layout.addWidget(btn, row, col)
        
        model_layout.addLayout(model_grid_layout)
        model_group.setLayout(model_layout)
        layout.addWidget(model_group)
        
        # Advanced Parameters
        params_group = QGroupBox("Advanced Parameters")
        params_layout = QVBoxLayout()
        
        # Common parameters
        self.radius_slider = QSlider(Qt.Horizontal)
        self.radius_slider.setRange(1, 200)  # 0.1 to 20.0
        self.radius_slider.setValue(20)  # 2.0
        self.radius_label = QLabel("Radius: 2.0")
        self.radius_slider.valueChanged.connect(self.update_radius)
        params_layout.addWidget(self.radius_label)
        params_layout.addWidget(self.radius_slider)
        
        self.height_slider = QSlider(Qt.Horizontal)
        self.height_slider.setRange(-100, 100)  # -10.0 to 10.0
        self.height_slider.setValue(0)
        self.height_label = QLabel("Height: 0.0")
        self.height_slider.valueChanged.connect(self.update_height)
        params_layout.addWidget(self.height_label)
        params_layout.addWidget(self.height_slider)
        
        # Model-specific parameters
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(1, 200)  # 0.1 to 20.0
        self.speed_slider.setValue(100)  # 1.0
        self.speed_label = QLabel("Speed: 1.0")
        self.speed_slider.valueChanged.connect(self.update_speed)
        params_layout.addWidget(self.speed_label)
        params_layout.addWidget(self.speed_slider)
        
        self.turns_slider = QSlider(Qt.Horizontal)
        self.turns_slider.setRange(1, 100)  # 0.1 to 10.0
        self.turns_slider.setValue(50)  # 5.0
        self.turns_label = QLabel("Turns: 5.0")
        self.turns_slider.valueChanged.connect(self.update_turns)
        params_layout.addWidget(self.turns_label)
        params_layout.addWidget(self.turns_slider)
        
        params_group.setLayout(params_layout)
        layout.addWidget(params_group)
        
        # Quick Actions
        actions_group = QGroupBox("Quick Actions")
        actions_layout = QVBoxLayout()
        
        actions_btn_layout = QHBoxLayout()
        preview_btn = QPushButton("Preview")
        preview_btn.clicked.connect(self.refresh_preview)
        actions_btn_layout.addWidget(preview_btn)
        
        focus_btn = QPushButton("Focus View")
        focus_btn.clicked.connect(self.focus_view)
        actions_btn_layout.addWidget(focus_btn)
        
        import_btn = QPushButton("Import .hol")
        import_btn.clicked.connect(self.import_hol)
        actions_btn_layout.addWidget(import_btn)
        
        actions_layout.addLayout(actions_btn_layout)
        actions_group.setLayout(actions_layout)
        layout.addWidget(actions_group)
        
        layout.addStretch()
        return panel
    
    def create_info_panel(self):
        """Create the information panel."""
        panel = QFrame()
        panel.setFrameStyle(QFrame.StyledPanel)
        layout = QVBoxLayout(panel)
        
        # Track List
        tracks_group = QGroupBox("Active Tracks")
        tracks_layout = QVBoxLayout()
        
        self.track_list = QTextEdit()
        self.track_list.setReadOnly(True)
        self.track_list.setMaximumHeight(150)
        tracks_layout.addWidget(self.track_list)
        
        tracks_group.setLayout(tracks_layout)
        layout.addWidget(tracks_group)
        
        # Progress
        progress_group = QGroupBox("Animation Progress")
        progress_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        progress_layout.addWidget(self.progress_bar)
        
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)
        
        # Log
        log_group = QGroupBox("Activity Log")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        log_layout.addWidget(self.log_text)
        
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        layout.addStretch()
        return panel
    
    def setup_connections(self):
        """Connect bridge signals to UI updates."""
        self.bridge.update_osc_status.connect(self.update_osc_status)
        self.bridge.update_transport_status.connect(self.update_transport_status)
        self.bridge.update_track_list.connect(self.update_track_list)
        self.bridge.update_model_info.connect(self.update_model_info)
        
        # Slider connections
        self.radius_slider.valueChanged.connect(self.update_radius)
        self.height_slider.valueChanged.connect(self.update_height)
    
    def update_parameter(self, param_id, value, label):
        """Update parameter display and Blender value."""
        if param_id == "radius":
            radius = value / 10.0
            label.setText(f"Radius: {radius:.1f}")
            self.update_blender_param("radius", radius)
        elif param_id == "height":
            height = value / 10.0
            label.setText(f"Height: {height:.1f}")
            self.update_blender_param("height", height)
        elif param_id == "speed":
            speed = value / 100.0
            label.setText(f"Speed: {speed:.1f}")
            self.update_blender_param("speed", speed)
        elif param_id == "turns":
            turns = value / 10.0
            label.setText(f"Turns: {turns:.1f}")
            self.update_blender_param("turns", turns)
    
    def update_osc_status(self, connected, ip):
        """Update OSC status display."""
        if connected:
            self.osc_status_label.setText("🟢 OSC: Connected")
            self.osc_status_label.setStyleSheet("""
                QLabel {
                    color: #44ff44;
                    font-weight: bold;
                    font-size: 14px;
                    padding: 4px 8px;
                    background: rgba(68, 255, 68, 0.1);
                    border-radius: 4px;
                }
            """)
        else:
            self.osc_status_label.setText("🔴 OSC: Disconnected")
            self.osc_status_label.setStyleSheet("""
                QLabel {
                    color: #ff4444;
                    font-weight: bold;
                    font-size: 14px;
                    padding: 4px 8px;
                    background: rgba(255, 68, 68, 0.1);
                    border-radius: 4px;
                }
            """)
        self.osc_ip_label.setText(f"IP: {ip}")
    
    def update_transport_status(self, n_active):
        """Update transport status."""
        if n_active > 0:
            self.transport_status_label.setText(f"🎵 Playing: {n_active}")
            self.transport_status_label.setStyleSheet("""
                QLabel {
                    color: #44ff44;
                    font-weight: bold;
                    font-size: 14px;
                    padding: 4px 8px;
                    background: rgba(68, 255, 68, 0.1);
                    border-radius: 4px;
                }
            """)
        else:
            self.transport_status_label.setText("⏹ Stopped")
            self.transport_status_label.setStyleSheet("""
                QLabel {
                    color: #888;
                    font-weight: bold;
                    font-size: 14px;
                    padding: 4px 8px;
                    background: rgba(136, 136, 136, 0.1);
                    border-radius: 4px;
                }
            """)
    
    def update_track_list(self, tracks):
        """Update track list display."""
        text = "\n".join([f"🎵 Track {tid:03d}: {name}" for tid, name in tracks])
        self.track_list.setText(text)
    
    def update_model_info(self, model_label):
        """Update model info."""
        self.model_label.setText(f"Model: {model_label}")
    
    def update_radius(self, value):
        """Update radius parameter (legacy)."""
        radius = value / 10.0
        if hasattr(self, 'radius_label'):
            self.radius_label.setText(f"Radius: {radius:.1f}")
        self.update_blender_param("radius", radius)
    
    def update_height(self, value):
        """Update height parameter (legacy)."""
        height = value / 10.0
        if hasattr(self, 'height_label'):
            self.height_label.setText(f"Height: {height:.1f}")
        self.update_blender_param("height", height)
    
    def update_blender_param(self, param_name, value):
        """Update parameter in Blender."""
        try:
            scene = bpy.context.scene
            param_key = f"hol_param_{param_name}"
            scene[param_key] = value
        except Exception as e:
            if hasattr(self, 'log_text'):
                self.log_text.append(f"Error updating {param_name}: {e}")
    
    def update_trajectory_visualization(self, points):
        """Update trajectory visualization widget."""
        if hasattr(self, 'trajectory_widget'):
            self.trajectory_widget.update_trajectory(points)
    
    def toggle_osc(self):
        """Toggle OSC connection."""
        try:
            osc = bpy.context.scene.holo_osc_settings
            if hasattr(self, 'log_text'):
                self.log_text.append(f"📡 OSC status: {'Connected' if osc.connected else 'Disconnected'}")
            
            if osc.connected:
                bpy.ops.holophonix.osc_disconnect()
                if hasattr(self, 'log_text'):
                    self.log_text.append("📡 OSC disconnected")
            else:
                bpy.ops.holophonix.osc_connect()
                if hasattr(self, 'log_text'):
                    self.log_text.append("📡 OSC connecting...")
        except Exception as e:
            if hasattr(self, 'log_text'):
                self.log_text.append(f"📡 OSC toggle error: {e}")
    
    def play_selected(self):
        """Start playback."""
        try:
            # Check if we have selected tracks - use context override for PySide
            track_objects = []
            for window in bpy.context.window_manager.windows:
                for area in window.screen.areas:
                    if area.type == 'VIEW_3D':
                        override = {'window': window, 'screen': window.screen, 'area': area}
                        with bpy.context.temp_override(**override):
                            selected_objects = getattr(bpy.context, 'selected_objects', [])
                            track_objects = [obj for obj in selected_objects if obj.name.startswith('holo.track')]
                            break
                        if track_objects:
                            break
            
            if not track_objects:
                # Fallback: check all track objects in scene
                all_tracks = [obj for obj in bpy.data.objects if obj.name.startswith('holo.track')]
                if all_tracks:
                    if hasattr(self, 'log_text'):
                        self.log_text.append(f"⚠️ No tracks selected! Found {len(all_tracks)} tracks in scene. Select one in viewport.")
                    # Use first available track as fallback
                    track_objects = [all_tracks[0]]
                    if hasattr(self, 'log_text'):
                        self.log_text.append(f"🔄 Using fallback track: {track_objects[0].name}")
                else:
                    if hasattr(self, 'log_text'):
                        self.log_text.append("⚠️ No tracks in scene! Create tracks first.")
                    return
            
            if hasattr(self, 'log_text'):
                self.log_text.append(f"🎵 Starting playback on {len(track_objects)} track(s): {', '.join([t.name for t in track_objects])}")
            
            # Select the tracks before playing
            bpy.ops.object.select_all(action='DESELECT')
            for track in track_objects:
                track.select_set(True)
            
            bpy.ops.holophonix.play_selected()
            if hasattr(self, 'log_text'):
                self.log_text.append("🎵 Playback started")
        except Exception as e:
            if hasattr(self, 'log_text'):
                self.log_text.append(f"🎵 Play error: {e}")
    
    def stop_all(self):
        """Stop all playback."""
        try:
            bpy.ops.holophonix.stop_all()
            if hasattr(self, 'log_text'):
                self.log_text.append("⏹ Playback stopped")
        except Exception as e:
            if hasattr(self, 'log_text'):
                self.log_text.append(f"⏹ Stop error: {e}")
    
    def set_model(self, model_id):
        """Set animation model."""
        try:
            if hasattr(self, 'log_text'):
                self.log_text.append(f"🎭 Setting model to: {model_id}")
            
            bpy.ops.holophonix.set_anim_model(model_id=model_id)
            if hasattr(self, 'log_text'):
                self.log_text.append(f"🎭 Model set to: {model_id}")
        except Exception as e:
            if hasattr(self, 'log_text'):
                self.log_text.append(f"🎭 Model set error: {e}")
    
    def osc_dump(self):
        """Trigger OSC dump (not implemented yet)."""
        if hasattr(self, 'log_text'):
            self.log_text.append("⚠️ OSC dump not implemented yet")
    
    def update_loop_mode(self, mode_text):
        """Update loop mode."""
        try:
            mode_map = {"Once": "ONCE", "Loop": "LOOP", "Ping-Pong": "PING_PONG"}
            mode = mode_map.get(mode_text, "LOOP")
            # Store loop mode as a custom property on the scene
            bpy.context.scene["holo_quick_loop"] = mode
            if hasattr(self, 'log_text'):
                self.log_text.append(f"🔄 Loop mode set to: {mode}")
        except Exception as e:
            if hasattr(self, 'log_text'):
                self.log_text.append(f"Loop mode error: {e}")
    
    def update_duration(self, value):
        """Update duration."""
        duration = value / 10.0  # Convert to seconds
        if hasattr(self, 'duration_label'):
            self.duration_label.setText(f"Duration: {duration:.1f}s")
        try:
            # Store duration as a custom property on the scene
            bpy.context.scene["holo_quick_duration"] = duration
            # Also update the anim_params duration if available
            params_pg = getattr(bpy.context.scene, 'holo_anim_params', None)
            if params_pg:
                params_pg.duration = duration
        except Exception as e:
            if hasattr(self, 'log_text'):
                self.log_text.append(f"Duration update error: {e}")
    
    def update_speed(self, value):
        """Update speed parameter."""
        speed = value / 100.0
        if hasattr(self, 'speed_label'):
            self.speed_label.setText(f"Speed: {speed:.1f}")
        self.update_blender_param("speed", speed)
    
    def update_turns(self, value):
        """Update turns parameter."""
        turns = value / 10.0
        if hasattr(self, 'turns_label'):
            self.turns_label.setText(f"Turns: {turns:.1f}")
        self.update_blender_param("turns", turns)
    
    def refresh_preview(self):
        """Refresh trajectory preview."""
        try:
            bpy.ops.holophonix.refresh_preview()
            if hasattr(self, 'log_text'):
                self.log_text.append("🔄 Preview refreshed")
        except Exception as e:
            if hasattr(self, 'log_text'):
                self.log_text.append(f"Preview error: {e}")
    
    def focus_view(self):
        """Focus view on tracks."""
        try:
            bpy.ops.holophonix.focus_view()
            if hasattr(self, 'log_text'):
                self.log_text.append("🎯 View focused")
        except Exception as e:
            if hasattr(self, 'log_text'):
                self.log_text.append(f"Focus view error: {e}")
    
    def import_hol(self):
        """Import .hol file."""
        try:
            bpy.ops.holophonix.import_hol()
            if hasattr(self, 'log_text'):
                self.log_text.append("📁 Import dialog opened")
        except Exception as e:
            if hasattr(self, 'log_text'):
                self.log_text.append(f"Import error: {e}")
    
    def closeEvent(self, event):
        """Handle window close event."""
        self.bridge.timer.stop()
        event.accept()


# Global window instance
_pyside_window = None
_pyside_app = None


def show_pyside_window():
    """Show the PySide window."""
    global _pyside_window, _pyside_app
    
    if not PYSIDE_AVAILABLE:
        print("[Holophonix] PySide not available. Install PySide6 to use advanced UI.")
        return False
    
    # Always recreate window to handle closed windows
    # Create application if needed
    if _pyside_app is None:
        _pyside_app = QApplication.instance()
        if _pyside_app is None:
            _pyside_app = QApplication(sys.argv)
    
    # Create new window instance
    if _pyside_window:
        _pyside_window.close()
    
    _pyside_window = HolophonixWindow()
    _pyside_window.show()
    return True


def close_pyside_window():
    """Close the PySide window."""
    global _pyside_window, _pyside_app
    
    if _pyside_window:
        _pyside_window.close()
        _pyside_window = None
    
    if _pyside_app:
        _pyside_app.quit()
        _pyside_app = None
