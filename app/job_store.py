from typing import Dict, Optional, List
from threading import Lock
import uuid
from datetime import datetime
from app.models.job import Job, JobStatus  # Import from models instead of redefining

class JobStore:
    """Thread-safe in-memory job store."""
    def __init__(self):
        self._jobs: Dict[str, Job] = {}
        self._lock = Lock()
    
    def create_job(self, question: str) -> Job:
        """Create a new job."""
        job_id = str(uuid.uuid4())
        job = Job(
            job_id=job_id,
            question=question,
            status=JobStatus.QUEUED,  # Use enum here
            created_at=datetime.utcnow(),
            logs=[]
        )
        with self._lock:
            self._jobs[job_id] = job
        return job
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID."""
        return self._jobs.get(job_id)
    
    def update_job(self, job_id: str, status: str = None, result_url: str = None, error: str = None) -> None:
        """Update job status."""
        with self._lock:
            if job := self._jobs.get(job_id):
                if status:
                    job.status = JobStatus[status.upper()]  # Convert string to enum
                if result_url:
                    job.result_url = result_url
                if error:
                    job.error = error
                job.updated_at = datetime.utcnow()
    
    def add_log(self, job_id: str, message: str) -> None:
        """Add a log message to the job."""
        with self._lock:
            if job := self._jobs.get(job_id):
                job.logs.append(message)

# Global job store instance and lock
job_store = JobStore()
job_store_lock = job_store._lock  # Expose the lock for testing purposes 