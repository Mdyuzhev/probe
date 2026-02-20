# Задача 006: Зонд ra-auth-patterns

## Цель
Извлечь модель авторизации из тестов: кто какие роли использует, какие эндпоинты защищены.

## Паттерны

```java
.header("Authorization", "Bearer " + operatorToken)
.auth().basic("admin", "password")
.auth().oauth2(token)
.header("X-Role", "MANAGER")
// Тесты БЕЗ авторизации (тоже ценная информация)
given().when().get("/api/v1/reports/daily")
```

## Формат findings

```json
{
  "probe": "ra-auth-patterns",
  "env": "test",
  "entity": "POST /api/v1/movements",
  "fact": "auth_required",
  "data": {
    "auth_type": "bearer",
    "role": "ROLE_OPERATOR",
    "token_variable": "operatorToken",
    "is_public": false
  },
  "location": "MovementCreateTest.java:30",
  "confidence": 0.9,
  "tags": ["auth", "security", "role"]
}
```

## Критерий готовности

- Находит все паттерны авторизации
- Извлекает роли из имён переменных/констант
- Находит публичные эндпоинты (без auth в тесте)
- Строит матрицу: роль → эндпоинты
