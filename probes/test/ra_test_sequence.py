"""Зонд ra-test-sequence — извлекает бизнес-процессы из упорядоченных тестов."""

from __future__ import annotations

import re
from pathlib import Path

from probe.models import Finding
from probes.base import BaseProbe

# Признак упорядоченного класса
_RE_TEST_METHOD_ORDER = re.compile(r'@TestMethodOrder\b')

# @Order(N) аннотация
_RE_ORDER = re.compile(r'@Order\(\s*(\d+)\s*\)')

# Объявление метода (после @Order)
_RE_METHOD_DEF = re.compile(
    r'(?:public|private|protected)\s+(?:static\s+)?(?:\w[\w<>[\]]*)\s+(\w+)\s*\([^)]*\)\s*\{',
    re.MULTILINE,
)

# Первый HTTP-вызов в теле метода
_RE_HTTP = re.compile(
    r'\.(get|post|put|delete|patch|head|options)\(\s*"([^"]+)"', re.IGNORECASE
)

# Ожидаемый статус-код
_RE_STATUS = re.compile(r'\.statusCode\(\s*(\d+)\s*\)')


def _workflow_name(class_name: str) -> str:
    """Имя workflow из имени класса: MovementFlowTest → MovementFlow."""
    name = re.sub(r'Test$', '', class_name)
    return name or class_name


def _extract_ordered_steps(source: str) -> list[tuple[int, str, str, int]]:
    """Возвращает [(order, method_name, body, line)] отсортированные по order."""
    results = []
    for om in _RE_ORDER.finditer(source):
        order_num = int(om.group(1))
        # Ищем объявление метода в пределах 400 символов после @Order
        search_end = min(len(source), om.end() + 400)
        mm = _RE_METHOD_DEF.search(source, om.end(), search_end)
        if not mm:
            continue
        method_name = mm.group(1)
        start = mm.end() - 1  # позиция открывающей {
        line = source[: om.start()].count("\n") + 1
        # Вырезаем тело метода по балансу скобок
        depth = 0
        for i, ch in enumerate(source[start:]):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    results.append((order_num, method_name, source[start: start + i + 1], line))
                    break
    results.sort(key=lambda x: x[0])
    return results


def _build_step(order: int, method_name: str, body: str) -> dict:
    """Формирует шаг workflow из тела метода."""
    step: dict = {"order": order, "test_method": method_name,
                  "action": "", "method": "", "path": "", "status_code": 0}
    hm = _RE_HTTP.search(body)
    if hm:
        step["method"] = hm.group(1).upper()
        step["path"] = hm.group(2)
        step["action"] = f"{step['method']} {step['path']}"
    sm = _RE_STATUS.search(body)
    if sm:
        step["status_code"] = int(sm.group(1))
    return step


class RaTestSequence(BaseProbe):
    """Извлекает бизнес-процессы (workflows) из упорядоченных тест-классов."""

    name = "ra-test-sequence"
    env = "test"

    def scan(self, target: str | Path) -> list[Finding]:
        """Сканирует Java-тесты и собирает упорядоченные последовательности."""
        target = Path(target)
        findings: list[Finding] = []
        for java_file in target.rglob("*.java"):
            f = self._scan_file(java_file, target)
            if f:
                findings.append(f)
        return findings

    def _scan_file(self, java_file: Path, base: Path) -> Finding | None:
        source = java_file.read_text(encoding="utf-8", errors="ignore")

        # Только классы с @TestMethodOrder
        if not _RE_TEST_METHOD_ORDER.search(source):
            return None

        class_name = java_file.stem
        relative = java_file.relative_to(base).as_posix()
        steps_raw = _extract_ordered_steps(source)

        if not steps_raw:
            return None

        steps = [_build_step(o, m, body) for o, m, body, _ in steps_raw]
        workflow = _workflow_name(class_name)

        return Finding(
            probe=self.name,
            env=self.env,
            entity=f"workflow:{workflow}",
            fact="business_workflow",
            data={
                "workflow_name": workflow,
                "test_class": class_name,
                "step_count": len(steps),
                "steps": steps,
            },
            location=relative,
            confidence=1.0,
            tags=["workflow", "sequence", "business-process"],
        )
