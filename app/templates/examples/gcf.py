from manim import *
from app.templates.base.scene_base import ManimVoiceoverBase

class GCFCalculationScene(ManimVoiceoverBase):
    """
    A Manim scene that explains how to calculate the greatest common factor (GCF)
    of two numbers. This explanation is aimed at middle school students.
    """
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
        
        # Create factor mobjects for 18 and 24
        factor_mobs_18 = []
        factor_mobs_24 = []
        gcf_mob_18 = None
        gcf_mob_24 = None
        
        # Create mobjects for factors of 18
        for f in factors_18:
            is_common = f in common_factors
            is_gcf = (f == 6)
            mob = self.create_factor_mob(f, is_common, is_gcf)
            factor_mobs_18.append(mob)
            if is_gcf:
                gcf_mob_18 = mob
        row_18 = VGroup(*factor_mobs_18).arrange(RIGHT, buff=0.3)

        # Create mobjects for factors of 24
        for f in factors_24:
            is_common = f in common_factors
            is_gcf = (f == 6)
            mob = self.create_factor_mob(f, is_common, is_gcf)
            factor_mobs_24.append(mob)
            if is_gcf:
                gcf_mob_24 = mob
        row_24 = VGroup(*factor_mobs_24).arrange(RIGHT, buff=0.3)

        # Create labels and groups
        label_18 = Text("Factors of 18:", font_size=32)
        label_24 = Text("Factors of 24:", font_size=32)
        group_18 = VGroup(label_18, row_18).arrange(DOWN, aligned_edge=LEFT, buff=0.4)
        group_24 = VGroup(label_24, row_24).arrange(DOWN, aligned_edge=LEFT, buff=0.4)

        # Add numbers above factor lists
        number_18 = Text("18", font_size=48)
        number_24 = Text("24", font_size=48)
        number_18.next_to(group_18, UP, buff=0.2)
        number_24.next_to(group_24, UP, buff=0.2)
        group_18.add(number_18)
        group_24.add(number_24)

        # Arrange and ensure visibility
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
    
        # Highlight the GCF
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