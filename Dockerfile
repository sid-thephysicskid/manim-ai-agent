# Use Manim image as base
FROM manimcommunity/manim:latest

USER root
RUN apt-get update && apt-get install -y sox

# Set the working directory inside the container
WORKDIR /app

# Copy requirements from root directory
COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ./app /app/app/
COPY ./workflow_beta.py /app/

# Create necessary directories for media output and logs
RUN mkdir -p /app/media/videos /app/generated/logs && \
    chmod -R 777 /app/media /app/generated

# Set environment variables
ENV PYTHONPATH=/app
ENV MANIM_QUALITY="-ql"
ENV OPENAI_API_KEY=""
ENV SENDGRID_API_KEY=""
ENV FROM_EMAIL=""

# Expose port for FastAPI
EXPOSE 8000

# Run FastAPI with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 