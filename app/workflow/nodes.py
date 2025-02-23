import os
import subprocess
import ast
import py_compile
import re
import sys
import traceback
import logging
from typing import Dict, Any, Optional
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
    ERROR_CACHE,
    GENERATED_DIR,
    BASE_DIR
)
from app.workflow.utils import (
    log_state_transition,
    # setup_question_logger,
    generate_scene_filename,
    create_temp_dir
)
from black import format_str, FileMode

client = OpenAI()

SCENE_PLANNING_PROMPT = """Plan a Khan Academy-style animation to explain the concept. 
Break it down into clear scenes that:
1. Introduce the concept
2. Show step-by-step visual explanations
3. Include practical examples
4. End with a summary

Each scene should have clear objectives and specific animation notes."""

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
        raise FileNotFoundError(f"Required Manim API documentation not found at {api_file}")

def read_gcf_example() -> str:
    """Read the GCF example from templates."""
    try:
        with open("app/templates/examples/gcf.py", "r") as f:
            return f.read()
    except FileNotFoundError:
        return ""

@traceable(name="plan_scenes")
def plan_scenes(state: GraphState, **kwargs) -> GraphState:
    """Plan the scenes based on user input."""
    logger = setup_question_logger(state["user_input"])
    logger.info(f"Planning scenes for input: {state['user_input']}")
    
    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{
                "role": "system",
                "content": SCENE_PLANNING_PROMPT
            }, {
                "role": "user",
                "content": state["user_input"]
            }]
        )
        
        return GraphState(
            user_input=state["user_input"],
            plan=response.choices[0].message.content,
            generated_code=None,
            execution_result=None,
            error=None,
            current_stage="plan",
            correction_attempts=0
        )
        
    except Exception as e:
        return GraphState(
            user_input=state["user_input"],
            plan=None,
            generated_code=None,
            execution_result=None,
            error=f"Scene planning failed: {str(e)}",
            current_stage="plan",
            correction_attempts=0
        )

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

def _get_code_generation_prompt(state: Dict[str, Any], api_context: str, code_template: str) -> str:
    """Generate the base prompt for code generation."""
    return f"""
    Generate Manim code to explain "{state['user_input']}" in Khan Academy style, step by step, by following the plan and the rules below.
    Plan: {state['plan']}
    Generate complete, working code that implements this plan in the following format:
    {code_template}

    VOICEOVER RULES (MUST FOLLOW EXACTLY):
    1. Every animation must be wrapped in a voiceover block using this exact pattern:
         with self.voiceover(text="Your narration here") as tracker:
             self.play(Your_Animation_Here, run_time=tracker.duration)
    2. Never use self.voiceover() directly without a 'with' statement.
    3. Use tracker.duration to sync animation timing.
    4. Split long narrations into multiple voiceover blocks.
    5. Each animation sequence should have its own voiceover block with appropriate narration.

    BASE CLASS RULES (MUST INHERIT FROM THIS CLASS):
    Inherit from ManimVoiceoverBase which sets up:
      - Custom background and voice service.
      - Helper methods:
             create_title(text)
             ensure_group_visible(group, margin)
             fade_out_scene()  # Use fade_out_scene() for scene cleanup.

    SCENE STRUCTURE RULES:
      - Every scene method (i.e., a method whose name ends with _scene) must end with a call to self.fade_out_scene().
      - The construct() method should call these scene methods in the desired order.

    DO NOT USE self.clear() anywhere in the code.
    Please look at Manim's documentation for more information on the API: {api_context}
    """

def _get_example_code(code_template: str) -> str:
    """Get example code from gcf.py or fallback to template."""
    example_file = Path("app/templates/examples/gcf.py")
    try:
        with open(example_file, "r") as f:
            return f.read()
    except FileNotFoundError as e:
        logging.error(f"Example file '{example_file}' not found. Aborting code generation.")
        raise e

