"""Correlator — синтез findings в карту продукта (Product Map)."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from probe.models import Dossier, Finding


# ---------------------------------------------------------------------------
# Загрузка findings
# ---------------------------------------------------------------------------

def load_findings(path: str | Path) -> Dossier:
    """Загружает findings из JSON-файла или директории с JSON-файлами."""
    p = Path(path)
    raw: list[dict] = []

    if p.is_dir():
        for f in sorted(p.glob("*.json")):
            data = json.loads(f.read_text(encoding="utf-8"))
            raw.extend(data if isinstance(data, list) else [data])
    elif p.is_file():
        data = json.loads(p.read_text(encoding="utf-8"))
        raw = data if isinstance(data, list) else [data]

    dossier = Dossier(target=str(path), env=raw[0]["env"] if raw else "unknown")
    dossier.findings = [Finding(**r) for r in raw]
    return dossier


# ---------------------------------------------------------------------------
# Секции Product Map
# ---------------------------------------------------------------------------

def _header(dossier: Dossier) -> str:
    probes_count = len({f.probe for f in dossier.findings})
    return (
        f"# Product Map\n\n"
        f"**Цель:** `{dossier.target}`  "
        f"**Среда:** `{dossier.env}`  "
        f"**Сканирование:** {dossier.scanned_at.strftime('%Y-%m-%d %H:%M')} UTC\n\n"
        f"Зондов: {probes_count}  |  Findings: {len(dossier.findings)}\n\n---"
    )


def _api_surface(dossier: Dossier) -> str:
    """Таблица эндпоинтов: endpoint | auth | статусы | тест-классы."""
    eps: dict[str, dict] = {}

    # Эндпоинты от ra-endpoint-census
    for f in dossier.by_fact("endpoint_tested"):
        ep = f.entity
        if ep not in eps:
            eps[ep] = {"auth_roles": set(), "is_public": False,
                       "classes": set(), "statuses": set()}
        eps[ep]["classes"].add(f.data.get("test_class", ""))

    # Auth от ra-auth-patterns (entity тоже "METHOD /path")
    for f in dossier.findings:
        if f.fact not in ("auth_required", "public_endpoint"):
            continue
        ep = f.entity
        if ep not in eps:
            eps[ep] = {"auth_roles": set(), "is_public": False,
                       "classes": set(), "statuses": set()}
        if f.data.get("is_public"):
            eps[ep]["is_public"] = True
        elif f.data.get("role"):
            eps[ep]["auth_roles"].add(f.data["role"])
        eps[ep]["classes"].add(f.data.get("test_class", ""))

    # Статусы от ra-expected-status через test_class
    class_statuses: dict[str, set] = defaultdict(set)
    for f in dossier.by_fact("expected_status"):
        tc = f.data.get("test_class", "")
        class_statuses[tc].add(str(f.data.get("status_code", "")))

    for info in eps.values():
        for cls in info["classes"]:
            info["statuses"].update(class_statuses.get(cls, set()))

    if not eps:
        return ""

    lines = ["## API Surface\n",
             "| Эндпоинт | Auth | Статусы | Тест-классы |",
             "|----------|------|---------|-------------|"]
    for ep, info in sorted(eps.items()):
        auth = "public" if info["is_public"] else (
            ", ".join(sorted(info["auth_roles"])) or "—"
        )
        statuses = ", ".join(sorted(info["statuses"])) or "—"
        classes = ", ".join(sorted(c for c in info["classes"] if c)) or "—"
        lines.append(f"| `{ep}` | {auth} | {statuses} | {classes} |")
    return "\n".join(lines)


def _business_rules(dossier: Dossier) -> str:
    """Нумерованный список бизнес-правил R01, R02..."""
    findings = dossier.by_fact("business_rule")
    if not findings:
        return ""
    lines = ["## Бизнес-правила\n"]
    for i, f in enumerate(findings, 1):
        rule = f.data.get("rule_text", f.entity)
        src = f.location or f.data.get("test_class", "")
        lines.append(f"**R{i:02d}** {rule}  *(→ {src})*")
    return "\n".join(lines)


def _workflows(dossier: Dossier) -> str:
    """Именованные workflow с пошаговым описанием."""
    findings = dossier.by_fact("business_workflow")
    if not findings:
        return ""
    lines = ["## Workflows\n"]
    for f in findings:
        name = f.data.get("workflow_name", f.entity)
        steps = f.data.get("steps", [])
        lines.append(f"### {name}\n")
        for step in steps:
            action = step.get("action") or "—"
            status = step.get("status_code", "")
            method = step.get("test_method", "")
            lines.append(f"{step['order']}. `{action}` → {status}  *({method})*")
        lines.append("")
    return "\n".join(lines)


def _role_matrix(dossier: Dossier) -> str:
    """Матрица: роль → доступные эндпоинты."""
    role_eps: dict[str, set] = defaultdict(set)
    for f in dossier.findings:
        if f.fact not in ("auth_required", "public_endpoint"):
            continue
        role = f.data.get("role", "")
        if role:
            role_eps[role].add(f.entity)
        elif f.data.get("is_public"):
            role_eps["PUBLIC"].add(f.entity)
    if not role_eps:
        return ""
    lines = ["## Ролевая модель\n",
             "| Роль | Эндпоинты |",
             "|------|-----------|"]
    for role, endpoints in sorted(role_eps.items()):
        eps_str = ", ".join(f"`{ep}`" for ep in sorted(endpoints))
        lines.append(f"| {role} | {eps_str} |")
    return "\n".join(lines)


def _stats(dossier: Dossier) -> str:
    """Статистика зондов."""
    by_probe: dict[str, int] = defaultdict(int)
    for f in dossier.findings:
        by_probe[f.probe] += 1
    lines = ["## Статистика зондов\n"]
    for probe_name, count in sorted(by_probe.items()):
        lines.append(f"- `{probe_name}`: {count} findings")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Точка входа
# ---------------------------------------------------------------------------

def correlate(dossier: Dossier, out_path: str | Path | None = None) -> str:
    """Синтезировать findings досье в Markdown Product Map.

    Args:
        dossier: Досье с findings от всех зондов.
        out_path: Путь для сохранения. Если None — только возвращает строку.

    Returns:
        Markdown-строка с картой продукта.
    """
    sections = [
        _header(dossier),
        _api_surface(dossier),
        _business_rules(dossier),
        _workflows(dossier),
        _role_matrix(dossier),
        _stats(dossier),
    ]
    result = "\n\n".join(s for s in sections if s)

    if out_path is not None:
        Path(out_path).write_text(result, encoding="utf-8")

    return result
