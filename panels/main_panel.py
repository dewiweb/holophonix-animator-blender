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


# ─── Animation panel ─────────────────────────────────────────────────────────

class HOL_PT_Animation(bpy.types.Panel):
    bl_label = "Animation"
    bl_idname = "HOL_PT_Animation"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = PANEL_CATEGORY
    bl_order = 2

    def draw(self, context):
        layout = self.layout
        from ..core import animation as anim_core
        from ..core import playback as pb

        # Quick play on selected tracks
        box = layout.box()
        box.label(text="Quick Play", icon='PLAY')

        scene = context.scene
        box.prop(scene, "holo_quick_model", text="Model")
        box.prop(scene, "holo_quick_duration", text="Duration (s)")
        box.prop(scene, "holo_quick_loop", text="Loop")

        row = box.row(align=True)
        row.operator("holophonix.quick_play", text="Play Selected", icon='PLAY')
        row.operator("holophonix.cue_stop_all", text="Stop All", icon='SNAP_FACE')

        # Playing status
        active = pb.get_active_animations()
        if active:
            layout.label(text=f"{len(active)} animation(s) running", icon='TIME')
            for slot_id, anim in active.items():
                row = layout.row()
                row.label(text=f"  {slot_id} [{anim.loop_mode}]")
                op = row.operator("holophonix.cue_stop", text="", icon='PANEL_CLOSE')
                op.cue_name = slot_id


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


# ─── Quick play operator & scene props ───────────────────────────────────────

class HOL_OT_QuickPlay(bpy.types.Operator):
    """Play animation on currently selected track objects."""
    bl_idname = "holophonix.quick_play"
    bl_label = "Quick Play"
    bl_options = {'REGISTER'}

    def execute(self, context):
        from ..core import playback as pb
        from ..core.track import TRACK_OBJECT_PREFIX

        selected_ids = []
        for obj in context.selected_objects:
            if obj.name.startswith(TRACK_OBJECT_PREFIX) and hasattr(obj, "holo_track"):
                selected_ids.append(obj.holo_track.track_id)

        if not selected_ids:
            self.report({'WARNING'}, "No Holophonix track objects selected")
            return {'CANCELLED'}

        scene = context.scene
        pb.play(
            slot_id=f"quick_{'_'.join(str(i) for i in selected_ids)}",
            track_ids=selected_ids,
            model_id=scene.holo_quick_model,
            params={},
            duration=scene.holo_quick_duration,
            loop_mode=scene.holo_quick_loop,
        )
        return {'FINISHED'}


# ─── Registration ─────────────────────────────────────────────────────────────

classes = (
    HOL_PT_OSC,
    HOL_PT_Tracks,
    HOL_PT_Animation,
    HOL_PT_Cues,
    HOL_UL_CueList,
    HOL_OT_QuickPlay,
)


def register():
    from ..core import animation as anim_core
    anim_core.load_all_models()

    for cls in classes:
        bpy.utils.register_class(cls)

    # Quick-play scene properties
    bpy.types.Scene.holo_quick_model = bpy.props.EnumProperty(
        name="Model",
        items=anim_core.get_model_enum_items,
    )
    bpy.types.Scene.holo_quick_duration = bpy.props.FloatProperty(
        name="Duration", default=4.0, min=0.1, unit='TIME_ABSOLUTE'
    )
    bpy.types.Scene.holo_quick_loop = bpy.props.EnumProperty(
        name="Loop",
        items=[
            ('ONCE',      "Once",      "Play once"),
            ('LOOP',      "Loop",      "Loop continuously"),
            ('PING_PONG', "Ping-Pong", "Ping-pong loop"),
        ],
        default='LOOP'
    )


def unregister():
    del bpy.types.Scene.holo_quick_loop
    del bpy.types.Scene.holo_quick_duration
    del bpy.types.Scene.holo_quick_model
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
