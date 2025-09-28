# LUCA Flask Application Dockerfile
# Builds a container image for the LUCA educational AI system
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    python3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire application
COPY . .

# Note: Running as root in Docker container for SSL support
# In production, consider using a reverse proxy like nginx for SSL termination

# Set environment variables for Flask
ENV FLASK_ENV=production
ENV FLASK_SECRET_KEY=production-secret-key-change-me
ENV PYTHONPATH=/app

# Health check (supports both HTTP and HTTPS)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f -k https://localhost:443/ || curl -f http://localhost:5000/ || exit 1

# Expose ports for both HTTP and HTTPS
EXPOSE 5000 443

# Set the working directory to frontend for proper imports
WORKDIR /app/frontend

# Command to run the application
CMD ["python", "docker_run.py"]