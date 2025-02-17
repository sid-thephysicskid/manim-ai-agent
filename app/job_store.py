from pydantic import BaseModel
from typing import List, Optional, Literal, Dict
from threading import Lock

# Define valid job statuses
JobStatusLiteral = Literal["queued", "processing", "completed", "failed"]

class JobStatus(BaseModel):
    job_id: str
    status: JobStatusLiteral = "queued"
    logs: List[str] = []
    message: str = ""
    result: Optional[str] = None

# In-memory store for jobs and a threading lock for safe concurrent access
job_store: Dict[str, JobStatus] = {}
job_store_lock = Lock()

def add_job(job: JobStatus) -> None:
    """Add a new job to the store."""
    with job_store_lock:
        job_store[job.job_id] = job

def get_job(job_id: str) -> Optional[JobStatus]:
    """Retrieve a job by its job_id."""
    with job_store_lock:
        return job_store.get(job_id)

def update_job(job_id: str, **kwargs) -> None:
    """Update job fields based on provided keyword arguments."""
    with job_store_lock:
        if job_id in job_store:
            job_data = job_store[job_id].model_dump()
            for field in kwargs.keys():
                job_data[field] = kwargs[field]
            # Re-assign the updated model back to the store
            job_store[job_id] = JobStatus(**job_data) 