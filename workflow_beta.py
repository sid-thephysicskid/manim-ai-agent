#!/usr/bin/env python3
"""
workflow_beta_working.py

This file implements a Manim-based workflow using a state graph.
It generates a lesson plan, produces Manim code (with voiceovers), validates 
the code, executes it (rendering a video), and provides error correction.

This file now also contains comprehensive tests (unit tests, integration tests,
and end‑to‑end tests). To run the tests, execute:
    python workflow_beta_working.py --test
Otherwise, the normal workflow executes.
"""

# ------------------------------------------------------------------------------
# Imports and Initial Configuration
# ------------------------------------------------------------------------------
import os
import subprocess
import tempfile
import logging
import ast
import json
import re
import sys
import traceback
import difflib
from datetime import datetime
from functools import lru_cache
from cachetools import TTLCache
from typing import TypedDict, Literal, List
from langsmith import traceable
from langsmith.wrappers import wrap_openai
from openai import OpenAI
from langgraph.graph import StateGraph, END
from IPython.display import display, HTML, Image
from dotenv import load_dotenv
import py_compile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import ModuleType
from manim import Scene  # Add missing import

# For testing purposes later
import unittest
from unittest.mock import patch, MagicMock

# Load environment variables
load_dotenv()

# Initialize OpenAI client and logging
# Wrap the OpenAI client to automatically trace all API interactions.
client = wrap_openai(OpenAI())
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
# Global Constants and Configuration
# ------------------------------------------------------------------------------
OPENAI_MODEL = "o3-mini"
MANIM_QUALITY = "-ql"  # Low quality for faster rendering
EXECUTION_TIMEOUT = 180  # seconds
ERROR_HISTORY = "error_fixes.json"
ERROR_CACHE = TTLCache(maxsize=100, ttl=3600)  # 1 hour cache
VALID_COLORS = ["blue", "teal", "green", "yellow", "gold", "red", "maroon", "purple", "pink", "light_pink", "orange", "light_brown", "dark_brown", "gray_brown", "white", "black", "lighter_gray", "light_gray", "gray", "dark_gray", "darker_gray", "blue_a", "blue_b", "blue_c", "blue_d", "blue_e", "pure_blue"]

# Set up the directory for all generated files (both scripts and logs)
GENERATED_DIR = os.path.join(os.path.dirname(__file__), "app", "generated")
os.makedirs(GENERATED_DIR, exist_ok=True)

# Establish a run-level timestamp (used both for file names and log file)
RUN_TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

# Add to Global Constants section
LOGS_DIR = os.path.join(GENERATED_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# ------------------------------------------------------------------------------
# Type Definitions
# ------------------------------------------------------------------------------
class GraphState(TypedDict):
    user_input: str
    plan: str | None
    generated_code: str | None
    execution_result: dict | None
    error: str | None
    current_stage: Literal['plan', 'code', 'execute', 'correct', 'lint', 'lint_passed']
    correction_attempts: int  # Added tracking

# ------------------------------------------------------------------------------
# Utility Functions
# ------------------------------------------------------------------------------
def log_state_transition(node_name: str, input_state: dict, output_state: dict):
    """Log the state transition for a node, showing what changed."""
    logger.info(f"\n{'='*50}\nNode: {node_name}")
    
    # Log input state
    logger.info("Input State:")
    for k, v in input_state.items():
        if k in ['generated_code', 'plan'] and v:
            logger.info(f"  {k}: <{len(str(v))} chars>")
        else:
            logger.info(f"  {k}: {v}")
    
    # Log changes between input and output states
    logger.info("Changes:")
    for k in output_state:
        if k in input_state:
            if output_state[k] != input_state[k]:
                if k in ['generated_code', 'plan']:
                    logger.info(f"  {k}: <updated - {len(str(output_state[k]))} chars>")
                else:
                    logger.info(f"  {k}: {input_state[k]} -> {output_state[k]}")
        else:
            logger.info(f"  + {k}: {output_state[k]}")
    
    # Log error if present
    if output_state.get('error'):
        logger.error(f"Error in {node_name}: {output_state['error']}")
    
    logger.info(f"{'='*50}\n")
    return output_state

def create_temp_dir():
    """Create a temporary directory for Manim operations."""
    temp_dir = tempfile.mkdtemp(prefix="manim_")
    logger.info(f"Created temporary directory at: {temp_dir}")
    return temp_dir

def extract_concept(text: str) -> str:
    """
    Extract the underlying concept from a user input string.
    
    This function converts the input to lower case, strips out any punctuation,
    and removes common prompting words from the beginning (such as "how to", "what is",
    "explain", etc.) to obtain a concise concept name.
    """
    text = text.lower().strip()
    # List of common prompt prefixes to remove:
    prefixes = ["how to", "what is", "explain", "describe", "why is", "tell me", "show me"]
    for prefix in prefixes:
        if text.startswith(prefix):
            text = text[len(prefix):].strip()
            break
    # Remove punctuation
    text = re.sub(r'[^\w\s]', '', text)
    # Replace multiple spaces with a single underscore
    concept = re.sub(r'\s+', '_', text)
    return concept

def generate_scene_filename(topic: str) -> str:
    """
    Generate a unique scene filename from the user input.
    
    This function extracts the underlying concept from the input and
    appends a truncated timestamp (date, hour, and minute). The filename 
    follows the format: "<concept>_<timestamp>.py" and is saved in the GENERATED_DIR.
    
    For example, an input "how to convert fractions to decimals?" becomes:
       "convert_fractions_to_decimals_20250212_0847.py"
    """
    concept = extract_concept(topic)
    # Use the RUN_TIMESTAMP but only date, hour, and minute (drop seconds)
    timestamp = RUN_TIMESTAMP[:13]
    filename = f"{concept}_{timestamp}.py"
    return os.path.join(GENERATED_DIR, filename)

def setup_question_logger(question: str) -> logging.Logger:
    """Set up a dedicated logger for each question."""
    # Create a sanitized filename from the question
    safe_name = re.sub(r'[^\w\s-]', '', question.lower())
    safe_name = re.sub(r'[-\s]+', '_', safe_name)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(LOGS_DIR, f"{safe_name}_{timestamp}.log")
    
    # Create a new logger for this question
    logger = logging.getLogger(f"question_{safe_name}")
    logger.setLevel(logging.INFO)
    
    # Remove any existing handlers
    logger.handlers = []
    
    # Add file handler
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.INFO)
    fh.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    logger.addHandler(fh)
    
    # Add console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    logger.addHandler(ch)
    
    return logger

