from fastapi import FastAPI, BackgroundTasks, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
import uuid
import time
from app.schemas import JobSubmission
from app.job_store import add_job, get_job, update_job
from app.workflow import run_full_workflow

app = FastAPI(
    title="Manim Video Rendering Workflow API",
    debug=(settings.ENVIRONMENT == "development")
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    """
    Simple health-check endpoint to confirm the API is running.
    """
    return {"status": "ok"}

def process_job(job_id: str, submission: JobSubmission) -> None:
    """
    Stub background task to simulate processing a job.
    In real life, this function would call the workflow to process the question.
    """
    # Update job status to processing
    update_job(job_id, status="processing", logs=["Started processing job."], message="Processing started.")
    # Call the workflow to process the submission using the refactored function.
    from app.workflow import run_full_workflow
    result = run_full_workflow(submission.question)
    # If available, extract the video file name from execution_result.
    video_file = result.get("execution_result", {}).get("scene_file", "Unknown")
    # Final update for completion with the obtained result.
    update_job(job_id, status="completed", logs=result["logs"], message="Job completed successfully.", result=video_file)
    
    # Send email notification if an email is provided
    if submission.email:
        from app.email_service import send_email_notification
        subject = "Your Manim Video Rendering is Complete"
        content = (
            f"Hello,\n\nYour job with ID {job_id} has been completed successfully.\n"
            f"Video file: {video_file}\n\nThank you."
        )
        send_email_notification(submission.email, subject, content)

@app.post("/api/generate", status_code=status.HTTP_202_ACCEPTED)
def generate_job(submission: JobSubmission, background_tasks: BackgroundTasks):
    """
    Enqueue a new job to process the provided question.
    """
    job_id = str(uuid.uuid4())
    from app.job_store import JobStatus  # import here to avoid circular dependency if any
    new_job = JobStatus(job_id=job_id)
    add_job(new_job)

    # Enqueue background task to process the job
    background_tasks.add_task(process_job, job_id, submission)

    return {"job_id": job_id, "status": new_job.status}

@app.get("/api/status/{job_id}")
def get_job_status(job_id: str):
    """
    Retrieve the current status of a job.
    """
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job.model_dump()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True) 