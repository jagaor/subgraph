"""Fetcher pasivo basado en Wayback Machine CDX API.

Consulta el índice histórico de Wayback Machine para descubrir subdominios
que hayan aparecido en URLs archivadas. No se realiza ninguna petición
contra el dominio objetivo.
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

import httpx

from src.models import SubdomainRecord

logger = logging.getLogger(__name__)

CDX_ENDPOINT = "http://web.archive.org/cdx/search/cdx"
SOURCE_NAME = "wayback"


def _format_timestamp(raw: str) -> str | None:
    """Convierte un timestamp CDX (YYYYMMDDhhmmss) a YYYY-MM-DD."""
    if not raw or len(raw) < 8:
        return None
    return f"{raw[0:4]}-{raw[4:6]}-{raw[6:8]}"


async def fetch_wayback(domain: str, client: httpx.AsyncClient) -> list[SubdomainRecord]:
    """Recupera subdominios históricos desde Wayback Machine CDX API.

    Devuelve una lista de SubdomainRecord con source='wayback'. Ante
    cualquier error de red o parseo se retorna una lista vacía para no
    romper la orquestación paralela.
    """
    params: dict[str, Any] = {
        "url": f"*.{domain}",
        "output": "json",
        "fl": "original,timestamp",
        "collapse": "urlkey",
        "limit": 5000,
    }

    try:
        response = await client.get(CDX_ENDPOINT, params=params)
        response.raise_for_status()
        rows = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Wayback fetcher falló para %s: %s", domain, exc)
        return []

    if not isinstance(rows, list) or len(rows) < 2:
        return []

    # La primera fila contiene los nombres de columna, se descarta.
    records: dict[str, SubdomainRecord] = {}
    for row in rows[1:]:
        if not isinstance(row, list) or len(row) < 2:
            continue
        original, timestamp = row[0], row[1]
        hostname = urlparse(original).hostname
        if not hostname:
            continue
        hostname = hostname.lower().strip(".")
        if hostname == domain or not hostname.endswith(f".{domain}"):
            continue
        first_seen = _format_timestamp(timestamp)
        existing = records.get(hostname)
        if existing is None:
            records[hostname] = SubdomainRecord(
                fqdn=hostname,
                sources=[SOURCE_NAME],
                first_seen=first_seen,
            )
        elif first_seen and (existing.first_seen is None or first_seen < existing.first_seen):
            existing.first_seen = first_seen

    logger.info("Wayback: %d subdominios únicos para %s", len(records), domain)
    return list(records.values())