def process_single_question(question: str) -> dict:
    """Process a single question through the workflow."""
    # Set up dedicated logger for this question
    question_logger = setup_question_logger(question)
    question_logger.info(f"Starting processing for question: {question}")
    
    try:
        # Initialize state
        initial_state = {
            "user_input": question,
            "plan": None,
            "generated_code": None,
            "execution_result": None,
            "error": None,
            "current_stage": "plan",
            "correction_attempts": 0
        }
        
        # Run the workflow
        result = app.invoke(initial_state)
        
        # Log the final result
        if result.get("error"):
            question_logger.error(f"Failed to process question: {result['error']}")
        else:
            question_logger.info("Successfully processed question")
            if result.get("execution_result", {}).get("scene_file"):
                question_logger.info(f"Generated scene file: {result['execution_result']['scene_file']}")
        
        return {
            "question": question,
            "success": not bool(result.get("error")),
            "error": result.get("error"),
            "scene_file": result.get("execution_result", {}).get("scene_file")
        }
        
    except Exception as e:
        question_logger.error(f"Unexpected error processing question: {str(e)}")
        return {
            "question": question,
            "success": False,
            "error": str(e),
            "scene_file": None
        }

def batch_process_questions(questions: List[str], max_workers: int = 1) -> List[dict]:
    """
    Process a batch of questions, handling failures gracefully.
    
    Args:
        questions: List of questions to process
        max_workers: Number of parallel workers (default 1 for sequential processing)
    
    Returns:
        List of results for each question
    """
    main_logger = logging.getLogger(__name__)
    main_logger.info(f"Starting batch processing of {len(questions)} questions")
    
    results = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_question = {
            executor.submit(process_single_question, question): question 
            for question in questions
        }
        
        for future in future_to_question:
            question = future_to_question[future]
            try:
                result = future.result()
                results.append(result)
                
                # Log overall progress
                main_logger.info(f"Completed question: {question}")
                if result['success']:
                    main_logger.info("Status: Success")
                else:
                    main_logger.warning(f"Status: Failed - {result['error']}")
                    
            except Exception as e:
                main_logger.error(f"Failed to process question '{question}': {str(e)}")
                results.append({
                    "question": question,
                    "success": False,
                    "error": str(e),
                    "scene_file": None
                })
    
    # Generate summary report
    success_count = sum(1 for r in results if r['success'])
    main_logger.info(f"\nBatch Processing Summary:")
    main_logger.info(f"Total questions: {len(questions)}")
    main_logger.info(f"Successful: {success_count}")
    main_logger.info(f"Failed: {len(questions) - success_count}")
    
    return results

# ------------------------------------------------------------------------------
# Workflow Node Functions
# ------------------------------------------------------------------------------
@traceable(name="plan_scenes")
def plan_scenes(state: GraphState, **kwargs) -> GraphState:
    """Generate lesson plan using LLM."""
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

def validate_math_tex(code: str) -> str:
    """Enhanced validation with more pattern matching."""
    code = re.sub(
        r'create_(\w+)\(self,\s*color\s*:\s*Color\s*\)',
        r'create_\1(self, color: str)',
        code
    )
    # code = re.sub(
    #     r'Text\(.*?(\\frac|\\sum|\\int|\\lim|\\alpha|\\beta|\\theta|\\pi)',
    #     lambda m: m.group().replace('Text(', 'MathTex('), 
    #     code
    # )
    # code = re.sub(
    #     r'\.set_color\(([A-Z]+)\)',
    #     lambda m: f'.set_color("{m.group(1).lower()}")',
    #     code
    # )
    return code

