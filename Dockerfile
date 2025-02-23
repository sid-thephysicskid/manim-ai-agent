# Use Manim image as base
FROM manimcommunity/manim:latest

USER root

# Install required packages
RUN apt-get update && apt-get install -y sox

# Set the working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary directories with proper permissions
RUN mkdir -p /app/media/videos /app/generated/logs && \
    chmod -R 777 /app/media /app/generated

# Copy application code
COPY ./app /app/app/
COPY ./workflow_beta.py /app/

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