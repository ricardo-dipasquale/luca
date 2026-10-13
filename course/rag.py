"""Búsqueda en los apuntes indexados en Chroma por `python -m ingest --only apuntes`.

En runtime sólo se embebe la consulta; los documentos se embeben en la ingesta batch.
"""

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import chromadb

DEFAULT_COLLECTION = "apuntes"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"


def chroma_client() -> Any:
    return chromadb.HttpClient(
        host=os.getenv("CHROMA_HOST", "localhost"), port=int(os.getenv("CHROMA_PORT", "8001"))
    )


def collection_name() -> str:
    return os.getenv("CHROMA_COLLECTION", DEFAULT_COLLECTION)


def embedding_model() -> str:
    return os.getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)


def openai_embeddings(model: str | None = None) -> Any:
    from langchain_openai import OpenAIEmbeddings

    return OpenAIEmbeddings(model=model or embedding_model())


class ApuntesNoIndexados(RuntimeError):
    pass


@dataclass
class Fragmento:
    texto: str
    apunte: str
    pagina: int
    similitud: float


class ApuntesRetriever:
    def __init__(self, client: Any = None, embeddings: Any = None, collection: str | None = None):
        client = client or chroma_client()
        name = collection or collection_name()
        hint = "Generalo con: python -m ingest --only apuntes"
        try:
            self._collection = client.get_collection(name)
        except Exception as e:
            raise ApuntesNoIndexados(f"No existe la colección '{name}' en Chroma ({e}). {hint}") from e
        if self._collection.count() == 0:
            raise ApuntesNoIndexados(f"La colección '{name}' está vacía. {hint}")
        indexed_with = (self._collection.metadata or {}).get("embedding_model")
        self._embeddings = embeddings or openai_embeddings(indexed_with)
        configured = getattr(self._embeddings, "model", indexed_with)
        if indexed_with != configured:
            raise ApuntesNoIndexados(
                f"Los apuntes se indexaron con '{indexed_with}' y la consulta usa '{configured}'. "
                "Reindexá con: python -m ingest --only apuntes --force"
            )

    def search(self, query: str, k: int = 4, apuntes: list[str] | None = None, min_similitud: float | None = None) -> list[Fragmento]:
        where = {"source": {"$in": apuntes}} if apuntes else None
        res = self._collection.query(
            query_embeddings=[self._embeddings.embed_query(query)], n_results=k, where=where,
            include=["documents", "metadatas", "distances"],
        )
        fragmentos = [
            Fragmento(texto=doc, apunte=meta["source"], pagina=meta["page"], similitud=1 - dist)
            for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0])
        ]
        return fragmentos if min_similitud is None else [f for f in fragmentos if f.similitud >= min_similitud]


@lru_cache(maxsize=1)
def get_apuntes_retriever() -> ApuntesRetriever:
    return ApuntesRetriever()
