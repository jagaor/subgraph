import csv
import json
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table

from src.models import SubdomainRecord


class ReportBuilder:
    """Construye la salida consolidada en formato tabla, JSON o CSV.

    No realiza peticiones de red ni resolución DNS: solo formatea los
    registros ya normalizados por el Merger.
    """

    @staticmethod
    def build(
        records: list[SubdomainRecord],
        fmt: str,
        output_path: Optional[str] = None,
    ) -> None:
        """Genera la salida segun el formato solicitado.

        - table: siempre se imprime en consola con rich. Si ademas se
          indica output_path, se guarda una copia en JSON.
        - json: se escribe en fichero si output_path no es None, si no en stdout.
        - csv: se escribe en fichero si output_path no es None, si no en stdout.
        """
        fmt_normalizado = fmt.lower().strip()

        if fmt_normalizado == "table":
            ReportBuilder._render_table(records)
            if output_path:
                ReportBuilder._write_json(records, output_path)
            return

        if fmt_normalizado == "json":
            payload = ReportBuilder._to_dicts(records)
            texto = json.dumps(payload, indent=2, ensure_ascii=False)
            if output_path:
                Path(output_path).write_text(texto + "\n", encoding="utf-8")
            else:
                sys.stdout.write(texto + "\n")
            return

        if fmt_normalizado == "csv":
            ReportBuilder._write_csv(records, output_path)
            return

        raise ValueError(f"Formato no soportado: {fmt!r}. Usa 'table', 'json' o 'csv'.")

    @staticmethod
    def _to_dicts(records: list[SubdomainRecord]) -> list[dict]:
        """Serializa los registros pydantic a diccionarios planos."""
        return [r.model_dump() for r in records]

    @staticmethod
    def _render_table(records: list[SubdomainRecord]) -> None:
        """Imprime una tabla rich con subdominio, fuentes y primer avistamiento."""
        tabla = Table(title="SubGraph — Subdominios consolidados")
        tabla.add_column("Subdominio", style="cyan", no_wrap=True)
        tabla.add_column("Fuentes", style="magenta")
        tabla.add_column("Primer visto", style="green")

        for rec in records:
            fuentes = ", ".join(rec.sources) if rec.sources else "-"
            primer_visto = rec.first_seen or "-"
            tabla.add_row(rec.fqdn, fuentes, primer_visto)

        Console().print(tabla)

    @staticmethod
    def _write_json(records: list[SubdomainRecord], output_path: str) -> None:
        """Escribe la representacion JSON en el fichero indicado."""
        payload = ReportBuilder._to_dicts(records)
        Path(output_path).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def _write_csv(records: list[SubdomainRecord], output_path: Optional[str]) -> None:
        """Escribe CSV con las columnas fqdn, sources y first_seen."""
        campos = ["fqdn", "sources", "first_seen"]
        destino = open(output_path, "w", newline="", encoding="utf-8") if output_path else sys.stdout
        try:
            writer = csv.DictWriter(destino, fieldnames=campos)
            writer.writeheader()
            for rec in records:
                writer.writerow(
                    {
                        "fqdn": rec.fqdn,
                        "sources": "|".join(rec.sources),
                        "first_seen": rec.first_seen or "",
                    }
                )
        finally:
            if output_path:
                destino.close()
