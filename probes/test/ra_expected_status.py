"""Зонд ra-expected-status — извлекает ожидаемые HTTP-статусы из RestAssured-тестов."""

from __future__ import annotations

from pathlib import Path

import javalang

from probe.models import Finding
from probes.base import BaseProbe

# Константы Apache HttpStatus → числовые коды
HTTPSTATUS_CONSTANTS: dict[str, int] = {
    "SC_OK": 200, "SC_CREATED": 201, "SC_ACCEPTED": 202, "SC_NO_CONTENT": 204,
    "SC_MOVED_PERMANENTLY": 301, "SC_NOT_MODIFIED": 304,
    "SC_BAD_REQUEST": 400, "SC_UNAUTHORIZED": 401, "SC_FORBIDDEN": 403,
    "SC_NOT_FOUND": 404, "SC_METHOD_NOT_ALLOWED": 405,
    "SC_CONFLICT": 409, "SC_UNPROCESSABLE_ENTITY": 422,
    "SC_INTERNAL_SERVER_ERROR": 500, "SC_SERVICE_UNAVAILABLE": 503,
}


def _status_context(code: int) -> str:
    """Определяет смысловой контекст по HTTP-коду."""
    if 200 <= code < 300:
        return "happy_path"
    if code == 400:
        return "validation_error"
    if code in (401, 403):
        return "auth"
    if code == 404:
        return "not_found"
    if code in (409, 422):
        return "conflict"
    if code >= 500:
        return "server_error"
    return "other"


class RaExpectedStatus(BaseProbe):
    """Извлекает все ожидаемые HTTP-статусы из .statusCode() вызовов."""

    name = "ra-expected-status"
    env = "test"

    def scan(self, target: str | Path) -> list[Finding]:
        """Сканирует Java-тесты и собирает ожидаемые статус-коды."""
        target = Path(target)
        findings: list[Finding] = []
        for java_file in target.rglob("*.java"):
            findings.extend(self._scan_file(java_file, target))
        return findings

    def _scan_file(self, java_file: Path, base: Path) -> list[Finding]:
        source = java_file.read_text(encoding="utf-8", errors="ignore")
        relative = java_file.relative_to(base).as_posix()
        class_name = java_file.stem
        findings: list[Finding] = []

        try:
            tree = javalang.parse.parse(source)
        except javalang.parser.JavaSyntaxError:
            return findings

        for path, node in tree.filter(javalang.tree.MethodInvocation):
            if node.member not in ("statusCode", "statusLine"):
                continue

            codes = _extract_status_codes(node)
            if not codes:
                continue

            test_method = _find_enclosing_method(path)
            line = node.position.line if node.position else 0
            location = f"{relative}:{line}"

            for code, confidence in codes:
                context = _status_context(code)
                is_success = 200 <= code < 300

                findings.append(Finding(
                    probe=self.name,
                    env=self.env,
                    entity=f"{class_name}::{test_method or '?'}",
                    fact="expected_status",
                    data={
                        "status_code": code,
                        "is_success": is_success,
                        "test_class": class_name,
                        "test_method": test_method or "",
                        "context": context,
                    },
                    location=location,
                    confidence=confidence,
                    tags=["api", "status", "contract", context],
                ))

        return findings


def _extract_status_codes(node: javalang.tree.MethodInvocation) -> list[tuple[int, float]]:
    """Извлекает числовые статус-коды из аргументов statusCode()."""
    if not node.arguments:
        return []

    results: list[tuple[int, float]] = []
    for arg in node.arguments:
        _collect_codes(arg, results)
    return results


def _collect_codes(node, results: list[tuple[int, float]]) -> None:
    """Рекурсивно извлекает коды из AST-узла (литерал, константа, is(), anyOf())."""
    # Числовой литерал: statusCode(200)
    if isinstance(node, javalang.tree.Literal):
        try:
            code = int(node.value)
            if 100 <= code < 600:
                results.append((code, 1.0))
        except (ValueError, TypeError):
            pass
        return

    # Обращение к полю: HttpStatus.SC_CREATED или SC_CREATED
    if isinstance(node, javalang.tree.MemberReference):
        name = node.member
        if name in HTTPSTATUS_CONSTANTS:
            results.append((HTTPSTATUS_CONSTANTS[name], 0.9))
        return

    # Вызов метода: is(200), equalTo(201), anyOf(is(200), is(201))
    if isinstance(node, javalang.tree.MethodInvocation):
        for arg in (node.arguments or []):
            _collect_codes(arg, results)
        return

    # ClassCreator, Cast — пропускаем


def _find_enclosing_method(path) -> str | None:
    """Возвращает имя метода-теста, в котором находится узел AST."""
    for node in reversed(path):
        if isinstance(node, javalang.tree.MethodDeclaration):
            return node.name
    return None
