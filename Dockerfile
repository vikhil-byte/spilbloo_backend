# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install system dependencies (netcat is used in entrypoint.sh to wait for DB)
RUN apt-get update && apt-get install -y netcat-openbsd

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy project
COPY . /app/

# Make the entrypoint script executable
RUN chmod +x /app/entrypoint.sh

# Collect static files during build
RUN python manage.py collectstatic --noinput

# Run the entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"]

# Command to run on start
CMD ["gunicorn", "--config", "gunicorn_config.py", "spilbloo_backend.wsgi:application"]
