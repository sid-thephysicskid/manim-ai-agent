# Product Requirements Document (PRD)

## 1. Overview

**Project Name:** Manim Video Rendering Workflow with Voiceover  
**Version:** Alpha (Initial Release)  
**Date:** *[Insert Date]*  
**Author:** *[Your Name]*

### 1.1. Purpose

This project refines and deploys an educational video generation workflow based on Manim. The original code (`workflow_beta.py`) implements a multi-stage process that:

- Generates an educational lesson plan.
- Produces Manim code integrated with voiceover instructions.
- Validates and executes the code.
- Renders a video (with voiceovers and scene transitions).

The goal of this phase is to refactor the existing workflow into a FastAPI-based backend that supports:
  
- **Job Submission:** Clients submit a “question” along with metadata such as rendering quality, desired detail/duration, user knowledge level, and a preferred voice model (with the option to supply an email address for notifications).  
- **Progress Reporting:** Clients receive real-time (via polling for alpha) progress updates until the video is rendered.
- **Persistence:** The frontend will store finished jobs locally so that users can return later and see the final video output.
- **Deployment:** The backend will be containerized and deployed on Railway (using their hobby plan, upgradeable later if needed) while the frontend is deployed on Vercel.

---

## 2. Objectives

1. **Refactor Business Logic:**  
   - Separate dedicated workflow logic from API routing.
   - Expose the workflow as a callable function (or sequence of functions) so it can be orchestrated by the FastAPI endpoints.

2. **API Design:**  
   - Create a POST endpoint (`/api/generate`) to submit a job with the following metadata:
     - `question` (string)
     - `rendering_quality` (default: `"medium"`)
     - `duration_detail` (descriptor, default: `"normal"`)
     - `user_level` (e.g., `"child"`, `"high_school"`, `"college"`)
     - `voice_model` (selection among three choices, default: `"nova"`)
     - `email` (optional email string for job notifications)
   - Create a GET polling endpoint (`/api/status/{job_id}`) to report:
     - Job status (`queued`, `processing`, `completed`, or `failed`)
     - A log summary of key processing steps (plan generation, code generation, validation, rendering)
     - The final output reference (e.g., a URL/path to the rendered video)

3. **Background Processing & Job Queue:**  
   - Leverage FastAPI’s `BackgroundTasks` to process long-running jobs.
   - Use an in-memory job store (for alpha) to keep track of job IDs, statuses, and logs.

4. **Email Notification:**  
   - Integrate with SendGrid to send success/failure notifications.
   - Use environment-configured variables (`SENDGRID_API_KEY` and `FROM_EMAIL`) for authentication.

5. **Deployment:**  
   - Containerize the entire application using Docker.
   - Use a Manim-compatible Docker base image (which includes system-level dependencies such as ffmpeg, TeX, etc.).
   - Deploy the FastAPI container on Railway.
   - Ensure CORS is properly configured so that the Vite-based frontend (deployed on Vercel) only interacts with the approved backend.

6. **Testing:**  
   - Implement exhaustive unit tests, integration tests, and end‑to‑end tests.
   - Include tests for each processing stage (plan generation, code generation, validation, execution, error correction).
   - Validate that logging, state transitions, and error notifications operate as expected.

---

## 3. Functional Requirements

### 3.1. Frontend Integration

- **User Submission:**  
  - A simple input form that collects:
    - The question or lesson topic.
    - Dropdowns or selectors for rendering quality, user level, preferred voice model.
    - An optional email address.
  - On submission, display a message noting that video rendering may take a few minutes.
  - Once the job is submitted, persist the job information in local storage so that if the user refreshes or returns later, they see the status or final output.

- **Job Progress:**  
  - The frontend requests `/api/status/{job_id}` periodically until the status is set to `completed` or `failed`.
  - Display a log/progress summary to build user trust, e.g., “Plan generated”, “Code generated”, “Rendering in progress”, etc.
  
### 3.2. API Endpoints

- **POST `/api/generate`:**  
  - Accepts a JSON payload containing:
    ```json
    {
      "question": "How to plot a function?",
      "rendering_quality": "medium",
      "duration_detail": "normal",
      "user_level": "college",
      "voice_model": "nova",
      "email": "user@example.com"
    }
    ```
  - Immediately responds with a JSON payload containing a unique job ID:
    ```json
    {
      "job_id": "some-unique-uuid",
      "status": "queued"
    }
    ```

