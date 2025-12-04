FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for video/image processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY docs/ ./docs/

# Set Python path
ENV PYTHONPATH=/app

# Cloud Run uses PORT environment variable
ENV PORT=8080

# Run the FastAPI app
CMD uvicorn src.main:app --host 0.0.0.0 --port $PORT

