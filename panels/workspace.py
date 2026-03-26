# SPDX-License-Identifier: GPL-3.0-or-later
# Workspace setup — creates a dedicated Holophonix layout in Blender

import bpy


# ─── Operator: Setup workspace ────────────────────────────────────────────────

class HOL_OT_SetupWorkspace(bpy.types.Operator):
    """Create or switch to the dedicated Holophonix Animator workspace."""
    bl_idname = "holophonix.setup_workspace"
    bl_label = "Setup Holophonix Workspace"
    bl_options = {'REGISTER'}

    def execute(self, context):
        ws = _get_or_create_workspace(context, "Holophonix")
        if ws is None:
            self.report({'ERROR'}, "Could not create workspace")
            return {'CANCELLED'}

        # Switch to it
        context.window.workspace = ws
        self.report({'INFO'}, "Switched to Holophonix workspace")
        return {'FINISHED'}


class HOL_OT_SetupScene(bpy.types.Operator):
    """Configure the current scene for Holophonix use (units, grid, clip)."""
    bl_idname = "holophonix.setup_scene"
    bl_label = "Setup Scene for Holophonix"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene

        # Units: metric, 1 unit = 1 meter
        scene.unit_settings.system = 'METRIC'
        scene.unit_settings.scale_length = 1.0
        scene.unit_settings.length_unit = 'METERS'

        # FPS: 30 (matches our 30fps playback timer)
        scene.render.fps = 30

        # Clip range: enough for long sessions
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.clip_start = 0.01
                        space.clip_end = 1000.0
                        # Show floor grid at 1m intervals
                        space.overlay.grid_scale = 1.0
                        space.overlay.show_floor = True
                        space.overlay.show_axis_x = True
                        space.overlay.show_axis_y = True
                        space.overlay.show_axis_z = False
                        # Show object names
                        space.overlay.show_object_origins = True

        self.report({'INFO'}, "Scene configured for Holophonix (metric, 30fps)")
        return {'FINISHED'}


class HOL_OT_NewScene(bpy.types.Operator):
    """Clear default objects and configure scene for Holophonix."""
    bl_idname  = "holophonix.new_scene"
    bl_label   = "New Holophonix Scene"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Remove all default objects
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete()

        # Setup scene settings
        bpy.ops.holophonix.setup_scene()

        self.report({'INFO'}, "New Holophonix scene ready")
        return {'FINISHED'}


class HOL_OT_FocusView(bpy.types.Operator):
    """Frame all Holophonix tracks in the viewport."""
    bl_idname = "holophonix.focus_view"
    bl_label = "Focus on Tracks"
    bl_options = {'REGISTER'}

    def execute(self, context):
        from ..core.track import TRACK_OBJECT_PREFIX
        # Select all track objects
        bpy.ops.object.select_all(action='DESELECT')
        found = False
        for obj in bpy.data.objects:
            if obj.name.startswith(TRACK_OBJECT_PREFIX):
                obj.select_set(True)
                found = True
        if found:
            bpy.ops.view3d.view_selected()
        else:
            self.report({'WARNING'}, "No tracks in scene")
        return {'FINISHED'}


# ─── Header / top bar buttons ─────────────────────────────────────────────────

class HOL_HT_Header(bpy.types.Header):
    """Holophonix quick-access buttons in the 3D view header."""
    bl_space_type = 'VIEW_3D'

    def draw(self, context):
        layout = self.layout
        from ..core import playback as pb
        from ..core import osc as osc_core

        row = layout.row(align=True)
        row.separator()

        # OSC status indicator
        s = context.scene.holo_osc_settings
        connected = s.connected
        icon = 'LINKED' if connected else 'UNLINKED'
        if connected:
            row.operator("holophonix.osc_disconnect", text="OSC", icon=icon, depress=True)
        else:
            row.operator("holophonix.osc_connect", text="OSC", icon=icon)

        row.separator()

        # Quick playback controls
        n_playing = len(pb.get_active_animations())
        if n_playing > 0:
            row.label(text=f"{n_playing} playing", icon='PLAY')
            row.operator("holophonix.stop_all", text="", icon='SNAP_FACE')
        else:
            row.operator("holophonix.play_selected", text="Play", icon='PLAY')

        row.separator()

        # Focus view
        row.operator("holophonix.focus_view", text="", icon='ZOOM_ALL')

        # Setup scene button
        row.operator("holophonix.setup_scene", text="", icon='SCENE_DATA')


# ─── Keymap registration ──────────────────────────────────────────────────────

_keymaps = []


def _register_keymaps():
    """Deferred keymap registration — must run after all operators are registered."""
    kc = bpy.context.window_manager.keyconfigs.addon
    if not kc:
        return None  # timers: returning None means don't repeat

    km = kc.keymaps.new(name='3D View', space_type='VIEW_3D')

    kmi = km.keymap_items.new("holophonix.play_selected",  type='F5', value='PRESS')
    _keymaps.append((km, kmi))

    kmi = km.keymap_items.new("holophonix.stop_all",       type='F6', value='PRESS')
    _keymaps.append((km, kmi))

    kmi = km.keymap_items.new("holophonix.refresh_preview", type='F7', value='PRESS')
    _keymaps.append((km, kmi))

    kmi = km.keymap_items.new("holophonix.focus_view", type='H',
                               value='PRESS', ctrl=True, shift=True)
    _keymaps.append((km, kmi))
    return None  # don't repeat


def _unregister_keymaps():
    for km, kmi in _keymaps:
        km.keymap_items.remove(kmi)
    _keymaps.clear()


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _get_or_create_workspace(context, name: str):
    """Return existing workspace or duplicate the current one."""
    # Check if workspace already exists
    for ws in bpy.data.workspaces:
        if ws.name == name:
            return ws

    # Duplicate current workspace and rename
    bpy.ops.workspace.duplicate()
    new_ws = context.window.workspace
    new_ws.name = name
    return new_ws


# ─── Registration ─────────────────────────────────────────────────────────────

classes = (
    HOL_OT_SetupWorkspace,
    HOL_OT_SetupScene,
    HOL_OT_NewScene,
    HOL_OT_FocusView,
    HOL_HT_Header,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    # Defer keymap registration until Blender's context is fully ready
    bpy.app.timers.register(_register_keymaps, first_interval=0.1)


def unregister():
    _unregister_keymaps()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
