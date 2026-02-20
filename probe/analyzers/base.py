"""Базовый класс аналитика и утилиты загрузки findings."""

from __future__ import annotations

import json
from pathlib import Path

from probe.models import AnalysisResult, Finding


def load_findings(findings_dir: str | Path) -> list[Finding]:
    """Читает все JSON-файлы из директории и возвращает список Finding.

    Args:
        findings_dir: Путь к директории с JSON-файлами findings.

    Returns:
        Плоский список Finding из всех файлов.
    """
    p = Path(findings_dir)
    results: list[Finding] = []

    for json_file in sorted(p.glob("*.json")):
        data = json.loads(json_file.read_text(encoding="utf-8"))
        items = data if isinstance(data, list) else [data]
        results.extend(Finding(**item) for item in items)

    return results


class BaseAnalyzer:
    """Базовый класс аналитика.

    Аналитик работает с findings, не с исходным кодом.
    Извлекает выводы: обобщения, автоматы, противоречия, белые пятна.
    """

    name: str = ""
    description: str = ""

    def analyze(self, findings: list[Finding]) -> AnalysisResult:
        """Анализирует findings и возвращает результат.

        Args:
            findings: Список findings для анализа.

        Returns:
            Структурированный результат анализа.
        """
        raise NotImplementedError(f"Аналитик {self.__class__.__name__} не реализован")
