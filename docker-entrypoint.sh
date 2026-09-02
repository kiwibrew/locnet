#!/bin/sh
set -eu

python -m app.database_bootstrap
alembic upgrade head

exec "$@"
