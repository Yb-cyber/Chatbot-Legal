"""Test de recuperación sin LLM.

Verifica que la búsqueda vectorial funciona usando only_need_context=True,
lo que evita llamar al LLM para generar respuestas.
"""

import asyncio

import pytest
from lightrag import QueryParam


@pytest.fixture
def rag():
    from rag_manager import get_rag, init_rag

    r = get_rag()
    if r is None:
        r = asyncio.run(init_rag())
    return r


@pytest.mark.asyncio
async def test_query_monotributo(rag):
    """Verifica que se recupera contexto sobre monotributo."""
    ctx = await rag.aquery(
        "monotributo", param=QueryParam(mode="naive", only_need_context=True)
    )
    assert ctx is not None, "No se recuperó contexto"
    assert len(str(ctx)) > 0, "Contexto vacío"
    assert (
        "monotributo" in str(ctx).lower()
        or "categoría" in str(ctx).lower()
        or "cuota" in str(ctx).lower()
    ), f"Contexto no relevante: {str(ctx)[:200]}"


@pytest.mark.asyncio
async def test_query_categoria_a(rag):
    """Verifica recuperación de categoría A."""
    ctx = await rag.aquery(
        "categoría A monotributo",
        param=QueryParam(mode="naive", only_need_context=True),
    )
    assert ctx is not None
    assert len(str(ctx)) > 50, f"Contexto muy corto: {str(ctx)}"


@pytest.mark.asyncio
async def test_query_sin_resultados(rag):
    """Verifica que una query vacía no rompe el sistema."""
    ctx = await rag.aquery(
        "xyz123noexiste",
        param=QueryParam(mode="naive", only_need_context=True),
    )
    # Puede retornar None o vacío, pero no debe romper
    assert ctx is None or isinstance(ctx, str)


@pytest.mark.asyncio
async def test_recuperacion_hibrida(rag):
    """Verifica recuperación con modo hybrid sin LLM."""
    ctx = await rag.aquery(
        "prestaciones seguridad social",
        param=QueryParam(mode="hybrid", only_need_context=True),
    )
    assert ctx is not None
    assert len(str(ctx)) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
