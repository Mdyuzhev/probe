# Задача 004: Зонд ra-expected-status

## Цель
Извлечь все ожидаемые HTTP-статусы из ассертов RestAssured-тестов.

## Что зонд делает

Находит все `.statusCode(...)` и `.statusLine(...)` вызовы. Группирует по эндпоинту: для каждого URL+метод — набор ожидаемых кодов.

## Паттерны

```java
.then().statusCode(200)
.then().statusCode(HttpStatus.SC_CREATED)
.then().statusCode(is(400))
.then().statusCode(anyOf(is(200), is(201)))
.then().assertThat().statusCode(404)
```

## Формат findings

```json
{
  "probe": "ra-expected-status",
  "env": "test",
  "entity": "POST /api/v1/movements",
  "fact": "expected_status",
  "data": {
    "status_code": 201,
    "is_success": true,
    "test_class": "MovementCreateTest",
    "test_method": "shouldCreateMovement",
    "context": "happy_path"
  },
  "location": "MovementCreateTest.java:45",
  "confidence": 1.0,
  "tags": ["api", "status", "contract"]
}
```

## Критерий готовности

- Находит все statusCode из sample-restassured
- Группирует success vs error коды
- Определяет context: happy_path (2xx), validation_error (400), not_found (404), auth (401/403), conflict (409)
- Тесты проходят
