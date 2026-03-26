# SPDX-License-Identifier: GPL-3.0-or-later
# Holophonix Header in 3D Viewport - Status + Transport

import bpy
from ..core import playback as pb


class HOL_HT_ViewportHeader(bpy.types.Header):
    """Custom header for Holophonix in 3D Viewport."""
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'HEADER'

    def draw(self, context):
        layout = self.layout
        
        # OSC Status
        osc = context.scene.holo_osc_settings
        icon = 'LINKED' if osc.connected else 'UNLINKED'
        layout.label(text=f"OSC: {'Connected' if osc.connected else 'Disconnected'}", icon=icon)
        
        layout.separator()
        
        # Quick model selector (compact)
        params_pg = getattr(context.scene, 'holo_anim_params', None)
        if params_pg:
            from ..core import animation as anim_core
            model = anim_core.get_model(params_pg.model_id)
            model_label = model.get('label', params_pg.model_id) if model else params_pg.model_id
            layout.label(text=f"Model: {model_label}", icon='CURVE_PATH')
        
        layout.separator()
        
        # Transport controls
        active = pb.get_active_animations()
        n_active = len(active)
        
        if n_active:
            layout.label(text=f"Playing: {n_active}", icon='PLAY')
            layout.operator("holophonix.stop_all", text="", icon='CANCEL')
        else:
            layout.operator("holophonix.play_selected", text="Play", icon='PLAY')
        
        layout.separator()
        
        # Quick actions
        layout.operator("holophonix.refresh_preview", text="", icon='FILE_REFRESH')
        layout.operator("holophonix.focus_view", text="", icon='VIEW_PERSPECTIVE')


# ─── Registration ─────────────────────────────────────────────────────

classes = (
    HOL_HT_ViewportHeader,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
