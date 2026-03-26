# SPDX-License-Identifier: GPL-3.0-or-later
# Cue system — list of triggerable animation cues

import bpy
from bpy.props import (
    StringProperty, IntProperty, FloatProperty,
    BoolProperty, EnumProperty, CollectionProperty
)
from . import playback as pb


# ─── Single cue definition ────────────────────────────────────────────────────

class HOL_CueTrackSlot(bpy.types.PropertyGroup):
    """One track ID entry in a cue's target list."""
    track_id: IntProperty(name="Track ID", min=1, max=999, default=1)


class HOL_Cue(bpy.types.PropertyGroup):
    """One animation cue."""
    name: StringProperty(name="Name", default="Cue")
    enabled: BoolProperty(name="Enabled", default=True)

    # Target tracks
    target_tracks: CollectionProperty(type=HOL_CueTrackSlot)

    # Animation model
    model_id: StringProperty(name="Model", default="circular")

    # Serialized JSON parameters (simple key=value pairs via custom props)
    # We store as a JSON string for flexibility
    params_json: StringProperty(name="Parameters (JSON)", default="{}")

    # Timing
    duration: FloatProperty(name="Duration (s)", min=0.1, default=4.0, unit='TIME_ABSOLUTE')
    loop_mode: EnumProperty(
        name="Loop",
        items=[
            ('ONCE',      "Once",      "Play once and stop"),
            ('LOOP',      "Loop",      "Loop continuously"),
            ('PING_PONG', "Ping-Pong", "Loop back and forth"),
        ],
        default='LOOP'
    )
    blend_duration: FloatProperty(
        name="Blend (s)", min=0.0, default=0.5,
        description="Crossfade duration when starting this cue over an active one"
    )

    # State (runtime, not saved meaningfully)
    is_playing: BoolProperty(name="Playing", default=False)

    def get_params(self) -> dict:
        import json
        try:
            return json.loads(self.params_json) if self.params_json else {}
        except Exception:
            return {}

    def set_params(self, params: dict):
        import json
        self.params_json = json.dumps(params)

    def get_track_ids(self) -> list:
        return [slot.track_id for slot in self.target_tracks]

    def get_slot_id(self) -> str:
        """Unique slot id used in the playback engine."""
        return f"cue_{self.name}"


# ─── Scene-level cue list ─────────────────────────────────────────────────────

class HOL_CueList(bpy.types.PropertyGroup):
    cues: CollectionProperty(type=HOL_Cue)
    active_index: IntProperty(name="Active Cue", default=0)


# ─── Operators ────────────────────────────────────────────────────────────────

class HOL_OT_CueAdd(bpy.types.Operator):
    """Add a new cue to the list."""
    bl_idname = "holophonix.cue_add"
    bl_label = "Add Cue"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        cues = context.scene.holo_cues.cues
        cue = cues.add()
        cue.name = f"Cue {len(cues):03d}"
        context.scene.holo_cues.active_index = len(cues) - 1
        return {'FINISHED'}


class HOL_OT_CueRemove(bpy.types.Operator):
    """Remove the active cue."""
    bl_idname = "holophonix.cue_remove"
    bl_label = "Remove Cue"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        cue_list = context.scene.holo_cues
        idx = cue_list.active_index
        if 0 <= idx < len(cue_list.cues):
            # Stop if playing
            cue = cue_list.cues[idx]
            pb.stop(cue.get_slot_id())
            cue_list.cues.remove(idx)
            cue_list.active_index = max(0, idx - 1)
        return {'FINISHED'}


class HOL_OT_CueTrigger(bpy.types.Operator):
    """Trigger (play) a cue by name."""
    bl_idname = "holophonix.cue_trigger"
    bl_label = "Trigger Cue"
    bl_options = {'REGISTER'}

    cue_name: StringProperty(name="Cue Name")

    def execute(self, context):
        cue = _find_cue(context.scene, self.cue_name)
        if cue is None:
            self.report({'WARNING'}, f"Cue '{self.cue_name}' not found")
            return {'CANCELLED'}
        if not cue.enabled:
            return {'CANCELLED'}

        track_ids = cue.get_track_ids()
        if not track_ids:
            self.report({'WARNING'}, "Cue has no target tracks")
            return {'CANCELLED'}

        pb.play(
            slot_id=cue.get_slot_id(),
            track_ids=track_ids,
            model_id=cue.model_id,
            params=cue.get_params(),
            duration=cue.duration,
            loop_mode=cue.loop_mode,
            blend_duration=cue.blend_duration,
        )
        cue.is_playing = True
        return {'FINISHED'}


class HOL_OT_CueStop(bpy.types.Operator):
    """Stop a cue by name."""
    bl_idname = "holophonix.cue_stop"
    bl_label = "Stop Cue"
    bl_options = {'REGISTER'}

    cue_name: StringProperty(name="Cue Name")

    def execute(self, context):
        cue = _find_cue(context.scene, self.cue_name)
        if cue:
            pb.stop(cue.get_slot_id())
            cue.is_playing = False
        return {'FINISHED'}


class HOL_OT_CueStopAll(bpy.types.Operator):
    """Stop all running cues."""
    bl_idname = "holophonix.cue_stop_all"
    bl_label = "Stop All"
    bl_options = {'REGISTER'}

    def execute(self, context):
        pb.stop_all()
        for cue in context.scene.holo_cues.cues:
            cue.is_playing = False
        return {'FINISHED'}


class HOL_OT_CueAddTrack(bpy.types.Operator):
    """Add a track to the active cue's target list."""
    bl_idname = "holophonix.cue_add_track"
    bl_label = "Add Track to Cue"
    bl_options = {'REGISTER', 'UNDO'}

    track_id: IntProperty(name="Track ID", min=1, max=999, default=1)

    def execute(self, context):
        cue_list = context.scene.holo_cues
        idx = cue_list.active_index
        if 0 <= idx < len(cue_list.cues):
            cue = cue_list.cues[idx]
            slot = cue.target_tracks.add()
            slot.track_id = self.track_id
        return {'FINISHED'}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _find_cue(scene, name: str):
    for cue in scene.holo_cues.cues:
        if cue.name == name:
            return cue
    return None


# ─── Registration ─────────────────────────────────────────────────────────────

classes = (
    HOL_CueTrackSlot,
    HOL_Cue,
    HOL_CueList,
    HOL_OT_CueAdd,
    HOL_OT_CueRemove,
    HOL_OT_CueTrigger,
    HOL_OT_CueStop,
    HOL_OT_CueStopAll,
    HOL_OT_CueAddTrack,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.holo_cues = bpy.props.PointerProperty(type=HOL_CueList)


def unregister():
    del bpy.types.Scene.holo_cues
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
