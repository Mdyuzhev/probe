"""Зонд ra-assertion-rules — извлекает бизнес-правила из body()-ассертов RestAssured."""

from __future__ import annotations

import re
from pathlib import Path

import javalang

from probe.models import Finding
from probes.base import BaseProbe

# Ключевые слова в имени теста, указывающие на негативный сценарий
_NEGATIVE_KEYWORDS = frozenset([
    "negative", "invalid", "error", "fail", "bad", "wrong",
    "forbidden", "unauthorized", "notfound", "notFound", "missing",
])

# Шаблоны rule_text: matcher → русский шаблон
_RULE_TEMPLATES: dict[str, str] = {
    "equalTo":        "поле {field} = {expected}",
    "is":             "поле {field} = {expected}",
    "notNullValue":   "поле {field} не пустое (not null)",
    "notNull":        "поле {field} не пустое (not null)",
    "nullValue":      "поле {field} должно быть null",
    "hasSize":        "коллекция {field} содержит {expected} элементов",
    "greaterThan":    "поле {field} > {expected}",
    "greaterThanOrEqualTo": "поле {field} >= {expected}",
    "lessThan":       "поле {field} < {expected}",
    "containsString": "поле {field} содержит подстроку {expected}",
    "startsWith":     "поле {field} начинается с {expected}",
    "endsWith":       "поле {field} заканчивается на {expected}",
    "not":            "поле {field} НЕ соответствует {expected}",
    "emptyString":    "поле {field} не является пустой строкой",
    "everyItem":      "каждый элемент {field} соответствует {expected}",
    "hasItem":        "коллекция {field} содержит {expected}",
}


def _make_rule_text(field: str, matcher: str, expected: str) -> str:
    """Генерирует читаемое правило на русском."""
    tmpl = _RULE_TEMPLATES.get(matcher, "поле {field} соответствует {matcher}({expected})")
    return tmpl.format(field=field, matcher=matcher, expected=expected or "")


def _is_negative(test_method: str | None, class_name: str) -> bool:
    """Определяет негативный тест по имени метода/класса."""
    name = (test_method or "") + class_name
    low = name.lower()
    return any(kw.lower() in low for kw in _NEGATIVE_KEYWORDS)


def _entity_from_class(class_name: str) -> str:
    """Определяет бизнес-сущность по имени тест-класса."""
    # MovementCreateTest → Movement, StockTest → Stock
    match = re.match(r'^([A-Z][a-z]+)', class_name)
    return match.group(1) if match else class_name


class RaAssertionRules(BaseProbe):
    """Извлекает бизнес-правила из .body() ассертов RestAssured."""

    name = "ra-assertion-rules"
    env = "test"

    def scan(self, target: str | Path) -> list[Finding]:
        """Сканирует Java-тесты и собирает body()-ассерты."""
        target = Path(target)
        findings: list[Finding] = []
        for java_file in target.rglob("*.java"):
            findings.extend(self._scan_file(java_file, target))
        return findings

    def _scan_file(self, java_file: Path, base: Path) -> list[Finding]:
        source = java_file.read_text(encoding="utf-8", errors="ignore")
        relative = java_file.relative_to(base).as_posix()
        class_name = java_file.stem
        entity_base = _entity_from_class(class_name)
        findings: list[Finding] = []

        try:
            tree = javalang.parse.parse(source)
        except javalang.parser.JavaSyntaxError:
            return findings

        for path, node in tree.filter(javalang.tree.MethodInvocation):
            if node.member != "body":
                continue
            args = node.arguments or []
            if len(args) < 2:
                continue

            # Первый аргумент — путь к полю (строковый литерал)
            field, field_conf = _extract_string(args[0])
            if field is None:
                continue

            # Второй аргумент — matcher
            matcher, expected = _extract_matcher(args[1])

            test_method = _find_enclosing_method(path)
            line = node.position.line if node.position else 0
            location = f"{relative}:{line}"
            is_negative = _is_negative(test_method, class_name)
            rule_text = _make_rule_text(field, matcher, expected)

            # entity: SomeClass.fieldName
            entity = f"{entity_base}.{field.split('.')[0].split('[')[0]}"

            tags = ["rule"]
            if is_negative:
                tags.append("constraint")
            else:
                tags.append("business-rule")

            findings.append(Finding(
                probe=self.name,
                env=self.env,
                entity=entity,
                fact="business_rule",
                data={
                    "field": field,
                    "matcher": matcher,
                    "expected": expected,
                    "rule_text": rule_text,
                    "test_class": class_name,
                    "test_method": test_method or "",
                    "is_negative_test": is_negative,
                },
                location=location,
                confidence=field_conf,
                tags=tags,
            ))

        return findings


def _extract_string(node) -> tuple[str | None, float]:
    """Извлекает строку из AST-узла."""
    if isinstance(node, javalang.tree.Literal):
        val = node.value
        if val.startswith('"') and val.endswith('"'):
            return val[1:-1], 1.0
    return None, 0.0


def _extract_matcher(node) -> tuple[str, str]:
    """Извлекает имя matcher и ожидаемое значение из AST-узла."""
    if isinstance(node, javalang.tree.MethodInvocation):
        matcher = node.member
        expected = ""
        if node.arguments:
            expected = _literal_value(node.arguments[0])
        return matcher, expected

    if isinstance(node, javalang.tree.MemberReference):
        return node.member, ""

    return "unknown", ""


def _literal_value(node) -> str:
    """Возвращает строковое представление значения из литерала."""
    if isinstance(node, javalang.tree.Literal):
        val = node.value
        if val.startswith('"') and val.endswith('"'):
            return val[1:-1]
        return val
    if isinstance(node, javalang.tree.MemberReference):
        return node.member
    if isinstance(node, javalang.tree.MethodInvocation):
        inner = node.arguments[0] if node.arguments else None
        return f"{node.member}({_literal_value(inner) if inner else ''})"
    return ""


def _find_enclosing_method(path) -> str | None:
    """Возвращает имя метода-теста, в котором находится узел AST."""
    for node in reversed(path):
        if isinstance(node, javalang.tree.MethodDeclaration):
            return node.name
    return None
