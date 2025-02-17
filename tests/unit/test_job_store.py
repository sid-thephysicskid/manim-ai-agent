import pytest
from datetime import datetime
from app.job_store import JobStore
from app.models.job import Job, JobStatus

@pytest.mark.unit
class TestJobStore:
    @pytest.fixture
    def job_store(self):
        return JobStore()

    def test_create_job(self, job_store):
        """Test job creation."""
        job = job_store.create_job("What is the GCF of 18 and 24?")
        assert job.job_id is not None
        assert job.status == JobStatus.QUEUED
        assert job.question == "What is the GCF of 18 and 24?"
        assert job.current_stage == "plan"
        assert isinstance(job.created_at, datetime)
        assert isinstance(job.updated_at, datetime)
        assert job.logs == []
        assert job.result_url is None
        assert job.error is None

    def test_get_job(self, job_store):
        """Test job retrieval."""
        job = job_store.create_job("Test question")
        retrieved_job = job_store.get_job(job.job_id)
        assert retrieved_job == job

    def test_update_job(self, job_store):
        """Test job update."""
        job = job_store.create_job("Test question")
        job_store.update_job(
            job.job_id,
            status=JobStatus.COMPLETED,
            result_url="test.mp4"
        )
        updated_job = job_store.get_job(job.job_id)
        assert updated_job.status == JobStatus.COMPLETED
        assert updated_job.result_url == "test.mp4"

    def test_add_log(self, job_store):
        """Test log addition."""
        job = job_store.create_job("Test question")
        job_store.add_log(job.job_id, "Test log message")
        updated_job = job_store.get_job(job.job_id)
        assert len(updated_job.logs) == 1
        assert "Test log message" in updated_job.logs[0] 