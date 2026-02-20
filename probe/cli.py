"""CLI точка входа PROBE: команда `probe scan`."""

from __future__ import annotations

import importlib
import json
import logging
import pkgutil
from pathlib import Path

import click

from probe.correlator import correlate, load_findings
from probe.runner import run_probes
from probes.base import BaseProbe

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def _discover_probes(env: str) -> list[BaseProbe]:
    """Автообнаружение зондов для заданной среды.

    Сканирует пакет `probes.<env>` и импортирует все классы, наследующие BaseProbe.
    """
    probe_instances: list[BaseProbe] = []

    pkg_name = f"probes.{env}"
    try:
        pkg = importlib.import_module(pkg_name)
    except ModuleNotFoundError:
        raise click.BadParameter(f"Среда '{env}' не поддерживается (пакет {pkg_name} не найден)")

    for module_info in pkgutil.iter_modules(pkg.__path__):
        module = importlib.import_module(f"{pkg_name}.{module_info.name}")
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, BaseProbe)
                and attr is not BaseProbe
                and attr.name
            ):
                probe_instances.append(attr())

    return probe_instances


@click.group()
def cli() -> None:
    """PROBE — рой зондов для картографии программных продуктов."""


@cli.command()
@click.option("--target", "-t", required=True, help="Путь к директории или URL цели")
@click.option(
    "--env",
    "-e",
    required=True,
    type=click.Choice(["test", "db", "java", "api", "infra", "doc"]),
    help="Тип среды",
)
@click.option("--out", "-o", default="findings", help="Директория для сохранения findings")
@click.option("--workers", default=8, help="Число параллельных потоков")
def scan(target: str, env: str, out: str, workers: int) -> None:
    """Запустить все зонды на целевой проект."""
    click.echo(f"Цель: {target}  среда: {env}")

    probes = _discover_probes(env)
    if not probes:
        click.echo("Зонды не найдены. Добавьте зонды в probes/<env>/")
        return

    click.echo(f"Найдено зондов: {len(probes)}")

    dossier = run_probes(probes, target, env, max_workers=workers)

    out_dir = Path(out)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{env}_findings.json"
    out_file.write_text(
        json.dumps(
            [f.model_dump(mode="json") for f in dossier.findings],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    click.echo(f"Findings: {len(dossier.findings)} → {out_file}")


@cli.command(name="map")
@click.option("--findings", "-f", required=True,
              help="JSON-файл или директория с findings")
@click.option("--out", "-o", default="product-map.md",
              help="Выходной файл Product Map")
def map_cmd(findings: str, out: str) -> None:
    """Синтезировать findings в карту продукта (Product Map)."""
    dossier = load_findings(findings)
    click.echo(f"Загружено findings: {len(dossier.findings)}")

    result = correlate(dossier, out_path=out)
    lines = result.count("\n") + 1
    click.echo(f"Product Map сохранён: {out}  ({lines} строк)")
