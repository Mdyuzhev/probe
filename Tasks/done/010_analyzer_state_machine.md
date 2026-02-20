# Задача 010: Аналитик — построитель конечных автоматов

## Проблема

В findings есть R13 "status=CREATED", R23 "status=APPROVED", R24 "status=COMPLETED",
R28 "error=INVALID_STATE_TRANSITION" при попытке approve после complete.
Это конечный автомат, но карта его не строит — показывает как 4 отдельных правила.

## Цель

Создать аналитик `analyzer_state_machine.py`, который извлекает конечные автоматы
сущностей из findings.

## Логика

1. Найти все сущности с полем `status` (из entity_model или напрямую из findings)
2. Собрать все значения status: CREATED, APPROVED, COMPLETED, DRAFT...
3. Из workflow findings (ra-test-sequence) извлечь переходы:
   - step1 POST → status=CREATED
   - step3 PUT /approve → status=APPROVED  
   - step4 PUT /complete → status=COMPLETED
   Значит: CREATED → APPROVED → COMPLETED
4. Из negative tests извлечь запрещённые переходы:
   - step6 PUT /approve после COMPLETED → 409 (INVALID_STATE_TRANSITION)
   Значит: COMPLETED → APPROVED запрещён
5. Построить граф переходов:
   ```
   Movement: CREATED --approve--> APPROVED --complete--> COMPLETED
                                                    X-- approve (409)
   
   Document: DRAFT --approve--> APPROVED
                  X-- reject после approve (409)
   ```

## Выход

```json
{
  "analyzer": "state-machine",
  "machines": [
    {
      "entity": "Movement",
      "status_field": "status",
      "states": ["CREATED", "APPROVED", "COMPLETED"],
      "initial_state": "CREATED",
      "transitions": [
        {"from": "CREATED", "to": "APPROVED", "trigger": "PUT /movements/{id}/approve", "evidence": ["workflow:MovementFlow:step3"]},
        {"from": "APPROVED", "to": "COMPLETED", "trigger": "PUT /movements/{id}/complete", "evidence": ["workflow:MovementFlow:step4"]}
      ],
      "forbidden_transitions": [
        {"from": "COMPLETED", "to": "APPROVED", "trigger": "PUT /movements/{id}/approve", "error": "INVALID_STATE_TRANSITION", "evidence": ["R28"]}
      ],
      "terminal_states": ["COMPLETED"],
      "unknown_transitions": "Нет тестов на: CREATED→COMPLETED (прямое), APPROVED→CREATED (откат)"
    }
  ]
}
```

## Визуализация в карте

```
Movement lifecycle:
  CREATED ──approve──► APPROVED ──complete──► COMPLETED
                                         ✗ approve (409)

Document lifecycle:
  DRAFT ──approve──► APPROVED
                 ✗ reject (409)
```

## Куда кладётся

`probe/analyzers/state_machine.py`

## Критерий готовности

- Извлекает автоматы для Movement и Document
- Показывает разрешённые и запрещённые переходы
- Показывает непроверенные переходы (белые пятна)
- Тесты проходят
