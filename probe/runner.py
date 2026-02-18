"""Параллельный запуск зондов через ThreadPoolExecutor."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Sequence

from probe.models import Dossier, Finding
from probes.base import BaseProbe

logger = logging.getLogger(__name__)


def run_probes(
    probes: Sequence[BaseProbe],
    target: str | Path,
    env: str,
    max_workers: int = 8,
) -> Dossier:
    """Запустить зонды параллельно и собрать досье.

    Args:
        probes: Список зондов для запуска.
        target: Путь или URL цели.
        env: Тип среды.
        max_workers: Максимальное число потоков.

    Returns:
        Досье с findings от всех зондов.
    """
    dossier = Dossier(target=str(target), env=env)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_run_one, probe, target): probe for probe in probes}

        for future in as_completed(futures):
            probe = futures[future]
            try:
                findings: list[Finding] = future.result()
                dossier.findings.extend(findings)
                logger.info("[%s] %d findings", probe.name, len(findings))
            except Exception as exc:
                logger.error("[%s] ошибка: %s", probe.name, exc)

    return dossier


def _run_one(probe: BaseProbe, target: str | Path) -> list[Finding]:
    """Запустить один зонд и вернуть его findings."""
    logger.debug("Запуск зонда %s на %s", probe.name, target)
    return probe.scan(target)
