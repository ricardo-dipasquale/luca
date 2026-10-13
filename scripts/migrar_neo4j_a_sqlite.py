#!/usr/bin/env python3
"""Migración única: usuarios, conversaciones y mensajes de Neo4j → SQLite (storage/db.py).

Idempotente: lo que ya existe en SQLite (mismo email o id) no se toca. Las contraseñas, que en Neo4j
estaban en texto plano, se guardan con hash. La memoria del agente viejo no se migra.

Uso: python scripts/migrar_neo4j_a_sqlite.py [--dry-run]
Requiere NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD y Neo4j levantado.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from werkzeug.security import generate_password_hash

from kg.connection import KGConnection
from storage import db


def _iso(value) -> str | None:
    if value is None:
        return None
    return value.to_native().isoformat(timespec="seconds") if hasattr(value, "to_native") else str(value)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="Sólo contar, sin escribir en SQLite")
    args = parser.parse_args()

    with KGConnection() as kg:
        usuarios = kg.execute_query("MATCH (u:Usuario) RETURN u.email AS email, u.nombre AS nombre, "
                                    "u.password AS password, u.created_at AS created_at, u.last_login AS last_login")
        conversaciones = kg.execute_query(
            "MATCH (u:Usuario)-[:OWNS]->(c:Conversacion) RETURN u.email AS email, c.id AS id, c.title AS title, "
            "c.subject AS subject, c.created_at AS created_at, c.updated_at AS updated_at")
        mensajes = kg.execute_query(
            "MATCH (c:Conversacion)-[:CONTAINS]->(m:Mensaje) RETURN c.id AS conv, m.id AS id, m.role AS role, "
            "m.content AS content, m.order AS ord, m.created_at AS created_at ORDER BY c.id, m.order, m.created_at")

    print(f"Neo4j: {len(usuarios)} usuarios, {len(conversaciones)} conversaciones, {len(mensajes)} mensajes")
    if args.dry_run:
        return 0

    nuevos = {"usuarios": 0, "conversaciones": 0, "mensajes": 0}
    with db.connect() as con:
        for u in usuarios:
            if not u["email"] or not u["password"]:
                print(f"  usuario sin email o contraseña, se omite: {u['email']!r}")
                continue
            cur = con.execute(
                "INSERT OR IGNORE INTO usuarios (email, nombre, password_hash, created_at, last_login) VALUES (?, ?, ?, ?, ?)",
                (u["email"].strip().lower(), u["nombre"], generate_password_hash(u["password"]),
                 _iso(u["created_at"]) or db._now(), _iso(u["last_login"])))
            nuevos["usuarios"] += cur.rowcount
        for c in conversaciones:
            cur = con.execute(
                "INSERT OR IGNORE INTO conversaciones (id, user_email, title, subject, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (c["id"], c["email"].strip().lower(), c["title"] or "Conversación", c["subject"],
                 _iso(c["created_at"]) or db._now(), _iso(c["updated_at"]) or db._now()))
            nuevos["conversaciones"] += cur.rowcount
        orden: dict[str, int] = {}
        for m in mensajes:
            orden[m["conv"]] = orden.get(m["conv"], 0) + 1
            if m["role"] not in ("user", "assistant") or m["content"] is None:
                continue
            cur = con.execute(
                "INSERT OR IGNORE INTO mensajes (id, conversation_id, role, content, ord, exercise_id, created_at) "
                "SELECT ?, ?, ?, ?, ?, NULL, ? WHERE EXISTS (SELECT 1 FROM conversaciones WHERE id = ?)",
                (m["id"], m["conv"], m["role"], m["content"], orden[m["conv"]], _iso(m["created_at"]) or db._now(), m["conv"]))
            nuevos["mensajes"] += cur.rowcount
        con.execute("UPDATE conversaciones SET message_count = "
                    "(SELECT COUNT(*) FROM mensajes WHERE mensajes.conversation_id = conversaciones.id)")

    print(f"SQLite ({db.db_path()}): nuevos {nuevos}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
