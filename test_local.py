import requests
import time

BASE_URL = "http://localhost:8000"

def test_generate_job():
    # Check health endpoint first
    health_response = requests.get(f"{BASE_URL}/health")
    print("Health check response:", health_response.json())

    # Define a sample request payload
    payload = {
        "question": "explain the process of photosynthesis in a simple way",
        "rendering_quality": "medium",
        "duration_detail": "normal",
        "user_level": "college",
        "voice_model": "nova",
        "email": None
    }

    # Send POST request to generate endpoint
    print("Submitting job...")
    generate_response = requests.post(f"{BASE_URL}/api/generate", json=payload)
    job_info = generate_response.json()
    print("Job response:", job_info)

    job_id = job_info.get("job_id")
    if not job_id:
        print("No job_id received. Check the API logs for errors.")
        return

    # Now poll the job status until it's completed or failed
    status_url = f"{BASE_URL}/api/status/{job_id}"
    while True:
        status_response = requests.get(status_url)
        status = status_response.json()
        print("Job status:", status)
        if status.get("status") in ["completed", "failed"]:
            break
        time.sleep(2)  # wait for 2 seconds between polls

    print("Final job status:", status)

if __name__ == "__main__":
    test_generate_job()