"""Test de embeddings OpenRouter sin LLM.

Verifica que la API de embeddings responde y la dimensión es correcta.
"""

import asyncio

import numpy as np
import pytest


@pytest.fixture
def rag():
    from rag_manager import get_rag, init_rag

    r = get_rag()
    if r is None:
        r = asyncio.run(init_rag())
    return r


@pytest.mark.asyncio
async def test_embedding_dimension(rag):
    """Verifica que el embedding tiene la dimensión configurada."""
    from rag_manager import get_config
    expected_dim = get_config()["embedding_dim"]
    emb = await rag.embedding_func(["hola mundo"])
    assert emb.shape == (1, expected_dim), f"Shape incorrecto: {emb.shape}"


@pytest.mark.asyncio
async def test_embedding_spanish(rag):
    """Verifica que funciona con texto en español."""
    from rag_manager import get_config
    expected_dim = get_config()["embedding_dim"]
    emb = await rag.embedding_func(["monotributo categoría A"])
    assert emb.shape == (1, expected_dim)
    assert emb[0][0] != 0, "Embedding vacío"


@pytest.mark.asyncio
async def test_embedding_similarity(rag):
    """Verifica que embeddings similares son cercanos."""
    emb1 = await rag.embedding_func(["monotributo"])
    emb2 = await rag.embedding_func(["monotributo AFIP"])
    emb3 = await rag.embedding_func(["fútbol argentino"])

    sim_1_2 = np.dot(emb1[0], emb2[0]) / (
        np.linalg.norm(emb1[0]) * np.linalg.norm(emb2[0])
    )
    sim_1_3 = np.dot(emb1[0], emb3[0]) / (
        np.linalg.norm(emb1[0]) * np.linalg.norm(emb3[0])
    )

    assert sim_1_2 > sim_1_3, "Embeddings similares deberían ser más cercanos"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
