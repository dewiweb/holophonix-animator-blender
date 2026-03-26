"""Test PySide integration for Holophonix."""

import bpy
import sys

print("\n[TEST PYSIDE INTEGRATION]")

# Check if PySide is available
try:
    import PySide6
    from PySide6.QtWidgets import QApplication, QLabel
    print("[OK] PySide6 imported successfully")
except ImportError as e:
    print("[FAIL] PySide6 not available:", e)
    print("[INFO] Run: python -m pip install PySide6")
    sys.exit(1)

# Test UI creation
try:
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    label = QLabel("Holophonix PySide Test")
    print("[OK] PySide6 UI creation works")
except Exception as e:
    print("[FAIL] PySide6 UI creation failed:", e)
    sys.exit(1)

# Test Blender bridge import
try:
    from holophonix_animator.ui.pyside_window import show_pyside_window, PYSIDE_AVAILABLE
    print("[OK] Holophonix PySide module imports")
    print("[INFO] PYSIDE_AVAILABLE:", PYSIDE_AVAILABLE)
except Exception as e:
    print("[FAIL] Holophonix PySide module import failed:", e)
    sys.exit(1)

print("\n[RESULT] All PySide tests passed!")
print("[INFO] Advanced UI window available in Blender N-Panel")
print("[INFO] Click 'Advanced Control Window' button to open")
