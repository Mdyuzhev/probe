# Задача 009: Аналитик — построитель модели сущностей

## Проблема

Сейчас карта перечисляет 44 отдельных правила вида "поле status = CREATED". 
Но не собирает из них сущности: какие объекты есть в системе, какие у них поля, какие типы.

## Цель

Создать аналитик `analyzer_entity_model.py`, который читает findings от зондов
и синтезирует модель данных.

## Вход

Все findings из `findings/test/`:
- ra-assertion-rules: поля и их ожидаемые значения
- ra-endpoint-census: URL-паттерны (имя сущности = часть URL)
- ra-request-body-schema (если есть): поля request body
- ra-expected-status: контекст использования

## Логика

1. Извлечь имена сущностей из URL: `/movements` → Movement, `/documents` → Document, `/stock` → Stock
2. Собрать все поля каждой сущности из ассертов:
   - `body("status", equalTo("CREATED"))` → Movement.status: string/enum
   - `body("id", notNullValue())` → Movement.id: auto-generated
   - `body("quantity", equalTo(50))` → Movement.quantity: integer
   - `body("actualQuantity", equalTo(98))` → Movement.actualQuantity: integer
   - `body("items[0].productId", ...)` → Stock.items[].productId
3. Определить тип поля по значениям:
   - Числа → integer
   - Строки в UPPER_CASE → enum (собрать все значения)
   - notNullValue() без конкретного значения → auto-generated
   - Вложенность через [] → массив объектов
4. Определить связи: Movement содержит warehouseId → связь с Warehouse
5. Определить обязательность: если negative test без поля → 400, поле обязательное

## Выход

```json
{
  "analyzer": "entity-model",
  "entities": [
    {
      "name": "Movement",
      "source_url": "/movements",
      "fields": [
        {"name": "id", "type": "auto", "required": true, "evidence": ["R14", "R18"]},
        {"name": "status", "type": "enum", "values": ["CREATED", "APPROVED", "COMPLETED"], "evidence": ["R13", "R23", "R24"]},
        {"name": "quantity", "type": "integer", "required": true, "evidence": ["R15", "R22", "R30"]},
        {"name": "actualQuantity", "type": "integer", "evidence": ["R25", "R27"]},
        {"name": "type", "type": "enum", "values": ["WRITE_OFF", "..."], "evidence": ["R16"]}
      ],
      "relations": [
        {"field": "warehouseId", "target": "Warehouse", "evidence": ["R34"]}
      ]
    }
  ]
}
```

## Куда кладётся

`probe/analyzers/entity_model.py`

Новая директория `probe/analyzers/` — аналитики живут отдельно от зондов.
Аналитик имеет интерфейс: `analyze(findings: list[Finding]) → AnalysisResult`

## Критерий готовности

- Из 154 findings извлекает минимум 3 сущности (Movement, Document, Stock)
- Для каждой — список полей с типами
- Enum-поля содержат все найденные значения
- Тесты проходят
