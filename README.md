# Freeal — Asistente RAG Legal 

Sistema RAG local para consultas legales y tributarias 

## Requisitos

1. **Python 3.10+** (con entorno virtual `.venv`).
2. **Ollama** con los modelos locales:
   ```bash
   ollama pull llama3.2:3b
   ollama pull nomic-embed-text
   ```

## Inicio Rápido

1. **Activar entorno e instalar dependencias:**
   ```bash
   .\.venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Cargar dataset inicial de prueba (solo la primera vez):**
   ```bash
   # Genera e indexa monotributo y datos clave
   curl -X POST http://localhost:8000/update-data?minimal=true
   ```

3. **Iniciar servidor:**
   ```bash
   uvicorn main:app --reload
   ```
   Abre [http://localhost:8000](http://localhost:8000) en tu navegador.

## Tests

```bash
pytest tests/ -v
```






<img width="1917" height="978" alt="Captura de pantalla 2026-10-19 203927" src="https://github.com/user-attachments/assets/0566094b-65b7-43bd-a968-e8bbae21144f" />

