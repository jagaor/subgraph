import re
from typing import Optional

from src.models import SubdomainRecord


class Merger:
    """Consolida los registros devueltos por los distintos fetchers.

    Normaliza FQDN, elimina duplicados, unifica fuentes y conserva el
    first_seen mas antiguo disponible. No realiza ninguna operacion de red.
    """

    _WILDCARD_PREFIX = re.compile(r"^\*\.")
    _VALID_FQDN = re.compile(r"^[a-z0-9]([a-z0-9\-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9\-]{0,61}[a-z0-9])?)+$")

    @staticmethod
    def _normalize(fqdn: str) -> Optional[str]:
        """Devuelve el FQDN normalizado o None si no es valido."""
        if not fqdn:
            return None
        candidate = fqdn.strip().lower().rstrip(".")
        # Elimina el prefijo wildcard tipico de crt.sh ("*.dominio.com").
        candidate = Merger._WILDCARD_PREFIX.sub("", candidate)
        if not candidate or len(candidate) > 253:
            return None
        if not Merger._VALID_FQDN.match(candidate):
            return None
        return candidate

    @staticmethod
    def _oldest(a: Optional[str], b: Optional[str]) -> Optional[str]:
        """Devuelve la fecha ISO mas antigua ignorando valores None."""
        if a is None:
            return b
        if b is None:
            return a
        return a if a <= b else b

    @staticmethod
    def merge(records: list[SubdomainRecord]) -> list[SubdomainRecord]:
        """Fusiona registros por FQDN normalizado.

        Para cada FQDN repetido une las fuentes (sin duplicados) y conserva
        el first_seen mas antiguo. Ordena por numero de fuentes descendente
        y, a igualdad, alfabeticamente por FQDN.
        """
        index: dict[str, SubdomainRecord] = {}

        for record in records:
            fqdn = Merger._normalize(record.fqdn)
            if fqdn is None:
                continue

            existing = index.get(fqdn)
            if existing is None:
                index[fqdn] = SubdomainRecord(
                    fqdn=fqdn,
                    sources=sorted(set(record.sources or [])),
                    first_seen=record.first_seen,
                )
                continue

            merged_sources = sorted(set(existing.sources) | set(record.sources or []))
            existing.sources = merged_sources
            existing.first_seen = Merger._oldest(existing.first_seen, record.first_seen)

        return sorted(index.values(), key=lambda r: (-len(r.sources), r.fqdn))
