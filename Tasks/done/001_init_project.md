# Задача 001: Инициализация проекта

## Цель
Создать структуру проекта PROBE, настроить зависимости, git, базовые классы.

## Шаги

1. Инициализировать git: `git init`, создать `.gitignore`
2. Создать структуру директорий:
   ```
   probe/          — ядро (cli, models, runner, correlator)
   probes/         — зонды (base.py + директории по средам)
   tests/          — тесты
   examples/       — примеры целей для сканирования
   findings/       — результаты (gitignored)
   ```
3. Создать `pyproject.toml` с метаданными проекта
4. Создать `requirements.txt`: pydantic, click, pytest, javalang
5. Создать `probe/models.py` — Pydantic-модели: Finding, Dossier, Diff
6. Создать `probes/base.py` — базовый класс BaseProbe с интерфейсом scan()
7. Создать `probe/runner.py` — параллельный запуск зондов через ThreadPoolExecutor
8. Создать `probe/cli.py` — точка входа CLI (click): `probe scan --target ... --env ...`
9. Создать `README.md` — описание проекта, установка, использование
10. Первый коммит: `[infra] Инициализация проекта PROBE`

## Критерий готовности

- `pip install -e .` работает
- `probe --help` показывает список команд
- `pytest tests/` проходит (хотя бы один тест на models.py)
- Структура соответствует CLAUDE.md

## Важно

- Python 3.10+
- Все модели через Pydantic
- CLI через click
- Type hints везде
- Docstrings на русском
