#!/usr/bin/env python3
"""Exporta conversaciones y mensajes de SQLite (storage/db.py) a Excel.

Hoja Conversaciones_Mensajes: una fila por mensaje (usuario, conversación, rol, contenido, fecha, orden y
ejercicio de la práctica sobre el que se habló). Hojas de resumen por usuario y por ejercicio.

Uso: python scripts/export_conversaciones.py [--output conversaciones_luca.xlsx] [--user EMAIL]
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from storage import db

QUERY = """
SELECT u.nombre AS usuario_nombre, u.email AS usuario_email,
       c.id AS conversacion_id, c.title AS conversacion_titulo, c.subject AS conversacion_materia,
       c.created_at AS conversacion_fecha, c.updated_at AS conversacion_actualizada,
       m.id AS mensaje_id, m.role AS mensaje_role, m.content AS mensaje_contenido,
       m.created_at AS mensaje_fecha, m.ord AS mensaje_orden, m.exercise_id AS ejercicio_id
FROM mensajes m
JOIN conversaciones c ON c.id = m.conversation_id
JOIN usuarios u ON u.email = c.user_email
{where}
ORDER BY u.email, c.created_at, m.ord
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, default=Path("conversaciones_luca.xlsx"))
    parser.add_argument("--user", help="Exportar sólo las conversaciones de este email")
    args = parser.parse_args()

    with db.connect() as con:
        where, params = ("WHERE u.email = ?", (args.user.lower(),)) if args.user else ("", ())
        df = pd.read_sql_query(QUERY.format(where=where), con, params=params)
    if df.empty:
        print("No hay mensajes para exportar.")
        return 0

    por_usuario = df.groupby(["usuario_email", "usuario_nombre"], dropna=False).agg(
        conversaciones=("conversacion_id", "nunique"), mensajes=("mensaje_id", "count")).reset_index()
    alumno = df[df["mensaje_role"] == "user"]
    por_ejercicio = (alumno.assign(ejercicio_id=alumno["ejercicio_id"].fillna("(consulta libre)"))
                     .groupby("ejercicio_id").agg(mensajes_de_alumnos=("mensaje_id", "count"),
                                                  alumnos=("usuario_email", "nunique"))
                     .reset_index().sort_values("mensajes_de_alumnos", ascending=False))

    with pd.ExcelWriter(args.output) as writer:
        df.to_excel(writer, sheet_name="Conversaciones_Mensajes", index=False)
        por_usuario.to_excel(writer, sheet_name="Por_Usuario", index=False)
        por_ejercicio.to_excel(writer, sheet_name="Por_Ejercicio", index=False)
    print(f"{len(df)} mensajes de {df['conversacion_id'].nunique()} conversaciones → {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
