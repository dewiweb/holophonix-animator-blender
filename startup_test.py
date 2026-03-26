"""
Startup script: enables addon + creates a test track + requests trajectory preview.
Run Blender normally and this will auto-setup the scene for testing.
Usage: blender --python startup_test.py
"""
import bpy


def setup():
    # Enable addon if not already
    if "holophonix_animator" not in bpy.context.preferences.addons:
        bpy.ops.preferences.addon_enable(module="holophonix_animator")

    scene = bpy.context.scene

    # Remove default scene objects (Cube, Light, Camera)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    # Create 3 test tracks
    from holophonix_animator.core.track import create_track_object
    create_track_object(1, "Violon",   location=( 2.0,  0.0, 0.0))
    create_track_object(2, "Hautbois", location=(-2.0,  0.0, 0.0))
    create_track_object(3, "Flute",    location=( 0.0,  2.0, 0.5))

    # Set animation params
    params_pg = scene.holo_anim_params
    params_pg.model_id  = "circular"
    params_pg.duration  = 5.0
    params_pg.loop_mode = 'LOOP'

    # Store circular params as scene custom props for the panel
    scene["hol_param_radius"] = 3.0
    scene["hol_param_height"] = 0.0

    # Select track 1
    obj = bpy.data.objects.get("holo.track.001")
    if obj:
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj

    # Request preview (draw handler already registered by addon)
    from holophonix_animator.core import draw as draw_core
    draw_core.request_preview(
        model_id="circular",
        params={"radius": 3.0, "height": 0.0},
        track_id=1,
        origin=(2.0, 0.0, 0.0),
        segments=128,
    )

    print("[startup_test] OK: 3 tracks + circular preview requested")
    print("[startup_test] Properties > Scene > Holophonix Animator")
    print("[startup_test] F5=Play  F6=Stop  F7=Refresh Preview")


# Register as a one-shot timer so Blender context is fully ready
bpy.app.timers.register(lambda: setup() or None, first_interval=0.5)
