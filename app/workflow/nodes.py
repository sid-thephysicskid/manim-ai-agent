import os
import subprocess
import ast
import py_compile
import re
import sys
import traceback
from typing import Dict, Any
from pathlib import Path
from langsmith import traceable
from openai import OpenAI
from app.templates import get_example_template, get_api_doc
from app.models.state import GraphState
from app.core.logging import setup_question_logger
from app.core.config import (
    OPENAI_MODEL, 
    MANIM_QUALITY, 
    EXECUTION_TIMEOUT,
    VALID_COLORS,
    ERROR_CACHE
)
from app.workflow.utils import (
    log_state_transition,
    setup_question_logger,
    generate_scene_filename,
    create_temp_dir
)

client = OpenAI()

def log_state_transition(node_name: str, input_state: GraphState, output_state: GraphState) -> GraphState:
    """Log state transitions for debugging and monitoring."""
    logger = setup_question_logger(input_state["user_input"])
    logger.info(f"Node: {node_name}")
    logger.info(f"Input state: {input_state}")
    logger.info(f"Output state: {output_state}")
    return output_state

def get_manim_api_context() -> str:
    """Get Manim API context by reading from the templates."""
    api_file = Path("app/templates/api_docs/manim_mobjects.py")
    try:
        with open(api_file, "r") as f:
            return f.read()
    except FileNotFoundError:
        return "Manim API v0.19.0 - Basic shapes and transformations"

def read_gcf_example() -> str:
    """Read the GCF example from templates."""
    try:
        with open("app/templates/examples/gcf.py", "r") as f:
            return f.read()
    except FileNotFoundError:
        return ""

@traceable(name="plan_scenes")
def plan_scenes(state: Dict[str, Any]) -> Dict[str, Any]:
    """Generate lesson plan using LLM."""
    logger = setup_question_logger(state["user_input"])
    logger.info(f"Planning scenes for input: {state['user_input']}")
    
    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{
                "role": "user",
                "content": f"Create detailed Manim lesson plan for: {state['user_input']}\n"
                           "Include 3-5 scenes with animation types (Create, Transform, etc.)\n"
                           "Format: bullet points with scene objectives and animation notes"
            }]
        )
        plan = response.choices[0].message.content
        output_state = {**state, "plan": plan, "current_stage": "plan"}
        return log_state_transition("plan_scenes", state, output_state)
    except Exception as e:
        error_msg = f"Failed to generate scene plan: {str(e)}"
        logger.error(error_msg)
        output_state = {**state, "error": error_msg, "current_stage": "plan"}
        return log_state_transition("plan_scenes", state, output_state)

def _get_voiceover_template() -> str:
    """Get the template for proper voiceover structure."""
    return '''
        with self.voiceover(text=(
            "{text}"
        )) as tracker:
            {animation_code}
            # Optional: Adjust animation timing to match voiceover
            # run_time=tracker.duration
'''

def _get_code_generation_prompt(state: Dict[str, Any], api_context: str) -> str:
    """Generate the base prompt for code generation."""
    voiceover_example = _get_voiceover_template().format(
        text="This is an example voiceover text",
        animation_code="self.play(Write(text), run_time=tracker.duration)"
    )
    
    return f"""
    Generate Manim code to explain {state['user_input']} by following the plan and the rules below.
    Plan: {state['plan']}
    Generate complete, working code that implements this plan.
    VOICEOVER RULES (MUST FOLLOW EXACTLY):
    1. Every animation must be wrapped in a voiceover block using this exact pattern:
        with self.voiceover(text="Your narration here") as tracker:
            self.play(Your_Animation_Here, run_time=tracker.duration)
    
    2. Never use self.voiceover() directly without a 'with' statement 
    3. Use tracker.duration to sync animation timing
    4. Split long narrations into multiple voiceover blocks   
    5. Each animation sequence should have its own voiceover block with appropriate narration
    
    BASE CLASS RULES (MUST INHERIT FROM THIS CLASS):
    Make sure to inherit from ManimVoiceoverBase. This base class provides:
    
    1. Background image setup and Voice service configuration
    2. Helper methods:
       - create_title(text): Creates properly sized titles, handles math notation
       - ensure_group_visible(group, margin): Ensures VGroups fit in frame
    
    The scene should use these methods appropriately. For example:
    - Use create_title() for section headings
    - Use ensure_group_visible() for complex arrangements
    - Background and voice are auto-configured in __init__
    """

