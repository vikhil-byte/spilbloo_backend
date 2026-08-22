#!/bin/bash
# entrypoint.sh

# Wait for the database to be ready
echo "Waiting for postgres..."

while ! nc -z $DB_HOST $DB_PORT; do
  sleep 0.1
done

echo "PostgreSQL started"

# Apply database migrations. Only the web process does this — web,
# celery_worker and celery_beat all share this image/entrypoint, and if more
# than one of them races to migrate at once, Postgres can throw
# "duplicate key value violates unique constraint pg_type_typname_nsp_index"
# when two containers CREATE TABLE for the same new model concurrently.
if [ "$RUN_MIGRATIONS" = "true" ] && [ "$1" = "gunicorn" ]; then
  echo "Applying database migrations..."
  python manage.py migrate --noinput

  echo "Seeding database..."
  python manage.py seed_data
else
  echo "Skipping migrations (RUN_MIGRATIONS != true, or not the web process)"
fi

# Start server
echo "Starting server"
exec "$@"
