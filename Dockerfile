# syntax=docker/dockerfile:1
# LUCA: imagen de la app (tutor + frontend). También ejecuta la ingesta con `python -m ingest`.

FROM python:3.12-slim-bookworm AS builder
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
COPY requirements.txt .
RUN /opt/venv/bin/pip install -r requirements.txt


FROM python:3.12-slim-bookworm
ENV PATH=/opt/venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/tmp \
    ANONYMIZED_TELEMETRY=False \
    FLASK_ENV=production

RUN groupadd --system --gid 10001 luca \
    && useradd --system --uid 10001 --gid luca --no-create-home --shell /usr/sbin/nologin luca

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
# Only the code the app and the ingestion need; secrets, content and tests never enter the image.
COPY agent ./agent
COPY course ./course
COPY ingest ./ingest
COPY storage ./storage
COPY guardrails ./guardrails
COPY tools ./tools
COPY frontend ./frontend
COPY scripts/import_usuarios.py scripts/export_conversaciones.py ./scripts/

# Volume mount points: named volumes inherit this ownership on first use.
RUN mkdir -p /app/data /app/artifacts && chown luca:luca /app/data /app/artifacts

USER luca
EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD ["python", "-c", "import urllib.request, sys; sys.exit(urllib.request.urlopen('http://127.0.0.1:5000/healthz', timeout=4).status != 200)"]

# One worker: the login throttle and the guardrails' rate limits live in memory and SQLite has a single writer.
CMD ["gunicorn", "--chdir", "/app/frontend", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "8", \
     "--timeout", "180", "--access-logfile", "-", "wsgi:app"]
