# SPDX-License-Identifier: GPL-3.0-or-later
# Playback engine — modal operator that drives animations in real time

import bpy
import time
from bpy.props import StringProperty
from . import animation as anim_core
from . import osc as osc_core
from .track import get_track_object

TIMER_INTERVAL = 1.0 / 30.0  # 30 fps update rate


# ─── Active animation slot ────────────────────────────────────────────────────

class ActiveAnimation:
    """One running animation instance."""
    def __init__(self, slot_id: str, track_ids: list[int], model_id: str,
                 params: dict, duration: float, loop_mode: str, blend_duration: float):
        self.slot_id = slot_id
        self.track_ids = track_ids
        self.model_id = model_id
        self.params = params
        self.duration = max(duration, 0.001)
        self.loop_mode = loop_mode          # ONCE | LOOP | PING_PONG
        self.blend_duration = blend_duration
        self.start_time = time.monotonic()
        self.paused_at: float | None = None
        self.elapsed_paused = 0.0
        self.done = False
        # Store each track's origin at animation start
        self.origins: dict[int, tuple] = {}
        for tid in track_ids:
            obj = get_track_object(tid)
            if obj:
                self.origins[tid] = tuple(obj.location)
            else:
                self.origins[tid] = (0.0, 0.0, 0.0)

    def elapsed(self) -> float:
        if self.paused_at is not None:
            return self.paused_at - self.start_time - self.elapsed_paused
        return time.monotonic() - self.start_time - self.elapsed_paused

    def t_normalized(self) -> float:
        return anim_core.apply_loop_mode(self.elapsed() / self.duration, self.loop_mode)

    def pause(self):
        if self.paused_at is None:
            self.paused_at = time.monotonic()

    def resume(self):
        if self.paused_at is not None:
            self.elapsed_paused += time.monotonic() - self.paused_at
            self.paused_at = None

    def is_paused(self) -> bool:
        return self.paused_at is not None

    def is_finished(self) -> bool:
        if self.loop_mode == 'ONCE' and self.elapsed() >= self.duration:
            return True
        return self.done


# ─── Global playback state ────────────────────────────────────────────────────

_active_animations: dict[str, ActiveAnimation] = {}   # slot_id → ActiveAnimation
_modal_running = False


def get_active_animations() -> dict[str, ActiveAnimation]:
    return _active_animations


def is_playing() -> bool:
    return _modal_running and len(_active_animations) > 0


def play(slot_id: str, track_ids: list[int], model_id: str, params: dict,
         duration: float, loop_mode: str = 'LOOP', blend_duration: float = 0.0):
    """Start or replace an animation slot."""
    _active_animations[slot_id] = ActiveAnimation(
        slot_id, track_ids, model_id, params, duration, loop_mode, blend_duration
    )
    _ensure_modal_running()


def stop(slot_id: str):
    """Stop a specific animation slot."""
    _active_animations.pop(slot_id, None)


def stop_all():
    """Stop all running animations."""
    _active_animations.clear()


def pause_all():
    for a in _active_animations.values():
        a.pause()


def resume_all():
    for a in _active_animations.values():
        a.resume()


# ─── Modal operator ───────────────────────────────────────────────────────────

def _ensure_modal_running():
    global _modal_running
    if not _modal_running:
        bpy.ops.holophonix.playback_modal('INVOKE_DEFAULT')


class HOL_OT_PlaybackModal(bpy.types.Operator):
    """Internal modal operator — drives real-time animation playback."""
    bl_idname = "holophonix.playback_modal"
    bl_label = "Holophonix Playback"
    bl_options = {'INTERNAL'}

    _timer = None

    def modal(self, context, event):
        global _modal_running

        if event.type == 'TIMER':
            # Tick all active animations
            finished = []
            for slot_id, anim in list(_active_animations.items()):
                if anim.is_paused():
                    continue
                if anim.is_finished():
                    finished.append(slot_id)
                    continue
                t = anim.t_normalized()
                for tid in anim.track_ids:
                    origin = anim.origins.get(tid, (0.0, 0.0, 0.0))
                    x, y, z = anim_core.compute_position(anim.model_id, anim.params, t, origin)
                    obj = get_track_object(tid)
                    if obj:
                        obj.location = (x, y, z)
                    osc_core.send_xyz(tid, x, y, z)

            for slot_id in finished:
                _active_animations.pop(slot_id, None)

            if _active_animations:
                context.area.tag_redraw() if context.area else None
            else:
                # No more animations — stop modal
                self._stop(context)
                _modal_running = False
                return {'FINISHED'}

        # Allow ESC to stop all
        if event.type == 'ESC' and event.value == 'PRESS':
            stop_all()
            self._stop(context)
            _modal_running = False
            return {'FINISHED'}

        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        global _modal_running
        if _modal_running:
            return {'CANCELLED'}
        _modal_running = True
        wm = context.window_manager
        self._timer = wm.event_timer_add(TIMER_INTERVAL, window=context.window)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def _stop(self, context):
        if self._timer:
            context.window_manager.event_timer_remove(self._timer)
            self._timer = None


# ─── Registration ─────────────────────────────────────────────────────────────

classes = (HOL_OT_PlaybackModal,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    stop_all()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
