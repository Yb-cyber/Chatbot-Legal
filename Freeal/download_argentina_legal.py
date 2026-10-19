import asyncio
import hashlib
import json
import logging
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import aiohttp
import pandas as pd
from bs4 import BeautifulSoup

from config import (
    AFIP_BASE,
    ANSES_BASE,
    AUTONOMOS_APORTES,
    BOLETIN_OFICIAL_BASE,
    CKAN_API_BASE,
    CKAN_ORGANIZATIONS,
    CKAN_SEARCH_QUERIES,
    DATA_CATEGORIES,
    DATA_DIR,
    INDEC_BASE,
    LEGISLACION_KEYWORDS,
    MONOTRIBUTO_CATEGORIES,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

METADATA_FILE = DATA_DIR / "metadata.json"


def ensure_directories():
    DATA_DIR.mkdir(exist_ok=True)
    for category_dir in DATA_CATEGORIES.values():
        category_dir.mkdir(exist_ok=True)


def load_metadata() -> Dict[str, Any]:
    if METADATA_FILE.exists():
        with open(METADATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"last_update": None, "downloads": {}}


def save_metadata(metadata: Dict[str, Any]):
    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)


def compute_file_hash(filepath: Path) -> str:
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


async def fetch_json(session: aiohttp.ClientSession, url: str, **kwargs) -> Optional[Dict]:
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30), **kwargs) as response:
            if response.status == 200:
                return await response.json(content_type=None)
            logger.warning(f"HTTP {response.status} for {url}")
            return None
    except Exception as e:
        logger.error(f"Error fetching {url}: {e}")
        return None


async def fetch_text(session: aiohttp.ClientSession, url: str, **kwargs) -> Optional[str]:
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30), **kwargs) as response:
            if response.status == 200:
                return await response.text()
            logger.warning(f"HTTP {response.status} for {url}")
            return None
    except Exception as e:
        logger.error(f"Error fetching {url}: {e}")
        return None


async def download_file(session: aiohttp.ClientSession, url: str, destination: Path) -> bool:
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=120)) as response:
            if response.status == 200:
                with open(destination, "wb") as f:
                    async for chunk in response.content.iter_chunked(8192):
                        f.write(chunk)
                logger.info(f"Downloaded: {destination.name}")
                return True
            logger.warning(f"HTTP {response.status} for {url}")
            return False
    except Exception as e:
        logger.error(f"Error downloading {url}: {e}")
        return False


async def search_ckan_datasets(session: aiohttp.ClientSession, query: str, rows: int = 20) -> List[Dict]:
    url = f"{CKAN_API_BASE}/package_search"
    params = {"q": query, "rows": rows}
    result = await fetch_json(session, url, params=params)
    if result and result.get("success"):
        return result["result"].get("results", [])
    return []


async def get_ckan_organization_datasets(session: aiohttp.ClientSession, org: str, limit: int = 100) -> List[Dict]:
    url = f"{CKAN_API_BASE}/package_search"
    params = {"q": f"organization:{org}", "rows": limit}
    result = await fetch_json(session, url, params=params)
    if result and result.get("success"):
        return result["result"].get("results", [])
    return []


async def download_ckan_resources(
    session: aiohttp.ClientSession,
    dataset: Dict,
    destination_dir: Path,
    metadata: Dict[str, Any],
    max_resources: Optional[int] = None,
):
    resources = dataset.get("resources", [])
    if max_resources is not None:
        resources = resources[:max_resources]
    dataset_title = dataset.get("title", "unknown")
    dataset_id = dataset.get("name", "unknown")

    for resource in resources:
        resource_url = resource.get("url", "")
        resource_format = resource.get("format", "").upper()
        resource_name = resource.get("name", resource_url.split("/")[-1] if resource_url else "unknown")

        if not resource_url:
            continue

        safe_name = re.sub(r"[^\w\-.]", "_", resource_name)
        if not safe_name or safe_name == "_":
            safe_name = f"resource_{int(time.time())}"

        if resource_format in ["CSV", "XLSX", "XLS", "JSON", "XML", "TXT", "PDF"]:
            ext = resource_format.lower() if resource_format != "XLSX" else "xlsx"
            if not safe_name.endswith(f".{ext}"):
                safe_name = f"{safe_name}.{ext}"

            destination = destination_dir / safe_name

            success = await download_file(session, resource_url, destination)
            if success:
                file_hash = compute_file_hash(destination)
                metadata["downloads"][str(destination.relative_to(DATA_DIR))] = {
                    "source": resource_url,
                    "dataset": dataset_title,
                    "dataset_id": dataset_id,
                    "format": resource_format,
                    "size": destination.stat().st_size,
                    "hash": file_hash,
                    "downloaded_at": datetime.now().isoformat(),
                }


