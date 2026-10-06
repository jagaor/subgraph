import logging

import httpx

from src.models import SubdomainRecord

logger = logging.getLogger(__name__)

CRT_URL = "https://crt.sh/"


async def fetch_crt(domain: str, client: httpx.AsyncClient) -> list[SubdomainRecord]:
    """Consulta crt.sh y devuelve los subdominios encontrados.

    crt.sh expone los certificados emitidos para un dominio en formato JSON.
    Consultamos el comodín %.{domain} para recoger también los subdominios
    cubiertos por certificados wildcard. No se realiza ninguna resolución DNS.
    """
    params = {"q": f"%.{domain}", "output": "json"}
    try:
        response = await client.get(CRT_URL, params=params)
        response.raise_for_status()
        payload = response.json()
    except httpx.RequestError as exc:
        logger.warning("crt.sh: error de red al consultar %s: %s", domain, exc)
        return []
    except ValueError as exc:
        logger.warning("crt.sh: respuesta no es JSON válido para %s: %s", domain, exc)
        return []

    if not isinstance(payload, list):
        logger.warning("crt.sh: formato inesperado para %s", domain)
        return []

    records: list[SubdomainRecord] = []
    for entry in payload:
        if not isinstance(entry, dict):
            continue
        name_value = entry.get("name_value")
        if not name_value:
            continue
        not_before = entry.get("not_before") or ""
        first_seen = not_before[:10] if not_before else None
        for raw in str(name_value).splitlines():
            fqdn = raw.strip().lower()
            if not fqdn:
                continue
            records.append(
                SubdomainRecord(fqdn=fqdn, sources=["crt"], first_seen=first_seen)
            )

    logger.info("crt.sh: %d registros crudos para %s", len(records), domain)
    return records
