# SPDX-License-Identifier: GPL-3.0-or-later
# Holophonix Animator — Blender addon for spatial audio animation
# Based in part on NodeOSC by maybites (GPL v3)

bl_info = {
    "name": "Holophonix Animator",
    "author": "Dewiweb",
    "description": "Spatial audio animation tool for Holophonix processors",
    "blender": (4, 2, 0),
    "version": (0, 1, 0),
    "location": "3D View > N-Panel > Holophonix",
    "warning": "Beta — Blender 5.0 compatible",
    "doc_url": "",
    "tracker_url": "",
    "category": "Animation",
}

import bpy
from . import auto_load

auto_load.init()

def register():
    auto_load.register()

def unregister():
    auto_load.unregister()