def validate_scene_cleanup(code: str) -> str:
    """Ensure each scene method ends with proper cleanup."""
    scene_methods = re.finditer(r'def (\w+_scene)\(self\):.*?(?=\n\s*def |\Z)', code, re.DOTALL)
    
    for match in scene_methods:
        method_body = match.group(0)
        if not re.search(r'self\.(play|remove|clear)\s*\(.*?FadeOut', method_body):
            cleaned_method = re.sub(
                r'(\s*)(return|$)', 
                r'\1self.clear()\n\1\2', 
                method_body
            )
            code = code.replace(method_body, cleaned_method)
    return code

@traceable( name="generate_code")
def generate_code(state: GraphState, **kwargs) -> GraphState:
    """Generate Manim code with proper scene inheritance and camera handling."""
    logger.info("Generating Manim code from plan")
    api_context = get_manim_api_context()
    
    try:
        # Code template with embedded references and placeholders
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
        # Call each scene in order:
        {scene_calls}
    
    # SCENES (each scene must end with self.play(*[FadeOut(mob)for mob in self.mobjects if mob != self.background]))
    {scene_methods}
'''
        # Safely read the example file "gcf.py" if present.
        try:
            with open("app/templates/examples/gcf.py", "r") as f:
                gcf_example = f.read()
        except FileNotFoundError:
            logger.warning("gcf.py not found, using default template")
            gcf_example = ""
            
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{
                "role": "user",
                "content": f"""Create a Manim scene that inherits from ManimVoiceoverBase. This base class provides:
    
    1. Background image setup
    2. Voice service configuration
    3. Helper methods:
       - create_title(text): Creates properly sized titles, handles math notation
       - ensure_group_visible(group, margin): Ensures VGroups fit in frame
    
    The scene should use these methods appropriately. For example:
    - Use create_title() for section headings
    - Use ensure_group_visible() to ensure all objects are visible in the frame
    - Background and voice are auto-configured in __init__
    Generate Manim code with voiceovers using this structure:
{gcf_example}
Convert this plan to Manim code following STRICT RULES:
{state['plan']}

RULES ENFORCED BY SYSTEM (MUST OBEY):
1. MATH RULES:
   - Use MathTex for mathematical content: fractions, Greek letters, operators, sub/superscripts.
   - Format: r"\\frac{{1}}{{2}}" not r"$\\frac{{1}}{{2}}$".
   - Never use Text/Tex for math content.
2. SCENE STRUCTURE:
   - Every scene method must end with: self.play(*[FadeOut(mob)for mob in self.mobjects if mob != self.background])
   - The construct() method must call the scene methods in order.
3. GENERATE CODE STRUCTURE:
   - Class name should reflect the topic.
   - Include between 3 and 5 scene methods.
   - Helper methods and all functions must include type hints.
   - Use Create() to create objects, not ShowCreation().

4. VALIDATE AGAINST:
   ❌ Text with math symbols.
   ❌ Color type annotations (use string color names).
   ❌ Missing scene fadeout.
5. LAYOUT & ALIGNMENT RULES:
   - Use Manim's built-in alignment utilities (e.g., align_to, next_to, VGroup().arrange(DOWN, buff=0.5)) to avoid overlapping visuals.
   - Ensure all objects are clearly visible and appropriately spaced.
   - For layering, explicitly set foreground elements using self.add_foreground_mobjects() where needed.
   - Apply structured arrangement for clear and well-organized scenes.
   - Validate and adjust mobject positions with ensure_group_visible().
6. VISUAL CONTENT RULES:
   - Do not import any assets like SVGs or images.
   - Incorporate as many valid, constructive visual elements as possible to teach the concept.
   - Use visual objects from the Manim API as defined in {api_context}.
   - Ensure that visuals are relevant, well-aligned, and enhance explanation. For example, include diagrams, charts, or geometric shapes that illustrate the topic.
   - If the lesson concept can benefit from a visualization, include at least one visual element to reinforce the narrative.
   - Validate that objects are constructed with valid parameters according to the latest Manim API (e.g., when creating a Square, ensure its parameters match those in Manim Community v0.19.0).

IMPORTANT: Only use the following colors (and their aliases) exactly as defined: blue, teal, green, yellow, gold, red, maroon, purple, pink, light_pink, orange, light_brown, dark_brown, gray_brown, white, black, lighter_gray, light_gray, gray, dark_gray, darker_gray, blue_a, blue_b, blue_c, blue_d, blue_e, pure_blue. Do not invent or use any other color names.

OUTPUT FORMAT:
{code_template}
"""
            }]
        )
        
        code = response.choices[0].message.content
        # Remove any extraneous lines starting with '!'
        code = '\n'.join([line for line in code.split('\n') if not line.strip().startswith('!')])
        
        # Minimal essential validation regex adjustments
        code = re.sub(r'\.set_color\(([A-Z]+)\)',
                      lambda m: f'.set_color("{m.group(1).lower()}")', code)
        code = re.sub(
            r'(def (?!__init__|construct)(\w+)\(self(?!, color: str)\))(\s*:)',
            r'\1 -> None\3',
            code
        )
        
        output_state = {
            **state, 
            "generated_code": code,
            "current_stage": "code",
            "correction_attempts": 0  # Reset the correction counter
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
@traceable( name="validate_code")
def validate_code(state: GraphState) -> GraphState:
    """Perform basic structural validation and linting on the generated code."""
    if not state.get("generated_code"):
        return {**state, "error": "No code to validate"}
    
    code = state["generated_code"]
    failures = []
    
    try:
        # 1. Basic syntax check
        ast.parse(code)
        
        # 2. Basic structural checks
        structural_checks = [
            (r'from manim import', "Missing Manim imports"),
            (r'from app.templates.base.scene_base import ManimVoiceoverBase', "Missing ManimVoiceoverBase imports"),
            # (r'class \w+\(.*Scene\)', "Missing scene class definition"),
            (r'def construct\(self\)', "Missing construct method"),
            # (r'self\.play\(*[FadeOut\(mob\)for mob in self\.mobjects if mob != self\.background]\)', "Missing scene fadeout")
        ]
        
        for pattern, message in structural_checks:
            if not re.search(pattern, code):
                failures.append(message)
        
        # 3. Validate that only allowed colors are used
        invalid_colors = validate_color_usage(code)
        if invalid_colors:
            failures.append(f"Invalid color(s) used: {', '.join(invalid_colors)}")
        
        if failures:
            error_msg = "Validation failures:\n- " + "\n- ".join(failures)
            return {**state, "error": error_msg, "current_stage": "validate"}
        
        return {**state, "error": None, "current_stage": "validate"}
        
    except SyntaxError as e:
        return {**state, "error": f"Syntax error: {str(e)}", "current_stage": "validate"}
    
@traceable(name="execute_code")
def execute_code(state: GraphState) -> GraphState:
    """Execute Manim code and capture the output."""
    logger.info("Executing Manim code")
    
    # Generate file name in the generated folder with a standard timestamp.
    scene_file = generate_scene_filename(state['user_input'])
    logger.info(f"Writing code to file: {scene_file}")
    
    base_name, ext = os.path.splitext(scene_file)
    counter = 1
    while os.path.exists(scene_file):
        scene_file = f"{base_name}_{counter}{ext}"
        counter += 1
    
    # Convert to absolute path
    scene_file = os.path.abspath(scene_file)
    
    with open(scene_file, 'w') as f:
        f.write(state['generated_code'])
    logger.info(f"Saved generated code to: {scene_file}")
    
    try:
        logger.info(f"Running Manim with quality setting: {MANIM_QUALITY}")
        result = subprocess.run(
            [sys.executable, "-m", "manim", MANIM_QUALITY, scene_file],
            capture_output=True,
            text=True,
            timeout=EXECUTION_TIMEOUT,
            cwd=os.getcwd(),
            env={**os.environ, "PYTHONPATH": f"{os.getcwd()}:{os.environ.get('PYTHONPATH', '')}"}
        )
        
        if result.returncode != 0:
            error_msg = f"Manim execution failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
            logger.error(error_msg)
            output_state = {**state, "error": error_msg, "current_stage": "execute"}
            return log_state_transition("execute_code", state, output_state)
        
        logger.info("Manim execution completed successfully.")
        output = {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "scene_file": scene_file
        }
        logger.info(f"Scene file preserved at: {scene_file}")
        output_state = {**state, "execution_result": output, "error": None, "current_stage": "execute"}
        return log_state_transition("execute_code", state, output_state)
    except Exception as e:
        error_msg = f"Execution failed: {str(e)}"
        _, _, tb = sys.exc_info()
        line_no = traceback.extract_tb(tb)[-1].lineno
        error_msg += f"\nNear generated code line: {line_no}"
        
        output_state = {**state, "error": error_msg, "current_stage": "execute"}
        return log_state_transition("execute_code", state, output_state)

@traceable( name="error_correction")
def error_correction(state: GraphState) -> GraphState:
    """Unified error correction for both validation and execution errors."""
    state["correction_attempts"] = state.get("correction_attempts", 0) + 1
    
    if state["correction_attempts"] >= 3:
        error_msg = "Maximum correction attempts reached"
        logger.error(error_msg)
        return {**state, "error": error_msg}
    
    api_context = get_manim_api_context()
    error_msg = state.get("error", "")
    code = state["generated_code"]
    
    # Determine error type and construct appropriate correction prompt
    if "Validation failures" in error_msg:
        correction_type = "validation"
    else:
        correction_type = "execution"
    
    # Build the correction prompt based on error type
    correction_prompt = f"""Fix the following {correction_type} error in the Manim code:

ERROR:
{error_msg}

CURRENT CODE:
{code}

MANIM API REFERENCE:
{api_context}

REQUIREMENTS:
IMPORTANT: Only use the following colors (and their aliases) exactly as defined: blue, teal, green, yellow, gold, red, maroon, purple, pink, light_pink, orange, light_brown, dark_brown, gray_brown, white, black, lighter_gray, light_gray, gray, dark_gray, darker_gray, blue_a, blue_b, blue_c, blue_d, blue_e, pure_blue. Do not invent or use any other color names.
1. Follow Manim's API exactly for class/method signatures
2. Use proper scene inheritance based on needed features
3. Ensure all animations are properly constructed
4. Clean up scenes appropriately
5. Replace any camera frame manipulations with proper object animations
6. Use MathTex for mathematical content
7. Ensure proper voiceover integration

COMMON FIXES:
1. For zoom effects: Scale objects instead of camera
   - Create VGroup of relevant objects
   - Use group.animate.scale()
2. For pan effects: Move objects instead of camera
   - Use group.animate.shift()
3. For math content: Use MathTex instead of Text
4. For scene cleanup: Add self.clear() or FadeOut

If you need specific features, use the appropriate scene class:
- For camera movement: MovingCameraScene
- For 3D scenes: ThreeDScene
- For voiceover: VoiceoverScene

Consult the API reference for exact method signatures and parameters.

OUTPUT THE COMPLETE CORRECTED CODE WITH NO EXPLANATION."""

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": correction_prompt}]
        )
        
        corrected_code = response.choices[0].message.content
        
        # Load error history if available
        try:
            with open(ERROR_HISTORY, 'r') as f:
                error_history = json.load(f)
        except FileNotFoundError:
            error_history = []
        
        # Log the error and correction attempt
        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "error_type": correction_type,
            "original_error": error_msg,
            "correction_attempt": state["correction_attempts"],
            "success": True  # We'll know if it failed in the next validation/execution
        }
        error_history.append(error_entry)
        
        # Save updated error history
        with open(ERROR_HISTORY, 'w') as f:
            json.dump(error_history[-100:], f, indent=2)  # Keep last 100 entries
        
        return {
            **state,
            "generated_code": corrected_code,
            "error": None
        }
    except Exception as e:
        return {**state, "error": f"Correction failed: {str(e)}"}

def lint_code(state: GraphState) -> GraphState:
    """Perform a lint check on the generated code to catch errors before execution."""
    logger.info("Linting generated code")
    lint_errors = []
    temp_file_path = None
    try:
        # Write the generated code to a temporary file
        temp_file_path = os.path.join(tempfile.gettempdir(), "lint_generated.py")
        with open(temp_file_path, "w") as temp_file:
            temp_file.write(state["generated_code"])
        
        # Attempt to compile the temporary file
        py_compile.compile(temp_file_path, doraise=True)
    except py_compile.PyCompileError as ce:
        lint_errors.append(str(ce))
    
    # New: Scene structure validation
    scene_errors = validate_scene_methods(state["generated_code"])
    if scene_errors:
        lint_errors.extend(scene_errors)
    
    # New: Dry-run scene initialization
    try:
        temp_module = ModuleType("temp_manim_module")
        exec(state["generated_code"], temp_module.__dict__)
        scene_class = next((cls for cls in temp_module.__dict__.values() 
                          if isinstance(cls, type) and issubclass(cls, Scene)), None)
        if scene_class:
            scene_instance = scene_class()
            scene_instance.setup()  # Test setup without rendering
    except Exception as e:
        lint_errors.append(f"Dry-run failed: {str(e)}")
    
    if lint_errors:
        error_msg = "Lint check failed: " + "; ".join(lint_errors)
        output_state = {
            **state,
            "error": error_msg,
            "current_stage": "lint"
        }
        return log_state_transition("lint_code", state, output_state)
    else:
        output_state = {
            **state,
            "current_stage": "lint_passed"
        }
        return log_state_transition("lint_code", state, output_state)

# ------------------------------------------------------------------------------
# Decision Functions
# ------------------------------------------------------------------------------
def decide_after_validation(state):
    decision = "correct_code" if state.get("error") else "execute_code"
    logger.info(f"\nDecision after validation: {decision}")
    logger.info(f"Current error state: {state.get('error', 'None')}")
    return decision

def decide_after_correction(state):
    decision = "correct_code" if state.get("error") else "validate_code"
    logger.info(f"\nDecision after correction: {decision}")
    logger.info(f"Current error state: {state.get('error', 'None')}")
    return decision

# ------------------------------------------------------------------------------
# Build the Workflow Graph
# ------------------------------------------------------------------------------
logger.info("Initializing workflow graph")
workflow = StateGraph(GraphState)

workflow.add_node("plan_scenes", plan_scenes)
workflow.add_node("generate_code", generate_code)
workflow.add_node("validate_code", validate_code)
workflow.add_node("execute_code", execute_code)
workflow.add_node("correct_code", error_correction)

workflow.set_entry_point("plan_scenes")
workflow.add_edge("plan_scenes", "generate_code")
workflow.add_edge("generate_code", "validate_code")

# Simplified conditional edges
workflow.add_conditional_edges(
    "validate_code",
    decide_after_validation,
    {
        "correct_code": "correct_code",
        "execute_code": "execute_code"
    }
)

workflow.add_conditional_edges(
    "correct_code",
    lambda x: "validate_code" if x["correction_attempts"] < 3 else END,
    {
        "validate_code": "validate_code",
        END: END
    }
)

workflow.add_conditional_edges(
    "execute_code",
    lambda x: "correct_code" if (x.get("error") and x["correction_attempts"] < 3) else END,
    {
        "correct_code": "correct_code",
        END: END
    }
)

logger.info("Compiling workflow graph")
app = workflow.compile()

# display(Image(app.get_graph().draw_mermaid_png(output_file_path='./beta_graph.png')))

# ------------------------------------------------------------------------------
# Additional Utility Functions for Diff and Logging
# ------------------------------------------------------------------------------
def extract_relevant_diff(original: str, fixed: str) -> str:
    """Return a unified diff of the original and fixed code, limited to the first 12 lines."""
    orig_lines = original.splitlines()
    fixed_lines = fixed.splitlines()
    diff = list(difflib.unified_diff(orig_lines, fixed_lines, lineterm=''))
    return "\n".join(diff[:12])  # Summary of diff

def log_error_fix(original_error: str, original_code: str, fixed_code: str, success: bool):
    """Log a concise error-correction summary to the knowledge base (error_fixes.json)."""
    diff_summary = extract_relevant_diff(original_code, fixed_code)
    entry = {
        "timestamp": datetime.now().isoformat(),
        "error": original_error.splitlines()[0],
        "fix_snippet": diff_summary,
        "success": success
    }
    
    history = load_error_history()
    history.append(entry)
    with open(ERROR_HISTORY, 'w') as f:
        json.dump(history[-100:], f, indent=2)

def load_error_history() -> list:
    """Load error correction history from file."""
    try:
        with open(ERROR_HISTORY, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def get_manim_api_context() -> str:
    """Load the up-to-date Manim API source from a dedicated file."""
    try:
        with open("app/templates/api_docs/manim_mobjects.py", "r") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Failed to load Manim API context: {e}")
        return ""

def remove_implementation_details(example: str) -> str:
    """Create a template with placeholders from the provided example."""
    template = re.sub(
        r'(def \w+_scene\(self\):).*?(\n\s*""".*?""")',
        r'\1\n        """SCENE IMPLEMENTATION"""\n        # Animate using helper methods',
        example,
        flags=re.DOTALL
    )
    template = re.sub(r'\[.*?\]', '[RELEVANT_CONTENT]', template)
    return template

def validate_color_usage(code: str) -> list[str]:
    """
    Scan the code for any usage of set_color() with a color name and return a
    list of invalid colors (i.e., not in ALLOWED_COLORS).
    """
    invalid_colors = []
    color_pattern = re.compile(
        r'\.(?:set_color|set_fill|set_stroke)\(["\']([\w_]+)["\']\)|'
        r'Color\(["\']([\w_]+)["\']\)|'
        r'color=["\']([\w_]+)["\']'
    )
    
    for match in color_pattern.finditer(code):
        for group in match.groups():
            if group and group.lower() not in VALID_COLORS:
                invalid_colors.append(group)
    
    return list(set(invalid_colors))  # Return unique invalid colors

def validate_scene_methods(code: str) -> list[str]:
    """Validate scene method structure before execution"""
    errors = []
    tree = ast.parse(code)
    
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for method in node.body:
                if isinstance(method, ast.FunctionDef) and method.name.endswith('_scene'):
                    last_expr = method.body[-1] if method.body else None
                    if not (isinstance(last_expr, ast.Expr) and 
                           isinstance(last_expr.value, ast.Call) and
                           last_expr.value.func.attr in ('clear', 'play', 'remove')):
                        errors.append(f"Scene method {method.name} missing cleanup")
    return errors

# # ------------------------------------------------------------------------------
# # Tests: Unit, Integration, and End-to-End Tests
# # ------------------------------------------------------------------------------
# class TestUtilityFunctions(unittest.TestCase):
#     def test_extract_concept(self):
#         self.assertEqual(extract_concept("how to convert fractions to decimals?"), "convert_fractions_to_decimals")
#         self.assertEqual(extract_concept("Explain Quantum Mechanics"), "quantum_mechanics")
#         self.assertEqual(extract_concept("What is the capital of France?"), "the_capital_of_france")
#         self.assertEqual(extract_concept("show me the money!"), "the_money")
#         self.assertEqual(extract_concept("Random Topic"), "random_topic")

#     def test_generate_scene_filename(self):
#         topic = "how to convert fractions to decimals?"
#         filename = generate_scene_filename(topic)
#         self.assertTrue(filename.endswith(".py"))
#         self.assertIn("convert_fractions_to_decimals", os.path.basename(filename))

#     def test_validate_math_tex(self):
#         input_code = 'create_example(self, color: Color)'
#         expected_code = 'create_example(self, color: str)'
#         self.assertEqual(validate_math_tex(input_code), expected_code)

#     def test_log_state_transition(self):
#         """Test state transition logging functionality"""
#         input_state = {
#             "user_input": "test",
#             "generated_code": "code1",
#             "current_stage": "plan"
#         }
#         output_state = {
#             "user_input": "test",
#             "generated_code": "code2",
#             "current_stage": "code"
#         }
#         result = log_state_transition("test_node", input_state, output_state)
#         self.assertEqual(result, output_state)

#     def test_validate_scene_cleanup(self):
#         """Test scene cleanup validation"""
#         input_code = """
#     def test_scene(self):
#         self.play(Create(Circle()))
#         """
#         result = validate_scene_cleanup(input_code)
#         self.assertIn("self.clear()", result)

#     def test_remove_implementation_details(self):
#         """Test template generation"""
#         example = """
#     def example_scene(self):
#         \"\"\"Test Scene\"\"\"
#         self.play([Create(Circle())])
#         """
#         result = remove_implementation_details(example)
#         self.assertIn("SCENE IMPLEMENTATION", result)
#         self.assertNotIn("Create(Circle())", result)

# class TestStateManagement(unittest.TestCase):
#     """New test class for state management"""
#     def setUp(self):
#         self.initial_state = {
#             "user_input": "test topic",
#             "plan": None,
#             "generated_code": None,
#             "execution_result": None,
#             "error": None,
#             "current_stage": "plan",
#             "correction_attempts": 0
#         }

#     def test_state_transitions(self):
#         """Test state transitions through workflow"""
#         state = self.initial_state.copy()
        
#         # Test plan transition
#         state["plan"] = "Test plan"
#         state["current_stage"] = "plan"
#         self.assertEqual(state["current_stage"], "plan")
        
#         # Test code generation transition
#         state["generated_code"] = "Test code"
#         state["current_stage"] = "code"
#         self.assertEqual(state["current_stage"], "code")

#     def test_error_state_handling(self):
#         """Test error state management"""
#         state = self.initial_state.copy()
#         state["error"] = "Test error"
#         state["correction_attempts"] = 1
        
#         # Test error correction limit
#         for _ in range(3):
#             state = error_correction(state)
#         self.assertIn("Maximum correction attempts", state["error"])

# class TestCodeGeneration(unittest.TestCase):
#     def test_math_content_validation(self):
#         """Test math content validation"""
#         code = 'Text("\\frac{1}{2}")'
#         result = validate_math_tex(code)
#         self.assertIn("MathTex", result)

#     def test_color_validation(self):
#         """Test color parameter validation"""
#         code = 'circle.set_color(RED)'
#         result = validate_math_tex(code)
#         self.assertIn('.set_color("red")', result.lower())

# class TestIntegration(unittest.TestCase):
#     """Enhanced integration tests"""
#     @patch.object(client.chat.completions, "create")
#     def test_plan_to_code_flow(self, mock_create):
#         """Test plan to code generation flow"""
#         # Mock responses
#         mock_create.side_effect = [
#             MagicMock(choices=[MagicMock(message=MagicMock(content="Test plan"))]),
#             MagicMock(choices=[MagicMock(message=MagicMock(content="Test code"))])
#         ]
        
#         state = {
#             "user_input": "test topic",
#             "plan": None,
#             "generated_code": None,
#             "execution_result": None,
#             "error": None,
#             "current_stage": "plan",
#             "correction_attempts": 0
#         }
        
#         # Test plan generation
#         state = plan_scenes(state)
#         self.assertIsNotNone(state["plan"])
        
#         # Test code generation
#         state = generate_code(state)
#         self.assertIsNotNone(state["generated_code"])

#     @patch("subprocess.run")
#     def test_code_execution_flow(self, mock_run):
#         """Test code execution and error handling"""
#         # Test successful execution
#         mock_run.return_value = subprocess.CompletedProcess(
#             args=["manim"],
#             returncode=0,
#             stdout="Success",
#             stderr=""
#         )
        
#         state = {
#             "user_input": "test topic",
#             "generated_code": "test code",
#             "plan": "test plan",
#             "execution_result": None,
#             "error": None,
#             "current_stage": "execute",
#             "correction_attempts": 0
#         }
        
#         result = execute_code(state)
#         self.assertIsNone(result["error"])
#         self.assertIsNotNone(result["execution_result"])

# class TestEndToEndWorkflow(unittest.TestCase):
#     def setUp(self):
#         # Use the existing workflow graph instead of recreating it
#         self.app = app  # Using the global 'app' that's already compiled
    
#     @patch.object(client.chat.completions, "create")
#     def test_complete_workflow(self, mock_create):
#         """Test complete workflow execution with the actual production graph"""
#         # Setup mock responses with proper voiceover and cleanup
#         good_code = '''
# from manim import *
# from manim_voiceover import VoiceoverScene
# from manim_voiceover.services.openai import OpenAIService

