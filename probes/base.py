"""Базовый класс для всех зондов PROBE."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from probe.models import Finding


class BaseProbe(ABC):
    """Интерфейс зонда. Один зонд = один факт об одной сущности среды."""

    #: Уникальный идентификатор зонда (kebab-case)
    name: str = ""
    #: Тип среды, для которой предназначен зонд
    env: str = ""

    @abstractmethod
    def scan(self, target: str | Path) -> list[Finding]:
        """Выполнить сканирование цели и вернуть список findings.

        Args:
            target: Путь к директории или URL цели.

        Returns:
            Список атомарных фактов (findings). Пустой список — норма.
        """
        ...

    def __repr__(self) -> str:
        return f"<Probe {self.name!r} env={self.env!r}>"
