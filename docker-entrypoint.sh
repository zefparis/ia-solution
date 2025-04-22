#!/bin/bash
set -e

# Print environment variables for debugging (excluding sensitive information)
echo "Environment: $APP_ENV"
echo "Starting IA-Solution API on port $APP_PORT"

# Wait for dependent services if using wait-for-it script
if [ "$DATABASE_URL" != "" ]; then
    # Extract host and port from DATABASE_URL
    DB_HOST=$(echo $DATABASE_URL | sed -n 's/.*@\(.*\):.*/\1/p')
    DB_PORT=$(echo $DATABASE_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
    
    if [ "$DB_HOST" != "" ] && [ "$DB_PORT" != "" ]; then
        echo "Waiting for PostgreSQL database at $DB_HOST:$DB_PORT..."
        ./wait-for-it.sh "$DB_HOST:$DB_PORT" -t 60
        echo "PostgreSQL is up!"
    fi
fi

if [ "$REDIS_HOST" != "" ] && [ "$REDIS_PORT" != "" ]; then
    echo "Waiting for Redis at $REDIS_HOST:$REDIS_PORT..."
    ./wait-for-it.sh "$REDIS_HOST:$REDIS_PORT" -t 30
    echo "Redis is up!"
fi

if [ "$ELASTICSEARCH_HOSTS" != "" ]; then
    # Extract host and port from ELASTICSEARCH_HOSTS
    ES_HOST=$(echo $ELASTICSEARCH_HOSTS | sed 's|http://||' | sed 's|https://||' | cut -d: -f1)
    ES_PORT=$(echo $ELASTICSEARCH_HOSTS | sed 's|http://||' | sed 's|https://||' | cut -d: -f2)
    
    if [ "$ES_HOST" != "" ] && [ "$ES_PORT" != "" ]; then
        echo "Waiting for Elasticsearch at $ES_HOST:$ES_PORT..."
        ./wait-for-it.sh "$ES_HOST:$ES_PORT" -t 60
        echo "Elasticsearch is up!"
    fi
fi

if [ "$RABBITMQ_HOST" != "" ] && [ "$RABBITMQ_PORT" != "" ]; then
    echo "Waiting for RabbitMQ at $RABBITMQ_HOST:$RABBITMQ_PORT..."
    ./wait-for-it.sh "$RABBITMQ_HOST:$RABBITMQ_PORT" -t 60
    echo "RabbitMQ is up!"
fi

# Run database migrations if needed
if [ "$APP_ENV" != "development" ]; then
    echo "Running database migrations..."
    python -c "from main import app; from models import db; app.app_context().push(); db.create_all()"
    echo "Database migrations complete."
fi

# Pass command line arguments to the entrypoint
exec "$@"