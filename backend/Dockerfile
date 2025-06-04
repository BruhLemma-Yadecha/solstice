# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install system dependencies required by OpenCV and other common libraries
# It's good practice to install these before Python dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
# We copy only requirements.txt first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Add gunicorn if not in requirements.txt; it's a common production server for Django
# This line assumes gunicorn might not be in requirements.txt.
# If it is, this line might be redundant or could be used to ensure a specific version.
RUN pip install --no-cache-dir gunicorn

# Copy the rest of the application code
COPY . .

# Expose the port the app runs on
EXPOSE 8000

# Run the application
# Adjust 'solstice.wsgi:application' if your Django project name is different.
# The number of workers can be adjusted based on your server's resources.
# The WEB_APP_CONTAINER_PORT environment variable (defaulting to 8000) is used here,
# similar to how it's used in the docker-compose.yml command.
CMD exec gunicorn --workers 3 --bind "0.0.0.0:${WEB_APP_CONTAINER_PORT:-8000}" solstice.wsgi:application

RUN python manage.py migrate