#!/usr/bin/env python3
"""Importa usuarios desde un Excel a SQLite (storage/db.py).

Columnas por posición: 1.ª nombre, 3.ª email (debe terminar en @uca.edu.ar), 4.ª contraseña.
Crea los usuarios nuevos y actualiza nombre y contraseña de los existentes. Las contraseñas se guardan con hash.

Uso: python scripts/import_usuarios.py [--file usuarios-luca.xlsx] [--dry-run]
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from storage import db


def load_users(path: Path) -> list[dict[str, str]]:
    users = []
    for i, row in pd.read_excel(path).iterrows():
        nombre, email, password = (str(row.iloc[c]).strip() if pd.notna(row.iloc[c]) else "" for c in (0, 2, 3))
        if not (nombre and email and password):
            print(f"  fila {i + 2}: faltan datos, se omite")
        elif not email.lower().endswith("@uca.edu.ar"):
            print(f"  fila {i + 2}: {email} no es @uca.edu.ar, se omite")
        else:
            users.append({"nombre": nombre, "email": email.lower(), "password": password})
    return users


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--file", type=Path, default=Path("usuarios-luca.xlsx"))
    parser.add_argument("--dry-run", action="store_true", help="Mostrar qué se importaría sin escribir")
    args = parser.parse_args()
    if not args.file.exists():
        print(f"No existe {args.file}")
        return 1

    users = load_users(args.file)
    existentes = {u["email"] for u in db.list_users()}
    print(f"{len(users)} usuarios válidos en {args.file}: "
          f"{sum(u['email'] not in existentes for u in users)} nuevos, {sum(u['email'] in existentes for u in users)} a actualizar")
    if args.dry_run:
        return 0
    for u in users:
        db.upsert_user(u["email"], u["password"], u["nombre"])
    print(f"Listo: {len(db.list_users())} usuarios en {db.db_path()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
