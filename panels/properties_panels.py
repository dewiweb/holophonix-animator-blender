# SPDX-License-Identifier: GPL-3.0-or-later
# Holophonix Animator — N-Panel (3D Viewport sidebar, tab "Holophonix")
# All controls in one place: N key → Holophonix tab

import bpy
from ..core import animation as anim_core
from ..core import playback as pb
from ..core import draw as draw_core
from ..core.track import TRACK_OBJECT_PREFIX

_SP  = 'VIEW_3D'
_RG  = 'UI'
_CAT = 'Holophonix'


# ═══════════════════════════════════════════════════════════════
#  ROOT PANEL — N-Panel tab "Holophonix"
# ═══════════════════════════════════════════════════════════════

class HOL_PT_Root(bpy.types.Panel):
    """Holophonix Animator — root panel in N-Panel sidebar."""
    bl_label       = "Holophonix Animator"
    bl_idname      = "HOL_PT_Root"
    bl_space_type  = _SP
    bl_region_type = _RG
    bl_category    = _CAT
    bl_order       = 0

    def draw(self, context):
        layout = self.layout
        # Quick status line
        s = context.scene.holo_osc_settings
        n_tracks = len(context.scene.holo_tracks.tracks)
        n_playing = len(pb.get_active_animations())

        row = layout.row(align=True)
        icon = 'LINKED' if s.connected else 'UNLINKED'
        row.label(text="OSC: " + ("Connected" if s.connected else "Disconnected"), icon=icon)

        row2 = layout.row(align=True)
        row2.label(text=f"{n_tracks} track(s)  |  {n_playing} animation(s) playing", icon='INFO')

        layout.separator()
        row3 = layout.row(align=True)
        row3.operator("holophonix.new_scene",       text="New Scene",       icon='FILE_NEW')
        row3.operator("holophonix.setup_scene",     text="Setup Scene",     icon='SCENE_DATA')
        row3.operator("holophonix.setup_workspace", text="Setup Workspace", icon='WORKSPACE')


# ═══════════════════════════════════════════════════════════════
#  OSC panel
# ═══════════════════════════════════════════════════════════════

class HOL_PT_OSC_Props(bpy.types.Panel):
    bl_label       = "OSC Connection"
    bl_idname      = "HOL_PT_OSC_Props"
    bl_space_type  = _SP
    bl_region_type = _RG
    bl_category    = _CAT
    bl_parent_id   = "HOL_PT_Root"

    def draw(self, context):
        layout = self.layout
        s = context.scene.holo_osc_settings

        col = layout.column(align=True)
        col.prop(s, "ip_out",   text="Holophonix IP")
        col.prop(s, "port_out", text="Port OUT")
        col.prop(s, "port_in",  text="Port IN (listen)")

        layout.separator()
        row = layout.row(align=True)
        if s.connected:
            row.operator("holophonix.osc_disconnect", text="Disconnect", icon='CANCEL')
        else:
            row.operator("holophonix.osc_connect",    text="Connect",    icon='PLAY')
        row.operator("holophonix.discover_tracks_osc", text="Dump", icon='RADIOBUT_ON')


# ═══════════════════════════════════════════════════════════════
#  Tracks panel
# ═══════════════════════════════════════════════════════════════

class HOL_PT_Tracks_Props(bpy.types.Panel):
    bl_label       = "Tracks"
    bl_idname      = "HOL_PT_Tracks_Props"
    bl_space_type  = _SP
    bl_region_type = _RG
    bl_category    = _CAT
    bl_parent_id   = "HOL_PT_Root"

    def draw(self, context):
        layout = self.layout
        holo = context.scene.holo_tracks

        row = layout.row(align=True)
        row.operator("holophonix.import_hol", text="Import .hol / .zip", icon='IMPORT')

        layout.template_list(
            "HOL_UL_TrackList", "holo_tracks",
            holo, "tracks",
            holo, "active_track_index",
            rows=6,
        )

        row = layout.row(align=True)
        row.operator("holophonix.track_add",        text="", icon='ADD')
        row.operator("holophonix.track_delete",     text="", icon='REMOVE')
        row.operator("holophonix.track_delete_all", text="", icon='TRASH')
        row.separator()
        row.operator("holophonix.focus_view", text="", icon='ZOOM_ALL')

        # Active track detail
        tracks = holo.tracks
        idx    = holo.active_track_index
        if 0 <= idx < len(tracks):
            item = tracks[idx]
            obj  = bpy.data.objects.get(item.object_name)
            if obj and hasattr(obj, "holo_track"):
                box = layout.box()
                col = box.column(align=True)
                col.label(text=f"Track {item.track_id}  —  {item.track_name}", icon='OBJECT_DATA')
                col.prop(obj.holo_track, "osc_direction", text="Direction")
                col.prop(obj.holo_track, "coord_system",  text="Coordinates")
                col.separator()
                # Live location display
                col.label(text=f"X={obj.location.x:.3f}  Y={obj.location.y:.3f}  Z={obj.location.z:.3f}")


