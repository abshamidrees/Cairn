# The read API and the record it serves, on one machine with one volume.
#
# The indexed database ships inside the image and is copied onto the volume once,
# on first boot. Re-indexing in production would rebuild 364 observations against
# a 5,242,880 byte cap that the file already sits within 250 KB of, and a cap
# reached mid-demo is a 500 on every dossier read. The record is built once,
# locally, and shipped.

FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencies first, so a code change does not refetch web3 on every deploy.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY apps/ ./apps/

# The seed lives outside /data because /data is the volume mount point and is
# replaced at runtime by whatever the volume already holds.
COPY data/memory.db /seed/memory.db

COPY docker-entrypoint.sh /usr/local/bin/entrypoint
RUN chmod +x /usr/local/bin/entrypoint

EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/entrypoint"]
