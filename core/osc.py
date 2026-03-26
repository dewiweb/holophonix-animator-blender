# SPDX-License-Identifier: GPL-3.0-or-later
# OSC wrapper — uses pythonosc (bundled in vendor/)
# Forked/inspired from NodeOSC by maybites (GPL v3)

import bpy
import threading
import sys
import os

# Add vendor path so bundled pythonosc is importable
_vendor_dir = os.path.join(os.path.dirname(__file__), "..", "vendor")
if _vendor_dir not in sys.path:
    sys.path.insert(0, _vendor_dir)

try:
    from pythonosc import udp_client, osc_message_builder, dispatcher, osc_server
    _HAS_OSC = True
except ImportError:
    _HAS_OSC = False
    print("[HolophonixAnimator] pythonosc not found — OSC disabled")


# ─── Singleton server/client state ───────────────────────────────────────────

class _OSCState:
    client = None           # UDPClient for sending
    server = None           # BlockingOSCUDPServer for receiving
    server_thread = None    # Thread running the server
    dispatcher = None       # pythonosc Dispatcher
    _handlers = {}          # address → list of Python callables


_state = _OSCState()


# ─── Public API ──────────────────────────────────────────────────────────────

def is_available() -> bool:
    return _HAS_OSC


def start_server(ip_in: str, port_in: int, ip_out: str, port_out: int) -> bool:
    """Start OSC UDP server (receive) and prepare client (send)."""
    if not _HAS_OSC:
        return False
    stop_server()
    try:
        # Send client
        _state.client = udp_client.UDPClient(ip_out, port_out)

        # Receive server
        _state.dispatcher = dispatcher.Dispatcher()
        _state.dispatcher.set_default_handler(_default_handler)
        _state.server = osc_server.BlockingOSCUDPServer((ip_in, port_in), _state.dispatcher)
        _state.server_thread = threading.Thread(target=_state.server.serve_forever, daemon=True)
        _state.server_thread.start()
        print(f"[OSC] Server listening on {ip_in}:{port_in} | Sending to {ip_out}:{port_out}")
        return True
    except Exception as e:
        print(f"[OSC] Failed to start server: {e}")
        return False


def stop_server():
    """Shutdown OSC server and client."""
    if _state.server:
        try:
            _state.server.shutdown()
        except Exception:
            pass
        _state.server = None
        _state.server_thread = None
    _state.client = None
    _state.dispatcher = None
    print("[OSC] Server stopped")


def send(address: str, *args):
    """Send an OSC message."""
    if not _state.client:
        return
    try:
        msg = osc_message_builder.OscMessageBuilder(address=address)
        for arg in args:
            msg.add_arg(arg)
        _state.client.send(msg.build())
    except Exception as e:
        print(f"[OSC] Send error ({address}): {e}")


def send_xyz(track_id: int, x: float, y: float, z: float):
    """Convenience: send /track/{id}/xyz x y z"""
    send(f"/track/{track_id}/xyz", float(x), float(y), float(z))


def send_aed(track_id: int, a: float, e: float, d: float):
    """Convenience: send /track/{id}/aed a e d"""
    send(f"/track/{track_id}/aed", float(a), float(e), float(d))


def add_handler(address: str, callback):
    """Register a Python callable for incoming OSC address."""
    if address not in _state._handlers:
        _state._handlers[address] = []
    _state._handlers[address].append(callback)
    if _state.dispatcher:
        _state.dispatcher.map(address, _dispatch_to_handlers)


def remove_handler(address: str, callback):
    if address in _state._handlers:
        _state._handlers[address] = [cb for cb in _state._handlers[address] if cb != callback]


# ─── Internal ────────────────────────────────────────────────────────────────

def _dispatch_to_handlers(address: str, *args):
    for cb in _state._handlers.get(address, []):
        try:
            cb(address, list(args))
        except Exception as e:
            print(f"[OSC] Handler error ({address}): {e}")


def _default_handler(address: str, *args):
    """Called for any OSC message without a specific handler."""
    # Route to wildcard handlers if registered
    for registered_addr, callbacks in _state._handlers.items():
        if _matches_wildcard(registered_addr, address):
            for cb in callbacks:
                try:
                    cb(address, list(args))
                except Exception as e:
                    print(f"[OSC] Default handler error: {e}")


def _matches_wildcard(pattern: str, address: str) -> bool:
    """Simple OSC wildcard matching (* only)."""
    import fnmatch
    return fnmatch.fnmatch(address, pattern)
