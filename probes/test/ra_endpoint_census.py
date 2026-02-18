"""Зонд ra-endpoint-census — извлекает все эндпоинты из RestAssured-тестов."""

from __future__ import annotations

import re
from pathlib import Path

import javalang

from probe.models import Finding
from probes.base import BaseProbe

# HTTP-методы RestAssured, которые соответствуют HTTP-глаголам
HTTP_METHODS = {"get", "post", "put", "delete", "patch", "head", "options"}


class RaEndpointCensus(BaseProbe):
    """Извлекает все URL + HTTP-методы из RestAssured-тестов."""

    name = "ra-endpoint-census"
    env = "test"

    def scan(self, target: str | Path) -> list[Finding]:
        """Сканирует директорию с Java-тестами и собирает эндпоинты."""
        target = Path(target)
        findings: list[Finding] = []

        for java_file in target.rglob("*.java"):
            findings.extend(self._scan_file(java_file, target))

        return findings

    def _scan_file(self, java_file: Path, base: Path) -> list[Finding]:
        """Парсит один Java-файл и извлекает вызовы RestAssured."""
        source = java_file.read_text(encoding="utf-8", errors="ignore")
        relative = java_file.relative_to(base).as_posix()
        class_name = java_file.stem
        findings: list[Finding] = []

        try:
            tree = javalang.parse.parse(source)
        except javalang.parser.JavaSyntaxError:
            return findings

        # Ищем вызовы методов с именами HTTP-глаголов
        for path, node in tree.filter(javalang.tree.MethodInvocation):
            if node.member.lower() not in HTTP_METHODS:
                continue

            http_method = node.member.upper()
            url, confidence = self._extract_url(node)
            if url is None:
                continue

            url = _normalize_url(url)
            has_path_params = "{" in url

            # Определяем метод-тест, в котором находится вызов
            test_method = _find_enclosing_method(path)

            # Номер строки из позиции узла (javalang даёт position)
            line = node.position.line if node.position else 0
            location = f"{relative}:{line}"

            entity = f"{http_method} {url}"
            tags = ["api", "endpoint"]
            if http_method in ("POST", "PUT", "PATCH", "DELETE"):
                tags.append("write")
            else:
                tags.append("read")
            if has_path_params:
                tags.append("path-param")

            findings.append(Finding(
                probe=self.name,
                env=self.env,
                entity=entity,
                fact="endpoint_tested",
                data={
                    "method": http_method,
                    "path": url,
                    "has_path_params": has_path_params,
                    "test_class": class_name,
                    "test_method": test_method or "",
                },
                location=location,
                confidence=confidence,
                tags=tags,
            ))

        return findings

    def _extract_url(self, node: javalang.tree.MethodInvocation) -> tuple[str | None, float]:
        """Извлекает URL из аргументов вызова метода.

        Returns:
            (url, confidence): url=None если не удалось извлечь.
        """
        if not node.arguments:
            return None, 0.0

        first_arg = node.arguments[0]

        # Строковый литерал: .get("/api/v1/movements")
        if isinstance(first_arg, javalang.tree.Literal):
            value = first_arg.value
            if value.startswith('"') and value.endswith('"'):
                return value[1:-1], 1.0

        # Бинарное выражение (конкатенация): "/movements/" + id
        if isinstance(first_arg, javalang.tree.BinaryOperation):
            url = _extract_string_from_binary(first_arg)
            if url:
                return url, 0.8

        # Переменная или вызов метода — URL неизвестен
        if isinstance(first_arg, (javalang.tree.MemberReference, javalang.tree.MethodInvocation)):
            return "{dynamic}", 0.3

        return None, 0.0


def _extract_string_from_binary(node: javalang.tree.BinaryOperation) -> str | None:
    """Собирает строку из бинарного выражения (конкатенация строк)."""
    parts = []
    _collect_parts(node, parts)
    if not parts:
        return None
    result = "".join(parts)
    # Нормализуем переменные в конкатенации → {param}
    return re.sub(r'\{[^}]*\}', r'{param}', result) if result else None


def _collect_parts(node, parts: list[str]) -> None:
    """Рекурсивно собирает строковые части из бинарного выражения."""
    if isinstance(node, javalang.tree.BinaryOperation) and node.operator == "+":
        _collect_parts(node.operandl, parts)
        _collect_parts(node.operandr, parts)
    elif isinstance(node, javalang.tree.Literal):
        val = node.value
        if val.startswith('"') and val.endswith('"'):
            parts.append(val[1:-1])
    else:
        # Переменная или выражение — заменяем placeholder
        parts.append("{param}")


def _normalize_url(url: str) -> str:
    """Нормализует URL: убирает trailing slash, схему/хост если попали."""
    url = url.strip()
    # Убираем схему и хост если вдруг попали полные URL
    url = re.sub(r'^https?://[^/]+', '', url)
    # Множественные слеши → один
    url = re.sub(r'/+', '/', url)
    return url or "/"


def _find_enclosing_method(path) -> str | None:
    """Возвращает имя метода-теста, в котором находится узел AST."""
    for node in reversed(path):
        if isinstance(node, javalang.tree.MethodDeclaration):
            return node.name
    return None
