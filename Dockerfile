FROM python:3.11-slim

# Arguments for build configuration
ARG APP_ENV=production
ARG APP_PORT=5000
ARG APP_USER=appuser
ARG APP_GROUP=appgroup
ARG APP_HOME=/app

# Set environment variables
ENV PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PYTHONUNBUFFERED=1 \
    APP_ENV=${APP_ENV} \
    APP_PORT=${APP_PORT}

# Create application directory
WORKDIR ${APP_HOME}

# Create non-root user
RUN groupadd -r ${APP_GROUP} && \
    useradd -r -g ${APP_GROUP} -d ${APP_HOME} -s /sbin/nologin -c "Docker image user" ${APP_USER} && \
    chown -R ${APP_USER}:${APP_GROUP} ${APP_HOME}

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ca-certificates \
    libpq-dev \
    netcat-traditional \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application
COPY . .

# Generate requirements.txt for reproducible builds
RUN pip freeze > requirements-lock.txt

# Make scripts executable
RUN chmod +x ./docker-entrypoint.sh ./wait-for-it.sh

# Change to non-root user
USER ${APP_USER}:${APP_GROUP}

# Expose the application port
EXPOSE ${APP_PORT}

# Set the entrypoint
ENTRYPOINT ["./docker-entrypoint.sh"]

# Default command
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--reload", "main_microservices:app"]