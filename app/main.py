from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from app.workflow.runner import WorkflowRunner
from app.models.state import GraphState
from app.job_store import job_store, Job
from app.models.job import JobStatus

app = FastAPI()

class GenerateRequest(BaseModel):
    """Request model for video generation."""
    question: str
    rendering_quality: str = "medium"
    duration_detail: str = "normal"
    user_level: str = "college"
    voice_model: str = "nova"
    email: str | None = None

def clear_job_store():
    """Clear the in-memory job store."""
    # TODO: Implement proper job store cleanup
    pass

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

@app.get("/api/status/{job_id}")
async def get_status(job_id: str):
    """Get job status."""
    if job := job_store.get_job(job_id):
        return {
            "status": job.status.value,  # Convert enum to string
            "result_url": job.result_url,
            "error": job.error
        }
    raise HTTPException(status_code=404, detail="Job not found")

@app.post("/api/generate", status_code=202)
async def generate_video(request: GenerateRequest, background_tasks: BackgroundTasks):
    """Generate a video for a math question."""
    job = job_store.create_job(request.question)
    
    # Create initial workflow state
    initial_state = GraphState(
        user_input=request.question,
        plan=None,
        generated_code=None,
        execution_result=None,
        error=None,
        current_stage="plan",
        correction_attempts=0
    )
    
    # Create and run workflow
    workflow = WorkflowRunner(initial_state, job.job_id)
    background_tasks.add_task(workflow.run)
    
    return {"job_id": job.job_id}