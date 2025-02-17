# app/workflow.py
"""
Production-ready workflow module.

This module refactors the full end-to-end workflow you tested in workflow_beta.py
into a set of modular nodes:
  - Plan Generation: Uses an LLM to generate an animation plan.
  - Code Generation: Uses an LLM to produce complete Manim code based on the plan.
  - Execution: Writes the generated code to a file and calls Manim to render the animation.
  - Error Correction: (A dummy placeholder that can be extended.)
  
In addition, every node logs its state transitions (before and after execution) including
timings and errors. These logs and metrics can be persisted and later analyzed to drive data‑driven
improvements—such as refining prompts or fine‑tuning LLM configurations.
"""

import os
import time
import uuid
import logging
import subprocess
import tempfile

from app.schemas import JobSubmission  # if needed for type hints

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Settings – adjust these or import from your config
EXECUTION_TIMEOUT = 180  # seconds to wait for code execution
MANIM_QUALITY = "-ql"    # low-quality flag for quick rendering

def log_state_transition(node_name, previous_state, new_state):
    """
    Logs the transition between workflow nodes.
    The log entry contains the node name, a timestamp, and snapshots of the state 
    before and after the node execution.
    """
    entry = {
        "node": node_name,
        "timestamp": time.time(),
        "state_before": previous_state.copy(),  # shallow copy
        "state_after": new_state.copy()
    }
    new_state.setdefault("transition_logs", []).append(entry)
    logger.info(f"Transition [{node_name}]: {entry}")
    return new_state

# ============================================================================
# These helper functions encapsulate the LLM calls/prompts from your tested
# workflow_beta.py. Replace the placeholder implementations with your
# actual integration as needed.
# ============================================================================

def generate_plan_with_llm(prompt: str) -> str:
    """
    Call the LLM (or use your tested logic from workflow_beta.py) to generate a plan.
    Replace this placeholder with your actual API call / prompt logic.
    """
    logger.info("Generating plan with prompt: " + prompt)
    # Simulate delay and return a tested/expected plan
    time.sleep(1)
    return "Simulated plan: " + prompt

def generate_code_with_llm(prompt: str) -> str:
    """
    Call the LLM (or use your tested logic from workflow_beta.py) to generate Manim code.
    Replace this placeholder with your actual code generation logic.
    """
    logger.info("Generating code with prompt: " + prompt)
    # Simulate delay and return code similar to what you tested in workflow_beta.py
    time.sleep(1)
    return (
        "from manim import *\n\n"
        "class GeneratedScene(Scene):\n"
        "    def construct(self):\n"
        f"        self.add(Text('Animation for: {prompt}'))\n"
    )

# ============================================================================
# Workflow Node implementations use the above helper functions.
# ============================================================================

def plan_generation(state):
    """
    Uses the tested prompt from workflow_beta.py to generate an animation plan.
    """
    logger.info("Starting plan generation.")
    # Use the tested prompt from workflow_beta.py
    prompt = f"Generate a detailed animation plan for explaining: {state['user_input']}"
    plan = generate_plan_with_llm(prompt)
    state["plan"] = plan.strip()
    state.setdefault("logs", []).append("Plan generated successfully.")
    state["current_stage"] = "plan_generation"
    return log_state_transition("plan_generation", state, state)

def code_generation(state):
    """
    Uses the tested code generation logic from workflow_beta.py.
    It builds a prompt based on the generated plan and expects complete Manim code.
    """
    logger.info("Starting code generation.")
    if "plan" not in state:
        state["error"] = "No plan available for code generation."
        return state
    prompt = f"Based on the plan: {state['plan']}, generate complete Manim code that implements the animation."
    generated_code = generate_code_with_llm(prompt)
    state["generated_code"] = generated_code
    state.setdefault("logs", []).append("Code generated successfully.")
    state["current_stage"] = "code_generation"
    return log_state_transition("code_generation", state, state)

def execute_code(state):
    """
    Writes the generated Manim code to a file, calls Manim (using subprocess) 
    to render the animation, and captures stdout/stderr.
    """
    logger.info("Starting code execution.")
    # Use the system temporary directory for generated code.
    temp_dir = tempfile.gettempdir()
    scene_file = os.path.join(temp_dir, f"generated_{uuid.uuid4().hex}.py")
    logger.info(f"Writing generated code to temporary file: {scene_file}")
    try:
        with open(scene_file, "w") as f:
            f.write(state["generated_code"])
        state.setdefault("logs", []).append(f"Generated code saved to {scene_file}.")
    except Exception as e:
        err = f"Failed to write code file: {str(e)}"
        logger.error(err)
        state["error"] = err
        state["current_stage"] = "execute_code"
        return log_state_transition("execute_code", state, state)
    
    # Execute the generated code using Manim.
    try:
        result = subprocess.run(
            ["manim", MANIM_QUALITY, scene_file],
            capture_output=True,
            text=True,
            timeout=EXECUTION_TIMEOUT,
            cwd=os.getcwd()
        )
        if result.returncode != 0:
            error_msg = (
                f"Manim execution failed.\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
            )
            logger.error(error_msg)
            state["error"] = error_msg
            state.setdefault("logs", []).append("Execution failed.")
            state["current_stage"] = "execute_code"
            return log_state_transition("execute_code", state, state)
        else:
            logger.info("Manim execution completed successfully.")
            state["execution_result"] = {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "scene_file": scene_file,
            }
            state.setdefault("logs", []).append("Execution completed successfully.")
            state["current_stage"] = "execute_code"
            return log_state_transition("execute_code", state, state)
    except Exception as ex:
        error_msg = f"Exception during execution: {str(ex)}"
        logger.error(error_msg)
        state["error"] = error_msg
        state.setdefault("logs", []).append("Exception encountered during code execution.")
        state["current_stage"] = "execute_code"
        return log_state_transition("execute_code", state, state)

def error_correction(state):
    """
    Dummy error correction step. In a production system, this might trigger retries,
    parameter adjustments, or delegate to a separate error-handling service.
    """
    if state.get("error"):
        logger.info("Attempting error correction.")
        time.sleep(1)  # Simulate error handling
        state["error_corrected"] = True
        state.setdefault("logs", []).append("Dummy error correction applied.")
        state["current_stage"] = "error_correction"
        return log_state_transition("error_correction", state, state)
    return state

def complete_workflow(state):
    """
    Orchestrates the full workflow, sequentially calling:
      1. plan_generation
      2. code_generation
      3. execute_code
      4. (optionally) error_correction if errors occurred.
      
    Records all transitions, and finally records the duration and overall status.
    """
    state = plan_generation(state)
    state = code_generation(state)
    state = execute_code(state)
    if state.get("error"):
        state = error_correction(state)
    state["status"] = "completed" if not state.get("error") else "failed"
    state["completion_time"] = time.time()
    state.setdefault("logs", []).append("Workflow completed.")
    state["duration"] = state["completion_time"] - state.get("start_time", state["completion_time"])
    return log_state_transition("workflow_complete", state, state)

def run_full_workflow(user_input):
    """
    Main entry point to run the complete workflow.
    Initializes the state with the user input and timing, then runs the workflow.
    
    Returns a detailed state dictionary including logs, metrics, errors, and results,
    which can later be analyzed to drive product improvements.
    """
    state = {
        "user_input": user_input,
        "start_time": time.time(),
        "logs": []
    }
    final_state = complete_workflow(state)
    logger.info(f"Final workflow state: {final_state}")
    return final_state