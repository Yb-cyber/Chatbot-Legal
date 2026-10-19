# Tests del Sistema RAG Freeal

Tests que verifican el sistema **sin depender del LLM** (solo embeddings + recuperación).

## Requisitos

1. Servidor corriendo: `uvicorn main:app --port 8000`
2. Datos indexados: `POST /update-data?minimal=true`
3. Dependencias: `pip install pytest pytest-asyncio`

## Ejecutar

```bash
# Todos los tests
pytest tests/ -v

# Solo tests sin LLM (solo embeddings + recuperación)
pytest tests/test_embeddings.py tests/test_recuperacion.py -v

# Tests de API (no requieren datos indexados para /health)
pytest tests/test_api.py -v

# Test específico
pytest tests/test_recuperacion.py::test_query_monotributo -v
```

## Qué verifica cada test

| Archivo | Verifica | ¿Usa LLM? |
|---------|----------|-----------|
| `test_embeddings.py` | OpenRouter embeddings responde, dim=2048, similitud | No (solo embeddings) |
| `test_recuperacion.py` | Búsqueda vectorial recupera chunks relevantes | No (`only_need_context=True`) |
| `test_api.py` | Endpoints HTTP responden | No |
| `test_indexacion.py` | Indexación crea grafo/chunks/entidades | Sí (entidades requieren LLM) |

## Resultado esperado

```
tests/test_embeddings.py::test_embedding_dimension PASSED
tests/test_embeddings.py::test_embedding_similarity PASSED
tests/test_recuperacion.py::test_query_monotributo PASSED
tests/test_api.py::test_health PASSED
```

## Nota

Los tests de recuperación usan `only_need_context=True` para evitar llamar
al LLM. Esto verifica embeddings + búsqueda vectorial, que es la parte del
sistema que debe funcionar de forma consistente.
