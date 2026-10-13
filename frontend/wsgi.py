"""WSGI entry point for gunicorn (production). Loads Docker secrets before the app reads its config."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.secrets import load_docker_secrets  # noqa: E402

load_docker_secrets()

from flask_app import app  # noqa: E402,F401
