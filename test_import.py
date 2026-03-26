"""Test .hol import with a real file."""
import bpy, sys

HOL_FILE = r"C:\Users\Administrateur\Desktop\Les Champs Libres 25\Presets\FRANKY.hol"

bpy.ops.preferences.addon_enable(module="holophonix_animator")

print("\n[TEST IMPORT]")
bpy.ops.holophonix.import_hol(filepath=HOL_FILE, import_tracks=True, clear_existing=True)

tracks = [o for o in bpy.data.objects if o.name.startswith("holo.track.")]
print(f"  Objects created: {len(tracks)}")
for t in sorted(tracks, key=lambda o: o.name)[:10]:
    loc = t.location
    name = t.holo_track.track_name if hasattr(t, 'holo_track') else '?'
    print(f"  {t.name:30s}  {name:20s}  xyz=({loc.x:.2f}, {loc.y:.2f}, {loc.z:.2f})")

non_zero = [t for t in tracks if t.location.length > 0.01]
print(f"  Non-zero positions: {len(non_zero)}/{len(tracks)}")
print(f"  [{'PASS' if tracks and non_zero else 'FAIL'}]")
sys.exit(0 if tracks and non_zero else 1)
