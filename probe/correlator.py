"""Correlator — синтез findings в карту продукта (Product Map)."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from probe.models import Dossier, Finding


def correlate(dossier: Dossier, out_path: str | Path | None = None) -> str:
    """Синтезировать findings досье в Markdown-карту продукта.

    Args:
        dossier: Досье с findings от всех зондов.
        out_path: Путь для сохранения карты. Если None — только возвращает строку.

    Returns:
        Markdown-строка с картой продукта.
    """
    sections: list[str] = [
        f"# Product Map\n",
        f"**Цель:** `{dossier.target}`  **Среда:** `{dossier.env}`  "
        f"**Сканирование:** {dossier.scanned_at.strftime('%Y-%m-%d %H:%M')} UTC\n",
        f"**Findings:** {len(dossier.findings)}\n",
        "---\n",
    ]

    # Группировка по типу факта
    by_fact: dict[str, list[Finding]] = defaultdict(list)
    for f in dossier.findings:
        by_fact[f.fact].append(f)

    for fact_type, findings in sorted(by_fact.items()):
        sections.append(f"## {fact_type}\n")
        for f in findings:
            confidence_str = f"  *(confidence: {f.confidence:.0%})*" if f.confidence < 1.0 else ""
            location_str = f"  `{f.location}`" if f.location else ""
            sections.append(f"- **{f.entity}**{location_str}{confidence_str}")
            for key, value in f.data.items():
                sections.append(f"  - {key}: `{value}`")
        sections.append("")

    # Статистика по зондам
    sections.append("## Статистика зондов\n")
    by_probe: dict[str, int] = defaultdict(int)
    for f in dossier.findings:
        by_probe[f.probe] += 1
    for probe_name, count in sorted(by_probe.items()):
        sections.append(f"- `{probe_name}`: {count} findings")

    result = "\n".join(sections)

    if out_path is not None:
        Path(out_path).write_text(result, encoding="utf-8")

    return result