async def download_seguridad_social(session: aiohttp.ClientSession, metadata: Dict[str, Any], test_mode: bool = False):
    logger.info("Downloading seguridad social data...")
    dest_dir = DATA_CATEGORIES["seguridad_social"]

    queries = ["ANSES", "seguridad social", "prestaciones", "asignaciones familiares", "jubilaciones", "pensiones", "desempleo"]
    if test_mode:
        queries = queries[:2]
    downloaded_datasets = set()
    rows = 5 if test_mode else 30

    for query in queries:
        datasets = await search_ckan_datasets(session, query, rows=rows)
        for dataset in datasets:
            dataset_id = dataset.get("name")
            if dataset_id in downloaded_datasets:
                continue
            downloaded_datasets.add(dataset_id)
            await download_ckan_resources(session, dataset, dest_dir, metadata, max_resources=2 if test_mode else None)
        await asyncio.sleep(0.3 if test_mode else 0.5)

    orgs = ["anses"] if test_mode else ["anses", "ministerio-de-trabajo"]
    for org in orgs:
        datasets = await get_ckan_organization_datasets(session, org, limit=5 if test_mode else 100)
        for dataset in datasets:
            dataset_id = dataset.get("name")
            if dataset_id in downloaded_datasets:
                continue
            downloaded_datasets.add(dataset_id)
            await download_ckan_resources(session, dataset, dest_dir, metadata, max_resources=2 if test_mode else None)
        await asyncio.sleep(0.3 if test_mode else 0.5)

    monotributo_data = {
        "fuente": "AFIP/ARCA - Resolución General 5227/2023",
        "descripcion": "Categorías del Monotributo - Límites de facturación y cuotas mensuales",
        "fecha_actualizacion": datetime.now().isoformat(),
        "categorias": MONOTRIBUTO_CATEGORIES,
        "aportes_autonomos": AUTONOMOS_APORTES,
        "nota": "Los valores son aproximados y deben verificarse con la normativa vigente",
    }

    monotributo_file = dest_dir / "monotributo_categorias.json"
    with open(monotributo_file, "w", encoding="utf-8") as f:
        json.dump(monotributo_data, f, indent=2, ensure_ascii=False)

    metadata["downloads"][str(monotributo_file.relative_to(DATA_DIR))] = {
        "source": "AFIP/ARCA",
        "dataset": "Monotributo Categorías",
        "format": "JSON",
        "size": monotributo_file.stat().st_size,
        "hash": compute_file_hash(monotributo_file),
        "downloaded_at": datetime.now().isoformat(),
    }

    logger.info(f"Seguridad social: {len(downloaded_datasets)} datasets processed")


async def download_mercado_laboral(session: aiohttp.ClientSession, metadata: Dict[str, Any], test_mode: bool = False):
    logger.info("Downloading mercado laboral data...")
    dest_dir = DATA_CATEGORIES["mercado_laboral"]

    queries = ["INDEC", "EPH", "encuesta permanente hogares", "empleo", "salarios", "mercado laboral", "actividad economica"]
    if test_mode:
        queries = queries[:2]
    downloaded_datasets = set()
    rows = 5 if test_mode else 30

    for query in queries:
        datasets = await search_ckan_datasets(session, query, rows=rows)
        for dataset in datasets:
            dataset_id = dataset.get("name")
            if dataset_id in downloaded_datasets:
                continue
            downloaded_datasets.add(dataset_id)
            await download_ckan_resources(session, dataset, dest_dir, metadata, max_resources=2 if test_mode else None)
        await asyncio.sleep(0.3 if test_mode else 0.5)

    orgs = ["indec"] if test_mode else ["indec", "ministerio-de-trabajo"]
    for org in orgs:
        datasets = await get_ckan_organization_datasets(session, org, limit=5 if test_mode else 100)
        for dataset in datasets:
            dataset_id = dataset.get("name")
            if dataset_id in downloaded_datasets:
                continue
            downloaded_datasets.add(dataset_id)
            await download_ckan_resources(session, dataset, dest_dir, metadata, max_resources=2 if test_mode else None)
        await asyncio.sleep(0.3 if test_mode else 0.5)

    indec_data = {
        "fuente": "INDEC",
        "descripcion": "Principales indicadores del mercado laboral argentino",
        "fecha_actualizacion": datetime.now().isoformat(),
        "indicadores": {
            "tasa_actividad": "Porcentaje de personas en edad de trabajar que están ocupadas o buscan empleo",
            "tasa_empleo": "Porcentaje de personas en edad de trabajar que están ocupadas",
            "tasa_desempleo": "Porcentio de personas en la fuerza de trabajo que están desocupadas",
            "tasa_subempleo": "Porcentaje de ocupados que trabajan menos de 35 horas semanales y desean trabajar más",
        },
        "nota": "Los valores específicos deben consultarse en los datasets descargados",
    }

    indec_file = dest_dir / "indicadores_mercado_laboral.json"
    with open(indec_file, "w", encoding="utf-8") as f:
        json.dump(indec_data, f, indent=2, ensure_ascii=False)

    metadata["downloads"][str(indec_file.relative_to(DATA_DIR))] = {
        "source": "INDEC",
        "dataset": "Indicadores Mercado Laboral",
        "format": "JSON",
        "size": indec_file.stat().st_size,
        "hash": compute_file_hash(indec_file),
        "downloaded_at": datetime.now().isoformat(),
    }

    logger.info(f"Mercado laboral: {len(downloaded_datasets)} datasets processed")


