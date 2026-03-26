# SPDX-License-Identifier: GPL-3.0-or-later
# Animation model system — loads JSON models and computes positions

import math
import json
import os
from typing import Any

MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "models")

# Registry: model_id → model dict (loaded from JSON)
_registry: dict[str, dict] = {}


# ─── Model loading ───────────────────────────────────────────────────────────

def load_all_models():
    """Scan models/ directory and load all JSON model definitions."""
    _registry.clear()
    if not os.path.isdir(MODELS_DIR):
        return
    for fname in os.listdir(MODELS_DIR):
        if fname.endswith(".json"):
            path = os.path.join(MODELS_DIR, fname)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    model = json.load(f)
                model_id = model.get("id") or fname[:-5]
                _registry[model_id] = model
            except Exception as e:
                print(f"[Animation] Failed to load model {fname}: {e}")
    print(f"[Animation] Loaded {len(_registry)} models: {list(_registry.keys())}")


def get_model(model_id: str) -> dict | None:
    return _registry.get(model_id)


def get_all_models() -> list[dict]:
    return list(_registry.values())


def get_model_enum_items(self, context):
    """Returns items for a Blender EnumProperty."""
    items = []
    for mid, model in _registry.items():
        label = model.get("label", mid)
        desc = model.get("description", "")
        items.append((mid, label, desc))
    if not items:
        items.append(("none", "No models", ""))
    return items


# ─── Position computation ────────────────────────────────────────────────────

def compute_position(model_id: str, params: dict, t: float, origin: tuple = (0.0, 0.0, 0.0)) -> tuple[float, float, float]:
    """
    Compute XYZ position for a given model at normalized time t ∈ [0, 1].
    Returns (x, y, z) in meters relative to origin.
    """
    model = _registry.get(model_id)
    if model is None:
        return origin

    kind = model.get("type", "unknown")

    ox, oy, oz = origin

    if kind == "circular":
        radius = float(params.get("radius", model["parameters"]["radius"]["default"]))
        height = float(params.get("height", model["parameters"].get("height", {}).get("default", 0.0)))
        angle = 2 * math.pi * t
        x = ox + radius * math.cos(angle)
        y = oy + radius * math.sin(angle)
        z = oz + height
        return x, y, z

    if kind == "linear":
        x0 = float(params.get("x0", model["parameters"]["x0"]["default"]))
        y0 = float(params.get("y0", model["parameters"]["y0"]["default"]))
        z0 = float(params.get("z0", model["parameters"].get("z0", {}).get("default", 0.0)))
        x1 = float(params.get("x1", model["parameters"]["x1"]["default"]))
        y1 = float(params.get("y1", model["parameters"]["y1"]["default"]))
        z1 = float(params.get("z1", model["parameters"].get("z1", {}).get("default", 0.0)))
        x = ox + x0 + (x1 - x0) * t
        y = oy + y0 + (y1 - y0) * t
        z = oz + z0 + (z1 - z0) * t
        return x, y, z

    if kind == "figure8":
        radius = float(params.get("radius", model["parameters"]["radius"]["default"]))
        angle = 2 * math.pi * t
        x = ox + radius * math.sin(angle)
        y = oy + radius * math.sin(angle) * math.cos(angle)
        z = oz + float(params.get("height", 0.0))
        return x, y, z

    if kind == "spiral":
        radius_start = float(params.get("radius_start", model["parameters"]["radius_start"]["default"]))
        radius_end = float(params.get("radius_end", model["parameters"]["radius_end"]["default"]))
        turns = float(params.get("turns", model["parameters"]["turns"]["default"]))
        height_total = float(params.get("height", model["parameters"].get("height", {}).get("default", 2.0)))
        radius = radius_start + (radius_end - radius_start) * t
        angle = 2 * math.pi * turns * t
        x = ox + radius * math.cos(angle)
        y = oy + radius * math.sin(angle)
        z = oz + height_total * t
        return x, y, z

    if kind == "pendulum":
        amplitude = float(params.get("amplitude", model["parameters"]["amplitude"]["default"]))
        axis = params.get("axis", model["parameters"].get("axis", {}).get("default", "x"))
        angle = math.pi * math.sin(2 * math.pi * t)
        offset = amplitude * math.sin(angle)
        if axis == "x":
            return ox + offset, oy, oz
        elif axis == "y":
            return ox, oy + offset, oz
        else:
            return ox, oy, oz + offset

    if kind == "random_walk":
        # Deterministic pseudo-random based on t — seeded by params
        import random
        seed = int(params.get("seed", model["parameters"].get("seed", {}).get("default", 42)))
        radius = float(params.get("radius", model["parameters"]["radius"]["default"]))
        rng = random.Random(seed + int(t * 1000))
        x = ox + rng.uniform(-radius, radius)
        y = oy + rng.uniform(-radius, radius)
        z = oz + rng.uniform(0, float(params.get("height", 0.0)))
        return x, y, z

    # Fallback: stay at origin
    return origin


def apply_loop_mode(t_raw: float, loop_mode: str) -> float:
    """
    Convert raw elapsed time ratio to normalized t ∈ [0,1] based on loop mode.
    t_raw = elapsed / duration (can be > 1 for loops)
    """
    if loop_mode == 'ONCE':
        return min(t_raw, 1.0)
    elif loop_mode == 'LOOP':
        return t_raw % 1.0
    elif loop_mode == 'PING_PONG':
        cycle = t_raw % 2.0
        return cycle if cycle <= 1.0 else 2.0 - cycle
    return min(t_raw, 1.0)
