"""Аналитик модели сущностей — строит модель данных из findings."""

from __future__ import annotations

import re
from collections import defaultdict

from probe.analyzers.base import BaseAnalyzer
from probe.models import AnalysisResult, Finding


def _infer_type(matcher: str, value: str) -> str:
    """Определить тип поля по матчеру и значению."""
    if matcher == "notNullValue":
        return "auto"
    if matcher in ("greaterThan", "lessThan", "greaterThanOrEqualTo", "lessThanOrEqualTo"):
        return "integer"
    if matcher in ("equalTo", "is", "hasItem"):
        try:
            int(value)
            return "integer"
        except (ValueError, TypeError):
            pass
        try:
            float(value)
            return "number"
        except (ValueError, TypeError):
            pass
        # UPPER_CASE → enum
        if value and re.match(r"^[A-Z][A-Z0-9_]+$", str(value)):
            return "enum"
        return "string"
    return "string"


def _merge_type(current: str, new: str) -> str:
    """Выбрать более специфичный тип при накоплении."""
    priority = {"auto": 0, "string": 1, "integer": 2, "number": 2, "enum": 3}
    return new if priority.get(new, 0) > priority.get(current, 0) else current


class EntityModelAnalyzer(BaseAnalyzer):
    """Строит модель сущностей из findings аналитика зондов."""

    name = "entity-model"
    description = "Извлекает сущности, поля и типы из findings ra-assertion-rules"

    def analyze(self, findings: list[Finding]) -> AnalysisResult:
        # entity в ra-assertion-rules имеет формат "EntityName.fieldName"
        # или "EntityName.items[0].subfield" — берём первый уровень
        entity_fields: dict[str, dict[str, dict]] = defaultdict(dict)

        for f in findings:
            if f.probe != "ra-assertion-rules" or f.fact != "business_rule":
                continue

            parts = f.entity.split(".", 1)
            if len(parts) != 2:
                continue
            entity_name, field_path = parts

            # Упрощаем вложенные пути: items[0].productId → items
            field_name = re.split(r"[\[.]", field_path)[0]

            matcher = f.data.get("matcher", "")
            value = str(f.data.get("expected", ""))
            field_type = _infer_type(matcher, value)

            if field_name not in entity_fields[entity_name]:
                entity_fields[entity_name][field_name] = {
                    "name": field_name,
                    "type": field_type,
                    "values": [],
                    "evidence": [],
                }

            field = entity_fields[entity_name][field_name]
            field["type"] = _merge_type(field["type"], field_type)

            if field_type == "enum" and value and value not in field["values"]:
                field["values"].append(value)

            loc = f.location or ""
            if loc and loc not in field["evidence"]:
                field["evidence"].append(loc)

        # Сущности из URL-паттернов (ra-endpoint-census)
        url_entities: set[str] = set()
        for f in findings:
            if f.probe != "ra-endpoint-census":
                continue
            # entity вида "GET /api/v1/movements"
            for segment in re.findall(r"/([a-z][a-z0-9-]+)", f.entity.lower()):
                if segment in ("api", "v1", "v2"):
                    continue
                candidate = segment.rstrip("s").capitalize()
                url_entities.add(candidate)

        # Сборка результата
        entities_out: list[dict] = []
        for entity_name, fields in sorted(entity_fields.items()):
            fields_list = []
            relations = []

            for field_name, fd in sorted(fields.items()):
                entry: dict = {"name": field_name, "type": fd["type"]}
                if fd["type"] == "enum" and fd["values"]:
                    entry["values"] = sorted(fd["values"])
                if fd["evidence"]:
                    entry["evidence"] = fd["evidence"]
                fields_list.append(entry)

                # Связь: поля вида xxxId
                if field_name.endswith("Id"):
                    target = field_name[:-2].capitalize()
                    relations.append({
                        "field": field_name,
                        "target": target,
                        "evidence": fd["evidence"],
                    })

            entities_out.append({
                "name": entity_name,
                "fields": fields_list,
                "relations": relations,
            })

        # Сущности только из URL, без полей
        for ue in sorted(url_entities):
            if ue not in entity_fields:
                entities_out.append({"name": ue, "fields": [], "relations": [], "source": "url_only"})

        summary = "\n".join(
            [f"Сущностей: {len(entities_out)}"]
            + [f"  {e['name']}: {len(e.get('fields', []))} полей" for e in entities_out]
        )

        return AnalysisResult(
            analyzer=self.name,
            data={"entities": entities_out},
            summary=summary,
        )
