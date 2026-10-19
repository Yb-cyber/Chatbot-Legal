"""Fixtures compartidas para los tests."""

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="session")
def rag():
    from rag_manager import get_rag, init_rag

    r = get_rag()
    if r is None:
        r = asyncio.run(init_rag())
    return r


@pytest.fixture
def sample_text():
    return (
        "El monotributo es un régimen simplificado para pequeños contribuyentes "
        "en Argentina. Tiene categorías de A a K con diferentes límites de "
        "facturación y cuotas mensuales. La categoría A tiene un límite de "
        "$7.575.000 anuales y una cuota de $15.000 mensuales."
    )


@pytest.fixture
def rag_storage_files():
    from rag_manager import get_config

    storage = Path(get_config()["working_dir"])
    return {
        "graph": storage / "graph_chunk_entity_relation.graphml",
        "chunks": storage / "kv_store_text_chunks.json",
        "entities": storage / "kv_store_full_entities.json",
        "relations": storage / "kv_store_full_relations.json",
        "docs": storage / "kv_store_full_docs.json",
    }
