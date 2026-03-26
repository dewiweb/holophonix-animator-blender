# SPDX-License-Identifier: GPL-3.0-or-later
# Auto-registration of all Blender classes in the addon

import bpy
import importlib
import pkgutil
import sys
from pathlib import Path

_modules = []

def init():
    global _modules
    addon_dir = Path(__file__).parent
    _modules = _discover_modules(addon_dir, __package__)

def _discover_modules(addon_dir: Path, package: str):
    modules = []
    for finder, name, ispkg in pkgutil.walk_packages(
        path=[str(addon_dir)],
        prefix=package + ".",
        onerror=lambda x: None,
    ):
        # Skip vendor libs and __init__
        if any(skip in name for skip in ("auto_load", "vendor.", "pythonosc.", "oscpy.", "test_", "startup_")):
            continue
        try:
            mod = importlib.import_module(name)
            modules.append(mod)
        except Exception as e:
            print(f"[HolophonixAnimator] Could not import {name}: {e}")
    return modules

def _get_classes(module):
    classes = []
    for obj in vars(module).values():
        if isinstance(obj, type) and issubclass(obj, bpy.types.bpy_struct) and obj.__module__ == module.__name__:
            classes.append(obj)
    return classes

def register():
    for mod in _modules:
        if hasattr(mod, "register"):
            try:
                mod.register()
            except Exception as e:
                print(f"[HolophonixAnimator] register() failed in {mod.__name__}: {e}")
        else:
            for cls in _get_classes(mod):
                try:
                    bpy.utils.register_class(cls)
                except Exception as e:
                    print(f"[HolophonixAnimator] register_class {cls} failed: {e}")

def unregister():
    for mod in reversed(_modules):
        if hasattr(mod, "unregister"):
            try:
                mod.unregister()
            except Exception as e:
                print(f"[HolophonixAnimator] unregister() failed in {mod.__name__}: {e}")
        else:
            for cls in reversed(_get_classes(mod)):
                try:
                    bpy.utils.unregister_class(cls)
                except Exception as e:
                    print(f"[HolophonixAnimator] unregister_class {cls} failed: {e}")