async def download_impuestos(session: aiohttp.ClientSession, metadata: Dict[str, Any], test_mode: bool = False):
    logger.info("Downloading impuestos data...")
    dest_dir = DATA_CATEGORIES["impuestos"]

    queries = ["impuestos", "AFIP", "ingresos publicos", "monotributo", "autonomos", "tributos", "fiscal"]
    if test_mode:
        queries = queries[:2]
    downloaded_datasets = set()
    rows = 5 if test_mode else 30

    for query in queries:
        datasets = await search_ckan_datasets(session, query, rows=rows)
        for dataset in datasets:
            dataset_id = dataset.get("name")
            if dataset_id in downloaded_datasets:
                continue
            downloaded_datasets.add(dataset_id)
            await download_ckan_resources(session, dataset, dest_dir, metadata, max_resources=2 if test_mode else None)
        await asyncio.sleep(0.3 if test_mode else 0.5)

    orgs = ["afip"] if test_mode else ["afip", "ministerio-de-economia"]
    for org in orgs:
        datasets = await get_ckan_organization_datasets(session, org, limit=5 if test_mode else 100)
        for dataset in datasets:
            dataset_id = dataset.get("name")
            if dataset_id in downloaded_datasets:
                continue
            downloaded_datasets.add(dataset_id)
            await download_ckan_resources(session, dataset, dest_dir, metadata, max_resources=2 if test_mode else None)
        await asyncio.sleep(0.3 if test_mode else 0.5)

    impuestos_data = {
        "fuente": "AFIP/ARCA",
        "descripcion": "Regímenes tributarios para freelancers y autónomos en Argentina",
        "fecha_actualizacion": datetime.now().isoformat(),
        "regimenes": {
            "monotributo": {
                "descripcion": "Régimen simplificado para pequeños contribuyentes",
                "categorias": list(MONOTRIBUTO_CATEGORIES.keys()),
                "limite_facturacion_anual": "Hasta $60.600.000 (2024)",
                "cuota_mensual": "Varía según categoría ($15.000 - $150.000 aprox)",
                "obligaciones": ["Facturación mensual", "Pago de cuota mensual", "Declaración jurada anual"],
            },
            "autonomos": {
                "descripcion": "Régimen general para trabajadores autónomos",
                "aportes": AUTONOMOS_APORTES,
                "obligaciones": ["Inscripción en AFIP", "Aportes a seguridad social", "Facturación", "Declaraciones juradas"],
            },
            "responsable_inscripto": {
                "descripcion": "Régimen general para empresas y profesionales",
                "obligaciones": ["IVA", "Ganancias", "Bienes personales", "Aportes"],
            },
        },
        "nota": "Los valores son aproximados y deben verificarse con la normativa vigente",
    }

    impuestos_file = dest_dir / "regimenes_tributarios.json"
    with open(impuestos_file, "w", encoding="utf-8") as f:
        json.dump(impuestos_data, f, indent=2, ensure_ascii=False)

    metadata["downloads"][str(impuestos_file.relative_to(DATA_DIR))] = {
        "source": "AFIP/ARCA",
        "dataset": "Regímenes Tributarios",
        "format": "JSON",
        "size": impuestos_file.stat().st_size,
        "hash": compute_file_hash(impuestos_file),
        "downloaded_at": datetime.now().isoformat(),
    }

    logger.info(f"Impuestos: {len(downloaded_datasets)} datasets processed")


