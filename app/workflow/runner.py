from typing import Dict, Any
import logging
from app.models.state import GraphState
from app.core.logging import setup_question_logger
from .nodes import generate_code, plan_scenes
from app.job_store import job_store

class WorkflowRunner:
    """Handles the execution of the video generation workflow."""
    
    def __init__(self, initial_state: GraphState, job_id: str):
        """Initialize the workflow runner with initial state and job ID."""
        self.state = initial_state
        self.job_id = job_id
        self.logger = setup_question_logger(initial_state["user_input"])

    async def run(self) -> None:
        """Execute the workflow steps."""
        try:
            # Update job status to processing
            job_store.update_job(self.job_id, status="processing")
            
            # Plan generation
            job_store.add_log(self.job_id, "Starting scene planning")
            self.state = plan_scenes(self.state)
            if self.state.get("error"):
                raise Exception(self.state["error"])
            
            # Code generation
            job_store.add_log(self.job_id, "Starting code generation")
            self.state = generate_code(self.state)
            if self.state.get("error"):
                raise Exception(self.state["error"])
            
            # Update job with success
            job_store.update_job(
                self.job_id,
                status="completed",
                result_url=self.state.get("execution_result", {}).get("scene_file")
            )
            
        except Exception as e:
            # Update job with error
            job_store.update_job(
                self.job_id,
                status="failed",
                error=str(e)
            )
            job_store.add_log(self.job_id, f"Error: {str(e)}")
            self.logger.error(f"Workflow error: {str(e)}")
            self.state["error"] = str(e)
            return self.state 