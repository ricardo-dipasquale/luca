#!/usr/bin/env python3
"""Importa usuarios desde un Excel a SQLite (storage/db.py). Lo mismo se puede hacer desde /admin.

Columnas por posición: 1.ª nombre, 3.ª email (debe terminar en @uca.edu.ar), 4.ª contraseña (8 caracteres
o más). Crea los usuarios nuevos y actualiza el nombre de los existentes. Las contraseñas se guardan con hash
y son provisorias: hay que cambiarlas al entrar por primera vez.
A quien ya existe no se le cambia la contraseña (puede haberla cambiado desde LUCA), salvo con
--reset-passwords: así se blanquea la de quienes la olvidaron (dejar en la planilla sólo esas filas).

Uso: python scripts/import_usuarios.py [--file usuarios-luca.xlsx] [--dry-run] [--reset-passwords]
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from storage import db
from storage.user_admin import import_users, read_planilla


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--file", type=Path, default=Path("usuarios-luca.xlsx"))
    parser.add_argument("--dry-run", action="store_true", help="Mostrar qué se importaría sin escribir")
    parser.add_argument("--reset-passwords", action="store_true",
                        help="Reemplazar también la contraseña de los usuarios que ya existen")
    args = parser.parse_args()
    if not args.file.exists():
        print(f"No existe {args.file}")
        return 1

    users, skipped = read_planilla(args.file)
    for reason in skipped:
        print(f"  {reason}, se omite")
    result = import_users(users, reset_passwords=args.reset_passwords, dry_run=args.dry_run)
    print(f"{len(users)} usuarios válidos en {args.file}: {len(result.created)} nuevos, "
          f"{len(result.updated)} a actualizar ({'con' if args.reset_passwords else 'sin'} cambio de contraseña)")
    if not args.dry_run:
        print(f"Listo: {len(db.list_users())} usuarios en {db.db_path()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
