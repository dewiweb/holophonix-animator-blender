"""
Test script for holophonix_animator addon.
Run with: blender --background --python test_addon.py
"""
import bpy
import sys
import traceback

PASS = []
FAIL = []

def check(name, condition, detail=""):
    if condition:
        PASS.append(name)
        print(f"  [PASS] {name}")
    else:
        FAIL.append(name)
        print(f"  [FAIL] {name}" + (f" — {detail}" if detail else ""))

print("\n" + "="*60)
print("  holophonix_animator — addon test suite")
print("="*60)

# ── 1. Enable addon ──────────────────────────────────────────────
print("\n[1] Enabling addon...")
try:
    bpy.ops.preferences.addon_enable(module="holophonix_animator")
    enabled = "holophonix_animator" in bpy.context.preferences.addons
    check("addon_enable", enabled)
except Exception as e:
    check("addon_enable", False, str(e))

# ── 2. Scene properties registered ──────────────────────────────
print("\n[2] Scene properties...")
scene = bpy.context.scene
check("holo_tracks",      hasattr(scene, "holo_tracks"))
check("holo_cues",        hasattr(scene, "holo_cues"))
check("holo_osc_settings",hasattr(scene, "holo_osc_settings"))
check("holo_anim_params", hasattr(scene, "holo_anim_params"))

# ── 3. Animation models loaded ───────────────────────────────────
print("\n[3] Animation models...")
try:
    from holophonix_animator.core import animation as anim_core
    anim_core.load_all_models()
    models = anim_core.get_all_models()
    check("models_loaded",    len(models) > 0, f"found {len(models)}")
    model_ids = [m.get("id") for m in models]
    check("model_circular",   "circular"   in model_ids)
    check("model_linear",     "linear"     in model_ids)
    check("model_figure8",    "figure8"    in model_ids)
    check("model_spiral",     "spiral"     in model_ids)
    check("model_pendulum",   "pendulum"   in model_ids)
    check("model_random_walk","random_walk" in model_ids)
except Exception as e:
    check("models_loaded", False, str(e))

# ── 4. compute_position ─────────────────────────────────────────
print("\n[4] compute_position...")
try:
    for mid in ("circular", "linear", "figure8"):
        model = anim_core.get_model(mid)
        params = {k: v.get("default", 0) for k, v in model.get("parameters", {}).items()}
        x, y, z = anim_core.compute_position(mid, params, 0.0, (0,0,0))
        check(f"compute_{mid}", isinstance(x, float), f"({x:.2f},{y:.2f},{z:.2f})")
except Exception as e:
    check("compute_position", False, str(e))
    traceback.print_exc()

# ── 5. create_track_object ──────────────────────────────────────
print("\n[5] Track object creation...")
try:
    from holophonix_animator.core.track import create_track_object, TRACK_OBJECT_PREFIX
    obj = create_track_object(1, "Test Track", location=(1.0, 2.0, 3.0))
    check("track_object_created", obj is not None)
    check("track_object_name",    obj.name == f"{TRACK_OBJECT_PREFIX}001")
    check("track_object_location",abs(obj.location.x - 1.0) < 0.001)
    check("track_holo_prop",      hasattr(obj, "holo_track"))
    check("track_id_set",         obj.holo_track.track_id == 1)
except Exception as e:
    check("track_object_created", False, str(e))
    traceback.print_exc()

# ── 6. Operators registered ──────────────────────────────────────
print("\n[6] Operators...")
ops_to_check = [
    "holophonix.track_add",
    "holophonix.osc_connect",
    "holophonix.import_hol",
    "holophonix.play_selected",
    "holophonix.stop_all",
    "holophonix.refresh_preview",
    "holophonix.setup_scene",
    "holophonix.setup_workspace",
    "holophonix.focus_view",
]
for op_id in ops_to_check:
    parts = op_id.split(".")
    cat   = getattr(bpy.ops, parts[0], None)
    op    = getattr(cat, parts[1], None) if cat else None
    check(f"op_{parts[1]}", op is not None)

# ── 7. Panels registered ─────────────────────────────────────────
print("\n[7] Panels...")
panels_to_check = [
    "HOL_PT_Root",
    "HOL_PT_OSC_Props",
    "HOL_PT_Tracks_Props",
    "HOL_PT_Animation_Props",
    "HOL_PT_Cues_Props",
    "HOL_PT_TrackObject",
]
for pid in panels_to_check:
    check(f"panel_{pid}", pid in bpy.types.__dir__())

# ── 8. draw handler registered ──────────────────────────────────
print("\n[8] Draw handler...")
try:
    from holophonix_animator.core import draw as draw_core
    draw_core.enable()
    check("draw_handler_enabled", draw_core._draw_handle is not None)
    draw_core.disable()
    check("draw_handler_disabled", draw_core._draw_handle is None)
except Exception as e:
    check("draw_handler", False, str(e))
    traceback.print_exc()

# ── Summary ──────────────────────────────────────────────────────
print("\n" + "="*60)
print(f"  RESULTS: {len(PASS)} passed, {len(FAIL)} failed")
if FAIL:
    print(f"  FAILED: {', '.join(FAIL)}")
print("="*60 + "\n")

sys.exit(1 if FAIL else 0)
