import html
import re
from typing import List

import httpx

from src.models import SubdomainRecord

# Endpoint público de RapidDNS para enumeración pasiva de subdominios
RAPID_BASE_URL = "https://rapiddns.io/subdomain/{domain}?full=1"

# Patrón genérico de FQDN dentro del HTML. Se restringe después al dominio objetivo.
FQDN_PATTERN = re.compile(r"[a-zA-Z0-9_](?:[a-zA-Z0-9_-]{0,61}[a-zA-Z0-9_])?(?:\.[a-zA-Z0-9_](?:[a-zA-Z0-9_-]{0,61}[a-zA-Z0-9_])?)+")

# Cabecera de navegador para evitar bloqueos triviales del scraping
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) SubGraph/1.0",
    "Accept": "text/html,application/xhtml+xml",
}


def _extract_fqdns(body: str, domain: str) -> List[str]:
    """Extrae FQDN válidos del HTML, filtrando por el dominio objetivo."""
    # Desescapamos entidades HTML para normalizar el contenido de las celdas <td>
    text = html.unescape(body)
    domain = domain.strip().lower().lstrip(".")
    suffix = "." + domain
    found = set()
    for candidate in FQDN_PATTERN.findall(text):
        fqdn = candidate.strip().strip(".").lower()
        # Solo aceptamos el dominio raíz o subdominios reales del objetivo
        if fqdn == domain or fqdn.endswith(suffix):
            found.add(fqdn)
    return sorted(found)


async def fetch_rapid(domain: str, client: httpx.AsyncClient) -> List[SubdomainRecord]:
    """Consulta RapidDNS y devuelve los subdominios detectados.

    No realiza resolución DNS ni contacta con el objetivo: solo consulta el
    agregador público. Ante cualquier fallo de red devuelve lista vacía.
    """
    url = RAPID_BASE_URL.format(domain=domain)
    try:
        response = await client.get(url, headers=DEFAULT_HEADERS, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError:
        # Fallo de transporte, timeout o código de estado no exitoso
        return []

    fqdns = _extract_fqdns(response.text, domain)
    return [
        SubdomainRecord(fqdn=fqdn, sources=["rapid"], first_seen=None)
        for fqdn in fqdns
    ]
