#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Punto de entrada CLI de SubGraph.

Autor: Javier Garrido Ortiz

Expone dos subcomandos:
  - recon   : ejecuta la enumeración pasiva cruzando las fuentes seleccionadas.
  - sources : lista las fuentes disponibles con su URL base y descripción.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from typing import List

import httpx
from rich.console import Console
from rich.table import Table

from src.orchestrator import Orchestrator
from src.report import ReportBuilder

__version__ = "0.1.0"
TOOL_NAME = "SubGraph"

console = Console()

# Catálogo estático de fuentes disponibles. La clave se usa en --sources.
SOURCES_CATALOG = [
    ("crt", "https://crt.sh", "Certificate Transparency logs (crt.sh API JSON)."),
    ("rapid", "https://rapiddns.io", "RapidDNS subdomain listing (HTML/JSON pasivo)."),
    ("wayback", "http://web.archive.org/cdx", "Wayback Machine CDX API (URLs históricas)."),
]


def _build_parser() -> argparse.ArgumentParser:
    """Construye el parser principal con sus subcomandos."""
    parser = argparse.ArgumentParser(
        prog="subgraph",
        description="Enumeración pasiva de subdominios sin emitir tráfico al objetivo.",
    )
    parser.add_argument("--version", action="version", version=f"{TOOL_NAME} {__version__}")

    sub = parser.add_subparsers(dest="command", required=True)

    # Subcomando: recon
    p_recon = sub.add_parser("recon", help="Ejecuta la enumeración pasiva completa.")
    p_recon.add_argument("--domain", required=True, help="Dominio raíz a enumerar (ej: example.com).")
    p_recon.add_argument(
        "--sources",
        nargs="+",
        default=["crt", "rapid", "wayback"],
        choices=[s[0] for s in SOURCES_CATALOG],
        help="Fuentes a consultar (por defecto: todas).",
    )
    p_recon.add_argument("--output", default=None, help="Ruta del fichero de salida.")
    p_recon.add_argument(
        "--format",
        choices=["json", "csv", "table"],
        default="table",
        help="Formato de salida (por defecto: table).",
    )

    # Subcomando: sources
    sub.add_parser("sources", help="Lista las fuentes disponibles.")
    return parser


def _print_header() -> None:
    """Muestra la cabecera de la herramienta antes de empezar."""
    console.print(f"[bold cyan]{TOOL_NAME}[/bold cyan] [dim]v{__version__}[/dim]")
    console.print("[dim]Enumeración pasiva de subdominios — sin tráfico activo al objetivo.[/dim]\n")


def _cmd_sources() -> int:
    """Imprime la tabla de fuentes disponibles."""
    _print_header()
    table = Table(title="Fuentes disponibles", show_lines=False)
    table.add_column("Nombre", style="cyan", no_wrap=True)
    table.add_column("URL base", style="green")
    table.add_column("Descripción", style="white")
    for name, url, desc in SOURCES_CATALOG:
        table.add_row(name, url, desc)
    console.print(table)
    return 0


async def _run_recon(domain: str, sources: List[str], output: str | None, fmt: str) -> int:
    """Ejecuta el flujo recon: orquesta, consolida y reporta."""
    _print_header()
    console.print(f"[bold]Dominio:[/bold] {domain}")
    console.print(f"[bold]Fuentes:[/bold] {', '.join(sources)}\n")

    orchestrator = Orchestrator(domain=domain, sources=sources)
    try:
        records = await orchestrator.run()
    except httpx.TimeoutException as exc:
        console.print(f"[yellow]Advertencia:[/yellow] timeout consultando fuentes ({exc}). "
                      "Se continúa con las fuentes que respondieron.")
        records = await orchestrator.partial_results()

    builder = ReportBuilder(records)
    builder.render(fmt)

    if output:
        builder.save(output, fmt)
        console.print(f"\n[green]Resultados guardados en:[/green] {output}")

    console.print(f"\n[bold]Total subdominios únicos:[/bold] {len(records)}")
    return 0


def main(argv: List[str] | None = None) -> int:
    """Punto de entrada principal del CLI."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "sources":
        return _cmd_sources()

    if args.command == "recon":
        try:
            return asyncio.run(_run_recon(args.domain, args.sources, args.output, args.format))
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrumpido por el usuario.[/yellow]")
            return 130

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