def _get_example_code(code_template: str) -> str:
    """Get example code from gcf.py or fallback to template."""
    try:
        with open("gcf.py", "r") as f:
            return f.read()
    except FileNotFoundError:
        return code_template
def _sanitize_generated_code(code: str) -> str:
    """Minimal sanitization for non-semantic issues."""
    # Only handle truly safe transformations like whitespace and comments
    return '\n'.join([line for line in code.split('\n') if not line.strip().startswith('!')])

# def _sanitize_generated_code(code: str) -> str:
#     """Clean and validate the generated code."""
#     # Remove lines starting with '!'
#     code = '\n'.join([line for line in code.split('\n') if not line.strip().startswith('!')])
    
#     # Fix color syntax
#     code = re.sub(r'\.set_color\(([A-Z]+)\)',
#                   lambda m: f'.set_color("{m.group(1).lower()}")', code)
    
#     # Add return type hints
#     code = re.sub(
#         r'(def (?!__init__|construct)(\w+)\(self(?!, color: str)\))(\s*:)',
#         r'\1 -> None\3',
#         code
#     )
    
#     # Fix direct voiceover calls
#     code = re.sub(
#         r'self\.voiceover\((.*?)\)\s*\n\s*self\.play\((.*?)\)',
#         lambda m: f'with self.voiceover({m.group(1)}) as tracker:\n            self.play({m.group(2)}, run_time=tracker.duration)',
#         code,
#         flags=re.DOTALL
#     )
    
#     return code

