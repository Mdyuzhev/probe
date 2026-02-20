# Задача 013: Базовый класс аналитика + инфраструктура

## Проблема

Аналитики — новый тип компонента. Нужен базовый класс и интеграция в pipeline.
Зонды работают с кодом (парсят файлы). Аналитики работают с findings (парсят JSON).

## Цель

Создать инфраструктуру для аналитиков.

## Шаги

### 1. Базовый класс

`probe/analyzers/base.py`:

```python
class BaseAnalyzer:
    """Базовый класс аналитика."""
    
    name: str               # "entity-model", "state-machine"
    description: str

    def analyze(self, findings: list[Finding]) -> AnalysisResult:
        """Анализирует findings и возвращает результат."""
        raise NotImplementedError
```

### 2. Модель AnalysisResult

Добавить в `probe/models.py`:

```python
class AnalysisResult(BaseModel):
    """Результат работы аналитика."""
    analyzer: str
    timestamp: datetime
    data: dict              # специфичные для аналитика данные
    summary: str            # человекочитаемый вывод
    confidence: float = 1.0
```

### 3. Структура директорий

```
probe/
├── analyzers/
│   ├── __init__.py
│   ├── base.py              # BaseAnalyzer + AnalysisResult
│   ├── entity_model.py      # задача 009
│   ├── state_machine.py     # задача 010
│   ├── contradictions.py    # задача 011
│   └── blind_spots.py       # задача 012
```

### 4. Загрузчик findings

Утилита для чтения findings из директории:

```python
def load_findings(findings_dir: str) -> list[Finding]:
    """Читает все JSON-файлы из директории и возвращает список Finding."""
```

### 5. Runner аналитиков

Аналогично runner зондов — запускает все аналитики последовательно
(параллелизм не нужен, аналитики быстрые).

### 6. Интеграция в CLI

```bash
probe analyze --findings ./findings/ --out ./analysis/
```

## Критерий готовности

- BaseAnalyzer создан и работает
- AnalysisResult добавлен в models.py
- load_findings читает JSON из директории
- CLI команда `probe analyze` работает
- Хотя бы один тест

## Важно

ЭТУ ЗАДАЧУ ВЫПОЛНИТЬ ПЕРВОЙ из волны 2 — она создаёт инфраструктуру
для задач 009-012. Задачи 009-012 зависят от неё.
