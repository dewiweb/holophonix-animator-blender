# SPDX-License-Identifier: GPL-3.0-or-later
# Animation panel — dynamic parameters from JSON model + live trajectory preview

import bpy
from bpy.props import (
    FloatProperty, IntProperty, StringProperty,
    EnumProperty, BoolProperty, CollectionProperty
)
from ..core import animation as anim_core
from ..core import draw as draw_core
from ..core import playback as pb

PANEL_CATEGORY = "Holophonix"


# ─── Per-scene animation parameter storage ────────────────────────────────────

class HOL_AnimParamItem(bpy.types.PropertyGroup):
    """One key-value pair for animation parameters (stored as strings, cast on use)."""
    key:   StringProperty(name="Key")
    value: StringProperty(name="Value")
    param_type: StringProperty(name="Type", default="float")  # float | int | enum


class HOL_AnimParams(bpy.types.PropertyGroup):
    """Current model parameters — updated whenever a widget changes."""
    model_id:  StringProperty(name="Model", default="circular")
    duration:  FloatProperty(name="Duration (s)", default=4.0, min=0.1, max=600.0)
    loop_mode: EnumProperty(
        name="Loop",
        items=[
            ('ONCE',      "Once",      "Play once and stop"),
            ('LOOP',      "Loop",      "Loop continuously"),
            ('PING_PONG', "Ping-Pong", "Ping-pong loop"),
        ],
        default='LOOP'
    )
    params: CollectionProperty(type=HOL_AnimParamItem)

    def get_params_dict(self) -> dict:
        return {item.key: _cast_value(item.value, item.param_type) for item in self.params}

    def set_param(self, key: str, value, param_type: str = "float"):
        for item in self.params:
            if item.key == key:
                item.value = str(value)
                item.param_type = param_type
                return
        item = self.params.add()
        item.key = key
        item.value = str(value)
        item.param_type = param_type

    def init_from_model(self, model_id: str):
        """Load default values from JSON model definition."""
        self.model_id = model_id
        model = anim_core.get_model(model_id)
        if not model:
            return
        self.params.clear()
        for key, spec in model.get("parameters", {}).items():
            item = self.params.add()
            item.key = key
            item.value = str(spec.get("default", 0))
            item.param_type = spec.get("type", "float")


def _cast_value(s: str, param_type: str):
    try:
        if param_type == "int":
            return int(float(s))
        elif param_type == "float":
            return float(s)
        else:
            return s
    except (ValueError, TypeError):
        return s


# ─── Update callbacks ─────────────────────────────────────────────────────────

def _on_model_change(scene, model_id: str):
    """Initialize parameters and refresh preview when model changes."""
    scene.holo_anim_params.init_from_model(model_id)
    _refresh_preview(scene)


def _refresh_preview(scene):
    """Recompute and draw the trajectory preview in the viewport."""
    params_pg = scene.holo_anim_params
    model_id = params_pg.model_id
    params = params_pg.get_params_dict()

    # Get origin from active track if any
    origin = (0.0, 0.0, 0.0)
    tracks = scene.holo_tracks.tracks
    idx = scene.holo_tracks.active_track_index
    if 0 <= idx < len(tracks):
        obj = bpy.data.objects.get(tracks[idx].object_name)
        if obj:
            origin = tuple(obj.location)

    draw_core.request_preview(model_id, params, origin=origin)


# ─── Operators for dynamic parameter control ──────────────────────────────────

class HOL_OT_SetAnimModel(bpy.types.Operator):
    """Set the animation model and initialize its parameters."""
    bl_idname = "holophonix.set_anim_model"
    bl_label = "Set Animation Model"
    bl_options = {'REGISTER', 'UNDO'}

    model_id: StringProperty(name="Model ID")

    def execute(self, context):
        _on_model_change(context.scene, self.model_id)
        return {'FINISHED'}


class HOL_OT_RefreshPreview(bpy.types.Operator):
    """Refresh the trajectory preview in the viewport."""
    bl_idname = "holophonix.refresh_preview"
    bl_label = "Refresh Preview"
    bl_options = {'REGISTER'}

    def execute(self, context):
        _refresh_preview(context.scene)
        return {'FINISHED'}


class HOL_OT_PlaySelected(bpy.types.Operator):
    """Play the current animation model on selected Holophonix track objects."""
    bl_idname = "holophonix.play_selected"
    bl_label = "Play Selected"
    bl_options = {'REGISTER'}

    def execute(self, context):
        selected_ids = _get_selected_track_ids(context)
        if not selected_ids:
            self.report({'WARNING'}, "No Holophonix track objects selected")
            return {'CANCELLED'}

        params_pg = context.scene.holo_anim_params
        pb.play(
            slot_id=f"selected_{'_'.join(str(i) for i in selected_ids)}",
            track_ids=selected_ids,
            model_id=params_pg.model_id,
            params=params_pg.get_params_dict(),
            duration=params_pg.duration,
            loop_mode=params_pg.loop_mode,
        )
        # Show playback curves
        draw_core.build_playback_curves()
        return {'FINISHED'}


