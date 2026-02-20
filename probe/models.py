"""Модели данных PROBE: Finding, Dossier, Diff, AnalysisResult."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field


class Finding(BaseModel):
    """Сейсмограмма — атомарный факт, зафиксированный зондом."""

    probe: str = Field(..., description="Идентификатор зонда")
    env: str = Field(..., description="Тип среды: db, java, python, api, infra, doc, test")
    entity: str = Field(..., description="Сущность, к которой относится факт")
    fact: str = Field(..., description="Тип факта (snake_case)")
    data: dict[str, Any] = Field(..., description="Данные факта")
    ts: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Временная метка",
    )
    location: Optional[str] = Field(None, description="Файл:строка источника")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Уверенность [0..1]")
    tags: list[str] = Field(default_factory=list, description="Теги для фильтрации")

    model_config = {"json_encoders": {datetime: lambda v: v.isoformat()}}


class Dossier(BaseModel):
    """Досье — совокупность findings от одного или всех зондов."""

    target: str = Field(..., description="Путь или URL цели")
    env: str = Field(..., description="Тип среды")
    scanned_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    findings: list[Finding] = Field(default_factory=list)

    def by_probe(self, probe_name: str) -> list[Finding]:
        """Вернуть findings конкретного зонда."""
        return [f for f in self.findings if f.probe == probe_name]

    def by_fact(self, fact: str) -> list[Finding]:
        """Вернуть findings с конкретным типом факта."""
        return [f for f in self.findings if f.fact == fact]

    def by_tag(self, tag: str) -> list[Finding]:
        """Вернуть findings с конкретным тегом."""
        return [f for f in self.findings if tag in f.tags]


class Diff(BaseModel):
    """Разница между двумя сканированиями."""

    added: list[Finding] = Field(default_factory=list, description="Новые findings")
    removed: list[Finding] = Field(default_factory=list, description="Исчезнувшие findings")
    changed: list[tuple[Finding, Finding]] = Field(
        default_factory=list, description="Изменённые findings (было, стало)"
    )


class AnalysisResult(BaseModel):
    """Результат работы аналитика."""

    analyzer: str = Field(..., description="Идентификатор аналитика")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Временная метка анализа",
    )
    data: dict[str, Any] = Field(..., description="Данные, специфичные для аналитика")
    summary: str = Field(..., description="Человекочитаемый вывод")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Уверенность [0..1]")

    model_config = {"json_encoders": {datetime: lambda v: v.isoformat()}}
