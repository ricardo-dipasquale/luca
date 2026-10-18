import sqlite3

import pytest

from storage import db


@pytest.fixture
def path(tmp_path):
    return tmp_path / "luca.db"


def test_passwords_are_hashed_and_email_is_case_insensitive(path):
    assert db.upsert_user("Ana@UCA.edu.ar", "secreta", "Ana", path=path) is True
    stored = sqlite3.connect(path).execute("SELECT password_hash FROM usuarios").fetchone()[0]
    assert "secreta" not in stored
    assert db.authenticate("ana@uca.edu.ar", "secreta", path=path)["nombre"] == "Ana"
    assert db.authenticate("ana@uca.edu.ar", "otra", path=path) is None
    assert db.authenticate("nadie@uca.edu.ar", "secreta", path=path) is None


def test_upsert_updates_password_of_existing_user(path):
    db.upsert_user("ana@uca.edu.ar", "vieja", "Ana", path=path)
    assert db.upsert_user("ana@uca.edu.ar", "nueva", None, path=path) is False
    assert db.authenticate("ana@uca.edu.ar", "vieja", path=path) is None
    assert db.authenticate("ana@uca.edu.ar", "nueva", path=path)["nombre"] == "Ana"


def test_messages_keep_order_exercise_and_count(path):
    db.upsert_user("ana@uca.edu.ar", "x", path=path)
    conv = db.create_conversation("ana@uca.edu.ar", "t", "BD", path=path)
    db.add_message(conv, "user", "hola", None, path=path)
    db.add_message(conv, "assistant", "¿en qué te ayudo?", None, path=path)
    db.add_message(conv, "user", "el 4.1.75", "4.1.75", path=path)
    msgs = db.list_messages(conv, path=path)
    assert [(m["order"], m["role"], m["exercise_id"]) for m in msgs] == [(1, "user", None), (2, "assistant", None), (3, "user", "4.1.75")]
    assert [m["content"] for m in db.list_messages(conv, limit=2, path=path)] == ["¿en qué te ayudo?", "el 4.1.75"]
    assert db.list_conversations("ana@uca.edu.ar", path=path)[0]["message_count"] == 3


def test_only_the_owner_can_delete_and_messages_go_with_it(path):
    for email in ("ana@uca.edu.ar", "beto@uca.edu.ar"):
        db.upsert_user(email, "x", path=path)
    conv = db.create_conversation("ana@uca.edu.ar", "t", "BD", path=path)
    db.add_message(conv, "user", "hola", None, path=path)
    assert db.conversation_owner(conv, path=path) == "ana@uca.edu.ar"
    assert db.delete_conversation(conv, "beto@uca.edu.ar", path=path) is False
    assert db.delete_conversation(conv, "ana@uca.edu.ar", path=path) is True
    assert db.conversation_owner(conv, path=path) is None
    assert sqlite3.connect(path).execute("SELECT COUNT(*) FROM mensajes").fetchone()[0] == 0


def test_conversations_are_listed_per_user_most_recent_first(path):
    db.upsert_user("ana@uca.edu.ar", "x", path=path)
    db.upsert_user("beto@uca.edu.ar", "x", path=path)
    vieja = db.create_conversation("ana@uca.edu.ar", "vieja", "BD", path=path)
    nueva = db.create_conversation("ana@uca.edu.ar", "nueva", "BD", path=path)
    db.create_conversation("beto@uca.edu.ar", "de beto", "BD", path=path)
    db.add_message(nueva, "user", "hola", None, path=path)
    db.rename_conversation(vieja, "renombrada", path=path)
    titulos = [c["title"] for c in db.list_conversations("ana@uca.edu.ar", path=path)]
    assert sorted(titulos) == ["nueva", "renombrada"]


def test_change_password_requires_the_current_one(path):
    db.upsert_user("ana@uca.edu.ar", "vieja-clave", "Ana", path=path)
    before = db.password_fingerprint("ana@uca.edu.ar", path=path)
    assert db.change_password("ana@uca.edu.ar", "equivocada", "nueva-clave", path=path) is False
    assert db.change_password("ana@uca.edu.ar", "vieja-clave", "nueva-clave", path=path) is True
    assert db.authenticate("ana@uca.edu.ar", "nueva-clave", path=path)
    assert db.authenticate("ana@uca.edu.ar", "vieja-clave", path=path) is None
    after = db.password_fingerprint("ana@uca.edu.ar", path=path)
    assert after != before and "nueva-clave" not in after
    assert db.password_fingerprint("nadie@uca.edu.ar", path=path) is None


def test_reimport_keeps_a_changed_password_unless_reset(path):
    db.upsert_user("ana@uca.edu.ar", "de-la-planilla", "Ana", path=path)
    db.change_password("ana@uca.edu.ar", "de-la-planilla", "elegida-por-ana", path=path)
    db.upsert_user("ana@uca.edu.ar", "de-la-planilla", "Ana María", path=path, reset_password=False)
    assert db.authenticate("ana@uca.edu.ar", "elegida-por-ana", path=path)["nombre"] == "Ana María"
    db.upsert_user("ana@uca.edu.ar", "blanqueada", None, path=path, reset_password=True)
    assert db.authenticate("ana@uca.edu.ar", "blanqueada", path=path)


def test_old_databases_get_the_provisional_password_column(tmp_path):
    path = tmp_path / "vieja.db"
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE usuarios (email TEXT PRIMARY KEY, nombre TEXT, password_hash TEXT NOT NULL, "
                "created_at TEXT NOT NULL, last_login TEXT)")
    con.execute("INSERT INTO usuarios VALUES ('ana@uca.edu.ar', 'Ana', 'x', '2025-01-01', NULL)")
    con.commit()
    con.close()
    assert db.auth_state("ana@uca.edu.ar", path=path)["provisional"] is False


def test_provisional_password_is_cleared_when_changed(path):
    db.upsert_user("ana@uca.edu.ar", "provisoria-1", "Ana", path=path, provisional=True)
    assert db.auth_state("ana@uca.edu.ar", path=path)["provisional"] is True
    db.change_password("ana@uca.edu.ar", "provisoria-1", "propia-de-ana", path=path)
    assert db.auth_state("ana@uca.edu.ar", path=path)["provisional"] is False
    db.upsert_user("ana@uca.edu.ar", "x", None, path=path, reset_password=False, provisional=True)
    assert db.auth_state("ana@uca.edu.ar", path=path)["provisional"] is False  # untouched password stays hers


def test_generated_provisional_passwords_pass_the_rules():
    from storage.user_admin import generate_provisional_password, password_problem

    passwords = {generate_provisional_password() for _ in range(50)}
    assert len(passwords) == 50
    assert all(password_problem(p, "ana@uca.edu.ar") is None for p in passwords)