async def download_legislacion(session: aiohttp.ClientSession, metadata: Dict[str, Any], test_mode: bool = False):
    logger.info("Downloading legislacion data...")
    dest_dir = DATA_CATEGORIES["legislacion"]

    if test_mode:
        logger.info("Test mode: saltando Boletín Oficial (scraping inestable)")

    queries = ["leyes", "decretos", "resoluciones", "monotributo", "autonomos", "seguridad social", "trabajo", "AFIP", "ANSES"]
    if test_mode:
        queries = queries[:2]
    downloaded_datasets = set()
    rows = 5 if test_mode else 20

    for query in queries:
        datasets = await search_ckan_datasets(session, query, rows=rows)
        for dataset in datasets:
            dataset_id = dataset.get("name")
            if dataset_id in downloaded_datasets:
                continue
            downloaded_datasets.add(dataset_id)
            await download_ckan_resources(session, dataset, dest_dir, metadata, max_resources=2 if test_mode else None)
        await asyncio.sleep(0.3 if test_mode else 0.5)

    boletin_url = f"{BOLETIN_OFICIAL_BASE}/seccion/primera"
    html = await fetch_text(session, boletin_url)
    if html:
        soup = BeautifulSoup(html, "html.parser")
        leyes = []

        for link in soup.find_all("a", href=True):
            href = link["href"]
            text = link.get_text(strip=True)
            if any(keyword in text.lower() for keyword in LEGISLACION_KEYWORDS):
                full_url = urljoin(BOLETIN_OFICIAL_BASE, href)
                leyes.append({"titulo": text, "url": full_url})

        boletin_data = {
            "fuente": "Boletín Oficial de la República Argentina",
            "descripcion": "Normativas publicadas en el Boletín Oficial",
            "fecha_actualizacion": datetime.now().isoformat(),
            "normativas": leyes[:100],
        }

        boletin_file = dest_dir / "boletin_oficial_normativas.json"
        with open(boletin_file, "w", encoding="utf-8") as f:
            json.dump(boletin_data, f, indent=2, ensure_ascii=False)

        metadata["downloads"][str(boletin_file.relative_to(DATA_DIR))] = {
            "source": BOLETIN_OFICIAL_BASE,
            "dataset": "Boletín Oficial Normativas",
            "format": "JSON",
            "size": boletin_file.stat().st_size,
            "hash": compute_file_hash(boletin_file),
            "downloaded_at": datetime.now().isoformat(),
        }

    logger.info(f"Legislacion: {len(downloaded_datasets)} datasets processed")


def _generate_local_json_files(metadata: Dict[str, Any]):
    dest_dir = DATA_CATEGORIES["seguridad_social"]
    monotributo_data = {
        "fuente": "AFIP/ARCA",
        "descripcion": "Categorías del Monotributo",
        "fecha_actualizacion": datetime.now().isoformat(),
        "categorias": MONOTRIBUTO_CATEGORIES,
        "aportes_autonomos": AUTONOMOS_APORTES,
        "nota": "Valores aproximados de referencia para pruebas",
    }
    monotributo_file = dest_dir / "monotributo_categorias.json"
    with open(monotributo_file, "w", encoding="utf-8") as f:
        json.dump(monotributo_data, f, indent=2, ensure_ascii=False)
    metadata["downloads"][str(monotributo_file.relative_to(DATA_DIR))] = {
        "source": "AFIP/ARCA", "dataset": "Monotributo", "format": "JSON",
        "size": monotributo_file.stat().st_size, "hash": compute_file_hash(monotributo_file),
        "downloaded_at": datetime.now().isoformat(),
    }

    impuestos_dir = DATA_CATEGORIES["impuestos"]
    regimenes_data = {
        "fuente": "AFIP/ARCA",
        "descripcion": "Regímenes tributarios para freelancers",
        "fecha_actualizacion": datetime.now().isoformat(),
        "regimenes": {
            "monotributo": {
                "descripcion": "Régimen simplificado para pequeños contribuyentes",
                "categorias": list(MONOTRIBUTO_CATEGORIES.keys()),
                "obligaciones": ["Facturación mensual", "Pago de cuota mensual"],
            },
            "autonomos": {
                "descripcion": "Régimen general para trabajadores autónomos",
                "obligaciones": ["Inscripción AFIP", "Aportes seguridad social", "Facturación"],
            },
        },
        "nota": "Información de referencia para pruebas",
    }
    regimenes_file = impuestos_dir / "regimenes_tributarios.json"
    with open(regimenes_file, "w", encoding="utf-8") as f:
        json.dump(regimenes_data, f, indent=2, ensure_ascii=False)
    metadata["downloads"][str(regimenes_file.relative_to(DATA_DIR))] = {
        "source": "AFIP/ARCA", "dataset": "Regímenes Tributarios", "format": "JSON",
        "size": regimenes_file.stat().st_size, "hash": compute_file_hash(regimenes_file),
        "downloaded_at": datetime.now().isoformat(),
    }

    mercado_dir = DATA_CATEGORIES["mercado_laboral"]
    indec_data = {
        "fuente": "INDEC",
        "descripcion": "Indicadores del mercado laboral argentino",
        "fecha_actualizacion": datetime.now().isoformat(),
        "indicadores": {
            "tasa_actividad": "Personas en edad de trabajar ocupadas o buscando empleo",
            "tasa_empleo": "Personas en edad de trabajar que están ocupadas",
            "tasa_desempleo": "Personas en la fuerza de trabajo desocupadas",
        },
        "nota": "Definiciones de referencia para pruebas",
    }
    indec_file = mercado_dir / "indicadores_mercado_laboral.json"
    with open(indec_file, "w", encoding="utf-8") as f:
        json.dump(indec_data, f, indent=2, ensure_ascii=False)
    metadata["downloads"][str(indec_file.relative_to(DATA_DIR))] = {
        "source": "INDEC", "dataset": "Indicadores Mercado Laboral", "format": "JSON",
        "size": indec_file.stat().st_size, "hash": compute_file_hash(indec_file),
        "downloaded_at": datetime.now().isoformat(),
    }


