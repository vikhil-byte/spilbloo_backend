#!/bin/bash
# entrypoint.sh

# Wait for the database to be ready
echo "Waiting for postgres..."

while ! nc -z $DB_HOST $DB_PORT; do
  sleep 0.1
done

echo "PostgreSQL started"

# Apply database migrations
if [ "$RUN_MIGRATIONS" = "true" ]; then
  echo "Applying database migrations..."
  python manage.py migrate --noinput

  echo "Seeding database..."
  python manage.py seed_data
else
  echo "Skipping migrations (RUN_MIGRATIONS != true)"
fi

# Start server
echo "Starting server"
exec "$@"
