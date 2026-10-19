"""Indexa los archivos de data/ en el RAG.

- Soporta csv/json/txt/md/xlsx/xls/pdf/docx/pptx
- Trocea textos largos para no saturar la ruta gratis de OpenRouter
- Primero un subset curado (INDEX_MAX_FILES), resto con full=True
"""

import json
import logging
import os
from pathlib import Path

import pandas as pd

from config import DATA_CATEGORIES

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

MAX_CHARS_PER_INSERT = 12000

CURATED_KEYWORDS = [
    "monotributo",
    "regimen",
    "prestacion",
    "asignacion",
    "jubilacion",
    "pension",
    "desempleo",
    "EPH",
    "empleo",
    "salario",
    "autonomo",
]


def _chunk_text(text: str, size: int = MAX_CHARS_PER_INSERT):
    text = text.strip()
    for i in range(0, len(text), size):
        yield text[i : i + size]


def extract_text_from_csv(file_path: Path) -> str:
    try:
        df = pd.read_csv(file_path, encoding="utf-8", errors="ignore")
        return df.to_string(index=False)
    except Exception as e:
        logger.warning(f"Error leyendo CSV {file_path.name}: {e}")
        return ""


def extract_text_from_json(file_path: Path) -> str:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return json.dumps(data, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Error leyendo JSON {file_path.name}: {e}")
        return ""


def extract_text_from_txt(file_path: Path) -> str:
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception as e:
        logger.warning(f"Error leyendo TXT {file_path.name}: {e}")
        return ""


def extract_text_from_xlsx(file_path: Path) -> str:
    try:
        df = pd.read_excel(file_path, engine="openpyxl")
        return df.to_string(index=False)
    except Exception as e:
        logger.warning(f"Error leyendo XLSX {file_path.name}: {e}")
        return ""


def extract_text_from_pdf(file_path: Path) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(file_path))
        return "\n".join((p.extract_text() or "") for p in reader.pages)
    except Exception as e:
        logger.warning(f"Error leyendo PDF {file_path.name}: {e}")
        return ""


def extract_text_from_docx(file_path: Path) -> str:
    try:
        import docx

        doc = docx.Document(str(file_path))
        return "\n".join(p.text for p in doc.paragraphs)
    except Exception as e:
        logger.warning(f"Error leyendo DOCX {file_path.name}: {e}")
        return ""


def extract_text_from_pptx(file_path: Path) -> str:
    try:
        from pptx import Presentation

        prs = Presentation(str(file_path))
        parts = []
        for slide in prs.slides:
            for shape in slide.shapes:
                if shape.has_text_frame:
                    parts.append(shape.text)
        return "\n".join(parts)
    except Exception as e:
        logger.warning(f"Error leyendo PPTX {file_path.name}: {e}")
        return ""


def extract_text(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    if suffix == ".csv":
        return extract_text_from_csv(file_path)
    if suffix == ".json":
        return extract_text_from_json(file_path)
    if suffix in (".txt", ".md"):
        return extract_text_from_txt(file_path)
    if suffix in (".xlsx", ".xls"):
        return extract_text_from_xlsx(file_path)
    if suffix == ".pdf":
        return extract_text_from_pdf(file_path)
    if suffix == ".docx":
        return extract_text_from_docx(file_path)
    if suffix == ".pptx":
        return extract_text_from_pptx(file_path)
    return ""


def _priority_score(name: str) -> int:
    lowered = name.lower()
    return sum(1 for kw in CURATED_KEYWORDS if kw.lower() in lowered)


def collect_files(full: bool = False, max_files: int = 100):
    all_files = []
    for category_dir in DATA_CATEGORIES.values():
        if not category_dir.exists():
            continue
        for fp in category_dir.glob("*"):
            if fp.is_file() and fp.name != "metadata.json":
                all_files.append(fp)
    if full:
        return all_files
    ranked = sorted(all_files, key=lambda p: _priority_score(p.name), reverse=True)
    return ranked[:max_files]


async def index_all_data(rag, full: bool = False, max_files: int = 100) -> dict:
    if not rag:
        return {"status": "error", "message": "RAG no inicializado"}

    files = collect_files(full=full, max_files=max_files)
    stats = {"total_files": len(files), "indexed": 0, "skipped": 0, "errors": 0}

    for i, file_path in enumerate(files, 1):
        try:
            text = extract_text(file_path)
            if not text or len(text.strip()) < 50:
                stats["skipped"] += 1
                continue
            for chunk in _chunk_text(text):
                if len(chunk.strip()) >= 50:
                    await rag.ainsert(chunk)
            stats["indexed"] += 1
            if i % 10 == 0:
                logger.info(f"Indexados {i}/{len(files)}...")
        except Exception as e:
            stats["errors"] += 1
            logger.error(f"Error indexando {file_path.name}: {e}")

    logger.info(f"Indexación completa: {stats}")
    return stats


def run_indexing(full: bool = False):
    import asyncio

    from rag_manager import get_rag, init_rag

    async def _run():
        rag = get_rag() or await init_rag()
        max_files = int(os.getenv("INDEX_MAX_FILES", "100"))
        return await index_all_data(rag, full=full, max_files=max_files)

    result = asyncio.run(_run())
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    run_indexing()
