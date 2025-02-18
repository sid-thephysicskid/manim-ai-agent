# Use an official Manim image which includes system-level dependencies
FROM manimcommunity/manim:latest

# Switch user to root to run apt-get and install SoX
USER root
RUN apt-get update && apt-get install -y sox

# Set the working directory inside the container
WORKDIR /app

# Copy requirements.txt and install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Create and set permissions for media and generated directories
RUN mkdir -p /app/media /app/generated && chmod -R 777 /app/media /app/generated

# Copy the entire codebase into the container
COPY . /app/

# Expose port 8000 for the FastAPI application
EXPOSE 8000

# Pre-download the voiceover model (ignore errors to keep building)
RUN python3 -m manim -ql --media_dir /tmp/media gcf.py GCFCalculationScene || true

# Run the FastAPI application using Uvicorn
CMD ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 