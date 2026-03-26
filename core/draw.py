# SPDX-License-Identifier: GPL-3.0-or-later
# Trajectory visualization — draws animation paths in the 3D viewport using gpu module

import bpy
import gpu
from gpu_extras.batch import batch_for_shader
import math
from . import animation as anim_core
from . import playback as pb
from .track import get_track_object, TRACK_OBJECT_PREFIX

# ─── State ────────────────────────────────────────────────────────────────────

_draw_handle = None          # SpaceView3D draw handler
_preview_curves: dict = {}   # model_id+params_hash → list of (x,y,z) points
_preview_request: dict = {}  # pending preview: {model_id, params, origin, track_id}


# ─── Public API ───────────────────────────────────────────────────────────────

def enable():
    """Register the viewport draw handler."""
    global _draw_handle
    if _draw_handle is None:
        _draw_handle = bpy.types.SpaceView3D.draw_handler_add(
            _draw_callback, (), 'WINDOW', 'POST_VIEW'
        )


def disable():
    """Unregister the viewport draw handler."""
    global _draw_handle
    if _draw_handle is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_draw_handle, 'WINDOW')
        _draw_handle = None
    _preview_curves.clear()


def request_preview(model_id: str, params: dict, track_id: int = 0,
                    origin: tuple = (0.0, 0.0, 0.0), segments: int = 64):
    """
    Request a trajectory preview curve for a given model+params.
    Called from the panel when parameters change.
    """
    _preview_request['model_id'] = model_id
    _preview_request['params'] = params.copy()
    _preview_request['track_id'] = track_id
    _preview_request['origin'] = origin
    _preview_request['segments'] = segments
    _build_preview_curve()


def clear_preview():
    """Remove all preview curves."""
    _preview_curves.clear()


# ─── Curve building ───────────────────────────────────────────────────────────

def _build_preview_curve():
    """Compute the path points and store them for drawing."""
    if not _preview_request:
        return

    model_id = _preview_request.get('model_id', '')
    params = _preview_request.get('params', {})
    origin = _preview_request.get('origin', (0.0, 0.0, 0.0))
    segments = _preview_request.get('segments', 64)
    track_id = _preview_request.get('track_id', 0)

    if not model_id:
        return

    points = []
    for i in range(segments + 1):
        t = i / segments
        x, y, z = anim_core.compute_position(model_id, params, t, origin)
        points.append((x, y, z))

    key = f"{model_id}_{track_id}"
    _preview_curves[key] = {
        'points': points,
        'track_id': track_id,
        'active': True,
    }

    # Force viewport redraw
    for area in bpy.context.screen.areas if bpy.context.screen else []:
        if area.type == 'VIEW_3D':
            area.tag_redraw()


def build_playback_curves():
    """Build curves for all currently playing animations."""
    active = pb.get_active_animations()
    for slot_id, anim in active.items():
        segments = 64
        for tid in anim.track_ids:
            origin = anim.origins.get(tid, (0.0, 0.0, 0.0))
            points = []
            for i in range(segments + 1):
                t_norm = i / segments
                t_loop = anim_core.apply_loop_mode(t_norm, anim.loop_mode)
                x, y, z = anim_core.compute_position(anim.model_id, anim.params, t_loop, origin)
                points.append((x, y, z))
            key = f"playback_{slot_id}_{tid}"
            _preview_curves[key] = {
                'points': points,
                'track_id': tid,
                'active': True,
            }


# ─── Draw callback ────────────────────────────────────────────────────────────

def _draw_callback():
    """Called by Blender on every 3D viewport redraw."""
    if not _preview_curves:
        return

    # Also update curves for active playback animations
    if pb.get_active_animations():
        build_playback_curves()

    shader = gpu.shader.from_builtin('POLYLINE_SMOOTH_COLOR')
    gpu.state.blend_set('ALPHA')
    gpu.state.depth_test_set('LESS_EQUAL')

    region = bpy.context.region
    rv3d = bpy.context.region_data

    for key, curve_data in list(_preview_curves.items()):
        points = curve_data.get('points', [])
        if len(points) < 2:
            continue

        n = len(points)
        coords = []
        colors = []

        for i, (x, y, z) in enumerate(points):
            coords.append((x, y, z))
            # Gradient: green (start) → orange → red (end)
            t = i / (n - 1)
            r = min(1.0, t * 2.0)
            g = min(1.0, (1.0 - t) * 2.0)
            b = 0.1
            a = 0.85
            colors.append((r, g, b, a))

        try:
            batch = batch_for_shader(shader, 'LINE_STRIP', {
                "pos": coords,
                "color": colors,
            })
            shader.uniform_float("lineWidth", 2.5)
            shader.uniform_float("viewportSize", (region.width, region.height))
            batch.draw(shader)
        except Exception as e:
            print(f"[Draw] Shader error for {key}: {e}")

    gpu.state.blend_set('NONE')
    gpu.state.depth_test_set('NONE')


# ─── Registration ─────────────────────────────────────────────────────────────

def register():
    enable()


def unregister():
    disable()
