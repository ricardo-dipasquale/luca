"""Security behaviour of the Flask app, with the tutor and the practice data faked (no Chroma, no OpenAI)."""

import importlib
import io
import json
import sys
from pathlib import Path

import pandas as pd
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
    for key in ("FLASK_ENV", "FLASK_SECRET_KEY", "LUCA_COOKIE_SECURE", "LUCA_BEHIND_PROXY", "LUCA_ACTIVITY_FILE",
                "LUCA_ADMINS"):
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


def test_only_logged_in_use_counts_as_activity(monkeypatch, tmp_path):
    marker = tmp_path / "last_activity"
    module = _load_app(monkeypatch, tmp_path, LUCA_ACTIVITY_FILE=str(marker))
    db.upsert_user("ana@uca.edu.ar", "clave-correcta", "Ana")
    client = module.app.test_client()
    client.get("/healthz")
    client.get("/practicas")
    _login(client, password="mala")
    assert not marker.exists()  # bots, health checks and failed logins don't keep the server awake
    assert _login(client).status_code == 200
    assert marker.exists()


def _change_password(client, current="clave-correcta", new="una-clave-nueva"):
    return client.post("/password", json={"current_password": current, "new_password": new})


def test_password_change_logs_out_other_sessions(app_module):
    laptop, phone = app_module.app.test_client(), app_module.app.test_client()
    _login(laptop)
    _login(phone)
    assert _change_password(laptop).json == {"success": True}
    assert laptop.get("/conversations").status_code == 200  # the session that changed it stays in
    assert phone.get("/auth/status").json == {"authenticated": False}
    assert b"loginForm" in phone.get("/conversations").data
    assert _login(phone).status_code == 401
    assert _login(phone, password="una-clave-nueva").status_code == 200


def test_password_change_validates_and_is_throttled(app_module):
    client = app_module.app.test_client()
    assert _change_password(client).status_code == 401  # login required
    _login(client)
    assert _change_password(client, new="corta").status_code == 400
    assert _change_password(client, new="clave-correcta").status_code == 400
    assert _change_password(client, new="ana@uca.edu.ar").status_code == 400
    assert _change_password(client, new=" con-espacio ").status_code == 400
    for _ in range(5):
        assert _change_password(client, current="adivinando").status_code == 403
    assert _change_password(client).status_code == 429  # a stolen session can't guess the password
    assert _login(app_module.app.test_client()).status_code == 429  # nor keep guessing through the login


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


ADMIN = {"X-Requested-With": "luca"}


@pytest.fixture
def admin_app(monkeypatch, tmp_path):
    module = _load_app(monkeypatch, tmp_path, LUCA_ADMINS="docente@uca.edu.ar")
    db.upsert_user("docente@uca.edu.ar", "clave-docente", "Docente")
    db.upsert_user("ana@uca.edu.ar", "clave-correcta", "Ana")
    return module


def _xlsx(rows):
    buffer = io.BytesIO()
    pd.DataFrame(rows, columns=["Nombre", "Legajo", "Email", "Contraseña"]).to_excel(buffer, index=False)
    buffer.seek(0)
    return buffer


def test_admin_is_only_for_the_configured_accounts(admin_app):
    student = admin_app.app.test_client()
    _login(student)
    assert b"/admin" not in student.get("/").data
    for method, path in (("get", "/admin"), ("get", "/admin/usuarios"), ("post", "/admin/usuarios"),
                         ("post", "/admin/usuarios/planilla")):
        assert getattr(student, method)(path, headers=ADMIN).status_code == 404, path
    assert b"loginForm" in admin_app.app.test_client().get("/admin/usuarios").data

    admin = admin_app.app.test_client()
    _login(admin, "docente@uca.edu.ar", "clave-docente")
    assert b"/admin" in admin.get("/").data
    assert admin.get("/admin").status_code == 200
    emails = [u["email"] for u in admin.get("/admin/usuarios").json]
    assert emails == ["ana@uca.edu.ar", "docente@uca.edu.ar"]
    assert all("password" not in key for u in admin.get("/admin/usuarios").json for key in u if key != "password_provisoria")
    # Without the custom header (what a cross-site form would send) writes are refused.
    assert admin.post("/admin/usuarios", json={"nombre": "X", "email": "x@uca.edu.ar"}).status_code == 400


