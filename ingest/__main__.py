"""Rutina batch de ingesta: python -m ingest [--only practicas|soluciones|apuntes] [--force]

practicas: Excel → artifacts/practicas.json (siempre se reconstruye; incluye las soluciones ya generadas).
soluciones: genera con el LLM el AR faltante y el SQL de cada ejercicio → content/soluciones_generadas.json.
apuntes: content/apuntes (PDF/MD) → fragmentos embebidos en Chroma (requiere Chroma levantado).
"""

import argparse
import logging
import sys
from pathlib import Path

from ingest import apuntes, practicas, soluciones
from ingest.apuntes import ConfiguracionCambiada
from ingest.practicas import IngestValidationError

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STEPS = ["practicas", "soluciones", "apuntes"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m ingest", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", choices=STEPS, action="append", help="Correr solo este paso (repetible)")
    parser.add_argument(
        "--force", action="store_true",
        help="soluciones: regenerar las no aprobadas aunque no hayan cambiado; apuntes: recrear la colección",
    )
    parser.add_argument(
        "--regenerar-no-conformes", action="store_true",
        help="Regenerar sólo las soluciones pendientes que no cumplen las reglas vigentes (esquema y forma canónica)",
    )
    parser.add_argument("--content", type=Path, default=PROJECT_ROOT / "content")
    parser.add_argument("--artifacts", type=Path, default=PROJECT_ROOT / "artifacts")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    for noisy in ("httpx", "openai", "langchain", "langchain_openai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    steps = args.only or STEPS
    soluciones_path = args.content / "soluciones_generadas.json"
    try:
        artifact = practicas.build_and_log(
            programa_path=args.content / "Programa.xlsx",
            practicas_path=args.content / "Prácticas Bases de Datos.xlsx",
            apuntes_dir=args.content / "apuntes",
        )
        if "soluciones" in steps:
            from tools.llm_config import get_default_llm_config

            soluciones.generate(
                artifact, soluciones_path, soluciones.default_llm_factory,
                modelo=get_default_llm_config()["model"], force=args.force,
                no_conformes=args.regenerar_no_conformes,
            )
        soluciones.merge(artifact, soluciones_path)
        practicas.write(artifact, args.artifacts / "practicas.json")
        if "apuntes" in steps:
            from course import rag

            try:
                client = rag.chroma_client()
                client.heartbeat()
            except Exception as e:
                logging.error(f"No se pudo conectar a Chroma ({e}). Levantalo con: docker compose up -d chroma")
                return 1
            apuntes.run(
                args.content / "apuntes", artifact["materia"], client, rag.openai_embeddings(),
                embedding_model=rag.embedding_model(), collection=rag.collection_name(), force=args.force,
            )
    except (IngestValidationError, ConfiguracionCambiada) as e:
        logging.error(str(e))
        return 1
    except FileNotFoundError as e:
        logging.error(f"No se encontró la fuente: {e.filename}. Copiá los originales en {args.content}/")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
