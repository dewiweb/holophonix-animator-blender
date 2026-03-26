# SPDX-License-Identifier: GPL-3.0-or-later
# Track operators — add, delete, select

import bpy
from bpy.props import IntProperty, StringProperty, BoolProperty
from ..core.track import create_track_object, delete_track_object, get_all_track_objects


class HOL_OT_TrackAdd(bpy.types.Operator):
    """Add a new Holophonix track object to the scene."""
    bl_idname = "holophonix.track_add"
    bl_label = "Add Track"
    bl_options = {'REGISTER', 'UNDO'}

    track_id: IntProperty(name="Track ID", min=1, max=999, default=1)
    track_name: StringProperty(name="Name", default="")

    def execute(self, context):
        # Auto-find next free ID if default
        if self.track_id == 1:
            existing_ids = {obj.holo_track.track_id for obj in get_all_track_objects()}
            tid = 1
            while tid in existing_ids:
                tid += 1
            self.track_id = tid

        obj = create_track_object(self.track_id, self.track_name)
        context.view_layer.objects.active = obj
        self.report({'INFO'}, f"Added track {self.track_id}")
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)


class HOL_OT_TrackDelete(bpy.types.Operator):
    """Delete the active Holophonix track."""
    bl_idname = "holophonix.track_delete"
    bl_label = "Delete Track"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        idx = context.scene.holo_tracks.active_track_index
        tracks = context.scene.holo_tracks.tracks
        if 0 <= idx < len(tracks):
            tid = tracks[idx].track_id
            delete_track_object(tid)
            self.report({'INFO'}, f"Deleted track {tid}")
        return {'FINISHED'}


class HOL_OT_TrackDeleteAll(bpy.types.Operator):
    """Delete all Holophonix track objects from the scene."""
    bl_idname = "holophonix.track_delete_all"
    bl_label = "Delete All Tracks"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        objs = get_all_track_objects()
        count = len(objs)
        for obj in objs:
            bpy.data.objects.remove(obj, do_unlink=True)
        context.scene.holo_tracks.tracks.clear()
        self.report({'INFO'}, f"Deleted {count} tracks")
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)


class HOL_OT_TrackSelect(bpy.types.Operator):
    """Select a track object by ID."""
    bl_idname = "holophonix.track_select"
    bl_label = "Select Track"
    bl_options = {'REGISTER'}

    track_id: IntProperty(name="Track ID", min=1, max=999)

    def execute(self, context):
        from ..core.track import get_track_object
        obj = get_track_object(self.track_id)
        if obj:
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            context.view_layer.objects.active = obj
        return {'FINISHED'}


class HOL_OT_OSCConnect(bpy.types.Operator):
    """Start the OSC server with current connection settings."""
    bl_idname = "holophonix.osc_connect"
    bl_label = "Connect OSC"
    bl_options = {'REGISTER'}

    def execute(self, context):
        from ..core import osc as osc_core
        s = context.scene.holo_osc_settings
        ok = osc_core.start_server(
            ip_in=s.ip_in,
            port_in=s.port_in,
            ip_out=s.ip_out,
            port_out=s.port_out,
        )
        if ok:
            s.connected = True
            self.report({'INFO'}, f"OSC connected — IN :{s.port_in}  OUT {s.ip_out}:{s.port_out}")
        else:
            s.connected = False
            self.report({'ERROR'}, "Failed to start OSC server — check console")
        return {'FINISHED'}


class HOL_OT_OSCDisconnect(bpy.types.Operator):
    """Stop the OSC server."""
    bl_idname = "holophonix.osc_disconnect"
    bl_label = "Disconnect OSC"
    bl_options = {'REGISTER'}

    def execute(self, context):
        from ..core import osc as osc_core
        osc_core.stop_server()
        context.scene.holo_osc_settings.connected = False
        self.report({'INFO'}, "OSC disconnected")
        return {'FINISHED'}


# ─── OSC settings property group ─────────────────────────────────────────────

class HOL_OSCSettings(bpy.types.PropertyGroup):
    ip_in:    bpy.props.StringProperty(name="Listen IP", default="0.0.0.0")
    port_in:  bpy.props.IntProperty(name="Listen Port", default=4003, min=1, max=65535)
    ip_out:   bpy.props.StringProperty(name="Target IP", default="holophonix.local")
    port_out: bpy.props.IntProperty(name="Target Port", default=4003, min=1, max=65535)
    connected: bpy.props.BoolProperty(name="Connected", default=False)


# ─── Registration ─────────────────────────────────────────────────────────────

classes = (
    HOL_OSCSettings,
    HOL_OT_TrackAdd,
    HOL_OT_TrackDelete,
    HOL_OT_TrackDeleteAll,
    HOL_OT_TrackSelect,
    HOL_OT_OSCConnect,
    HOL_OT_OSCDisconnect,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.holo_osc_settings = bpy.props.PointerProperty(type=HOL_OSCSettings)


def unregister():
    del bpy.types.Scene.holo_osc_settings
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
