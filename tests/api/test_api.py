import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import uuid
from datetime import datetime
from app.models.job import Job, JobStatus
from app.job_store import job_store, job_store_lock
from fastapi.testclient import TestClient
from app.main import app

@pytest.mark.api
class TestAPI:
    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.mark.asyncio
    async def test_generate_and_status(self, client):
        """Test job generation and status endpoints."""
        # Test job creation
        response = client.post("/api/generate", json={
            "question": "What is the GCF of 18 and 24?"
        })
        assert response.status_code == 202  # Async endpoint returns 202 Accepted
        data = response.json()
        assert "job_id" in data
        job_id = data["job_id"]

        # Test initial job status - should be queued
        response = client.get(f"/api/status/{job_id}")
        assert response.status_code == 200
        status_data = response.json()
        assert status_data["status"] == "queued"  # Use string value, not enum

        # Mock job completion instead of waiting for actual processing
        with job_store_lock:
            job_store.update_job(
                job_id,
                status=JobStatus.COMPLETED,
                result_url="test.mp4"
            )

        # Test completed job status
        response = client.get(f"/api/status/{job_id}")
        assert response.status_code == 200
        status_data = response.json()
        assert status_data["status"] == "completed"  # Use string value, not enum
        assert status_data["result_url"] == "test.mp4"

    @pytest.mark.asyncio
    async def test_error_handling(self, client):
        """Test API error handling."""
        # Test invalid job ID
        response = client.get("/api/status/invalid-id")
        assert response.status_code == 404
        
        # Test invalid request body
        response = client.post("/api/generate", json={})
        assert response.status_code == 422

    @pytest.mark.api
    def test_health_check(self, client):
        """Test the health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"} 