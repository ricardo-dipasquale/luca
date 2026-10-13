"""SQLite: usuarios, conversaciones y mensajes. Un archivo (LUCA_DB_PATH), sin servidor.

La memoria del agente (checkpoints de LangGraph) vive en el mismo archivo, en sus propias tablas.
"""

import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional

from werkzeug.security import check_password_hash, generate_password_hash

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PATH = PROJECT_ROOT / "data" / "luca.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
    email TEXT PRIMARY KEY,
    nombre TEXT,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    last_login TEXT
);
CREATE TABLE IF NOT EXISTS conversaciones (
    id TEXT PRIMARY KEY,
    user_email TEXT NOT NULL REFERENCES usuarios(email) ON DELETE CASCADE,
    title TEXT NOT NULL,
    subject TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    message_count INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_conversaciones_user ON conversaciones(user_email, updated_at);
CREATE TABLE IF NOT EXISTS mensajes (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversaciones(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    ord INTEGER NOT NULL,
    exercise_id TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_mensajes_conv ON mensajes(conversation_id, ord);
"""


def db_path() -> Path:
    return Path(os.environ.get("LUCA_DB_PATH", DEFAULT_PATH))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def connect(path: Optional[Path] = None) -> Iterator[sqlite3.Connection]:
    path = path or db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA journal_mode = WAL")  # Flask serves requests from several threads
    try:
        con.executescript(SCHEMA)
        yield con
        con.commit()
    finally:
        con.close()


# ---------- usuarios ----------

def upsert_user(email: str, password: str, nombre: Optional[str] = None, path: Optional[Path] = None) -> bool:
    """Creates or updates a user; returns True if it was created."""
    email = email.strip().lower()
    with connect(path) as con:
        existe = con.execute("SELECT 1 FROM usuarios WHERE email = ?", (email,)).fetchone()
        if existe:
            con.execute("UPDATE usuarios SET nombre = COALESCE(?, nombre), password_hash = ? WHERE email = ?",
                        (nombre, generate_password_hash(password), email))
        else:
            con.execute("INSERT INTO usuarios (email, nombre, password_hash, created_at) VALUES (?, ?, ?, ?)",
                        (email, nombre, generate_password_hash(password), _now()))
        return not existe


def authenticate(email: str, password: str, path: Optional[Path] = None) -> Optional[dict[str, Any]]:
    email = email.strip().lower()
    with connect(path) as con:
        row = con.execute("SELECT * FROM usuarios WHERE email = ?", (email,)).fetchone()
        if row is None or not check_password_hash(row["password_hash"], password):
            return None
        con.execute("UPDATE usuarios SET last_login = ? WHERE email = ?", (_now(), email))
        return {"email": row["email"], "nombre": row["nombre"], "created_at": row["created_at"]}


def list_users(path: Optional[Path] = None) -> list[dict[str, Any]]:
    with connect(path) as con:
        return [dict(r) for r in con.execute("SELECT email, nombre, created_at, last_login FROM usuarios ORDER BY email")]


# ---------- conversaciones ----------

def create_conversation(user_email: str, title: str, subject: Optional[str], path: Optional[Path] = None) -> str:
    conv_id = str(uuid.uuid4())
    now = _now()
    with connect(path) as con:
        con.execute(
            "INSERT INTO conversaciones (id, user_email, title, subject, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (conv_id, user_email, title, subject, now, now),
        )
    return conv_id


def conversation_owner(conversation_id: str, path: Optional[Path] = None) -> Optional[str]:
    with connect(path) as con:
        row = con.execute("SELECT user_email FROM conversaciones WHERE id = ?", (conversation_id,)).fetchone()
        return row["user_email"] if row else None


def list_conversations(user_email: str, path: Optional[Path] = None) -> list[dict[str, Any]]:
    with connect(path) as con:
        return [dict(r) for r in con.execute(
            "SELECT id, title, subject, created_at, updated_at, message_count FROM conversaciones "
            "WHERE user_email = ? ORDER BY updated_at DESC", (user_email,))]


def rename_conversation(conversation_id: str, title: str, path: Optional[Path] = None) -> None:
    with connect(path) as con:
        con.execute("UPDATE conversaciones SET title = ?, updated_at = ? WHERE id = ?", (title, _now(), conversation_id))


def delete_conversation(conversation_id: str, user_email: str, path: Optional[Path] = None) -> bool:
    """Deletes it (and its messages) only if it belongs to user_email."""
    with connect(path) as con:
        cur = con.execute("DELETE FROM conversaciones WHERE id = ? AND user_email = ?", (conversation_id, user_email))
        return cur.rowcount == 1


# ---------- mensajes ----------

def add_message(conversation_id: str, role: str, content: str, exercise_id: Optional[str] = None,
                path: Optional[Path] = None) -> str:
    msg_id = str(uuid.uuid4())
    now = _now()
    with connect(path) as con:
        ord_ = con.execute("SELECT COALESCE(MAX(ord), 0) + 1 FROM mensajes WHERE conversation_id = ?",
                           (conversation_id,)).fetchone()[0]
        con.execute(
            "INSERT INTO mensajes (id, conversation_id, role, content, ord, exercise_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (msg_id, conversation_id, role, content, ord_, exercise_id, now),
        )
        con.execute("UPDATE conversaciones SET message_count = message_count + 1, updated_at = ? WHERE id = ?",
                    (now, conversation_id))
    return msg_id


def list_messages(conversation_id: str, limit: Optional[int] = None, path: Optional[Path] = None) -> list[dict[str, Any]]:
    """Oldest first; with limit, the last `limit` messages."""
    with connect(path) as con:
        rows = con.execute(
            "SELECT content, role, ord AS \"order\", exercise_id, created_at FROM mensajes "
            "WHERE conversation_id = ? ORDER BY ord DESC LIMIT ?", (conversation_id, limit or -1)).fetchall()
    return [dict(r) for r in reversed(rows)]
