# SPDX-License-Identifier: GPL-3.0-or-later
# Track properties and management

import bpy
import math
from bpy.props import (
    StringProperty, IntProperty, FloatProperty,
    FloatVectorProperty, BoolProperty, EnumProperty, CollectionProperty
)

TRACK_OBJECT_PREFIX = "holo.track."
SPEAKER_OBJECT_PREFIX = "holo.speaker."


# ─── Per-object track properties ─────────────────────────────────────────────

class HOL_TrackProperties(bpy.types.PropertyGroup):
    """Properties stored on each track Blender object."""
    track_id: IntProperty(name="Track ID", min=1, max=999, default=1)
    track_name: StringProperty(name="Track Name", default="")
    coord_system: EnumProperty(
        name="Coordinate System",
        items=[
            ('XYZ', "XYZ (Cartesian)", "Cartesian coordinates in meters"),
            ('AED', "AED (Polar)", "Azimuth / Elevation / Distance"),
        ],
        default='XYZ'
    )
    is_selected_holo: BoolProperty(name="Selected", default=False)
    osc_direction: EnumProperty(
        name="OSC Direction",
        items=[
            ('OUTPUT', "Output", "Send position to Holophonix", 'EXPORT', 0),
            ('INPUT',  "Input",  "Receive position from Holophonix", 'IMPORT', 1),
            ('BOTH',   "Both",   "Bidirectional", 'FILE_REFRESH', 2),
        ],
        default='OUTPUT'
    )


# ─── Scene-level track list entry ────────────────────────────────────────────

class HOL_TrackListItem(bpy.types.PropertyGroup):
    """Entry in the scene track list (mirrors object track_props)."""
    track_id: IntProperty(name="ID", min=1, max=999)
    track_name: StringProperty(name="Name")
    object_name: StringProperty(name="Object")  # links to bpy.data.objects[object_name]


# ─── Scene-level properties ──────────────────────────────────────────────────

class HOL_SceneTrackProps(bpy.types.PropertyGroup):
    tracks: CollectionProperty(type=HOL_TrackListItem, name="Tracks")
    active_track_index: IntProperty(name="Active Track", default=0)


# ─── Utilities ───────────────────────────────────────────────────────────────

def get_track_object(track_id: int):
    """Return the Blender object for a given track ID, or None."""
    name = f"{TRACK_OBJECT_PREFIX}{track_id:03d}"
    return bpy.data.objects.get(name)


def get_all_track_objects():
    """Return all Blender objects that are Holophonix tracks."""
    return [
        obj for obj in bpy.data.objects
        if obj.name.startswith(TRACK_OBJECT_PREFIX) and hasattr(obj, "holo_track")
    ]


def create_track_object(track_id: int, name: str = "", location=(0.0, 0.0, 0.0)) -> bpy.types.Object:
    """Create (or reuse) a Blender object representing a Holophonix track."""
    obj_name = f"{TRACK_OBJECT_PREFIX}{track_id:03d}"

    obj = bpy.data.objects.get(obj_name)
    if obj is None:
        mesh = bpy.data.meshes.new(obj_name)
        obj = bpy.data.objects.new(obj_name, mesh)
        # Use a simple icosphere mesh for visual representation
        bpy.context.collection.objects.link(obj)

    obj.location = location
    obj.show_name = True
    obj.holo_track.track_id = track_id
    obj.holo_track.track_name = name or obj_name

    # Sync scene track list
    _sync_track_list(bpy.context.scene, track_id, name, obj_name)

    return obj


def delete_track_object(track_id: int):
    """Remove the Blender object and scene list entry for a track."""
    obj = get_track_object(track_id)
    if obj:
        bpy.data.objects.remove(obj, do_unlink=True)
    scene = bpy.context.scene
    idx = _find_track_list_index(scene, track_id)
    if idx >= 0:
        scene.holo_tracks.tracks.remove(idx)


def xyz_to_aed(x: float, y: float, z: float):
    """Convert Cartesian (m) to Azimuth(°), Elevation(°), Distance(m)."""
    d = math.sqrt(x**2 + y**2 + z**2)
    if d < 1e-9:
        return 0.0, 0.0, 0.0
    a = math.degrees(math.atan2(x, y))
    e = math.degrees(math.asin(z / d))
    return a, e, d


def aed_to_xyz(a_deg: float, e_deg: float, d: float):
    """Convert AED to Cartesian XYZ."""
    a = math.radians(a_deg)
    e = math.radians(e_deg)
    x = d * math.sin(a) * math.cos(e)
    y = d * math.cos(a) * math.cos(e)
    z = d * math.sin(e)
    return x, y, z


# ─── Internal helpers ────────────────────────────────────────────────────────

def _sync_track_list(scene, track_id: int, name: str, obj_name: str):
    props = scene.holo_tracks
    for item in props.tracks:
        if item.track_id == track_id:
            item.track_name = name
            item.object_name = obj_name
            return
    item = props.tracks.add()
    item.track_id = track_id
    item.track_name = name
    item.object_name = obj_name


def _find_track_list_index(scene, track_id: int) -> int:
    for i, item in enumerate(scene.holo_tracks.tracks):
        if item.track_id == track_id:
            return i
    return -1


# ─── Registration ────────────────────────────────────────────────────────────

classes = (
    HOL_TrackProperties,
    HOL_TrackListItem,
    HOL_SceneTrackProps,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Object.holo_track = bpy.props.PointerProperty(type=HOL_TrackProperties)
    bpy.types.Scene.holo_tracks = bpy.props.PointerProperty(type=HOL_SceneTrackProps)


def unregister():
    del bpy.types.Scene.holo_tracks
    del bpy.types.Object.holo_track
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
