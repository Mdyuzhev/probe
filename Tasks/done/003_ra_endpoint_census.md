# Задача 003: Первый зонд — ra-endpoint-census

## Цель
Реализовать первый рабочий зонд, который извлекает все эндпоинты из RestAssured-тестов.

## Что зонд делает

Парсит Java-файлы, находит все вызовы RestAssured (.get(), .post(), .put(), .delete(), .patch()) и извлекает URL + HTTP-метод.

## Входные паттерны для распознавания

```java
// Прямые вызовы
given().when().get("/api/v1/movements")
given().when().post("/api/v1/movements")
given().when().put("/api/v1/movements/{id}")
given().when().delete("/api/v1/movements/" + id)

// С pathParam
given().pathParam("id", 1).when().get("/api/v1/movements/{id}")

// Статические импорты
get("/api/v1/stock")
post("/api/v1/movements")

// С переменными (baseURI + basePath)
RestAssured.baseURI = "http://localhost";
RestAssured.basePath = "/api/v1";
```

## Формат findings

```json
{
  "probe": "ra-endpoint-census",
  "env": "test",
  "entity": "POST /api/v1/movements",
  "fact": "endpoint_tested",
  "data": {
    "method": "POST",
    "path": "/api/v1/movements",
    "has_path_params": false,
    "test_class": "MovementCreateTest",
    "test_method": "shouldCreateMovement",
    "test_count": 3
  },
  "location": "src/test/java/MovementCreateTest.java:42",
  "confidence": 1.0,
  "tags": ["api", "endpoint", "write"]
}
```

## Шаги

1. Изучить как javalang парсит Java (AST)
2. Написать парсер, который находит вызовы RestAssured-методов
3. Извлекать URL (строковые литералы и конкатенации)
4. Нормализовать URL: убрать конкатенации переменных, оставить path-параметры как {param}
5. Группировать по уникальным endpoint (method + path)
6. Написать тесты на examples/sample-restassured/
7. Проверить что findings валидны по модели

## Критерий готовности

- Зонд находит все эндпоинты из sample-restassured
- Формат findings соответствует models.py
- Тесты проходят
- Файл ≤ 150 строк

## Подводные камни

- URL может быть в переменной, не в строковом литерале
- baseURI + basePath задаются в setup-методе
- Path-параметры: "/movements/{id}" vs "/movements/" + id
- Статические импорты: `import static io.restassured.RestAssured.*`
- Для первой версии: ловить строковые литералы, переменные помечать confidence=0.5
