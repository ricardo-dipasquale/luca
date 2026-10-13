import uuid
from pathlib import Path

import chromadb
import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding

from course.rag import ApuntesNoIndexados, ApuntesRetriever
from ingest import apuntes
from ingest.apuntes import ConfiguracionCambiada

TALLER = Path(__file__).resolve().parent.parent / "content" / "apuntes" / "009 - Taller #8 - Visuals - De Algebra Relacional a SQL.pdf"
MATERIA = {"unidades": [{"temas": [{"descripcion": "Álgebra relacional", "apuntes": ["algebra.md"]}]}]}


class CountingEmbeddings(DeterministicFakeEmbedding):
    model: str = "fake-model"
    embedded: list = []

    def embed_documents(self, texts):
        self.embedded.extend(texts)
        return super().embed_documents(texts)


@pytest.fixture
def client():
    return chromadb.EphemeralClient()


@pytest.fixture
def collection():
    return f"apuntes-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def docs(tmp_path: Path) -> Path:
    d = tmp_path / "apuntes"
    d.mkdir()
    (d / "algebra.md").write_text("El cociente resuelve consultas con la idea de para todos.\n\n" * 3)
    (d / "sql.md").write_text("EXCEPT implementa la diferencia de conjuntos en SQL ANSI.")
    return d


def _run(docs, client, collection, emb=None, model="fake-model", force=False):
    emb = emb or CountingEmbeddings(size=16, embedded=[])
    return apuntes.run(docs, MATERIA, client, emb, embedding_model=model, collection=collection, force=force), emb


def test_indexes_every_note_with_source_page_and_topics(docs, client, collection):
    stats, _ = _run(docs, client, collection)
    assert stats["procesados"] == 2
    metas = client.get_collection(collection).get(include=["metadatas"])["metadatas"]
    assert {m["source"] for m in metas} == {"algebra.md", "sql.md"}
    assert all(m["page"] == 1 for m in metas)
    assert {m["temas"] for m in metas if m["source"] == "algebra.md"} == {"Álgebra relacional"}


def test_second_run_embeds_nothing(docs, client, collection):
    _run(docs, client, collection)
    stats, emb = _run(docs, client, collection)
    assert emb.embedded == [] and stats["sin_cambios"] == 2


def test_only_modified_note_is_reembedded_and_old_chunks_removed(docs, client, collection):
    _run(docs, client, collection)
    (docs / "sql.md").write_text("INTERSECT implementa la intersección.")
    stats, emb = _run(docs, client, collection)
    assert stats["procesados"] == 1 and emb.embedded == ["INTERSECT implementa la intersección."]
    textos = client.get_collection(collection).get(where={"source": "sql.md"})["documents"]
    assert textos == ["INTERSECT implementa la intersección."]


def test_deleted_note_loses_its_chunks(docs, client, collection):
    _run(docs, client, collection)
    (docs / "sql.md").unlink()
    stats, _ = _run(docs, client, collection)
    assert stats["eliminados"] == 1
    assert client.get_collection(collection).get(where={"source": "sql.md"})["ids"] == []


def test_changing_embedding_model_requires_force(docs, client, collection):
    _run(docs, client, collection)
    with pytest.raises(ConfiguracionCambiada, match="--force"):
        _run(docs, client, collection, model="otro-modelo")
    stats, _ = _run(docs, client, collection, model="otro-modelo", force=True)
    assert stats["procesados"] == 2


def test_pdf_chunks_keep_their_page():
    fragmentos = apuntes._fragmentos(TALLER)
    cociente = [p for p, t in fragmentos if "doble NOT EXISTS" in t and "A AS A3" in t]
    assert cociente == [18]


def test_retriever_filters_by_note_and_reports_page(docs, client, collection):
    _run(docs, client, collection)
    retriever = ApuntesRetriever(client, CountingEmbeddings(size=16, embedded=[]), collection)
    resultados = retriever.search("diferencia de conjuntos", k=5, apuntes=["sql.md"])
    assert [r.apunte for r in resultados] == ["sql.md"] and resultados[0].pagina == 1


def test_retriever_fails_clearly_when_not_indexed(client, collection):
    with pytest.raises(ApuntesNoIndexados, match="python -m ingest --only apuntes"):
        ApuntesRetriever(client, CountingEmbeddings(size=16, embedded=[]), collection)


def test_retriever_rejects_a_different_embedding_model(docs, client, collection):
    _run(docs, client, collection)
    other = CountingEmbeddings(size=16, embedded=[])
    other.model = "otro-modelo"
    with pytest.raises(ApuntesNoIndexados, match="otro-modelo"):
        ApuntesRetriever(client, other, collection)
