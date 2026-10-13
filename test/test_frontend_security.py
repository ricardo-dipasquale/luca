"""Security behaviour of the Flask app, with the tutor and the practice data faked (no Chroma, no OpenAI)."""

import importlib
import json
import sys
from pathlib import Path

import pytest

import agent.executor
import course.practices
from storage import db
from tools.secrets import load_docker_secrets

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"


class FakeExecutor:
    async def stream(self, message, session_id, exercise_id=None, user_id=None, subject=None):
        if message == "explotá":
            raise RuntimeError("detalle interno /app/secret/path sk-proj-SECRETO")
        yield {"is_task_complete": True, "content": "respuesta", "structured_response": {"modo": "teoria", "fuentes": []}}


class FakePractices:
    def get_subjects(self):
        return [{"name": "Bases de Datos Relacionales"}]

    def tree(self):
        return []


def _load_app(monkeypatch, tmp_path, **env):
    monkeypatch.setenv("LUCA_DB_PATH", str(tmp_path / "luca.db"))
    for key in ("FLASK_ENV", "FLASK_SECRET_KEY", "LUCA_COOKIE_SECURE", "LUCA_BEHIND_PROXY"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(agent.executor, "TutorExecutor", FakeExecutor)
    monkeypatch.setattr(course.practices, "get_practice_repository", lambda: FakePractices())
    monkeypatch.syspath_prepend(str(FRONTEND))
    monkeypatch.setattr("auth.generate_conversation_title", lambda m, s: "título", raising=False)
    for name in ("flask_app", "utils", "auth"):
        sys.modules.pop(name, None)
    module = importlib.import_module("flask_app")
    monkeypatch.setattr(module, "generate_conversation_title", lambda m, s: "título")
    return module


@pytest.fixture
def app_module(monkeypatch, tmp_path):
    module = _load_app(monkeypatch, tmp_path)
    db.upsert_user("ana@uca.edu.ar", "clave-correcta", "Ana")
    db.upsert_user("beto@uca.edu.ar", "otra-clave", "Beto")
    return module


def _login(client, email="ana@uca.edu.ar", password="clave-correcta"):
    return client.post("/login", json={"email": email, "password": password})


def test_production_refuses_placeholder_secret_key(monkeypatch, tmp_path):
    with pytest.raises(RuntimeError, match="FLASK_SECRET_KEY"):
        _load_app(monkeypatch, tmp_path, FLASK_ENV="production", FLASK_SECRET_KEY="production-secret-key-change-me")


def test_production_cookies_are_secure_and_hsts_is_sent(monkeypatch, tmp_path):
    module = _load_app(monkeypatch, tmp_path, FLASK_ENV="production", FLASK_SECRET_KEY="x" * 64)
    db.upsert_user("ana@uca.edu.ar", "clave-correcta")
    client = module.app.test_client()
    response = _login(client)
    cookie = response.headers["Set-Cookie"]
    assert "Secure" in cookie and "HttpOnly" in cookie and "SameSite=Lax" in cookie
    assert response.headers["Strict-Transport-Security"].startswith("max-age=")


def test_security_headers_and_no_cors(app_module):
    response = app_module.app.test_client().get("/healthz", headers={"Origin": "https://evil.example"})
    assert response.status_code == 200 and response.json == {"status": "ok"}
    csp = response.headers["Content-Security-Policy"]
    assert "frame-ancestors 'none'" in csp and "object-src 'none'" in csp
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "Access-Control-Allow-Origin" not in response.headers


def test_endpoints_require_login(app_module):
    client = app_module.app.test_client()
    assert client.post("/chat", json={"message": "hola"}).status_code == 401
    assert client.delete("/conversations/x", json={}).status_code == 401
    for path in ("/practicas", "/conversations", "/subjects", "/conversations/x/messages"):
        response = client.get(path)
        assert b"loginForm" in response.data and response.content_type.startswith("text/html"), path


def test_login_is_throttled_after_repeated_failures(app_module):
    client = app_module.app.test_client()
    for _ in range(5):
        assert _login(client, password="mala").status_code == 401
    response = _login(client)  # even the right password is refused while throttled
    assert response.status_code == 429 and "Demasiados intentos" in response.json["error"]
    assert _login(client, "beto@uca.edu.ar", "otra-clave").status_code == 200  # other accounts unaffected


def test_cannot_use_someone_elses_conversation(app_module):
    beto = app_module.app.test_client()
    _login(beto, "beto@uca.edu.ar", "otra-clave")
    conv = beto.post("/chat", json={"message": "hola"}).json["conversation_id"]

    ana = app_module.app.test_client()
    _login(ana)
    assert ana.post("/chat", json={"message": "leo tu memoria", "conversation_id": conv}).status_code == 403
    assert ana.get(f"/conversations/{conv}/messages").status_code == 403
    assert ana.delete(f"/conversations/{conv}").status_code == 400
    assert db.conversation_owner(conv) == "beto@uca.edu.ar"


def test_long_messages_are_rejected(app_module):
    client = app_module.app.test_client()
    _login(client)
    response = client.post("/chat", json={"message": "x" * (app_module.MAX_MESSAGE_CHARS + 1)})
    assert response.status_code == 400


def test_internal_errors_do_not_leak_details(app_module):
    client = app_module.app.test_client()
    _login(client)
    response = client.post("/chat", json={"message": "explotá"})
    assert response.status_code == 500
    body = json.dumps(response.json)
    assert "sk-proj" not in body and "/app/secret" not in body


def test_docker_secrets_are_loaded_without_overriding(tmp_path, monkeypatch):
    (tmp_path / "openai_api_key").write_text("sk-desde-secreto\n")
    (tmp_path / "flask_secret_key").write_text("desde-secreto")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("FLASK_SECRET_KEY", "ya-definida")
    assert load_docker_secrets(tmp_path) == ["OPENAI_API_KEY"]
    import os
    assert os.environ["OPENAI_API_KEY"] == "sk-desde-secreto" and os.environ["FLASK_SECRET_KEY"] == "ya-definida"
