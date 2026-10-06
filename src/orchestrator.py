import asyncio
import logging
from typing import List

import httpx
from rich.console import Console

from models import SubdomainRecord
from fetchers.crt_fetcher import CrtFetcher
from fetchers.rapid_fetcher import RapidFetcher
from fetchers.wayback_fetcher import WaybackFetcher
from merger import Merger

console = Console()
logger = logging.getLogger(__name__)


class Orchestrator:
    """Orquesta la ejecución de los fetchers pasivos y consolida resultados."""

    def __init__(self, domain: str, sources: List[str]) -> None:
        self.domain = domain
        self.sources = [s.lower() for s in sources]

    async def run(self) -> List[SubdomainRecord]:
        """Ejecuta los fetchers habilitados y devuelve la lista consolidada."""
        timeout = httpx.Timeout(15.0)
        headers = {"User-Agent": "SubGraph/1.0 (passive-recon)"}

        async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
            # Construir corutinas según fuentes habilitadas
            tasks = []
            if "crt" in self.sources:
                tasks.append(CrtFetcher(self.domain, client).fetch())
            if "rapid" in self.sources:
                tasks.append(RapidFetcher(self.domain, client).fetch())
            if "wayback" in self.sources:
                tasks.append(WaybackFetcher(self.domain, client).fetch())

            if not tasks:
                console.print("[yellow]No hay fuentes válidas seleccionadas.[/yellow]")
                return []

            # Ejecutar en paralelo, capturando excepciones individuales
            results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filtrar excepciones y aplanar resultados
        all_records: List[SubdomainRecord] = []
        for result in results:
            if isinstance(result, Exception):
                console.print(f"[red]Error en fetcher: {result}[/red]")
                logger.warning("Fetcher falló: %s", result, exc_info=True)
                continue
            if isinstance(result, list):
                all_records.extend(result)
            else:
                logger.warning("Resultado inesperado de fetcher: %r", result)

        # Consolidar mediante Merger
        merger = Merger()
        merged = merger.merge(all_records)
        return merged
