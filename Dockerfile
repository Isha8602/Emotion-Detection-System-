# Use Python 3.9 slim image
FROM python:3.9-slim

# Install system dependencies for audio processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libsndfile1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose the port
EXPOSE 5000

# Use Gunicorn with eventlet worker (recommended for production)
# If you prefer to run with python directly, replace with:
# CMD ["python", "app.py"]
CMD ["python", "app.py"]