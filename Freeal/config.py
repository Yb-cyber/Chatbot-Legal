import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = BASE_DIR / "uploads"

CKAN_API_BASE = "https://datos.gob.ar/api/3/action"
INDEC_BASE = "https://www.indec.gob.ar"
ANSES_BASE = "https://www.anses.gob.ar"
BOLETIN_OFICIAL_BASE = "https://www.boletinoficial.gob.ar"
AFIP_BASE = "https://www.afip.gob.ar"

DATA_CATEGORIES = {
    "seguridad_social": DATA_DIR / "seguridad_social",
    "mercado_laboral": DATA_DIR / "mercado_laboral",
    "impuestos": DATA_DIR / "impuestos",
    "legislacion": DATA_DIR / "legislacion",
}

CKAN_SEARCH_QUERIES = [
    "seguridad social",
    "ANSES",
    "prestaciones",
    "asignaciones familiares",
    "jubilaciones",
    "pensiones",
    "desempleo",
    "mercado laboral",
    "empleo",
    "salarios",
    "INDEC",
    "EPH",
    "encuesta permanente hogares",
    "impuestos",
    "monotributo",
    "autonomos",
    "AFIP",
    "ingresos publicos",
    "registro laboral",
    "relaciones laborales",
    "trabajo",
]

CKAN_ORGANIZATIONS = [
    "anses",
    "indec",
    "afip",
    "ministerio-de-trabajo",
    "ministerio-de-economia",
    "jefatura-de-gabinete",
]

MONOTRIBUTO_CATEGORIES = {
    "A": {"limite_facturacion": 7575000, "cuota_mensual": 15000},
    "B": {"limite_facturacion": 11362500, "cuota_mensual": 22000},
    "C": {"limite_facturacion": 15150000, "cuota_mensual": 30000},
    "D": {"limite_facturacion": 18937500, "cuota_mensual": 40000},
    "E": {"limite_facturacion": 22725000, "cuota_mensual": 50000},
    "F": {"limite_facturacion": 26512500, "cuota_mensual": 60000},
    "G": {"limite_facturacion": 30300000, "cuota_mensual": 70000},
    "H": {"limite_facturacion": 37875000, "cuota_mensual": 90000},
    "I": {"limite_facturacion": 45450000, "cuota_mensual": 110000},
    "J": {"limite_facturacion": 53025000, "cuota_mensual": 130000},
    "K": {"limite_facturacion": 60600000, "cuota_mensual": 150000},
}

AUTONOMOS_APORTES = {
    "minimo": 15000,
    "maximo": 150000,
    "base_calculo": 70000,
}

LEGISLACION_KEYWORDS = [
    "monotributo",
    "autonomos",
    "trabajo",
    "seguridad social",
    "empleo",
    "contrato",
    "prestaciones",
    "asignaciones",
    "jubilaciones",
    "pensiones",
    "desempleo",
    "AFIP",
    "ANSES",
    "INDEC",
    "relaciones laborales",
    "derecho laboral",
    "impuestos",
    "ingresos publicos",
    "registro mercantil",
    "sociedades",
    "contratos",
    "obligaciones",
    "sanciones",
    "procedimientos",
    "normativas",
    "resoluciones",
    "decretos",
    "leyes",
]
