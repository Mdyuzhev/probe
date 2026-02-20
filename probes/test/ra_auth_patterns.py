"""Зонд ra-auth-patterns — паттерны авторизации из RestAssured-тестов."""

from __future__ import annotations

import re
from pathlib import Path

import javalang

from probe.models import Finding
from probes.base import BaseProbe

# Паттерны авторизации (regex)
_RE_SPEC = re.compile(r'\.spec\(\s*(\w+)\s*\)')
_RE_BASIC = re.compile(r'\.auth\(\)\.basic\(\s*"([^"]+)"\s*,\s*"([^"]+)"\s*\)')
_RE_OAUTH2 = re.compile(r'\.auth\(\)\.oauth2\(\s*(\w+)\s*\)')
_RE_BEARER_LIT = re.compile(r'\.header\(\s*"Authorization"\s*,\s*"Bearer\s+([^"]+)"\s*\)')
_RE_BEARER_VAR = re.compile(r'\.header\(\s*"Authorization"\s*,\s*(?!"Bearer)(\w+)\s*\)')
_RE_HTTP = re.compile(
    r'\.(get|post|put|delete|patch|head|options)\(\s*"([^"]+)"', re.IGNORECASE
)
_RE_STATUS = re.compile(r'\.statusCode\(\s*(\d+)\s*\)')

# Spec-переменная → роль (эвристика по имени)
_SPEC_ROLES: dict[str, str] = {
    "operatorspec": "OPERATOR",
    "managerspec":  "MANAGER",
    "adminspec":    "ADMIN",
    "userspec":     "USER",
    "guestspec":    "GUEST",
    "viewerspec":   "VIEWER",
    "basespec":     "",   # публичный / без роли
}


def _role_from_var(var: str) -> str:
    """Определяет роль по имени переменной-токена."""
    key = var.lower()
    for role in ("operator", "manager", "admin", "user", "guest", "viewer"):
        if role in key:
            return role.upper()
    return ""


def _parse_auth(body: str) -> dict:
    """Извлекает auth-контекст из текста тела метода."""
    # Basic auth
    m = _RE_BASIC.search(body)
    if m:
        return {"auth_type": "basic", "role": m.group(1).upper(),
                "token_variable": "", "is_public": False, "username": m.group(1)}

    # OAuth2
    m = _RE_OAUTH2.search(body)
    if m:
        return {"auth_type": "oauth2", "role": _role_from_var(m.group(1)),
                "token_variable": m.group(1), "is_public": False, "username": ""}

    # Bearer literal header
    m = _RE_BEARER_LIT.search(body)
    if m:
        return {"auth_type": "bearer", "role": "",
                "token_variable": "literal", "is_public": False, "username": ""}

    # Bearer variable header
    m = _RE_BEARER_VAR.search(body)
    if m:
        var = m.group(1)
        return {"auth_type": "bearer", "role": _role_from_var(var),
                "token_variable": var, "is_public": False, "username": ""}

    # Spec-based auth
    for spec_name in _RE_SPEC.findall(body):
        role = _SPEC_ROLES.get(spec_name.lower(), "UNKNOWN")
        if role:
            return {"auth_type": "bearer", "role": role,
                    "token_variable": spec_name, "is_public": False, "username": ""}

    # Только baseSpec или ничего — публичный
    return {"auth_type": "none", "role": "", "token_variable": "",
            "is_public": True, "username": ""}


def _extract_method_bodies(source: str) -> list[tuple[str, str, int]]:
    """Возвращает список (method_name, body, start_line) для @Test методов."""
    pat = re.compile(
        r'@Test\b.*?(?:public|private|protected)\s+\w+\s+(\w+)\s*\([^)]*\)\s*\{',
        re.DOTALL,
    )
    results = []
    for m in pat.finditer(source):
        name = m.group(1)
        start = m.end() - 1  # позиция открывающей {
        line = source[: m.start()].count("\n") + 1
        depth = 0
        for i, ch in enumerate(source[start:]):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    results.append((name, source[start: start + i + 1], line))
                    break
    return results


class RaAuthPatterns(BaseProbe):
    """Извлекает паттерны авторизации из RestAssured-тестов."""

    name = "ra-auth-patterns"
    env = "test"

    def scan(self, target: str | Path) -> list[Finding]:
        """Сканирует Java-тесты и фиксирует auth-паттерны для каждого эндпоинта."""
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

        # Быстрая проверка: есть ли вообще @Test
        if "@Test" not in source:
            return findings

        for method_name, body, start_line in _extract_method_bodies(source):
            auth = _parse_auth(body)
            status_m = _RE_STATUS.search(body)
            status_code = int(status_m.group(1)) if status_m else 0

            # is_public уточняем по статус-коду
            if auth["is_public"] and status_code in (401, 403):
                auth["is_public"] = False

            fact = "public_endpoint" if auth["is_public"] else "auth_required"
            confidence = 1.0 if auth["auth_type"] in ("basic", "bearer") else 0.7
            tags = ["auth", "security"]
            if auth["role"]:
                tags.append(f"role:{auth['role'].lower()}")

            for http_m in _RE_HTTP.finditer(body):
                http_verb = http_m.group(1).upper()
                path = http_m.group(2)
                entity = f"{http_verb} {path}"
                findings.append(Finding(
                    probe=self.name,
                    env=self.env,
                    entity=entity,
                    fact=fact,
                    data={**auth, "test_class": class_name,
                          "test_method": method_name, "status_code": status_code},
                    location=f"{relative}:{start_line}",
                    confidence=confidence,
                    tags=tags,
                ))

        return findings
