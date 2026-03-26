# Holophonix Animator — Blender Addon

Spatial audio animation tool for Holophonix processors, built as a native Blender addon.

## Requirements

- Blender 4.2+ (tested on 5.0)
- Python 3.11+ (bundled with Blender)
- OSC libs bundled — no external install needed

## Features

- **Import** Holophonix projects (`.hol`, `.zip`)
- **Discover tracks** via OSC `/dump` request
- **Real-time animation** with loop / ping-pong / once modes
- **Multiple simultaneous animations** — each track can run independently
- **Cue list** — trigger, stop, blend animations on demand
- **Animation models** (JSON, user-extensible):
  - Circular, Linear, Figure-8, Spiral, Pendulum, Random Walk
- **OSC output** — sends `/track/{id}/xyz` in real time during playback

## Installation

1. Copy this folder to your Blender addons directory:
   `%APPDATA%\Blender Foundation\Blender\5.0\scripts\addons\`
2. In Blender: Edit → Preferences → Add-ons → search "Holophonix" → Enable

## Usage

Open the **N-Panel** (press N in 3D View) → **Holophonix** tab.

1. **OSC Connection** — set Holophonix IP and ports, click Connect
2. **Tracks** — import `.hol` file or click the antenna icon to discover via OSC
3. **Animation** — select tracks, choose model, click Play
4. **Cue List** — build a list of named cues, trigger with GO button

## Adding Custom Animation Models

Create a JSON file in the `models/` folder:

```json
{
  "id": "my_model",
  "label": "My Model",
  "description": "Custom trajectory",
  "type": "circular",
  "parameters": {
    "radius": { "label": "Radius (m)", "type": "float", "default": 2.0, "min": 0.1, "max": 50.0 }
  }
}
```

Then implement the `type` in `core/animation.py` → `compute_position()`.

## License

GPL v3 — see LICENSE file.
Includes code derived from [NodeOSC](https://github.com/maybites/blender.NodeOSC) (GPL v3, maybites).
Bundled libraries: `pythonosc` (MIT), `oscpy` (MIT).