@traceable(name="generate_code")
def generate_code(state: Dict[str, Any]) -> Dict[str, Any]:
    """Generate Manim code based on the plan."""
    logger = setup_question_logger(state["user_input"])
    logger.info("Generating Manim code from plan")
    api_context = get_manim_api_context()
    
    try:
        # Get base prompt
        prompt = _get_code_generation_prompt(state, api_context)
        
        # Get code template and example
        code_template = '''from manim import *
from app.templates.base.scene_base import ManimVoiceoverBase

class {ClassName}(ManimVoiceoverBase):
    """
    Note: For camera movements, use:
    - self.play(Group().animate.scale(1.2)) for scaling objects
    - self.play(Group().animate.shift(direction)) for moving objects
    Do not use camera.frame unless inheriting from MovingCameraScene
    """
    
    def construct(self):
        """Scene execution order"""
        {scene_calls}
    
    # SCENES (each scene must end with self.play(
            *[FadeOut(mob)for mob in self.mobjects if mob != self.background]
        ))
    {scene_methods}
'''
        gcf_example = _get_example_code(code_template)
        
        # Generate code using OpenAI
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{
                "role": "user",
                "content": f"""{prompt}
                Use the following example as a guide:
{gcf_example}
IMPORTANT: Only use the following colors exactly as defined: {', '.join(VALID_COLORS)}. Do not invent or use any other color names.

RULES ENFORCED(MUST OBEY):
1. MATH RULES:
   - Use MathTex for mathematical content: fractions, Greek letters, operators, sub/superscripts.
   - Format: r"\\frac{{1}}{{2}}" not r"$\\frac{{1}}{{2}}$".
   - Never use Text/Tex for math content.
2. SCENE STRUCTURE:
   - Every scene method must end with self.clear() or include FadeOut.
   - Suffix scene methods with _scene.
   - The construct() method must call the scene methods in order.
3. GENERATE CODE STRUCTURE:
   - Class name should reflect the topic.
   - Include between 3 and 5 scene methods.
   - Helper methods and all functions must include type hints.
4. PARAMETER VALIDATION:
   - Helper methods must be properly type-hinted.
   - Return type hints are required for all methods.
   - Validate and adjust mobject positions with ensure_group_visible().
5. VALIDATE AGAINST:
   ❌ Text with math symbols.
   ❌ Color type annotations (use string color names).
   ❌ Missing scene cleanup.
6. LAYOUT & ALIGNMENT RULES:
   - Use Manim's built-in alignment utilities (e.g., align_to, next_to, VGroup().arrange(DOWN, buff=0.5)) to avoid overlapping visuals.
   - Ensure all objects are clearly visible and appropriately spaced.
   - For layering, explicitly set foreground elements using self.add_foreground_mobjects() where needed.
   - Apply structured arrangement for clear and well-organized scenes.
7. VISUAL CONTENT RULES:
   - Do not import any assets like SVGs or images.
   - Incorporate as many valid, constructive visual elements as possible to teach the concept.
   - Use visual objects from the Manim API (e.g., Polygon, RegularPolygon, Star, Rectangle, Square, RoundedRectangle) as defined in {api_context}.
   - Ensure that visuals are relevant, well-aligned, and enhance explanation. For example, include diagrams, charts, or geometric shapes that illustrate the topic.
   - If the lesson concept can benefit from a visualization, include at least one visual element to reinforce the narrative.
   - Validate that objects are constructed with valid parameters according to the latest Manim API (e.g., when creating a Square, ensure its parameters match those in Manim Community v0.19.0).


OUTPUT FORMAT:
{code_template}
"""
            }]
        )
        
        # Process the generated code
        code = _sanitize_generated_code(response.choices[0].message.content)
        
        output_state = {
            **state, 
            "generated_code": code,
            "current_stage": "code",
            "correction_attempts": 0
        }
        return log_state_transition("generate_code", state, output_state)
    
    except Exception as e:
        error_msg = f"Code generation failed: {str(e)}"
        logger.error(error_msg)
        return {
            **state,
            "error": error_msg,
            "current_stage": "code",
            "generated_code": state.get("generated_code")
        }

@traceable(name="validate_code")
def validate_code(state: Dict[str, Any]) -> Dict[str, Any]:
    """Validate the generated code."""
    logger = setup_question_logger(state["user_input"])
    logger.info("Validating generated code")
    
    if not state.get("generated_code"):
        return {**state, "error": "No code to validate"}
    
    try:
        # Parse the code to AST
        tree = ast.parse(state["generated_code"])
        
        # Find the scene class
        scene_class = None
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                scene_class = node
                break
        
        if not scene_class:
            return {**state, "error": "No scene class found"}
        
        # Check inheritance
        valid_bases = {"VoiceoverScene", "ManimVoiceoverBase"}
        has_valid_base = False
        for base in scene_class.bases:
            if isinstance(base, ast.Name) and base.id in valid_bases:
                has_valid_base = True
                break
        
        if not has_valid_base:
            return {**state, "error": "Scene must inherit from VoiceoverScene or ManimVoiceoverBase"}
        
        # Add voiceover pattern validation
        if "with self.voiceover" not in state["generated_code"]:
            return {**state, "error": "Missing required voiceover pattern: 'with self.voiceover(...) as tracker:'"}
        
        # Check for proper voiceover usage
        scene_methods = re.findall(r'def \w+_scene.*?(?=def|\Z)', state["generated_code"], re.DOTALL)
        for method in scene_methods:
            if "self.voiceover" in method and "with" not in method:
                return {**state, "error": "Incorrect voiceover usage. Must use 'with' statement pattern."}
        
        # Code passed all validations
        output_state = {
            **state,
            "current_stage": "validation_passed"
        }
        return log_state_transition("validate_code", state, output_state)
        
    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        return {**state, "error": str(e)}

