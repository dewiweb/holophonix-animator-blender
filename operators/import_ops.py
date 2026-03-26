# SPDX-License-Identifier: GPL-3.0-or-later
# Import operators — .hol files and zip project archives

import bpy
import os
import json
import zipfile
import math
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty
from ..core.track import create_track_object, TRACK_OBJECT_PREFIX
from ..core import osc as osc_core


def _sph2cart(elev_deg: float, azim_deg: float, radius: float):
    """Holophonix spherical (elev, azim, radius) → Cartesian (x, y, z)."""
    e = math.radians(elev_deg)
    a = math.radians(azim_deg)
    x = radius * math.cos(e) * math.cos(a)
    y = radius * math.cos(e) * math.sin(a)
    z = radius * math.sin(e)
    return (x, y, z)


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

        top_keys = list(data.keys()) if isinstance(data, dict) else []
        print(f"[HOL Import] Top-level keys: {top_keys}")

        if self.clear_existing:
            _clear_existing_tracks(context)

        count = 0
        errors = 0

        if self.import_tracks:
            # ── Real Holophonix .hol format ──────────────────────────
            # data["hol"] = { "/track/1/name": ["TrackName"], ... }
            # data["ae"]  = ["/track/1/azim 45.0", "/track/1/elev 0.0", ...]
            if "hol" in data and "ae" in data:
                count, errors = _import_hol_native(data, context)
            else:
                # Fallback: try generic structure
                tracks_data = _extract_tracks(data)
                print(f"[HOL Import] Fallback parser: {len(tracks_data)} entries")
                for track in tracks_data:
                    try:
                        if not isinstance(track, dict):
                            continue
                        tid = _get_track_id(track)
                        if tid <= 0:
                            continue
                        name = (track.get("name") or track.get("label") or
                                track.get("trackName") or f"Track {tid:03d}")
                        pos = track.get("position") or track.get("xyz") or {}
                        x = float(pos.get("x", 0.0)) if isinstance(pos, dict) else 0.0
                        y = float(pos.get("y", 0.0)) if isinstance(pos, dict) else 0.0
                        z = float(pos.get("z", 0.0)) if isinstance(pos, dict) else 0.0
                        create_track_object(tid, name, location=(x, y, z))
                        count += 1
                    except Exception as e:
                        errors += 1
                        print(f"[HOL Import] Error: {e}")

        msg = f"Imported {count} tracks from {os.path.basename(hol_path)}"
        if errors:
            msg += f" ({errors} errors — see console)"
        self.report({'INFO'}, msg)
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


# ─── .hol parsing helpers ────────────────────────────────────────────────────────────

def _import_hol_native(data: dict, context) -> tuple:
    """
    Parse the native Holophonix .hol format.
    All track data lives in data['ae'] as OSC strings:
      /track/1/name "MUSIC L"
      /track/1/azim -35.0
      /track/1/elev 12.0
      /track/1/dist 9.79
    Returns (count, errors).
    """
    ae = data.get('ae', [])

    # Build lookup: { (track_id, param): value }
    track_data: dict[int, dict] = {}
    for entry in ae:
        if not isinstance(entry, str) or not entry.startswith('/track/'):
            continue
        parts = entry.split(None, 1)  # ['/track/1/azim', '-35.0']
        if len(parts) != 2:
            continue
        osc_path, raw_val = parts[0], parts[1]
        segs = osc_path.strip('/').split('/')  # ['track', '1', 'azim']
        if len(segs) < 3:
            continue
        try:
            tid = int(segs[1])
        except ValueError:
            continue
        param = segs[2]  # 'name', 'azim', 'elev', 'dist', 'color'...
        if param not in ('name', 'azim', 'elev', 'dist'):
            continue
        if tid not in track_data:
            track_data[tid] = {}
        # Strip surrounding quotes for string values
        val = raw_val.strip()
        if val.startswith('"') and val.endswith('"'):
            track_data[tid][param] = val[1:-1]
        else:
            try:
                track_data[tid][param] = float(val)
            except ValueError:
                track_data[tid][param] = val

    count = 0
    errors = 0
    for tid in sorted(track_data):
        try:
            td   = track_data[tid]
            name = td.get('name', '')
            if not name:
                continue  # skip unnamed tracks
            azim = float(td.get('azim', 0.0))
            elev = float(td.get('elev', 0.0))
            dist = float(td.get('dist', 1.0))
            x, y, z = _sph2cart(elev, azim, dist)
            create_track_object(tid, name, location=(x, y, z))
            count += 1
        except Exception as e:
            errors += 1
            print(f"[HOL Import] Track {tid} error: {e}")

    print(f"[HOL Import] Native: {count} tracks, {errors} errors")
    return count, errors


def _extract_tracks(data: dict) -> list:
    """
    Try multiple known Holophonix .hol JSON structures to find the track list.
    Logs the actual keys so we can adapt if the structure differs.
    """
    if not isinstance(data, dict):
        return []

    # Direct list fields
    for key in ("tracks", "sources", "speakers", "items"):
        val = data.get(key)
        if val is not None:
            if isinstance(val, list):
                return val
            if isinstance(val, dict):
                return list(val.values())

    # Nested: data["project"]["tracks"] or data["session"]["tracks"]
    for wrapper in ("project", "session", "content", "data"):
        sub = data.get(wrapper)
        if isinstance(sub, dict):
            for key in ("tracks", "sources", "items"):
                val = sub.get(key)
                if val is not None:
                    if isinstance(val, list):
                        return val
                    if isinstance(val, dict):
                        return list(val.values())

    # Last resort: if root is a list of dicts with an id-like field
    # (some .hol files are just a list at root level wrapped in another key)
    print(f"[HOL Import] Could not find track list. Available keys: {list(data.keys())}")
    # Dump first 500 chars of raw structure to help debugging
    import json as _json
    print(f"[HOL Import] Structure preview: {_json.dumps(data)[:500]}")
    return []


def _get_track_id(track: dict) -> int:
    """Extract numeric track ID from a track dict, trying multiple field names."""
    for field in ("index", "id", "trackIndex", "number", "trackId", "track_id", "num"):
        val = track.get(field)
        if val is not None:
            try:
                return int(val)
            except (ValueError, TypeError):
                continue
    return 0


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
