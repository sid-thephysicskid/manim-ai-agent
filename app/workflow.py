# # app/workflow.py
# """
# Refactored workflow module.

# This module encapsulates the end-to-end workflow into a single class,
# WorkflowRunner, which implements the following stages:
#   1. Plan Generation (e.g., using an LLM to generate a plan)
#   2. Code Generation (producing complete Manim code based on the plan)
#   3. Code Execution (writes the generated code to disk and runs Manim)
#   4. Voiceover Integration (integrates simulated voiceover)
#   5. Error Correction (attempts a dummy error correction if needed)

# Each stage logs its progress and updates an internal state dictionary.
# Logs are persisted locally (which can later be replaced with bucket storage).
# """

# import os
# import time
# import uuid
# import json
# import logging
# import subprocess
# import tempfile
# from typing import Dict, Any

# # Global constants – these mirror the ones from your legacy workflow.
# EXECUTION_TIMEOUT = 180  # seconds
# MANIM_QUALITY = "-ql"    # low-quality flag for quick rendering

# logger = logging.getLogger("workflow")
# logger.setLevel(logging.INFO)


# class WorkflowRunner:
#     def __init__(self, user_input: str):
#         self.state: Dict[str, Any] = {
#             "user_input": user_input,
#             "logs": [],
#             "start_time": time.time(),
#             "status": "initialized",
#             "plan": None,
#             "generated_code": None,
#             "execution_result": None,
#             "voiceover": None,
#             "error": None,
#         }
#         self.log("Workflow initialized.")

#     def log(self, message: str) -> None:
#         logger.info(message)
#         self.state["logs"].append(message)

#     def plan_generation(self):
#         """Generate a detailed plan from the provided user input using an LLM (simulated)."""
#         prompt = f"Generate a detailed plan for: {self.state['user_input']}"
#         self.log(f"Plan generation started with prompt: {prompt}")
#         try:
#             # Simulated LLM call; replace with your production code as needed.
#             time.sleep(1)
#             plan = f"Simulated plan for '{self.state['user_input']}'"
#             self.state["plan"] = plan.strip()
#             self.log("Plan generated successfully.")
#         except Exception as e:
#             self.state["error"] = f"Plan generation error: {e}"
#             self.log(self.state["error"])
#         return self

#     def code_generation(self):
#         """Generate complete Manim code based on the plan (simulated)."""
#         if not self.state["plan"]:
#             self.state["error"] = "Plan not available for code generation."
#             self.log(self.state["error"])
#             return self
#         prompt = f"Generate Manim code for the plan: {self.state['plan']}"
#         self.log(f"Code generation started with prompt: {prompt}")
#         try:
#             time.sleep(1)
#             code = (
#                 "from manim import *\n\n"
#                 "class GeneratedScene(Scene):\n"
#                 "    def construct(self):\n"
#                 f"        self.add(Text('Animation for: {self.state['user_input']}'))\n"
#             )
#             self.state["generated_code"] = code
#             self.log("Code generated successfully.")
#         except Exception as e:
#             self.state["error"] = f"Code generation error: {e}"
#             self.log(self.state["error"])
#         return self

#     def execute_code(self):
#         """Execute the generated code by writing it to a temporary file and invoking Manim."""
#         if not self.state.get("generated_code"):
#             self.state["error"] = "No generated code to execute."
#             self.log(self.state["error"])
#             return self

#         self.log("Executing generated code.")
#         temp_dir = tempfile.gettempdir()
#         scene_file = os.path.join(temp_dir, f"generated_{uuid.uuid4().hex}.py")
#         try:
#             with open(scene_file, "w") as f:
#                 f.write(self.state["generated_code"])
#             self.log(f"Generated code written to file: {scene_file}")
#         except Exception as e:
#             self.state["error"] = f"Failed to write generated code: {e}"
#             self.log(self.state["error"])
#             return self

#         try:
#             result = subprocess.run(
#                 ["manim", MANIM_QUALITY, scene_file],
#                 capture_output=True,
#                 text=True,
#                 timeout=EXECUTION_TIMEOUT,
#                 cwd=os.getcwd()
#             )
#             if result.returncode != 0:
#                 self.state["error"] = (
#                     f"Manim execution failed. STDOUT: {result.stdout}, STDERR: {result.stderr}"
#                 )
#                 self.log(self.state["error"])
#             else:
#                 self.state["execution_result"] = {
#                     "stdout": result.stdout,
#                     "stderr": result.stderr,
#                     "scene_file": scene_file,
#                     "returncode": result.returncode,
#                 }
#                 self.log("Manim execution completed successfully.")
#         except Exception as e:
#             self.state["error"] = f"Exception during code execution: {e}"
#             self.log(self.state["error"])
#         return self

#     def voiceover_integration(self):
#         """Integrate voiceover logic (simulated)."""
#         # Only run voiceover integration if there was no error during previous stages.
#         if self.state.get("error"):
#             self.log("Skipping voiceover integration due to previous error.")
#             return self
#         self.log("Integrating voiceover.")
#         try:
#             time.sleep(1)
#             # Simulate voiceover file generation/integration.
#             voiceover_file = "simulated_voiceover.mp3"
#             self.state["voiceover"] = voiceover_file
#             self.log("Voiceover integrated successfully.")
#         except Exception as e:
#             self.state["error"] = f"Voiceover integration failed: {e}"
#             self.log(self.state["error"])
#         return self

#     def error_correction(self):
#         """Attempt dummy error correction if an error is present (simulated correction)."""
#         if self.state.get("error"):
#             self.log("Attempting error correction.")
#             try:
#                 time.sleep(1)
#                 # Simulate an error correction; in production, plug in your logic here.
#                 self.state["error_corrected"] = True
#                 self.log("Error correction applied.")
#                 # For simulation, assume correction clears the error.
#                 self.state["error"] = None
#             except Exception as e:
#                 self.state["error"] = f"Error correction exception: {e}"
#                 self.log(self.state["error"])
#         return self

#     def run(self):
#         """
#         Execute the complete workflow:
#           - Generate plan
#           - Generate code based on the plan
#           - Execute code using Manim
#           - If errors occur, attempt error correction
#           - Otherwise, integrate voiceover
#         """
#         self.plan_generation().code_generation().execute_code()
#         if self.state.get("error"):
#             self.error_correction()
#         else:
#             self.voiceover_integration()

#         # Update final status and compute duration
#         self.state["status"] = "completed" if not self.state.get("error") else "failed"
#         self.state["completion_time"] = time.time()
#         self.state["duration"] = self.state["completion_time"] - self.state.get("start_time", self.state["completion_time"])
#         self.log("Workflow execution completed.")
#         self.persist_logs()
#         return self.state

#     def persist_logs(self):
#         """Persist workflow logs to a local file (can later be replaced with a persistent bucket)."""
#         logs_dir = "logs"
#         if not os.path.exists(logs_dir):
#             os.makedirs(logs_dir)
#         log_file = os.path.join(logs_dir, f"workflow_{uuid.uuid4().hex}.json")
#         try:
#             with open(log_file, "w") as f:
#                 json.dump(self.state, f, indent=4)
#             self.log(f"Persisted workflow logs to {log_file}")
#         except Exception as e:
#             self.log(f"Unable to persist logs: {e}")


# def run_full_workflow(user_input: str) -> dict:
#     """
#     Main entry point to run the complete workflow.
#     This function instantiates a WorkflowRunner with a given user input,
#     executes the workflow, and returns the final state.
#     """
#     runner = WorkflowRunner(user_input)
#     final_state = runner.run()
#     logger.info(f"Final workflow state: {final_state}")
#     return final_state