class HOL_OT_StopAll(bpy.types.Operator):
    """Stop all running animations."""
    bl_idname = "holophonix.stop_all"
    bl_label = "Stop All"
    bl_options = {'REGISTER'}

    def execute(self, context):
        pb.stop_all()
        draw_core.clear_preview()
        for cue in context.scene.holo_cues.cues:
            cue.is_playing = False
        return {'FINISHED'}


# ─── Main Animation panel ─────────────────────────────────────────────────────

class HOL_PT_AnimationMain(bpy.types.Panel):
    bl_label = "Animation"
    bl_idname = "HOL_PT_AnimationMain"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = PANEL_CATEGORY
    bl_order = 2

    def draw(self, context):
        layout = self.layout
        params_pg = context.scene.holo_anim_params
        model = anim_core.get_model(params_pg.model_id)

        # ── Model selector ──
        box = layout.box()
        box.label(text="Model", icon='CURVE_PATH')
        row = box.row(align=True)

        # Draw model buttons (like radio buttons)
        for m in anim_core.get_all_models():
            mid = m.get("id", "")
            label = m.get("label", mid)
            is_active = (mid == params_pg.model_id)
            op = row.operator(
                "holophonix.set_anim_model",
                text=label,
                depress=is_active,
            )
            op.model_id = mid

        # ── Dynamic parameters ──
        if model:
            param_specs = model.get("parameters", {})
            if param_specs:
                box = layout.box()
                box.label(text="Parameters", icon='SETTINGS')
                for key, spec in param_specs.items():
                    ptype = spec.get("type", "float")
                    label = spec.get("label", key)
                    # Find current value in storage
                    current_val = _get_param_value(params_pg, key, spec.get("default", 0), ptype)

                    row = box.row()
                    row.label(text=label)
                    # We use a prop_search-style approach via operator + custom property
                    # Stored in scene custom props for live editing
                    prop_key = f"hol_param_{key}"
                    if prop_key not in context.scene:
                        context.scene[prop_key] = current_val

                    if ptype == "enum":
                        items_list = spec.get("items", [])
                        # For enum we just show the current value as text for now
                        row.label(text=str(context.scene.get(prop_key, current_val)))
                    elif ptype == "int":
                        row.prop(context.scene, f'["{prop_key}"]', text="", slider=False)
                    else:
                        row.prop(context.scene, f'["{prop_key}"]', text="", slider=False)

                # Preview refresh button
                row = box.row()
                row.operator("holophonix.refresh_preview", text="Preview Trajectory", icon='CURVE_BEZCURVE')

        # ── Timing ──
        box = layout.box()
        box.label(text="Timing", icon='TIME')
        box.prop(params_pg, "duration")
        box.prop(params_pg, "loop_mode")

        # ── Transport ──
        box = layout.box()
        active = pb.get_active_animations()
        n_playing = len(active)
        label = f"Playing: {n_playing}" if n_playing else "Stopped"
        box.label(text=label, icon='PLAY' if n_playing else 'SNAP_FACE')

        row = box.row(align=True)
        row.operator("holophonix.play_selected", text="Play Selected", icon='PLAY')
        row.operator("holophonix.stop_all", text="Stop All", icon='SNAP_FACE')

        # Running animation slots
        if active:
            sub = box.box()
            for slot_id, anim_obj in active.items():
                row = sub.row()
                t = anim_obj.elapsed()
                row.label(text=f"{slot_id[:20]}  {t:.1f}s", icon='KEYTYPE_MOVING_HOLD_VEC')
                op = row.operator("holophonix.cue_stop", text="", icon='PANEL_CLOSE')
                op.cue_name = slot_id


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_selected_track_ids(context) -> list:
    return [
        obj.holo_track.track_id
        for obj in context.selected_objects
        if obj.name.startswith(TRACK_OBJECT_PREFIX) and hasattr(obj, "holo_track")
    ]


def _get_param_value(params_pg, key: str, default, ptype: str):
    for item in params_pg.params:
        if item.key == key:
            return _cast_value(item.value, ptype)
    return default


# ─── Registration ─────────────────────────────────────────────────────────────

classes = (
    HOL_AnimParamItem,
    HOL_AnimParams,
    HOL_OT_SetAnimModel,
    HOL_OT_RefreshPreview,
    HOL_OT_PlaySelected,
    HOL_OT_StopAll,
    HOL_PT_AnimationMain,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.holo_anim_params = bpy.props.PointerProperty(type=HOL_AnimParams)


def unregister():
    del bpy.types.Scene.holo_anim_params
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
