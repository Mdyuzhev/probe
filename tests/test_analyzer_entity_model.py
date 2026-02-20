"""Тесты аналитика entity-model."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from probe.analyzers.entity_model import EntityModelAnalyzer, _infer_type, _merge_type
from probe.models import Finding


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def make_rule(entity: str, field: str, matcher: str, expected: str = "",
              is_negative: bool = False, location: str = "") -> Finding:
    return Finding(
        probe="ra-assertion-rules",
        env="test",
        entity=f"{entity}.{field}",
        fact="business_rule",
        data={
            "field": field,
            "matcher": matcher,
            "expected": expected,
            "rule_text": f"поле {field} = {expected}",
            "test_class": "TestClass",
            "test_method": "test_method",
            "is_negative_test": is_negative,
        },
        location=location or f"src/test/java/{entity}Test.java:10",
    )


def make_endpoint(method: str, path: str) -> Finding:
    return Finding(
        probe="ra-endpoint-census",
        env="test",
        entity=f"{method} {path}",
        fact="endpoint_tested",
        data={"method": method, "path": path, "test_class": "TestClass"},
    )


# ---------------------------------------------------------------------------
# Тесты _infer_type
# ---------------------------------------------------------------------------

class TestInferType:
    def test_not_null_value(self):
        assert _infer_type("notNullValue", "") == "auto"

    def test_integer(self):
        assert _infer_type("equalTo", "50") == "integer"

    def test_enum_upper_case(self):
        assert _infer_type("equalTo", "CREATED") == "enum"
        assert _infer_type("equalTo", "WRITE_OFF") == "enum"

    def test_string(self):
        assert _infer_type("equalTo", "some-value") == "string"

    def test_greater_than(self):
        assert _infer_type("greaterThan", "0") == "integer"


# ---------------------------------------------------------------------------
# Тесты _merge_type
# ---------------------------------------------------------------------------

class TestMergeType:
    def test_enum_wins_over_string(self):
        assert _merge_type("string", "enum") == "enum"

    def test_keeps_current_if_lower_priority(self):
        assert _merge_type("enum", "string") == "enum"

    def test_auto_upgrades_to_enum(self):
        assert _merge_type("auto", "enum") == "enum"


# ---------------------------------------------------------------------------
# Тесты EntityModelAnalyzer
# ---------------------------------------------------------------------------

class TestEntityModelAnalyzer:
    def setup_method(self):
        self.analyzer = EntityModelAnalyzer()

    def test_name(self):
        assert self.analyzer.name == "entity-model"

    def test_empty_findings(self):
        result = self.analyzer.analyze([])
        assert result.analyzer == "entity-model"
        assert result.data["entities"] == []

    def test_extracts_single_entity(self):
        findings = [
            make_rule("Movement", "status", "equalTo", "CREATED"),
            make_rule("Movement", "status", "equalTo", "APPROVED"),
            make_rule("Movement", "quantity", "equalTo", "50"),
        ]
        result = self.analyzer.analyze(findings)
        entities = {e["name"]: e for e in result.data["entities"]}
        assert "Movement" in entities
        fields = {f["name"]: f for f in entities["Movement"]["fields"]}
        assert fields["status"]["type"] == "enum"
        assert "CREATED" in fields["status"]["values"]
        assert "APPROVED" in fields["status"]["values"]
        assert fields["quantity"]["type"] == "integer"

    def test_enum_values_collected(self):
        findings = [
            make_rule("Movement", "status", "equalTo", "CREATED"),
            make_rule("Movement", "status", "equalTo", "APPROVED"),
            make_rule("Movement", "status", "equalTo", "COMPLETED"),
        ]
        result = self.analyzer.analyze(findings)
        entities = {e["name"]: e for e in result.data["entities"]}
        fields = {f["name"]: f for f in entities["Movement"]["fields"]}
        assert set(fields["status"]["values"]) == {"CREATED", "APPROVED", "COMPLETED"}

    def test_auto_type_for_not_null(self):
        findings = [make_rule("Document", "id", "notNullValue", "")]
        result = self.analyzer.analyze(findings)
        entities = {e["name"]: e for e in result.data["entities"]}
        fields = {f["name"]: f for f in entities["Document"]["fields"]}
        assert fields["id"]["type"] == "auto"

    def test_relation_detected_for_id_fields(self):
        findings = [make_rule("Movement", "warehouseId", "notNullValue", "")]
        result = self.analyzer.analyze(findings)
        entities = {e["name"]: e for e in result.data["entities"]}
        relations = entities["Movement"]["relations"]
        assert any(r["field"] == "warehouseId" and r["target"] == "Warehouse"
                   for r in relations)

    def test_url_entities_discovered(self):
        findings = [
            make_endpoint("GET", "/api/v1/reports"),
            make_endpoint("POST", "/api/v1/reports"),
        ]
        result = self.analyzer.analyze(findings)
        entity_names = {e["name"] for e in result.data["entities"]}
        assert "Report" in entity_names

    def test_ignores_non_business_rule_facts(self):
        f = Finding(
            probe="ra-assertion-rules",
            env="test",
            entity="Movement.status",
            fact="other_fact",
            data={"field": "status", "matcher": "equalTo", "expected": "CREATED"},
        )
        result = self.analyzer.analyze([f])
        assert result.data["entities"] == []

    def test_multiple_entities(self):
        findings = [
            make_rule("Movement", "status", "equalTo", "CREATED"),
            make_rule("Document", "status", "equalTo", "DRAFT"),
            make_rule("Stock", "totalQuantity", "equalTo", "100"),
        ]
        result = self.analyzer.analyze(findings)
        entity_names = {e["name"] for e in result.data["entities"]}
        assert {"Movement", "Document", "Stock"}.issubset(entity_names)

    def test_real_findings(self):
        """Интеграционный тест: из 154 findings — минимум 3 сущности."""
        findings_file = Path("findings/test_findings.json")
        if not findings_file.exists():
            pytest.skip("findings/test_findings.json не найден")

        raw = json.loads(findings_file.read_text(encoding="utf-8"))
        findings = [Finding(**r) for r in raw]

        result = self.analyzer.analyze(findings)
        entity_names = {e["name"] for e in result.data["entities"]}

        assert len(entity_names) >= 3
        assert "Movement" in entity_names
        assert "Document" in entity_names
        assert "Stock" in entity_names

        # Проверяем что у Movement есть enum-поле status
        movement = next(e for e in result.data["entities"] if e["name"] == "Movement")
        fields = {f["name"]: f for f in movement["fields"]}
        assert "status" in fields
        assert fields["status"]["type"] == "enum"
        assert len(fields["status"].get("values", [])) >= 2