def test_admin_creates_a_user_with_a_provisional_password(admin_app):
    admin = admin_app.app.test_client()
    _login(admin, "docente@uca.edu.ar", "clave-docente")
    response = admin.post("/admin/usuarios", headers=ADMIN, json={"nombre": "Carla", "email": "Carla@UCA.edu.ar"})
    generated = response.json["password"]
    assert response.json["success"] and response.json["created"] and len(generated) == 14
    assert admin.post("/admin/usuarios", headers=ADMIN, json={"nombre": "Carla", "email": "carla@uca.edu.ar",
                                                              "password": "otra-clave-1"}).status_code == 409
    assert admin.post("/admin/usuarios", headers=ADMIN, json={"nombre": "D", "email": "d@gmail.com"}).status_code == 400
    assert admin.post("/admin/usuarios", headers=ADMIN, json={"nombre": "D", "email": "d@uca.edu.ar",
                                                              "password": "corta"}).status_code == 400

    carla = admin_app.app.test_client()
    assert _login(carla, "carla@uca.edu.ar", generated).status_code == 200
    assert b"MUST_CHANGE_PASSWORD = true" in carla.get("/").data
    blocked = carla.post("/chat", json={"message": "hola"})
    assert blocked.status_code == 403 and blocked.json["must_change_password"]
    assert carla.get("/practicas").status_code == 200  # the page can load behind the modal
    assert _change_password(carla, generated, "elegida-por-carla").json == {"success": True}
    assert carla.post("/chat", json={"message": "hola"}).status_code == 200
    assert b"MUST_CHANGE_PASSWORD = false" in carla.get("/").data

    # Forgotten password: reset with a provisional one; her open session is logged out.
    reset = admin.post("/admin/usuarios", headers=ADMIN, json={"nombre": "Carla", "email": "carla@uca.edu.ar",
                                                                "password": "blanqueo-123", "reset": True})
    assert reset.json == {"success": True, "created": False, "password": None}
    assert carla.get("/auth/status").json == {"authenticated": False}
    assert _login(carla, "carla@uca.edu.ar", "blanqueo-123").status_code == 200
    assert carla.post("/chat", json={"message": "hola"}).status_code == 403


def test_admin_uploads_a_planilla(admin_app):
    admin = admin_app.app.test_client()
    _login(admin, "docente@uca.edu.ar", "clave-docente")
    planilla = _xlsx([
        ["Ana Pérez", "1", "ana@uca.edu.ar", "no-se-usa-123"],
        ["Beto", "2", "BETO@uca.edu.ar", "01234567"],
        ["Ceci", "3", "ceci@gmail.com", "clave-ceci-1"],
        ["Dani", "4", "dani@uca.edu.ar", "corta"],
        ["", "5", "eli@uca.edu.ar", "clave-eli-12"],
    ])
    response = admin.post("/admin/usuarios/planilla", headers=ADMIN,
                          data={"planilla": (planilla, "usuarios.xlsx"), "reset": "false"})
    assert response.json["created"] == ["beto@uca.edu.ar"] and response.json["updated"] == ["ana@uca.edu.ar"]
    assert [r.split(":")[0] for r in response.json["skipped"]] == ["fila 4", "fila 5", "fila 6"]
    assert _login(admin_app.app.test_client()).status_code == 200  # Ana keeps her password
    assert _login(admin_app.app.test_client(), "beto@uca.edu.ar", "01234567").status_code == 200  # leading 0 kept

    bad = admin.post("/admin/usuarios/planilla", headers=ADMIN, data={"planilla": (io.BytesIO(b"hola"), "x.xlsx")})
    assert bad.status_code == 400 and "No se pudo leer" in bad.json["error"]
    assert admin.post("/admin/usuarios/planilla", headers=ADMIN,
                      data={"planilla": (io.BytesIO(b"a,b"), "x.csv")}).status_code == 400


def test_login_page_does_not_ship_credentials(app_module):
    page = app_module.app.test_client().get("/").data.decode()
    assert "visitante" not in page and ".value = '" not in page


def test_the_downloadable_template_is_accepted_by_the_importer(admin_app):
    from openpyxl import load_workbook
    from storage.user_admin import read_planilla

    template = FRONTEND / "static" / "plantilla_usuarios.xlsx"
    assert read_planilla(template) == ([], [])  # empty: no users, no warnings for the formatted rows
    workbook = load_workbook(template)
    workbook.worksheets[0]["A2"], workbook.worksheets[0]["C2"], workbook.worksheets[0]["D2"] = (
        "Ana", "ana.perez@uca.edu.ar", "01234567")
    buffer = io.BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    assert read_planilla(buffer)[0] == [{"nombre": "Ana", "email": "ana.perez@uca.edu.ar", "password": "01234567"}]

    admin = admin_app.app.test_client()
    _login(admin, "docente@uca.edu.ar", "clave-docente")
    assert b"plantilla_usuarios.xlsx" in admin.get("/admin").data