@traceable(name="execute_code")
def execute_code(state: Dict[str, Any]) -> Dict[str, Any]:
    """Execute Manim code and capture the output."""
    logger = setup_question_logger(state["user_input"])
    logger.info("Executing Manim code")
    
    # Generate file name in the generated folder
    scene_file = generate_scene_filename(state['user_input'])
    logger.info(f"Writing code to file: {scene_file}")
    
    with open(scene_file, 'w') as f:
        f.write(state['generated_code'])
    logger.info(f"Saved generated code to: {scene_file}")
    
    try:
        logger.info(f"Running Manim with quality setting: {MANIM_QUALITY}")
        result = subprocess.run(
            ["manim", MANIM_QUALITY, scene_file, "--media_dir", "/app/media"],
            capture_output=True,
            text=True,
            timeout=EXECUTION_TIMEOUT,
            cwd=os.getcwd()
        )
        
        if result.returncode != 0:
            error_msg = f"Manim execution failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
            logger.error(error_msg)
            output_state = {**state, "error": error_msg, "current_stage": "execute"}
            return log_state_transition("execute_code", state, output_state)
        
        # Find the generated video file
        video_file = None
        video_url = None
        for file in os.listdir("/app/media/videos"):
            if file.endswith(".mp4"):
                video_file = f"/app/media/videos/{file}"
                video_url = f"/api/video/{file}"  # URL for frontend
                break
        
        logger.info("Manim execution completed successfully.")
        output = {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "scene_file": scene_file,
            "scene_url": f"/api/code/{os.path.basename(scene_file)}",  # Code URL
            "video_file": video_file,
            "video_url": video_url  # Video URL
        }
        logger.info(f"Scene file preserved at: {scene_file}")
        logger.info(f"Video file generated at: {video_file}")
        output_state = {**state, "execution_result": output, "error": None, "current_stage": "execute"}
        return log_state_transition("execute_code", state, output_state)
    except Exception as e:
        error_msg = f"Execution failed: {str(e)}"
        _, _, tb = sys.exc_info()
        line_no = traceback.extract_tb(tb)[-1].lineno
        error_msg += f"\nNear generated code line: {line_no}"
        
        output_state = {**state, "error": error_msg, "current_stage": "execute"}
        return log_state_transition("execute_code", state, output_state)

@traceable(name="error_correction")
def error_correction(state: Dict[str, Any]) -> Dict[str, Any]:
    """Correct code based on error message."""
    logger = setup_question_logger(state["user_input"])
    logger.info(f"Attempting to fix error: {state.get('error')}")
    
    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{
                "role": "system",
                "content": """You are an expert Manim developer. Fix the code based on 
                the error message while maintaining the original animation intent."""
            }, {
                "role": "user",
                "content": f"""Fix this Manim code that generated an error:
                Error: {state['error']}
                
                Original code:
                {state['generated_code']}"""
            }]
        )
        
        corrected_code = response.choices[0].message.content
        output_state = {
            **state,
            "generated_code": corrected_code,
            "current_stage": "validate",
            "correction_attempts": state.get("correction_attempts", 0) + 1,
            "error": None
        }
        return log_state_transition("error_correction", state, output_state)
        
    except Exception as e:
        logger.error(f"Error in correction: {str(e)}")
        return {**state, "error": str(e)}

@traceable(name="lint_code")
def lint_code(state: Dict[str, Any]) -> Dict[str, Any]:
    """Lint and format the generated code."""
    logger = setup_question_logger(state["user_input"])
    logger.info("Linting generated code")
    
    if not state.get("generated_code"):
        return {**state, "error": "No code to lint"}
    
    try:
        # Basic linting checks
        code = state["generated_code"]
        
        # Check color usage
        for color in VALID_COLORS:
            if color.upper() in code:
                code = code.replace(color.upper(), f'"{color}"')
        
        # Ensure proper whitespace
        code = code.replace("\t", "    ")
        
        output_state = {
            **state,
            "generated_code": code,
            "current_stage": "lint_passed"
        }
        return log_state_transition("lint_code", state, output_state)
        
    except Exception as e:
        logger.error(f"Linting error: {str(e)}")
        return {**state, "error": str(e)}