class HOL_UL_TrackList(bpy.types.UIList):
    bl_idname = "HOL_UL_TrackList"

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        playing_ids = {
            tid
            for anim in pb.get_active_animations().values()
            for tid in anim.track_ids
        }
        is_playing = item.track_id in playing_ids
        row = layout.row(align=True)
        row.label(
            text=f"{item.track_id:03d}  {item.track_name}",
            icon='PLAY' if is_playing else 'OBJECT_DATA'
        )


# ═══════════════════════════════════════════════════════════════
#  Animation panel — model selector + dynamic params + transport
# ═══════════════════════════════════════════════════════════════

class HOL_PT_Animation_Props(bpy.types.Panel):
    bl_label       = "Animation"
    bl_idname      = "HOL_PT_Animation_Props"
    bl_space_type  = _SP
    bl_region_type = _RG
    bl_category    = _CAT
    bl_parent_id   = "HOL_PT_Root"

    def draw(self, context):
        layout = self.layout
        params_pg = getattr(context.scene, 'holo_anim_params', None)
        if params_pg is None:
            return
        model = anim_core.get_model(params_pg.model_id)

        # ── Model selector ──────────────────────────────────────
        box = layout.box()
        box.label(text="Model", icon='CURVE_PATH')
        grid = box.grid_flow(row_major=True, columns=3, even_columns=True, align=True)
        for m in anim_core.get_all_models():
            mid   = m.get("id", "")
            label = m.get("label", mid)
            op = grid.operator(
                "holophonix.set_anim_model",
                text=label,
                depress=(mid == params_pg.model_id),
            )
            op.model_id = mid

        # ── Dynamic parameters ──────────────────────────────────
        if model:
            param_specs = model.get("parameters", {})
            if param_specs:
                box = layout.box()
                box.label(text="Parameters", icon='SETTINGS')
                col = box.column(align=True)
                for key, spec in param_specs.items():
                    ptype    = spec.get("type", "float")
                    label    = spec.get("label", key)
                    prop_key = f"hol_param_{key}"
                    default  = spec.get("default", 0)
                    vmin     = spec.get("min", -9999)
                    vmax     = spec.get("max",  9999)

                    row = col.row(align=True)
                    row.label(text=label)
                    if ptype == "enum":
                        row.label(text=str(context.scene.get(prop_key, default)))
                    elif prop_key in context.scene:
                        row.prop(context.scene, f'["{prop_key}"]', text="", slider=False)
                    else:
                        row.label(text=f"{default} (click model to init)")

                col.separator()
                col.operator("holophonix.refresh_preview", text="Preview Trajectory", icon='CURVE_BEZCURVE')

        # ── Timing ──────────────────────────────────────────────
        box = layout.box()
        box.label(text="Timing", icon='TIME')
        row = box.row(align=True)
        row.prop(params_pg, "duration",  text="Duration (s)")
        box.prop(params_pg, "loop_mode", text="Loop")

        # ── Transport ───────────────────────────────────────────
        box = layout.box()
        active   = pb.get_active_animations()
        n_active = len(active)
        box.label(
            text=f"Playing: {n_active}" if n_active else "Stopped",
            icon='PLAY' if n_active else 'HANDLETYPE_FREE_VEC'
        )
        row = box.row(align=True)
        row.scale_y = 1.4
        row.operator("holophonix.play_selected", text="Play Selected", icon='PLAY')
        row.operator("holophonix.stop_all",      text="Stop All",      icon='CANCEL')

        if active:
            sub = box.box()
            for slot_id, anim_obj in active.items():
                row = sub.row(align=True)
                row.label(
                    text=f"{slot_id[:18]}  {anim_obj.elapsed():.1f}s  [{anim_obj.loop_mode}]",
                    icon='KEYFRAME'
                )
                op = row.operator("holophonix.cue_stop", text="", icon='PANEL_CLOSE')
                op.cue_name = slot_id


# ═══════════════════════════════════════════════════════════════
#  Cue List panel
# ═══════════════════════════════════════════════════════════════