- **GET `/api/status/{job_id}`:**
  - Returns the current state of the job:
    ```json
    {
      "status": "processing",
      "logs": [
          "Plan Generation: started",
          "Plan Generation: completed",
          "Code Generation: started",
          ...
      ],
      "result": "/videos/rendered_some-unique-uuid.mp4" // if completed
    }
    ```

### 3.3. Workflow & Business Logic Integration

- **Workflow Reuse:**  
  - Incorporate the logic from `workflow_beta.py` by refactoring its functions into a library or module that the API can call (e.g., a function like `process_single_question()`).
  - Preserve state transitions, logging, and error correction strategies as implemented in the original workflow.
  
- **Error Handling:**  
  - In the event of rendering failures or code generation issues, the system should update the job state to `failed` and return a short user-friendly error message.
  - If provided, trigger an email notification alerting the user to the failure.

- **Metadata-Driven Adjustments:**  
  - Use the metadata (especially the `voice_model`) to adjust generation prompts for the OpenAI-based code generation step.
  - Modify the output code if required (e.g., updating the voice setting in the generated code) based on the user’s selected voice model.

---

## 4. Non-Functional Requirements

### 4.1. Performance & Scalability

- **Processing Time:**  
  - Although video rendering is compute-intensive, for the alpha release the system will process tasks sequentially per job.  
  - Prepare for future migration to a more robust queue (e.g., Celery with Redis) if synchronous processing shows bottlenecks.
  
- **Resource Constraints:**  
  - The Railway Hobby plan (8 GB RAM / 8 vCPU) is the current target. Upgrade to Pro if tests show significant CPU or memory limitations.

### 4.2. Security & Availability

- **CORS & API Gatekeeping:**  
  - Use CORS to restrict API access to approved origins (i.e., the frontend hosted on Vercel).
  - Since there is no user login, minimal authentication is acceptable for the alpha.
  
- **Logging & Observability:**  
  - Maintain detailed logs (both on-screen and file-based) for every job progress stage.
  - Save logs for future analysis to improve both error recovery and user notifications.

### 4.3. Maintainability

- **Modular Code Structure:**  
  - Separate API routes, background processing logic, and business logic into distinct modules.
  - Ensure the code is organized to support easier refactoring, especially for later migration to asynchronous job queues or WebSocket-based progress updates.

---

## 5. Technical Architecture

### 5.1. Backend

- **Framework:** FastAPI (Python 3.10.15)  
- **Libraries:**
  - Manim, manim-voiceover[all]
  - langgraph, openai, anthropic
  - pydantic, pydantic-settings for data models
  - sendgrid (for email notifications)
  - fastapi, httpx for API and asynchronous requests
  - Standard libraries for logging, subprocess execution, threading, etc.
  
- **Processing:**  
  - Use FastAPI’s `BackgroundTasks` to offload long-running video rendering tasks.
  - Maintain an in-memory job store (dictionary mapping job IDs to status dictionaries) for the alpha release.
  
- **Workflow Integration:**  
  - Refactor `workflow_beta.py` into a set of callable functions for plan generation, code generation, validation, execution, error correction, and logging.

### 5.2. Frontend

- **Framework:** Vite-powered JavaScript SPA  
- **Deployment:** Hosted on Vercel  
- **Integration:**  
  - The frontend sends user requests to the backend’s `/api/generate` endpoint.
  - It polls `/api/status/{job_id}` for progress updates.
  - Uses localStorage to persist job results so the user sees the completed video even if they close and later reopen the browser.

### 5.3. Deployment

- **Containerization:**  
  - Write a Dockerfile that:
    - Uses a Manim-compatible base image (with ffmpeg, TeX, etc. installed).
    - Installs necessary Python packages (from `requirements.txt`).
    - Copies the code and exposes port 8000.
    - Runs the FastAPI application with Uvicorn.
  
- **Railway Deployment:**  
  - Deploy the Docker container on Railway.  
  - Configure environment variables: `SENDGRID_API_KEY`, `FROM_EMAIL`, and any additional secrets.
  
