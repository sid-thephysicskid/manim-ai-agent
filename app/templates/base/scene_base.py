from manim import *
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.openai import OpenAIService
from pathlib import Path

class ManimVoiceoverBase(VoiceoverScene):
    """Base class for all generated Manim scenes with voiceover support."""
    
    def __init__(self):
        super().__init__()
        # Setup background
        assets_path = Path(__file__).parent.parent.parent / "assets"
        self.background = ImageMobject(str(assets_path / "leap_background.png"))
        self.add(self.background)
        
        # Setup voice service
        self.set_speech_service(
            OpenAIService(
                voice="onyx",
                model="tts-1-hd"
            )
        )

    def create_title(self, text: str) -> VGroup:
        """Creates a title, using MathTex if mathematical notation is detected."""
        if any(c in text for c in {'\\', '$', '_', '^'}):
            return MathTex(text, font_size=42).to_edge(UP, buff=0.5)
        return Text(text, font_size=42).to_edge(UP, buff=0.5)

    def ensure_group_visible(self, group: VGroup, margin: float = 0.5):
        """Ensures the entire group is visible within the camera frame."""
        # Get group dimensions
        group_width = group.width
        group_height = group.height
        
        # Calculate available space
        available_width = self.camera.frame_width - 2 * margin
        available_height = self.camera.frame_height - 2 * margin
        
        # Scale if needed
        width_scale = available_width / group_width if group_width > available_width else 1
        height_scale = available_height / group_height if group_height > available_height else 1
        scale_factor = min(width_scale, height_scale)
        
        if scale_factor < 1:
            group.scale(scale_factor)
        
        # Ensure within bounds
        left_boundary = -self.camera.frame_width / 2 + margin
        right_boundary = self.camera.frame_width / 2 - margin
        bottom_boundary = -self.camera.frame_height / 2 + margin
        top_boundary = self.camera.frame_height / 2 - margin
        
        # Calculate necessary shifts
        shift_x = 0
        shift_y = 0
        
        if group.get_left()[0] < left_boundary:
            shift_x = left_boundary - group.get_left()[0]
        elif group.get_right()[0] > right_boundary:
            shift_x = right_boundary - group.get_right()[0]
            
        if group.get_bottom()[1] < bottom_boundary:
            shift_y = bottom_boundary - group.get_bottom()[1]
        elif group.get_top()[1] > top_boundary:
            shift_y = top_boundary - group.get_top()[1]
            
        group.shift(RIGHT * shift_x + UP * shift_y) 