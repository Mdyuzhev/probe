# Задача 005: Зонд ra-assertion-rules

## Цель
Извлечь бизнес-правила из ассертов RestAssured: body(...), каждый ассерт — микро-спецификация.

## Паттерны

```java
.body("status", equalTo("created"))
.body("id", notNullValue())
.body("quantity", greaterThan(0))
.body("items", hasSize(5))
.body("items[0].name", not(emptyString()))
.body("error.message", containsString("required"))
```

## Формат findings

```json
{
  "probe": "ra-assertion-rules",
  "env": "test",
  "entity": "Movement.status",
  "fact": "business_rule",
  "data": {
    "field": "status",
    "matcher": "equalTo",
    "expected": "created",
    "rule_text": "После создания movement, поле status = 'created'",
    "endpoint": "POST /api/v1/movements",
    "is_negative_test": false
  },
  "location": "MovementCreateTest.java:48",
  "confidence": 1.0,
  "tags": ["rule", "status", "lifecycle"]
}
```

## Дополнительно

- Из negative tests извлекать ограничения: "quantity не может быть < 1"
- Группировать по entity (Movement, Stock, Document)
- Генерировать читаемый rule_text на русском

## Критерий готовности

- Извлекает все body() ассерты из sample-restassured
- Формирует rule_text для каждого
- Отличает positive (бизнес-правило) от negative (ограничение)
- Тесты проходят