# class MathScene(VoiceoverScene):
#     def __init__(self):
#         super().__init__()
#         self.set_speech_service(OpenAIService())
        
#     def construct(self):
#         with self.voiceover(text="Explanation"):
#             self.play(Create(Circle()))
#         self.clear()
#     '''
#         mock_create.side_effect = [
#             MagicMock(choices=[MagicMock(message=MagicMock(content="Test plan"))]),
#             MagicMock(choices=[MagicMock(message=MagicMock(content=good_code))])
#         ]
        
#         inputs = {"user_input": "test topic"}
#         result = self.app.invoke(inputs)
        
#         self.assertIsNotNone(result["execution_result"])
#         self.assertIsNone(result["error"])
#         self.assertIn("scene_file", result["execution_result"])

#     @patch.object(client.chat.completions, "create")
#     def test_error_recovery(self, mock_create):
#         """Test workflow error recovery using the actual production graph"""
#         valid_corrected_code = '''
# from manim import *
# from manim_voiceover import VoiceoverScene
# from manim_voiceover.services.openai import OpenAIService

# class MathScene(VoiceoverScene):
#     def __init__(self):
#         super().__init__()
#         self.set_speech_service(OpenAIService())
        
#     def construct(self):
#         with self.voiceover(text="Explanation"):
#             self.play(Create(Circle()))
#         self.clear()
# '''
#         # Mock responses: first generate plan, then code with error, then corrected valid code
#         mock_create.side_effect = [
#             MagicMock(choices=[MagicMock(message=MagicMock(content="Test plan"))]),
#             MagicMock(choices=[MagicMock(message=MagicMock(content="Bad code"))]),
#             MagicMock(choices=[MagicMock(message=MagicMock(content=valid_corrected_code))])
#         ]
        
