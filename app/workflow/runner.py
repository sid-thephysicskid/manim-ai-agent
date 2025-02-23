import asyncio
import logging
from typing import Dict, Any
from app.models.state import GraphState
from app.core.logging import setup_question_logger
# from .nodes import generate_code, plan_scenes, validate_code, execute_code
from app.job_store import job_store
from app.workflow.graph import workflow

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
            
            # Run the compiled workflow
            # since the workflow logic could be blocking, we run it in an executor
            loop = asyncio.get_event_loop()
            self.state = await loop.run_in_executor(None, workflow.invoke, self.state)

            if self.state.get("error"):
                raise Exception(self.state["error"])
            # # Plan generation
            # job_store.add_log(self.job_id, "Starting scene planning")
            # self.state = await self.run_step(plan_scenes)
            # if self.state.get("error"):
            #     raise Exception(self.state["error"])
            
            # # Code generation
            # job_store.add_log(self.job_id, "Starting code generation")
            # self.state = await self.run_step(generate_code)
            # if self.state.get("error"):
            #     raise Exception(self.state["error"])
            
            # # Code validation
            # job_store.add_log(self.job_id, "Validating generated code")
            # self.state = await self.run_step(validate_code)
            # if self.state.get("error"):
            #     raise Exception(self.state["error"])
            
            # # Code execution
            # job_store.add_log(self.job_id, "Executing code")
            # self.state = await self.run_step(execute_code)
            # if self.state.get("error"):
            #     raise Exception(self.state["error"])
            
            # Update job with success
            job_store.update_job(
                self.job_id,
                status="completed",
                result_url=self.state.get("execution_result", {}).get("video_url")
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

    async def run_step(self, step_func):
        """Run a workflow step in a thread to avoid blocking."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, step_func, self.state) 