- **Vercel Configuration:**  
  - Set up CORS on the backend so the Vite frontend can call the API.
  - Ensure the frontend uses the proper production URL for the backend.

---

## 6. Implementation Roadmap

### Phase 1: Refactoring & API Integration

1. **Separate Business Logic:**
   - Refactor `workflow_beta.py` to extract the core workflow functions (plan generation, code generation, validation, execution, error correction) into a dedicated module (e.g., `/app/workflow.py`).

2. **API Endpoints:**
   - Create a FastAPI application (`/app/main.py`) that exposes:
     - POST `/api/generate` – accepts job metadata, initiates processing via background tasks.
     - GET `/api/status/{job_id}` – returns job status, logs, and result (if available).

3. **In-Memory Job Store & Background Tasks:**
   - Implement an in-memory dictionary for job storage.
   - Use FastAPI’s `BackgroundTasks` to process each job asynchronously.

4. **Integrate Email Notification:**
   - Build a module (e.g., `/app/email_service.py`) to send emails using SendGrid.
   - Trigger email notifications on job success or failure.

### Phase 2: Dockerization & Deployment

1. **Create a Dockerfile:**
   - Base from a Manim-compatible image.
   - Add system-level dependencies (ffmpeg, TeX, etc.).
   - Install Python requirements.
   - Copy source code and run Uvicorn.

2. **Deploy on Railway:**
   - Use Railway’s container deployment with proper resource allocation (start with Hobby plan, upgrade as needed).
   - Set environment variables and test connectivity.

3. **Configure CORS:**
   - Ensure the backend’s FastAPI instance allows requests from the Vercel frontend domain.

### Phase 3: Testing & Quality Assurance

1. **Unit Testing:**
   - Write tests for each refactored function (especially for state transitions and error logging).
   - Use `pytest` and `pytest-asyncio` for asynchronous route tests.

2. **Integration Testing:**
   - Mock external API calls (to OpenAI, SendGrid, etc.) for isolated tests.
   - Test API endpoint responses and background task execution.

3. **End-to-End Testing:**
   - Simulate complete job submission from the frontend through to video rendering.
   - Validate that job status polling and email notifications work as expected.

4. **Exhaustive Testing:**
   - Run tests using commands (e.g., `python workflow_beta.py --test`).
   - Use logging and state dumps to ensure each workflow node transitions correctly.
  
5. **Documentation & Logging:**
   - Update inline documentation and logs for every major function.
   - Provide a summary log for each job (both on server and for client consumption).

---

## 7. Future Considerations

- **Real-Time Progress with WebSockets:**  
  Migrate from polling to WebSockets for finer real-time progress updates.

- **Robust Queueing:**  
  Integrate a durable message queue like Celery/Redis once alpha proves successful.

- **Enhanced Security:**  
  Potentially add simple API key validation or header checks to limit API usage.

- **Scaling & Monitoring:**  
  Introduce application monitoring, better error aggregation, and logging aggregation solutions.

---

## 8. Appendices

### 8.1. Environment & Dependencies

- **Python Version:** 3.10.15  
- **Key Packages:**  
  - manim  
  - langgraph  
  - openai, anthropic  
  - manim-voiceover[all]  
  - pydantic, pydantic-settings  
  - fastapi, httpx  
  - sendgrid  
  - pytest, pytest-asyncio  

- **System Dependencies:** ffmpeg, TeX distribution, and other system libraries for Manim.

### 8.2. Example Dockerfile
```
# Use an official Manim image which includes system-level dependencies    
FROM manimcommunity/manim:latest
WORKDIR /app
# Copy requirements and install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
# Copy the entire codebase
COPY . /app/
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 9. Conclusion

This PRD defines the scope, features, and technical roadmap for refactoring the legacy `workflow_beta.py` into a robust, API-driven application. Following this document, you (or an automated system/LLM) can guide you step by step—from modularizing and refactoring the workflow, creating API endpoints and background tasks, to Dockerizing and deploying on Railway with a Vite/Vercel frontend integration.

Use this PRD alongside your existing code to ensure every aspect is covered for a successful alpha release with exhaustive testing and monitoring capabilities.