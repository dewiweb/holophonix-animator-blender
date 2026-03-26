# SPDX-License-Identifier: GPL-3.0-or-later
# Import operators — .hol files and zip project archives

import bpy
import os
import json
import zipfile
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty
from ..core.track import create_track_object, TRACK_OBJECT_PREFIX
from ..core import osc as osc_core


# ─── Import .hol file ─────────────────────────────────────────────────────────

class HOL_OT_ImportHol(bpy.types.Operator, ImportHelper):
    """Import tracks and speakers from a Holophonix .hol project file."""
    bl_idname = "holophonix.import_hol"
    bl_label = "Import Holophonix Project (.hol)"
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ".hol"
    filter_glob: StringProperty(default="*.hol;*.zip", options={'HIDDEN'})

    import_tracks: BoolProperty(name="Import Tracks", default=True)
    import_speakers: BoolProperty(name="Import Speakers", default=False)
    clear_existing: BoolProperty(name="Clear Existing Tracks", default=False)

    def execute(self, context):
        path = self.filepath
        if not os.path.exists(path):
            self.report({'ERROR'}, f"File not found: {path}")
            return {'CANCELLED'}

        # Handle zip archives (Holophonix project zip)
        if path.lower().endswith(".zip"):
            return self._import_zip(context, path)
        else:
            return self._import_hol(context, path)

    def _import_zip(self, context, zip_path: str):
        """Extract and import the first .hol file found in the zip."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(tmpdir)
            # Find .hol files
            hol_files = []
            for root, dirs, files in os.walk(tmpdir):
                for fname in files:
                    if fname.endswith('.hol'):
                        hol_files.append(os.path.join(root, fname))
            if not hol_files:
                self.report({'ERROR'}, "No .hol file found in zip archive")
                return {'CANCELLED'}
            # Import first found (or the one named like the zip)
            result = self._import_hol(context, hol_files[0])
        return result

    def _import_hol(self, context, hol_path: str):
        """Parse a .hol JSON file and create track objects."""
        try:
            with open(hol_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            self.report({'ERROR'}, f"Failed to parse .hol file: {e}")
            return {'CANCELLED'}

        if self.clear_existing:
            _clear_existing_tracks(context)

        count = 0

        # Holophonix .hol structure: data["tracks"] or data["sources"]
        tracks_data = data.get("tracks") or data.get("sources") or []
        if isinstance(tracks_data, dict):
            tracks_data = list(tracks_data.values())

        if self.import_tracks:
            for track in tracks_data:
                tid = int(track.get("index") or track.get("id") or track.get("trackIndex") or 0)
                if tid <= 0:
                    continue
                name = track.get("name") or track.get("label") or f"Track {tid:03d}"
                pos = track.get("position") or track.get("xyz") or {}
                x = float(pos.get("x") or pos.get("X") or 0.0)
                y = float(pos.get("y") or pos.get("Y") or 0.0)
                z = float(pos.get("z") or pos.get("Z") or 0.0)
                create_track_object(tid, name, location=(x, y, z))
                count += 1

        self.report({'INFO'}, f"Imported {count} tracks from {os.path.basename(hol_path)}")
        return {'FINISHED'}


# ─── Discover tracks via OSC dump ────────────────────────────────────────────

class HOL_OT_DiscoverTracksOSC(bpy.types.Operator):
    """Request a /dump from Holophonix processor to discover all tracks via OSC."""
    bl_idname = "holophonix.discover_tracks_osc"
    bl_label = "Discover Tracks via OSC"
    bl_options = {'REGISTER'}
    bl_description = "Send /dump to Holophonix and import responding tracks"

    def execute(self, context):
        if not osc_core.is_available():
            self.report({'ERROR'}, "OSC not available — check connection settings")
            return {'CANCELLED'}

        # Register a one-shot handler for /track responses
        _register_dump_handler(context)
        # Send /dump request
        osc_core.send("/dump")
        self.report({'INFO'}, "Sent /dump — waiting for track responses...")
        return {'FINISHED'}


def _register_dump_handler(context):
    """Register OSC handler to create tracks from incoming /track/{id}/xyz messages."""
    def on_track_xyz(address: str, args: list):
        # address = /track/{id}/xyz
        parts = address.strip('/').split('/')
        if len(parts) >= 2 and parts[0] == 'track':
            try:
                tid = int(parts[1])
                x = float(args[0]) if len(args) > 0 else 0.0
                y = float(args[1]) if len(args) > 1 else 0.0
                z = float(args[2]) if len(args) > 2 else 0.0

                def create_in_main():
                    if not bpy.data.objects.get(f"{TRACK_OBJECT_PREFIX}{tid:03d}"):
                        create_track_object(tid, location=(x, y, z))
                    return None

                bpy.app.timers.register(create_in_main, first_interval=0.0)
            except Exception as e:
                print(f"[ImportOps] dump handler error: {e}")

    osc_core.add_handler("/track/*/xyz", on_track_xyz)


# ─── Clear helpers ────────────────────────────────────────────────────────────

def _clear_existing_tracks(context):
    to_remove = [
        obj for obj in bpy.data.objects
        if obj.name.startswith(TRACK_OBJECT_PREFIX)
    ]
    for obj in to_remove:
        bpy.data.objects.remove(obj, do_unlink=True)
    context.scene.holo_tracks.tracks.clear()


# ─── Registration ─────────────────────────────────────────────────────────────

classes = (
    HOL_OT_ImportHol,
    HOL_OT_DiscoverTracksOSC,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