#         inputs = {"user_input": "test topic"}
#         result = self.app.invoke(inputs)
        
#         # Verify error recovery worked
#         self.assertIsNotNone(result["execution_result"])
#         self.assertIsNone(result["error"])
#         self.assertLessEqual(result["correction_attempts"], 3)

#     def test_maximum_correction_attempts(self):
#         """Test that workflow properly handles maximum correction attempts"""
#         with patch.object(client.chat.completions, "create") as mock_create:
#             # Always return bad code to trigger max attempts
#             mock_create.side_effect = [
#                 MagicMock(choices=[MagicMock(message=MagicMock(content="Test plan"))]),
#                 *[MagicMock(choices=[MagicMock(message=MagicMock(content="Bad code"))])]*4
#             ]
            
#             inputs = {"user_input": "test topic"}
#             result = self.app.invoke(inputs)
            
#             # Verify max attempts handled
#             self.assertIsNotNone(result["error"])
#             self.assertIn("Maximum correction attempts", result["error"])
#             self.assertEqual(result["correction_attempts"], 3)

# class TestValidation(unittest.TestCase):
#     def test_voiceover_validation(self):
#         code = "class TestScene(Scene): pass"
#         state = {"generated_code": code}
#         result = validate_code(state)
#         self.assertIn("VoiceoverScene inheritance", result["error"])
        
