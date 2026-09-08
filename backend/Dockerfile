# Base Image: Python 3.12 slim for lightweight footprint
FROM python:3.12-slim

# Set environment variables for Python in Docker
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory inside container
WORKDIR /app

# Install system dependencies required for compilation / psycopg2 / cryptography
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt first to leverage Docker layer caching
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend application code
COPY . /app/

# Expose port 8000 for Django development server
EXPOSE 8000

# Default CMD for local development (Note: For production, use Gunicorn/Uvicorn behind Nginx)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
