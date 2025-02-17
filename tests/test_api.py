import time
from fastapi.testclient import TestClient
from app.main import app
from app.job_store import job_store, job_store_lock

client = TestClient(app)

def clear_job_store():
    """Clear job_store for clean test runs."""
    with job_store_lock:
        job_store.clear()

def test_health_endpoint():
    clear_job_store()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_generate_and_status():
    clear_job_store()
    
    payload = {
        "question": "Test question?",
        "rendering_quality": "medium",
        "duration_detail": "normal",
        "user_level": "college",
        "voice_model": "nova",
        "email": None  # For testing, no email is provided.
    }
    
    # Submit a new job
    response = client.post("/api/generate", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    job_id = data["job_id"]
    
    # Fetch the initial status.
    status_response = client.get(f"/api/status/{job_id}")
    assert status_response.status_code == 200
    job_status = status_response.json()
    # Allow for queued, processing, or completed as valid initial statuses.
    assert job_status["status"] in {"queued", "processing", "completed"}
    
    # Poll until the job is completed (timeout after a reasonable wait)
    completed = False
    for _ in range(10):
        status_response = client.get(f"/api/status/{job_id}")
        assert status_response.status_code == 200
        job_status = status_response.json()
        if job_status["status"] == "completed":
            completed = True
            break
        time.sleep(1)
    
    assert completed, "Job did not complete in expected time."
    assert job_status["result"] is not None 