from __future__ import annotations

import re
from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class SourceEnum(str, Enum):
    """Fuentes de datos soportadas por SubGraph."""

    CRT = "crt"
    RAPID = "rapid"
    WAYBACK = "wayback"


# Patrón para validar FQDN de forma razonable (sin resolver DNS).
_FQDN_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)[a-z0-9-]{1,63}(?<!-)(\.(?!-)[a-z0-9-]{1,63}(?<!-))+$"
)


class SubdomainRecord(BaseModel):
    """Registro consolidado de un subdominio detectado por una o varias fuentes.

    No se realiza resolución DNS: el campo `fqdn` es únicamente texto normalizado.
    """

    model_config = {"str_strip_whitespace": True, "extra": "ignore"}

    # Si es True, se elimina el prefijo 'www.' del FQDN durante la normalización.
    strip_www: bool = Field(default=False, exclude=True)

    fqdn: str
    sources: list[SourceEnum] = Field(default_factory=list)
    first_seen: Optional[str] = None

    @field_validator("fqdn", mode="before")
    @classmethod
    def _normalize_fqdn(cls, value: object) -> object:
        """Normaliza el FQDN: minúsculas, sin wildcards y sin puntos sobrantes."""
        if not isinstance(value, str):
            return value
        v = value.strip().lower()
        # Elimina wildcards al inicio (p. ej. '*.api.dominio.com' -> 'api.dominio.com').
        v = re.sub(r"^(\*\.)+", "", v)
        # Elimina punto final (FQDN absoluto) y espacios residuales.
        v = v.rstrip(".")
        return v

    @field_validator("fqdn")
    @classmethod
    def _validate_fqdn(cls, value: str) -> str:
        """Valida que el valor resultante sea un FQDN sintácticamente válido."""
        if not _FQDN_RE.match(value):
            raise ValueError(f"FQDN inválido tras normalización: {value!r}")
        return value

    @field_validator("first_seen")
    @classmethod
    def _validate_first_seen(cls, value: Optional[str]) -> Optional[str]:
        """Acepta None o una fecha ISO (YYYY-MM-DD o ISO 8601 completo) y la normaliza."""
        if value is None:
            return None
        v = value.strip()
        if not v:
            return None
        try:
            if len(v) == 10:
                return date.fromisoformat(v).isoformat()
            return datetime.fromisoformat(v.replace("Z", "+00:00")).isoformat()
        except ValueError as exc:
            raise ValueError(f"first_seen no es una fecha ISO válida: {value!r}") from exc

    def merge_sources(self, other: "SubdomainRecord") -> "SubdomainRecord":
        """Fusiona fuentes y conserva el first_seen más antiguo entre dos registros."""
        merged_sources = sorted(set(self.sources) | set(other.sources), key=lambda s: s.value)
        candidates = [d for d in (self.first_seen, other.first_seen) if d]
        merged_first = min(candidates) if candidates else None
        return SubdomainRecord(
            fqdn=self.fqdn,
            sources=merged_sources,
            first_seen=merged_first,
            strip_www=self.strip_www,
        )
