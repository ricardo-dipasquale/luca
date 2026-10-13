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
