#!/bin/sh
# Put the record on the volume before anything serves a read.
#
# The copy happens once. A redeploy finds the file already there and leaves it
# alone, so shipping new code never overwrites the database, and a volume that
# was created empty can never boot an API with nothing to read.
set -e

DB="${SIBYL_DB:-/data/memory.db}"

if [ ! -f "$DB" ]; then
  echo "seeding $DB from the image"
  mkdir -p "$(dirname "$DB")"
  cp /seed/memory.db "$DB"
fi

echo "serving $DB ($(wc -c < "$DB") bytes, read_only=${FIRSTHAND_READ_ONLY:-0})"

exec uvicorn apps.agent.api.main:app --host 0.0.0.0 --port "${PORT:-8080}"
