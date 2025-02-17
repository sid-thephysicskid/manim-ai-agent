from typing import Dict, Optional
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
        """Create a new job and return its ID."""
        job_id = str(uuid.uuid4())
        job = Job(
            job_id=job_id,
            question=question
        )  # All other fields will use defaults
        with self._lock:
            self._jobs[job_id] = job
        return job
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID."""
        return self._jobs.get(job_id)
    
    def update_job(self, job_id: str, **kwargs) -> Optional[Job]:
        """Update job fields."""
        with self._lock:
            if job := self._jobs.get(job_id):
                # Update only valid fields
                for key, value in kwargs.items():
                    if hasattr(job, key):
                        setattr(job, key, value)
                job.updated_at = datetime.utcnow()
                return job
            return None
    
    def add_log(self, job_id: str, message: str) -> None:
        """Add a log message to the job."""
        with self._lock:
            if job := self._jobs.get(job_id):
                job.logs.append(f"[{datetime.utcnow().isoformat()}] {message}")
                job.updated_at = datetime.utcnow()

# Global job store instance and lock
job_store = JobStore()
job_store_lock = job_store._lock  # Expose the lock for testing purposes 