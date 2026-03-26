# SPDX-License-Identifier: GPL-3.0-or-later
# Holophonix Animator — Blender addon for spatial audio animation
# Based in part on NodeOSC by maybites (GPL v3)

bl_info = {
    "name": "Holophonix Animator",
    "author": "Dewiweb",
    "description": "Spatial audio animation tool for Holophonix processors",
    "blender": (4, 2, 0),
    "version": (0, 1, 0),
    "location": "Properties > Scene > Holophonix Animator",
    "warning": "Beta — Blender 5.0 compatible",
    "doc_url": "",
    "tracker_url": "",
    "category": "Animation",
}

import bpy
from . import auto_load

auto_load.init()


def _init_scene_props(scene):
    """Touch PropertyGroups so Blender initializes them on an existing scene."""
    _ = scene.holo_tracks
    _ = scene.holo_cues
    _ = scene.holo_osc_settings
    _ = scene.holo_anim_params


def _on_first_depsgraph(scene, depsgraph):
    """One-shot handler: initialize props on all scenes, then remove self."""
    for s in bpy.data.scenes:
        try:
            _init_scene_props(s)
        except Exception:
            pass
    bpy.app.handlers.depsgraph_update_post.remove(_on_first_depsgraph)


def register():
    auto_load.register()
    # Initialize PropertyGroups on existing scenes (reload-safe)
    bpy.app.handlers.depsgraph_update_post.append(_on_first_depsgraph)


def unregister():
    if _on_first_depsgraph in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(_on_first_depsgraph)
    auto_load.unregister()
