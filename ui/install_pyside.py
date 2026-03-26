# SPDX-License-Identifier: GPL-3.0-or-later
# PySide Installation Helper for Holophonix

import bpy
import subprocess
import sys
import platform


class HOL_OT_InstallPySide(bpy.types.Operator):
    """Install PySide6 for advanced UI window."""
    bl_idname = "holophonix.install_pyside"
    bl_label = "Install PySide6"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        try:
            # Determine Blender Python executable
            blender_python = sys.executable
            
            # Install PySide6
            self.report({'INFO'}, "Installing PySide6... This may take a few minutes.")
            
            result = subprocess.run([
                blender_python, "-m", "pip", "install", "PySide6"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                self.report({'INFO'}, "PySide6 installed successfully! Reload Blender to use advanced UI.")
                return {'FINISHED'}
            else:
                self.report({'ERROR'}, f"Installation failed: {result.stderr}")
                return {'CANCELLED'}
                
        except Exception as e:
            self.report({'ERROR'}, f"Installation error: {e}")
            return {'CANCELLED'}


class HOL_OT_CheckPySide(bpy.types.Operator):
    """Check if PySide6 is available."""
    bl_idname = "holophonix.check_pyside"
    bl_label = "Check PySide6"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        try:
            import PySide6
            self.report({'INFO'}, "PySide6 is available!")
            return {'FINISHED'}
        except ImportError:
            self.report({'WARNING'}, "PySide6 not found. Install it to use advanced UI.")
            return {'CANCELLED'}


def check_pyside_available():
    """Check if PySide6 is available."""
    try:
        import PySide6
        return True
    except ImportError:
        return False


classes = (
    HOL_OT_InstallPySide,
    HOL_OT_CheckPySide,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