class HOL_PT_Cues_Props(bpy.types.Panel):
    bl_label       = "Cue List"
    bl_idname      = "HOL_PT_Cues_Props"
    bl_space_type  = _SP
    bl_region_type = _RG
    bl_category    = _CAT
    bl_parent_id   = "HOL_PT_Root"
    bl_options     = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout   = self.layout
        cue_list = context.scene.holo_cues

        layout.template_list(
            "HOL_UL_CueListProps", "holo_cues",
            cue_list, "cues",
            cue_list, "active_index",
            rows=5,
        )

        row = layout.row(align=True)
        row.operator("holophonix.cue_add",      text="",        icon='ADD')
        row.operator("holophonix.cue_remove",   text="",        icon='REMOVE')
        row.separator()
        row.operator("holophonix.cue_stop_all", text="Stop All", icon='SNAP_FACE')

        idx = cue_list.active_index
        if 0 <= idx < len(cue_list.cues):
            cue = cue_list.cues[idx]
            box = layout.box()

            # Header row: name + GO button
            row = box.row(align=True)
            row.prop(cue, "name", text="")
            row.prop(cue, "enabled", text="")
            op = row.operator("holophonix.cue_trigger", text="GO", icon='PLAY')
            op.cue_name = cue.name
            op2 = row.operator("holophonix.cue_stop", text="", icon='SNAP_FACE')
            op2.cue_name = cue.name

            col = box.column(align=True)
            col.prop(cue, "model_id",      text="Model")
            col.prop(cue, "duration",      text="Duration")
            col.prop(cue, "loop_mode",     text="Loop")
            col.prop(cue, "blend_duration", text="Blend")

            # Target tracks
            box2 = box.box()
            box2.label(text="Target Tracks:", icon='OBJECT_DATA')
            for slot in cue.target_tracks:
                row = box2.row(align=True)
                row.label(text=f"Track {slot.track_id:03d}", icon='LAYER_USED')
            row = box2.row()
            op3 = row.operator("holophonix.cue_add_track", text="Add Track", icon='ADD')
            op3.track_id = 1

            # Params JSON (raw, for power users)
            box.prop(cue, "params_json", text="Params JSON")


class HOL_UL_CueListProps(bpy.types.UIList):
    bl_idname = "HOL_UL_CueListProps"

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        playing = item.get_slot_id() in pb.get_active_animations()
        row = layout.row(align=True)
        row.prop(item, "enabled", text="")
        row.label(text=item.name,     icon='PLAY' if playing else 'RADIOBUT_OFF')
        row.label(text=item.model_id, icon='CURVE_PATH')
        op = row.operator("holophonix.cue_trigger", text="", icon='PLAY')
        op.cue_name = item.name
        op2 = row.operator("holophonix.cue_stop", text="", icon='SNAP_FACE')
        op2.cue_name = item.name


# ═══════════════════════════════════════════════════════════════
#  OBJECT context — per-track properties (Properties > Object tab)
#  Visible only when a Holophonix track object is active
# ═══════════════════════════════════════════════════════════════

class HOL_PT_TrackObject(bpy.types.Panel):
    """Per-track properties — visible in N-Panel when a track object is active."""
    bl_label       = "Track Properties"
    bl_idname      = "HOL_PT_TrackObject"
    bl_space_type  = _SP
    bl_region_type = _RG
    bl_category    = _CAT
    bl_parent_id   = "HOL_PT_Root"
    bl_options     = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj is not None
                and obj.name.startswith(TRACK_OBJECT_PREFIX)
                and hasattr(obj, 'holo_track'))

    def draw(self, context):
        layout = self.layout
        obj    = context.active_object
        tp     = obj.holo_track

        col = layout.column(align=True)
        col.prop(tp, "track_id",      text="Track ID")
        col.prop(tp, "track_name",    text="Name")
        col.prop(tp, "osc_direction", text="OSC Direction")
        col.prop(tp, "coord_system",  text="Coordinates")

        layout.separator()
        box = layout.box()
        box.label(text="Live Position", icon='EMPTY_AXIS')
        row = box.row(align=True)
        row.label(text=f"X  {obj.location.x:+.3f} m")
        row.label(text=f"Y  {obj.location.y:+.3f} m")
        row.label(text=f"Z  {obj.location.z:+.3f} m")

        layout.separator()
        # Quick play on this track
        playing_ids = {
            tid
            for anim in pb.get_active_animations().values()
            for tid in anim.track_ids
        }
        is_playing = tp.track_id in playing_ids
        row = layout.row(align=True)
        if is_playing:
            op = row.operator("holophonix.cue_stop", text="Stop", icon='SNAP_FACE')
            op.cue_name = f"selected_{tp.track_id}"
        else:
            row.operator("holophonix.play_selected", text="Play", icon='PLAY')


# ═══════════════════════════════════════════════════════════════
#  Registration
# ═══════════════════════════════════════════════════════════════

classes = (
    HOL_PT_Root,
    HOL_PT_OSC_Props,
    HOL_PT_Tracks_Props,
    HOL_UL_TrackList,
    HOL_PT_Animation_Props,
    HOL_PT_Cues_Props,
    HOL_UL_CueListProps,
    HOL_PT_TrackObject,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
