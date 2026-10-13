"""Docker secrets → environment, so keys never live in the image or in the compose `environment:`.

`docker compose` mounts each secret as a file in /run/secrets/<name>. This loads the ones LUCA knows
(file name in lowercase, e.g. /run/secrets/openai_api_key → OPENAI_API_KEY) without overriding
variables that are already set.
"""

import os
from pathlib import Path

SECRETS_DIR = Path("/run/secrets")
KNOWN = ("OPENAI_API_KEY", "FLASK_SECRET_KEY")


def load_docker_secrets(directory: Path = SECRETS_DIR) -> list[str]:
    loaded = []
    for name in KNOWN:
        path = directory / name.lower()
        if name not in os.environ and path.is_file():
            os.environ[name] = path.read_text(encoding="utf-8").strip()
            loaded.append(name)
    return loaded