async def download_all(rag=None, full: bool = False, test_mode: bool = False, minimal: bool = False):
    import os as _os

    ensure_directories()
    metadata = load_metadata()

    if minimal:
        logger.info("MODO MINIMAL: sin descarga de red, solo archivos JSON locales")
        _generate_local_json_files(metadata)
        metadata["last_update"] = datetime.now().isoformat()
        save_metadata(metadata)
    else:
        async with aiohttp.ClientSession() as session:
            await download_seguridad_social(session, metadata, test_mode=test_mode)
            metadata["last_update"] = datetime.now().isoformat()
            save_metadata(metadata)

            await download_mercado_laboral(session, metadata, test_mode=test_mode)
            metadata["last_update"] = datetime.now().isoformat()
            save_metadata(metadata)

            await download_impuestos(session, metadata, test_mode=test_mode)
            metadata["last_update"] = datetime.now().isoformat()
            save_metadata(metadata)

            await download_legislacion(session, metadata, test_mode=test_mode)
            metadata["last_update"] = datetime.now().isoformat()
            save_metadata(metadata)

    total_files = len(metadata["downloads"])
    logger.info(f"Download complete. Total files: {total_files}")

    try:
        from index_data import index_all_data

        if rag is not None:
            max_files = int(_os.getenv("INDEX_MAX_FILES", "100"))
            logger.info("Starting automatic indexing of downloaded data...")
            index_stats = await index_all_data(
                rag, full=full, max_files=max_files
            )
            metadata["indexing"] = index_stats
            metadata["last_update"] = datetime.now().isoformat()
            save_metadata(metadata)
            logger.info(f"Indexing complete: {index_stats}")
        else:
            logger.warning("RAG no provisto. Descarga guardada sin indexar.")
    except Exception as e:
        logger.error(f"Error during indexing: {e}")

    return metadata


def download_only(full: bool = False, test_mode: bool = False, minimal: bool = False) -> Dict[str, Any]:
    """Síncrono: descarga archivos pero NO indexa. Para usar en executor thread."""
    ensure_directories()
    metadata = load_metadata()

    if minimal:
        _generate_local_json_files(metadata)
        metadata["last_update"] = datetime.now().isoformat()
        save_metadata(metadata)
        return metadata

    async def _dl():
        async with aiohttp.ClientSession() as session:
            await download_seguridad_social(session, metadata, test_mode=test_mode)
            metadata["last_update"] = datetime.now().isoformat()
            save_metadata(metadata)
            await download_mercado_laboral(session, metadata, test_mode=test_mode)
            metadata["last_update"] = datetime.now().isoformat()
            save_metadata(metadata)
            await download_impuestos(session, metadata, test_mode=test_mode)
            metadata["last_update"] = datetime.now().isoformat()
            save_metadata(metadata)
            await download_legislacion(session, metadata, test_mode=test_mode)
            metadata["last_update"] = datetime.now().isoformat()
            save_metadata(metadata)

    asyncio.run(_dl())
    return metadata


def run_download(rag=None, full: bool = False, test_mode: bool = False, minimal: bool = False):
    """Descarga + indexa. Usar solo en el event loop principal del servidor."""
    return asyncio.run(download_all(rag=rag, full=full, test_mode=test_mode, minimal=minimal))


if __name__ == "__main__":
    run_download()
