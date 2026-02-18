# PROBE — Product Reverse Observation by Bot Ensemble

Рой атомарных ботов-зондов для автоматической картографии программных продуктов.

## Концепция

Аналог сейсмической разведки: одна команда запускает десятки зондов параллельно, каждый фиксирует один факт о системе, Correlator синтезирует из совокупности фактов карту продукта.

**Один бот бесполезен — ценность возникает только в синтезе данных от всех ботов.**

## Установка

```bash
pip install -e ".[dev]"
```

## Использование

```bash
# Сканировать директорию с RestAssured-тестами
probe scan --target examples/sample-restassured --env test --out findings/

# Результат: findings/test_findings.json
```

## Структура проекта

```
probe/          — ядро (cli, models, runner, correlator)
probes/         — зонды по средам (test/, db/, java/, api/, infra/)
tests/          — тесты самого PROBE
examples/       — синтетические полигоны для отладки зондов
findings/       — результаты сканирования (gitignored)
Tasks/          — задачи (backlog/, done/)
```

## Зонды (test environment)

| Зонд | Назначение |
|------|-----------|
| `ra-endpoint-census` | Все URL + HTTP-методы из тестов |
| `ra-expected-status` | Ожидаемые HTTP-статусы |
| `ra-assertion-rules` | Бизнес-правила из ассертов |
| `ra-auth-patterns` | Паттерны авторизации |
| `ra-test-sequence` | Workflow из упорядоченных тестов |

## Разработка

```bash
# Тесты
pytest tests/ -v

# Добавить зонд
# 1. Создать probes/test/ra_<name>.py
# 2. Реализовать BaseProbe.scan() → list[Finding]
# 3. Написать тест в tests/
```

## Формат Finding

```json
{
  "probe": "ra-endpoint-census",
  "env": "test",
  "entity": "POST /api/v1/movements",
  "fact": "endpoint_exists",
  "data": {"method": "POST", "path": "/api/v1/movements"},
  "confidence": 1.0,
  "tags": ["api", "endpoint"]
}
```
