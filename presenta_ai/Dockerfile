# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV APP_HOME /app

# Create and set the working directory
WORKDIR ${APP_HOME}

# Install system dependencies that might be needed by PyMuPDF (fitz)
# PyMuPDF needs libraries like libmupdf-dev, mupdf-tools, etc.
# However, for a slim image, we might try without them first, or use a base image that includes them.
# For now, let's assume pip wheels might handle some of this or add them if runtime errors occur.
# A common one needed if not using full wheels: apt-get install -y libgl1-mesa-glx
# For now, minimal dependencies:
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*
    # Placeholder for any system deps, e.g., libgomp1 for some ML libs, though likely not needed here yet
    # For PyMuPDF, if wheels are not sufficient, you might need:
    # build-essential libpoppler-cpp-dev pkg-config python3-dev
    # For now, keeping it minimal. If pip install of PyMuPDF fails, this needs adjustment.



# Install pip requirements
# Copy only requirements.txt first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the working directory
# If Dockerfile is in 'presenta_ai/' and context is 'presenta_ai/',
# then '.' refers to the 'presenta_ai' directory content.
COPY . .
# This will copy app.py, config/, adk_logic/, utils/ into /app/

# Expose the port Streamlit will run on (default is 8501)
# Cloud Run will set the PORT env variable, which Streamlit can use.
EXPOSE 8501

# Command to run the Streamlit application
# Use environment variable $PORT if set (typical for Cloud Run), otherwise default to 8501.
# Using an entrypoint script could make this more robust.
# For Cloud Run, Streamlit automatically picks up the PORT environment variable.
CMD ["streamlit", "run", "app.py", "--server.port", "8501", "--server.enableCORS", "false", "--server.headless", "true"]
