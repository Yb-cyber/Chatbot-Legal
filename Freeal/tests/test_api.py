"""Test de endpoints HTTP sin LLM.

Verifica que la API responde correctamente sin llamar al LLM.
Requiere que el servidor esté corriendo en localhost:8000.
"""

import requests


BASE_URL = "http://localhost:8000"


def test_health():
    """Verifica que el servidor responde."""
    r = requests.get(f"{BASE_URL}/health", timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "healthy"
    assert data["rag_initialized"] is True


def test_data_status():
    """Verifica que hay datos indexados."""
    r = requests.get(f"{BASE_URL}/data-status", timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert data["total_files"] > 0, "No hay archivos indexados"


def test_query_only_context():
    """Verifica /query con only_need_context=true (sin LLM)."""
    r = requests.post(
        f"{BASE_URL}/query",
        json={
            "question": "monotributo",
            "mode": "naive",
            "only_need_context": True,
        },
        timeout=60,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["context"] is not None, "No se recuperó contexto"
    assert len(data["context"]) > 0


def test_list_categories():
    """Verifica que las categorías responden."""
    for cat in ["seguridad_social", "mercado_laboral", "impuestos"]:
        r = requests.get(f"{BASE_URL}/data/{cat}", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert "files" in data


def test_invalid_category():
    """Verifica manejo de categoría inválida."""
    r = requests.get(f"{BASE_URL}/data/invalid_category", timeout=10)
    assert r.status_code == 400


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
