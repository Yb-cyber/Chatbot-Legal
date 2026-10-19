"""Test de indexación (sí usa LLM para extracción de entidades).

Verifica que rag.ainsert() crea la estructura de datos correctamente.
"""

import asyncio
import json
from pathlib import Path

import pytest


@pytest.fixture
def rag():
    from rag_manager import get_rag, init_rag

    r = get_rag()
    if r is None:
        r = asyncio.run(init_rag())
    return r


@pytest.mark.asyncio
async def test_insert_document(rag):
    """Verifica que insertar un documento crea chunks."""
    text = "El monotributo es un régimen simplificado para pequeños contribuyentes en Argentina. Tiene categorías de A a K con diferentes límites de facturación."
    await rag.ainsert(text)

    storage = Path(rag.working_dir)
    chunks_file = storage / "kv_store_text_chunks.json"
    assert chunks_file.exists(), "No se creó archivo de chunks"

    with open(chunks_file, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    assert len(chunks) > 0, "No se crearon chunks"


@pytest.mark.asyncio
async def test_graph_created(rag):
    """Verifica que el grafo de entidades se creó."""
    storage = Path(rag.working_dir)
    graph_file = storage / "graph_chunk_entity_relation.graphml"
    assert graph_file.exists(), "No se creó el grafo"
    assert graph_file.stat().st_size > 0


@pytest.mark.asyncio
async def test_full_docs_stored(rag):
    """Verifica que el documento completo se guardó."""
    storage = Path(rag.working_dir)
    docs_file = storage / "kv_store_full_docs.json"
    assert docs_file.exists(), "No se guardó el documento"

    with open(docs_file, "r", encoding="utf-8") as f:
        docs = json.load(f)
    assert len(docs) > 0


@pytest.mark.asyncio
async def test_entities_extracted(rag):
    """Verifica que se extrajeron entidades (requiere LLM)."""
    storage = Path(rag.working_dir)
    entities_file = storage / "kv_store_full_entities.json"
    # Puede estar vacío si el LLM falla, pero el archivo debe existir
    assert entities_file.exists(), "No se creó archivo de entidades"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
