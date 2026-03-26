# SPDX-License-Identifier: GPL-3.0-or-later
# Main N-Panel — Holophonix Animator

import bpy


PANEL_CATEGORY = "Holophonix"


# ─── OSC Connection panel ─────────────────────────────────────────────────────

class HOL_PT_OSC(bpy.types.Panel):
    bl_label = "OSC Connection"
    bl_idname = "HOL_PT_OSC"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = PANEL_CATEGORY
    bl_order = 0

    def draw(self, context):
        layout = self.layout
        s = context.scene.holo_osc_settings

        connected = s.connected
        icon = 'LINKED' if connected else 'UNLINKED'
        layout.label(text="Status: " + ("Connected" if connected else "Disconnected"), icon=icon)

        col = layout.column(align=True)
        col.prop(s, "ip_out", text="Holophonix IP")
        col.prop(s, "port_out", text="Port OUT")
        col.prop(s, "port_in", text="Port IN (listen)")

        row = layout.row(align=True)
        if connected:
            row.operator("holophonix.osc_disconnect", text="Disconnect", icon='CANCEL')
        else:
            row.operator("holophonix.osc_connect", text="Connect", icon='PLAY')

        layout.separator()
        row = layout.row(align=True)
        row.operator("holophonix.setup_workspace", text="Setup Workspace", icon='WORKSPACE')
        row.operator("holophonix.setup_scene", text="Setup Scene", icon='SCENE_DATA')


# ─── Tracks panel ─────────────────────────────────────────────────────────────

class HOL_PT_Tracks(bpy.types.Panel):
    bl_label = "Tracks"
    bl_idname = "HOL_PT_Tracks"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = PANEL_CATEGORY
    bl_order = 1

    def draw(self, context):
        layout = self.layout
        holo = context.scene.holo_tracks

        # Import row
        row = layout.row(align=True)
        row.operator("holophonix.import_hol", text="Import .hol / .zip", icon='IMPORT')
        row.operator("holophonix.discover_tracks_osc", text="", icon='RADIOBUT_ON')

        # Track list
        layout.template_list(
            "UI_UL_list", "holo_tracks",
            holo, "tracks",
            holo, "active_track_index",
            rows=5,
        )

        row = layout.row(align=True)
        row.operator("holophonix.track_add", text="", icon='ADD')
        row.operator("holophonix.track_delete", text="", icon='REMOVE')
        row.operator("holophonix.track_delete_all", text="", icon='TRASH')

        # Active track properties
        tracks = holo.tracks
        idx = holo.active_track_index
        if 0 <= idx < len(tracks):
            item = tracks[idx]
            obj = bpy.data.objects.get(item.object_name)
            if obj and hasattr(obj, "holo_track"):
                box = layout.box()
                box.label(text=f"Track {item.track_id}: {item.track_name}", icon='OBJECT_DATA')
                box.prop(obj.holo_track, "osc_direction", text="Direction")
                box.prop(obj.holo_track, "coord_system", text="Coords")


# ─── Cue list panel ───────────────────────────────────────────────────────────

class HOL_PT_Cues(bpy.types.Panel):
    bl_label = "Cue List"
    bl_idname = "HOL_PT_Cues"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = PANEL_CATEGORY
    bl_order = 3

    def draw(self, context):
        layout = self.layout
        cue_list = context.scene.holo_cues

        layout.template_list(
            "HOL_UL_CueList", "holo_cues",
            cue_list, "cues",
            cue_list, "active_index",
            rows=6,
        )

        row = layout.row(align=True)
        row.operator("holophonix.cue_add", text="", icon='ADD')
        row.operator("holophonix.cue_remove", text="", icon='REMOVE')
        row.separator()
        row.operator("holophonix.cue_stop_all", text="Stop All", icon='SNAP_FACE')

        # Active cue detail
        idx = cue_list.active_index
        if 0 <= idx < len(cue_list.cues):
            cue = cue_list.cues[idx]
            box = layout.box()
            box.prop(cue, "name", text="Name")
            box.prop(cue, "enabled", text="Enabled")
            box.prop(cue, "model_id", text="Model")
            box.prop(cue, "duration", text="Duration")
            box.prop(cue, "loop_mode", text="Loop")
            box.prop(cue, "blend_duration", text="Blend")
            box.prop(cue, "params_json", text="Params (JSON)")

            # Target tracks
            box.label(text="Target Tracks:")
            for slot in cue.target_tracks:
                row = box.row()
                row.label(text=f"  Track {slot.track_id}")
            row = box.row(align=True)
            op = row.operator("holophonix.cue_add_track", text="Add Track", icon='ADD')
            op.track_id = 1

            # Trigger button
            row = layout.row(align=True)
            op = row.operator("holophonix.cue_trigger", text="GO", icon='PLAY')
            op.cue_name = cue.name
            op2 = row.operator("holophonix.cue_stop", text="Stop", icon='SNAP_FACE')
            op2.cue_name = cue.name


# ─── Cue list UIList ──────────────────────────────────────────────────────────

class HOL_UL_CueList(bpy.types.UIList):
    bl_idname = "HOL_UL_CueList"

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        from ..core import playback as pb
        playing = item.get_slot_id() in pb.get_active_animations()
        row = layout.row(align=True)
        row.prop(item, "enabled", text="")
        icon_play = 'PLAY' if playing else 'RADIOBUT_OFF'
        row.label(text=item.name, icon=icon_play)
        row.label(text=item.model_id)

        op = row.operator("holophonix.cue_trigger", text="", icon='PLAY')
        op.cue_name = item.name
        op2 = row.operator("holophonix.cue_stop", text="", icon='SNAP_FACE')
        op2.cue_name = item.name


# ─── Registration ─────────────────────────────────────────────────────────────

classes = (
    HOL_PT_OSC,
    HOL_PT_Tracks,
    HOL_PT_Cues,
    HOL_UL_CueList,
)


def register():
    from ..core import animation as anim_core
    anim_core.load_all_models()
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
