# SPDX-License-Identifier: GPL-3.0-or-later
# UI Operators for Holophonix

import bpy

class HOL_OT_OpenPySideWindow(bpy.types.Operator):
    """Open the advanced Holophonix control window (PySide)."""
    bl_idname = "holophonix.open_pyside_window"
    bl_label = "Advanced Control Window"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            from ..ui.pyside_window import show_pyside_window
            success = show_pyside_window()
            if success:
                self.report({'INFO'}, "Holophonix Advanced Window opened")
                return {'FINISHED'}
            else:
                self.report({'WARNING'}, "PySide not available. Install PySide6 to use this feature.")
                return {'CANCELLED'}
        except ImportError as e:
            self.report({'ERROR'}, f"Failed to import PySide: {e}")
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to open window: {e}")
            return {'CANCELLED'}


class HOL_OT_ClosePySideWindow(bpy.types.Operator):
    """Close the advanced Holophonix control window."""
    bl_idname = "holophonix.close_pyside_window"
    bl_label = "Close Advanced Window"
    bl_options = {'REGISTER'}

    def execute(self, context):
        try:
            from ..ui.pyside_window import close_pyside_window
            close_pyside_window()
            self.report({'INFO'}, "Holophonix Advanced Window closed")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to close window: {e}")
            return {'CANCELLED'}


classes = (
    HOL_OT_OpenPySideWindow,
    HOL_OT_ClosePySideWindow,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
