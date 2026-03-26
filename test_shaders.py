"""Test available GPU shaders in Blender 5.0 background mode."""
import gpu

shader_names = [
    'POLYLINE_SMOOTH_COLOR',
    'POLYLINE_UNIFORM_COLOR',
    'SMOOTH_COLOR',
    'FLAT_COLOR',
    'UNIFORM_COLOR',
    '3D_POLYLINE_SMOOTH_COLOR',
    '3D_SMOOTH_COLOR',
    '3D_FLAT_COLOR',
    '3D_UNIFORM_COLOR',
]

print("\n[SHADER TEST]")
for name in shader_names:
    try:
        gpu.shader.from_builtin(name)
        print(f"  [OK] {name}")
    except Exception as e:
        print(f"  [NO] {name} — {e}")
print()
