"""Paso `apuntes`: PDF/MD de content/apuntes → fragmentos embebidos en Chroma.

Incremental por archivo: el hash SHA-256 de cada apunte queda en la metadata de sus fragmentos; sólo se
reprocesan los archivos nuevos o modificados y se borran los fragmentos de los archivos eliminados.
Si cambia el modelo de embeddings o el fragmentado, hace falta --force (recrea la colección).
"""

import hashlib
import logging
from pathlib import Path
from typing import Any

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

logger = logging.getLogger(__name__)

CHUNK_SIZE = 1200
CHUNK_OVERLAP = 150
SUFFIXES = (".pdf", ".md")


class ConfiguracionCambiada(RuntimeError):
    pass


def _paginas(path: Path) -> list[tuple[int, str]]:
    if path.suffix.lower() == ".pdf":
        return [(i + 1, p.extract_text() or "") for i, p in enumerate(PdfReader(path).pages)]
    return [(1, path.read_text(encoding="utf-8"))]


def _fragmentos(path: Path) -> list[tuple[int, str]]:
    """(página, texto) per chunk; chunks never cross pages so citations stay exact."""
    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    return [(pagina, chunk) for pagina, texto in _paginas(path) for chunk in splitter.split_text(texto) if chunk.strip()]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _temas_por_apunte(materia: dict) -> dict[str, str]:
    temas: dict[str, list[str]] = {}
    for u in materia["unidades"]:
        for t in u["temas"]:
            for a in t["apuntes"]:
                temas.setdefault(a, []).append(t["descripcion"])
    return {a: "; ".join(ts) for a, ts in temas.items()}


def _collection(client: Any, name: str, metadata: dict, force: bool) -> Any:
    if force and name in [c.name for c in client.list_collections()]:
        client.delete_collection(name)
        logger.info(f"apuntes: colección '{name}' recreada (--force)")
    col = client.get_or_create_collection(
        name, configuration={"hnsw": {"space": "cosine"}}, metadata=metadata, embedding_function=None
    )
    actual = {k: (col.metadata or {}).get(k) for k in metadata}
    if actual != metadata:
        raise ConfiguracionCambiada(
            f"La colección '{name}' se generó con {actual} y la configuración actual es {metadata}. "
            "Reindexá todo con: python -m ingest --only apuntes --force"
        )
    return col


def run(apuntes_dir: Path, materia: dict, client: Any, embeddings: Any, embedding_model: str,
        collection: str, force: bool = False) -> dict[str, int]:
    metadata = {"embedding_model": embedding_model, "chunk_size": CHUNK_SIZE, "chunk_overlap": CHUNK_OVERLAP}
    col = _collection(client, collection, metadata, force)

    indexados: dict[str, str] = {}
    for meta in col.get(include=["metadatas"])["metadatas"]:
        indexados[meta["source"]] = meta["source_hash"]

    archivos = sorted(p for p in apuntes_dir.iterdir() if p.suffix.lower() in SUFFIXES) if apuntes_dir.is_dir() else []
    temas = _temas_por_apunte(materia)
    stats = {"procesados": 0, "sin_cambios": 0, "eliminados": 0, "fragmentos": 0}

    for borrado in sorted(set(indexados) - {p.name for p in archivos}):
        col.delete(where={"source": borrado})
        stats["eliminados"] += 1
        logger.info(f"apuntes: {borrado} ya no está; se borraron sus fragmentos")

    for path in archivos:
        h = _sha256(path)
        if indexados.get(path.name) == h:
            stats["sin_cambios"] += 1
            continue
        if path.name in indexados:
            col.delete(where={"source": path.name})
        fragmentos = _fragmentos(path)
        if not fragmentos:
            logger.warning(f"apuntes: {path.name} no tiene texto extraíble (¿imágenes?); no se indexa")
            continue
        textos = [t for _, t in fragmentos]
        col.upsert(
            ids=[f"{h[:16]}:{i}" for i in range(len(fragmentos))],
            embeddings=embeddings.embed_documents(textos),
            documents=textos,
            metadatas=[
                {"source": path.name, "page": pagina, "source_hash": h, "temas": temas.get(path.name, "")}
                for pagina, _ in fragmentos
            ],
        )
        stats["procesados"] += 1
        stats["fragmentos"] += len(fragmentos)
        logger.info(f"apuntes: {path.name} → {len(fragmentos)} fragmentos")

    logger.info(
        f"apuntes: {stats['procesados']} procesados ({stats['fragmentos']} fragmentos), {stats['sin_cambios']} sin cambios, "
        f"{stats['eliminados']} eliminados; colección '{collection}' con {col.count()} fragmentos"
    )
    return stats
