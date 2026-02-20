# Задача 007: Зонд ra-test-sequence

## Цель
Извлечь бизнес-процессы (workflows) из упорядоченных тестов.

## Паттерны

```java
@TestMethodOrder(OrderAnnotation.class)
class ReceiptFlowTest {
    @Test @Order(1) void createMovement() { ... POST /movements → 201 }
    @Test @Order(2) void createTask() { ... POST /tasks → 201 }
    @Test @Order(3) void completeTask() { ... PUT /tasks/{id}/complete → 200 }
    @Test @Order(4) void verifyCompleted() { ... GET /movements/{id} → status=completed }
}
```

## Формат findings

```json
{
  "probe": "ra-test-sequence",
  "env": "test",
  "entity": "workflow:receipt",
  "fact": "business_workflow",
  "data": {
    "workflow_name": "ReceiptFlow",
    "steps": [
      {"order": 1, "action": "POST /api/v1/movements", "result": "201"},
      {"order": 2, "action": "POST /api/v1/tasks", "result": "201"},
      {"order": 3, "action": "PUT /api/v1/tasks/{id}/complete", "result": "200"},
      {"order": 4, "action": "GET /api/v1/movements/{id}", "result": "status=completed"}
    ],
    "test_class": "ReceiptFlowTest"
  },
  "location": "ReceiptFlowTest.java",
  "confidence": 1.0,
  "tags": ["workflow", "sequence", "business-process"]
}
```

## Критерий готовности

- Находит классы с @Order или @TestMethodOrder
- Извлекает последовательность шагов
- Формирует читаемое описание workflow
