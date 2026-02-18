# Задача 002: Пример RestAssured-проекта для тестирования зондов

## Цель
Создать минимальный пример RestAssured-тестов в examples/sample-restassured/ — целевой проект для отладки зондов.

## Шаги

1. Создать `examples/sample-restassured/` со структурой Maven/Gradle тестового проекта
2. Создать 5-7 тестовых классов, покрывающих разные паттерны RestAssured:

### MovementCreateTest.java
- POST /api/v1/movements с JSON-телом
- Проверка statusCode(201)
- Проверка body("status", equalTo("created"))
- Проверка body("id", notNullValue())

### MovementNegativeTest.java
- POST с quantity=-1 → 400
- POST с пустым телом → 400
- POST без Authorization → 401
- GET несуществующего id → 404

### MovementFlowTest.java (@Order)
- POST → GET → PUT (complete) → GET (проверка status=completed)
- Workflow с последовательными шагами

### StockTest.java
- GET /api/v1/stock с query-параметрами (?warehouseId=1&category=DAIRY)
- Проверка body("items", hasSize(greaterThan(0)))
- Проверка body("items[0].quantity", greaterThan(0))

### DocumentApprovalTest.java
- POST /api/v1/documents → draft
- PUT /api/v1/documents/{id}/approve → approved
- Разные роли: OPERATOR не может approve, MANAGER может

### AuthTest.java
- Разные токены для разных ролей
- Basic auth для /admin/*
- Без авторизации для /reports/daily

### ConfigTest.java (base setup)
- BaseTest с RestAssured.baseURI, basePath, port
- Общие RequestSpecification

3. Файлы должны быть синтаксически корректным Java-кодом
4. Покрыть паттерны: given/when/then, body(), statusCode(), header(), auth(), pathParam(), queryParam(), extract()

## Критерий готовности

- 5-7 .java файлов в examples/sample-restassured/src/test/java/
- Покрыты все основные паттерны RestAssured
- Код валидный Java (парсится javalang)
- Минимум 20 тестовых методов

## Важно

Это не рабочий проект — это **синтетический полигон** для зондов. Компилируемость не требуется (нет зависимостей). Но синтаксис должен быть корректным для парсинга.
