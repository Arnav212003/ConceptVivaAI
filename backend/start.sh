#!/bin/sh
# Render's free plan has no background workers or pre-deploy step,
# so one container runs the migrations, the judge worker and the API.
set -e

alembic upgrade head

# Restart the worker if it ever exits, without taking the API down.
(
  while true; do
    python -m judge.worker || echo "judge worker exited, restarting in 5s"
    sleep 5
  done
) &

exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers "${WEB_CONCURRENCY:-1}"
