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
        QProgressBar, QSplitter, QFrame, QComboBox, QGridLayout
    )
    from PySide6.QtCore import QTimer, Qt, Signal, QObject
    from PySide6.QtGui import QFont, QIcon, QPixmap
    
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


class HolophonixWindow(QMainWindow):
    """Main PySide window for Holophonix advanced control."""
    
    def __init__(self):
        super().__init__()
        self.bridge = BlenderBridge()
        self.setWindowTitle("Holophonix Animator - Advanced Control")
        self.setGeometry(100, 100, 800, 600)
        
        # Setup UI
        self.setup_ui()
        self.setup_connections()
        
        # Set window flags
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
    
    def setup_ui(self):
        """Create the UI layout."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout(central_widget)
        
        # Left panel - Controls
        left_panel = self.create_control_panel()
        main_layout.addWidget(left_panel, 1)
        
        # Right panel - Info & Timeline
        right_panel = self.create_info_panel()
        main_layout.addWidget(right_panel, 1)
    
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
    
    def update_osc_status(self, connected, ip):
        """Update OSC status display."""
        if connected:
            self.osc_status_label.setText("Connected")
            self.osc_status_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.osc_status_label.setText("Disconnected")
            self.osc_status_label.setStyleSheet("color: red; font-weight: bold;")
        self.osc_ip_label.setText(f"IP: {ip}")
    
    def update_transport_status(self, n_active):
        """Update transport status."""
        if n_active > 0:
            self.transport_status_label.setText(f"Playing: {n_active}")
            self.transport_status_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.transport_status_label.setText("Stopped")
            self.transport_status_label.setStyleSheet("color: gray; font-weight: bold;")
    
    def update_track_list(self, tracks):
        """Update track list display."""
        text = "\n".join([f"Track {tid:03d}: {name}" for tid, name in tracks])
        self.track_list.setText(text)
    
    def update_model_info(self, model_label):
        """Update model info."""
        self.model_label.setText(f"Model: {model_label}")
    
    def update_radius(self, value):
        """Update radius parameter."""
        radius = value / 10.0
        self.radius_label.setText(f"Radius: {radius:.1f}")
        self.update_blender_param("radius", radius)
    
    def update_height(self, value):
        """Update height parameter."""
        height = value / 10.0
        self.height_label.setText(f"Height: {height:.1f}")
        self.update_blender_param("height", height)
    
    def update_blender_param(self, param_name, value):
        """Update parameter in Blender."""
        try:
            scene = bpy.context.scene
            param_key = f"hol_param_{param_name}"
            scene[param_key] = value
        except Exception as e:
            self.log_text.append(f"Error updating {param_name}: {e}")
    
    def toggle_osc(self):
        """Toggle OSC connection."""
        try:
            osc = bpy.context.scene.holo_osc_settings
            if osc.connected:
                bpy.ops.holophonix.osc_disconnect()
            else:
                bpy.ops.holophonix.osc_connect()
        except Exception as e:
            self.log_text.append(f"OSC toggle error: {e}")
    
    def play_selected(self):
        """Start playback."""
        try:
            bpy.ops.holophonix.play_selected()
            self.log_text.append("Playback started")
        except Exception as e:
            self.log_text.append(f"Play error: {e}")
    
    def stop_all(self):
        """Stop all playback."""
        try:
            bpy.ops.holophonix.stop_all()
            self.log_text.append("Playback stopped")
        except Exception as e:
            self.log_text.append(f"Stop error: {e}")
    
    def set_model(self, model_id):
        """Set animation model."""
        try:
            bpy.ops.holophonix.set_anim_model(model_id=model_id)
            self.log_text.append(f"Model set to: {model_id}")
        except Exception as e:
            self.log_text.append(f"Model set error: {e}")
    
    def osc_dump(self):
        """Trigger OSC dump."""
        try:
            bpy.ops.holophonix.osc_dump()
            self.log_text.append("OSC dump triggered")
        except Exception as e:
            self.log_text.append(f"OSC dump error: {e}")
    
    def update_loop_mode(self, mode_text):
        """Update loop mode."""
        try:
            mode_map = {"Once": "ONCE", "Loop": "LOOP", "Ping-Pong": "PING_PONG"}
            mode = mode_map.get(mode_text, "LOOP")
            # Store loop mode as a custom property on the scene
            bpy.context.scene["holo_quick_loop"] = mode
            self.log_text.append(f"Loop mode set to: {mode}")
        except Exception as e:
            self.log_text.append(f"Loop mode error: {e}")
    
    def update_duration(self, value):
        """Update duration."""
        duration = value / 10.0  # Convert to seconds
        self.duration_label.setText(f"Duration: {duration:.1f}s")
        try:
            # Store duration as a custom property on the scene
            bpy.context.scene["holo_quick_duration"] = duration
            # Also update the anim_params duration if available
            params_pg = getattr(bpy.context.scene, 'holo_anim_params', None)
            if params_pg:
                params_pg.duration = duration
        except Exception as e:
            self.log_text.append(f"Duration update error: {e}")
    
    def update_speed(self, value):
        """Update speed parameter."""
        speed = value / 100.0
        self.speed_label.setText(f"Speed: {speed:.1f}")
        self.update_blender_param("speed", speed)
    
    def update_turns(self, value):
        """Update turns parameter."""
        turns = value / 10.0
        self.turns_label.setText(f"Turns: {turns:.1f}")
        self.update_blender_param("turns", turns)
    
    def refresh_preview(self):
        """Refresh trajectory preview."""
        try:
            bpy.ops.holophonix.refresh_preview()
            self.log_text.append("Preview refreshed")
        except Exception as e:
            self.log_text.append(f"Preview error: {e}")
    
    def focus_view(self):
        """Focus view on tracks."""
        try:
            bpy.ops.holophonix.focus_view()
            self.log_text.append("View focused")
        except Exception as e:
            self.log_text.append(f"Focus view error: {e}")
    
    def import_hol(self):
        """Import .hol file."""
        try:
            bpy.ops.holophonix.import_hol()
            self.log_text.append("Import dialog opened")
        except Exception as e:
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
