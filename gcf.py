from manim import *
from manim_voiceover import VoiceoverScene
# from manim_voiceover.services.openai import  OpenAIService
from manim_voiceover.services.elevenlabs import ElevenLabsService
class GCFCalculationScene(VoiceoverScene):
    """
    A Manim scene that explains how to calculate the greatest common factor (GCF)
    of two numbers. This explanation is aimed at middle school students.
    """
    def __init__(self):
        super().__init__()
        # Setup voiceover
        self.background = ImageMobject("leap_background.png")
        self.add(self.background)
        self.set_speech_service(
            ElevenLabsService(
                voice_name="Russell",
                voice_id="U0neD5Gd97pQtdeDfaZu",
                model="eleven_multilingual_v2",
                voice_settings={
                    "stability": 0.5,
                    "similarity_boost": 0.75,
                    "style": 0,
                    "use_speaker_boost": True
                }
            )
        )
        # self.set_speech_service(
        #     OpenAIService(
        #         voice="nova",
        #         model="tts-1-hd"
        #     )
        # )

    def create_title(self, text: str) -> VGroup:
        r"""Creates a title, using MathTex if mathematical notation is detected"""
        if any(c in text for c in {'\\', '$', '_', '^'}):
            return MathTex(text, font_size=42).to_edge(UP, buff=0.5)
        return Text(text, font_size=42).to_edge(UP, buff=0.5)

    def ensure_group_visible(self, group: VGroup, margin: float = 0.5):
        """
        Ensures the entire group is visible within the camera frame.
        This function scales the group down if it exceeds the available width or height,
        then repositions it so that its bounding box fully resides inside the camera frame.
        """
        # --- Scaling Step ---
        group_width = group.width
        group_height = group.height
        available_width = self.camera.frame_width - 2 * margin
        available_height = self.camera.frame_height - 2 * margin
        width_scale = available_width / group_width if group_width > available_width else 1
        height_scale = available_height / group_height if group_height > available_height else 1
        scale_factor = min(width_scale, height_scale)
        if scale_factor < 1:
            group.scale(scale_factor)

        # --- Repositioning Step ---
        left_boundary = -self.camera.frame_width / 2 + margin
        right_boundary = self.camera.frame_width / 2 - margin
        bottom_boundary = -self.camera.frame_height / 2 + margin
        top_boundary = self.camera.frame_height / 2 - margin
        group_left = group.get_left()[0]
        group_right = group.get_right()[0]
        group_bottom = group.get_bottom()[1]
        group_top = group.get_top()[1]

        shift_x = 0
        if group_left < left_boundary:
            shift_x = left_boundary - group_left
        elif group_right > right_boundary:
            shift_x = right_boundary - group_right

        shift_y = 0
        if group_bottom < bottom_boundary:
            shift_y = bottom_boundary - group_bottom
        elif group_top > top_boundary:
            shift_y = top_boundary - group_top

        group.shift(RIGHT * shift_x + UP * shift_y)

    def create_factor_mob(self, factor: int, is_common: bool, is_gcf: bool) -> VGroup:
        """
        Creates a small circular mobject to represent a factor.
        Common factors are highlighted in yellow and the greatest common factor is outlined in red.
        """
        circle = Circle(radius=0.3)
        circle.set_stroke(width=2)
        # Set color depending on whether the factor is common or the GCF.
        if is_common:
            circle.set_color(YELLOW)
        else:
            circle.set_color(WHITE)
        if is_gcf:
            circle.set_color(RED)
            circle.set_stroke(width=4)
        label = Text(str(factor), font_size=24)
        mob = VGroup(circle, label)
        label.move_to(circle.get_center())
        return mob

    def construct(self):
        # Call each scene in order:
        self.intro_scene()
        self.listing_factors_scene()
        self.summary_scene()

    def intro_scene(self):
        """Scene 1: Introduction to the GCF concept."""
        title = self.create_title("Greatest Common Factor (GCF)")
        subtitle = Text("The largest number that divides two numbers evenly.", font_size=32)
        subtitle.next_to(title, DOWN)
        group = VGroup(title, subtitle)
        self.ensure_group_visible(group, margin=0.5)
    
        with self.voiceover(text=(
            "Today, we will learn how to find the Greatest Common Factor, or GCF, of two numbers. "
            "The GCF is the largest number that can divide both numbers without leaving a remainder."
        )) as tracker:
            self.play(Write(title), Write(subtitle), run_time=tracker.duration)
        # Fade out all mobjects except the background
        self.play(
            *[FadeOut(mob)for mob in self.mobjects if mob != self.background]
        )



    def listing_factors_scene(self):
        """Scene 2: List the factors of two numbers and highlight the common ones."""
        # We will use the numbers 18 and 24.
        factors_18 = [1, 2, 3, 6, 9, 18]
        factors_24 = [1, 2, 3, 4, 6, 8, 12, 24]
        common_factors = {1, 2, 3, 6}  # Factors common to both
        # Create factor mobjects for 18.
        factor_mobs_18 = []
        gcf_mob_18 = None
        for f in factors_18:
            is_common = f in common_factors
            is_gcf = (f == 6)
            mob = self.create_factor_mob(f, is_common, is_gcf)
            factor_mobs_18.append(mob)
            if is_gcf:
                gcf_mob_18 = mob
        row_18 = VGroup(*factor_mobs_18).arrange(RIGHT, buff=0.3)

        # Create factor mobjects for 24.
        factor_mobs_24 = []
        gcf_mob_24 = None
        for f in factors_24:
            is_common = f in common_factors
            is_gcf = (f == 6)
            mob = self.create_factor_mob(f, is_common, is_gcf)
            factor_mobs_24.append(mob)
            if is_gcf:
                gcf_mob_24 = mob
        row_24 = VGroup(*factor_mobs_24).arrange(RIGHT, buff=0.3)

        # Create labels for each number's factors.
        label_18 = Text("Factors of 18:", font_size=32)
        label_24 = Text("Factors of 24:", font_size=32)
        group_18 = VGroup(label_18, row_18).arrange(DOWN, aligned_edge=LEFT, buff=0.4)
        group_24 = VGroup(label_24, row_24).arrange(DOWN, aligned_edge=LEFT, buff=0.4)

        # Also show the numbers 18 and 24 above the factor lists.
        number_18 = Text("18", font_size=48)
        number_24 = Text("24", font_size=48)
        number_18.next_to(group_18, UP, buff=0.2)
        number_24.next_to(group_24, UP, buff=0.2)
        group_18.add(number_18)
        group_24.add(number_24)

        groups = VGroup(group_18, group_24).arrange(RIGHT, buff=3)
        self.ensure_group_visible(groups, margin=0.5)
    
        with self.voiceover(text=(
            "Now, let's find the GCF of 18 and 24 by listing their factors. "
            "For 18, the factors are 1, 2, 3, 6, 9, and 18. "
            "For 24, the factors are 1, 2, 3, 4, 6, 8, 12, and 24. "
            "The numbers that appear in both lists are 1, 2, 3, and 6. "
            "Since 6 is the largest number common to both, the GCF is 6."
        )) as tracker:
            self.play(Write(groups), run_time=tracker.duration * 0.8)
    
        # Highlight the GCF (6) in both groups.
        rect_18 = SurroundingRectangle(gcf_mob_18, buff=0.1, color=RED)
        rect_24 = SurroundingRectangle(gcf_mob_24, buff=0.1, color=RED)
        self.play(Create(rect_18), Create(rect_24), run_time=1)
        # Fade out all mobjects except the background
        self.play(
            *[FadeOut(mob)for mob in self.mobjects if mob != self.background]
        )

    def summary_scene(self):
        """Scene 3: Recap the process with a summary of the steps."""
        summary_title = self.create_title("Summary")
        bullet_points = VGroup(
            Text("1. List all factors of each number.", font_size=32),
            Text("2. Identify the common factors.", font_size=32),
            Text("3. The largest common factor is the GCF.", font_size=32)
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.5)
        bullet_points.next_to(summary_title, DOWN, buff=0.8)
        summary_group = VGroup(summary_title, bullet_points)
        self.ensure_group_visible(summary_group, margin=0.5)
    
        with self.voiceover(text=(
            "To summarize, first list all factors of each number. Then, identify the factors that are common to both numbers. "
            "The largest of these common factors is the Greatest Common Factor."
        )) as tracker:
            self.play(Write(summary_title), run_time=tracker.duration/3)
            self.play(Write(bullet_points), run_time=tracker.duration*2/3)

        # Fade out all mobjects except the background
        self.play(
            *[FadeOut(mob)for mob in self.mobjects if mob != self.background]
        )