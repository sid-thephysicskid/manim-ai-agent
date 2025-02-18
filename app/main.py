import logging
from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.workflow.runner import WorkflowRunner
from app.models.state import GraphState
from app.job_store import job_store, Job
from app.models.job import JobStatus
import traceback
from fastapi.staticfiles import StaticFiles
import os

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Log to console
        logging.FileHandler('app.log')  # Log to file
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development, restrict this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add error handling middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        logger.error(f"Request failed: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": str(e), "traceback": str(traceback.format_exc())}
        )

# Add exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception handler caught: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": str(exc),
            "traceback": str(traceback.format_exc())
        }
    )

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
async def get_job_status(job_id: str):
    try:
        job = job_store.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        return {
            "job_id": job_id,
            "status": job.status.value,
            "logs": job.logs,
            "message": "Job completed successfully." if job.status == JobStatus.COMPLETED else "Job in progress.",
            "result": job.result_url if job.status == JobStatus.COMPLETED else None,
            "error": job.error if job.error else None
        }
    except Exception as e:
        logger.error(f"Error getting job status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail={"error": str(e), "traceback": traceback.format_exc()}
        )

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