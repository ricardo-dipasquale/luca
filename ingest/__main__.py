"""Rutina batch de ingesta: python -m ingest [--only practicas] [--content DIR] [--artifacts DIR]"""

import argparse
import logging
import sys
from pathlib import Path

from ingest import practicas
from ingest.practicas import IngestValidationError

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STEPS = ["practicas"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m ingest", description=__doc__)
    parser.add_argument("--only", choices=STEPS, action="append", help="Correr solo este paso (repetible)")
    parser.add_argument("--content", type=Path, default=PROJECT_ROOT / "content")
    parser.add_argument("--artifacts", type=Path, default=PROJECT_ROOT / "artifacts")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    steps = args.only or STEPS
    try:
        if "practicas" in steps:
            practicas.run(
                programa_path=args.content / "Programa.xlsx",
                practicas_path=args.content / "Prácticas Bases de Datos.xlsx",
                output_path=args.artifacts / "practicas.json",
            )
    except IngestValidationError as e:
        logging.error(str(e))
        return 1
    except FileNotFoundError as e:
        logging.error(f"No se encontró la fuente: {e.filename}. Copiá los originales en {args.content}/")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