def _sanitize_generated_code(code: str) -> str:
    """
    Clean and validate the generated code.
    Specifically, fix calls to set_color that use an unquoted color name.
    """
    # Replace .set_color(blue) with .set_color("blue")
    # This regex looks for a set_color call whose first argument is not quoted.
    code = re.sub(
        r'\.set_color\(\s*(?![\'"])([A-Za-z_]+)\s*\)',
        lambda m: f'.set_color("{m.group(1).lower()}")',
        code
    )
    
    # (Optional) Add other sanitization steps – for example, remove unwanted lines,
    # format the code, or fix voiceover block usages.
    
    return code

@traceable(name="generate_code")
def generate_code(state: Dict[str, Any]) -> Dict[str, Any]:
    """Generate Manim code based on the plan."""
    logger = setup_question_logger(state["user_input"])
    logger.info("Generating Manim code from plan")
    api_context = get_manim_api_context()
    
    try:
       
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
    
    # SCENES (each scene must end with self.fade_out_scene()
        ))
    {scene_methods}
'''
        prompt = _get_code_generation_prompt(state, api_context, code_template)
        gcf_example = _get_example_code(code_template)
        
        # Generate code using OpenAI
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{
                "role": "user",
                "content": f"""{prompt}
                Use the following example as a guide:
{gcf_example}
IMPORTANT: Only use the following colors: {', '.join(VALID_COLORS)}. Do not invent or use any other color names.
Ensure that any color parameters passed to set_color are provided as string literals (e.g., set_color('blue')) and not as bare identifiers.”

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
def validate_code(state: GraphState, config: Optional[Dict[str, Any]] = None, **kwargs) -> GraphState:
    """Validate the generated code."""
    logger = setup_question_logger(state["user_input"])
    logger.info("Validating generated code")
    
    try:
        if not state["generated_code"]:
            return GraphState(
                user_input=state["user_input"],
                plan=state["plan"],
                generated_code=None,
                execution_result=None,
                error="No code to validate",
                current_stage="validate",
                correction_attempts=state.get("correction_attempts", 0)
            )
            
        # Log the code being validated
        logger.info(f"Validating code:\n{state['generated_code']}")
        
        # Validate code using ast
        ast.parse(state["generated_code"])
        
        # Additional Manim-specific validation
        if "class" not in state["generated_code"] or "Scene" not in state["generated_code"]:
            raise ValueError("Code must define a Scene class")
        
        if "def construct(self)" not in state["generated_code"]:
            raise ValueError("Scene class must have a construct method")
            
        return GraphState(
            user_input=state["user_input"],
            plan=state["plan"],
            generated_code=state["generated_code"],
            execution_result=None,
            error=None,
            current_stage="validate",
            correction_attempts=state.get("correction_attempts", 0)
        )
        
    except Exception as e:
        error_msg = f"Code validation failed: {str(e)}\nCode:\n{state['generated_code']}"
        logger.error(error_msg)
        return GraphState(
            user_input=state["user_input"],
            plan=state["plan"],
            generated_code=state["generated_code"],
            execution_result=None,
            error=error_msg,
            current_stage="validate",
            correction_attempts=state.get("correction_attempts", 0)
        )

@traceable(name="execute_code")
def execute_code(state: GraphState, **kwargs) -> GraphState:
    """Execute Manim code and capture the output."""
    logger = setup_question_logger(state["user_input"])
    logger.info("Executing Manim code")
    
    try:
        # Use environment-aware paths from config
        media_dir = GENERATED_DIR / "media"
        media_dir.mkdir(exist_ok=True, parents=True)
        (media_dir / "videos").mkdir(exist_ok=True)
        (media_dir / "images").mkdir(exist_ok=True)
        
        scene_file = generate_scene_filename(state['user_input'])
        scene_path = GENERATED_DIR / scene_file
        
        with open(scene_path, 'w') as f:
            f.write(state['generated_code'])
        
        process = subprocess.Popen(
            ["manim", "-ql", str(scene_path), "--media_dir", str(media_dir)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
            env={
                **os.environ,
                "PYTHONPATH": str(BASE_DIR)
            }
        )
        
        output_lines = []
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                logger.info(output.strip())
                output_lines.append(output.strip())
                
        return_code = process.poll()
        
        if return_code != 0:
            return GraphState(
                user_input=state["user_input"],
                plan=state["plan"],
                generated_code=state["generated_code"],
                execution_result=None,
                error=f"Manim execution failed:\n" + "\n".join(output_lines),
                current_stage="execute",
                correction_attempts=state.get("correction_attempts", 0)
            )
        
        # Find video file for result
        video_url = None
        for file in os.listdir(os.path.join(media_dir, "videos")):
            if file.endswith(".mp4"):
                video_url = f"/api/video/{file}"
                break
        
        return GraphState(
            user_input=state["user_input"],
            plan=state["plan"],
            generated_code=state["generated_code"],
            execution_result={"output": output_lines, "video_url": video_url},
            error=None,
            current_stage="execute",
            correction_attempts=state.get("correction_attempts", 0)
        )
        
    except Exception as e:
        return GraphState(
            user_input=state["user_input"],
            plan=state["plan"],
            generated_code=state["generated_code"],
            execution_result=None,
            error=f"Execution failed: {str(e)}",
            current_stage="execute",
            correction_attempts=state.get("correction_attempts", 0)
        )

@traceable(name="error_correction")
def error_correction(state: GraphState, config: Optional[Dict[str, Any]] = None, **kwargs) -> GraphState:
    """Correct code based on error message."""
    logger = setup_question_logger(state["user_input"])
    logger.info(f"Attempting to fix error (attempt {state.get('correction_attempts', 0) + 1}): {state.get('error')}")
    manim_api_context = get_manim_api_context()
    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{
                "role": "system",
                "content": f"""You are an expert Manim developer. Fix the code based on 
                the error message while maintaining the original animation intent.
                
                Requirements:
                1. Code must define a Scene class that inherits from  ManimVoiceoverBas
                2. Use only valid Manim methods and attributes from the following API documentation: {manim_api_context}
                3. Follow proper Python syntax
                """
            }, {
                "role": "user",
                "content": f"""Fix this Manim code that generated an error:
                Error: {state['error']}
                
                Original code:
                {state['generated_code']}
                
                Original plan:
                {state['plan']}
                
                IMPORTANT: Only use the following colors exactly as defined: {', '.join(VALID_COLORS)}"""
            }]
        )
        
        corrected_code = response.choices[0].message.content
        logger.info(f"Generated correction:\n{corrected_code}")
        
        return GraphState(
            user_input=state["user_input"],
            plan=state["plan"],
            generated_code=corrected_code,
            execution_result=None,
            error=None,
            current_stage="validate",
            correction_attempts=state.get("correction_attempts", 0) + 1
        )
        
    except Exception as e:
        error_msg = f"Error correction failed: {str(e)}"
        logger.error(error_msg)
        return GraphState(
            user_input=state["user_input"],
            plan=state["plan"],
            generated_code=state["generated_code"],
            execution_result=None,
            error=error_msg,
            current_stage="error_correction",
            correction_attempts=state.get("correction_attempts", 0)
        )

@traceable(name="lint_code")
def lint_code(state: GraphState) -> GraphState:
    """Lint and format the generated code."""
    logger = setup_question_logger(state["user_input"])
    
    if not state.get("generated_code"):
        return GraphState(
            user_input=state["user_input"],
            plan=state["plan"],
            generated_code=None,
            execution_result=None,
            error="No code to lint",
            current_stage="lint",
            correction_attempts=state.get("correction_attempts", 0)
        )
    
    try:
        # Format code using black
        code = format_str(state["generated_code"], mode=FileMode())
        
        return GraphState(
            user_input=state["user_input"],
            plan=state["plan"],
            generated_code=code,
            execution_result=None,
            error=None,
            current_stage="lint_passed",
            correction_attempts=state.get("correction_attempts", 0)
        )
        
    except Exception as e:
        return GraphState(
            user_input=state["user_input"],
            plan=state["plan"],
            generated_code=state["generated_code"],
            execution_result=None,
            error=f"Linting failed: {str(e)}",
            current_stage="lint",
            correction_attempts=state.get("correction_attempts", 0)
        )