#     def test_scene_cleanup_validation(self):
#         code = "def test_scene(self): self.play(Create(Circle()))"
#         state = {"generated_code": code}
#         result = validate_code(state)
#         self.assertIn("Missing scene cleanup", result["error"])

# ------------------------------------------------------------------------------
# Main Execution Block: Run Tests or Workflow Based on a Command-Line Flag
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    if "--test" in sys.argv:
        sys.argv.remove("--test")
        unittest.main()
    else:
        # Initialize workflow
        try:
            logger.info("Initializing workflow graph")
            app.get_graph().draw_mermaid_png(output_file_path='./beta_graph.png')
        except Exception as e:
            logger.warning(f"Could not generate workflow visualization: {e}")
            logger.info("Continuing with execution...")
        
        # Example questions
        questions = ["How do magnets work?",
                    #  "What causes the seasons?",
                    #  "Why is the sky blue?",
                    #  "How do earthquakes happen?",
                    #  "What is photosynthesis?",
                    #  "What is the difference between asexual and sexual reproduction?",
                    #  "Why do soap bubbles form perfect spheres?",
                    #  "Why do planets orbit in ellipses rather than circles?",
                    #  "Why do snowflakes always have six sides?",
                    #  "Why do spinning tops stay upright?",
                    #  "Why do waves break as they approach the shore?",
                    #  "Why do galaxies form spiral shapes?",
                    #  "Why do tornadoes spin in specific directions?",
                    # "Why can't we fold a paper more than 7-8 times?",
                    #  "Why do magnets have two poles?",
                    #  "Why do leaves change color in the fall?",
                    #  "Why do some objects float while others sink?",
                    #  "Why do some objects burn while others don't?",
                    #  "Why do we see the same patterns in river deltas and tree branches?",
                    #  "Why do prime numbers become rarer as numbers get bigger?",
                    #  "Why do bicycle wheels appear to spin backward sometimes?",
                    #  "Why do we see rainbows at specific angles?",
                    #  "Why do birds fly in V formations?",
                    #  "Why do cicadas emerge in prime number years?",
                    #  "Why do some objects rust while others don't?",
                    #  "Why do some objects rust while others don't?",
                    #  "Why do some objects rust while others don't?",
                    #  "Why do some objects rust while others don't?",
                    #  "Why do some objects rust while others don't?",
                    #  "Why do fireflies flash in synchrony?",
                    #  "Why do cats always land on their feet?",
                    #  "Why do wounds heal in a spiral pattern?",
                     ]
        
        # Process all questions
        results = batch_process_questions(questions)
        
        # Print final summary
        print("\nFinal Results:")
        for result in results:
            status = "✓" if result['success'] else "✗"
            print(f"{status} {result['question']}")
            if not result['success']:
                print(f"   Error: {result['error']}")
            if result.get('scene_file'):
                print(f"   Scene file: {result['scene_file']}")