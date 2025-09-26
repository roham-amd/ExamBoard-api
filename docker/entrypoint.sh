#!/usr/bin/env bash
set -euo pipefail

export PYTHONUNBUFFERED=1

python src/manage.py migrate --noinput
python src/manage.py collectstatic --noinput

if [ "$#" -gt 0 ]; then
  exec "$@"
else
  exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --chdir src
fi
