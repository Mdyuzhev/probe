"""Тесты зонда ra-assertion-rules."""

import textwrap
from pathlib import Path

import pytest

from probes.test.ra_assertion_rules import (
    RaAssertionRules,
    _entity_from_class,
    _is_negative,
    _make_rule_text,
)

SAMPLE_DIR = Path(__file__).parent.parent / "examples" / "sample-restassured"


class TestHelpers:
    def test_entity_from_class(self):
        assert _entity_from_class("MovementCreateTest") == "Movement"
        assert _entity_from_class("StockTest") == "Stock"
        assert _entity_from_class("DocumentApprovalTest") == "Document"

    def test_is_negative_by_method(self):
        assert _is_negative("createMovement_negativeQuantity_returns400", "Test") is True
        assert _is_negative("createMovement_success_returns201", "Test") is False

    def test_is_negative_by_class(self):
        assert _is_negative(None, "MovementNegativeTest") is True
        assert _is_negative(None, "MovementCreateTest") is False

    def test_make_rule_text_equal(self):
        text = _make_rule_text("status", "equalTo", "created")
        assert "status" in text
        assert "created" in text

    def test_make_rule_text_not_null(self):
        text = _make_rule_text("id", "notNullValue", "")
        assert "id" in text
        assert "null" in text

    def test_make_rule_text_unknown_matcher(self):
        text = _make_rule_text("x", "customMatcher", "val")
        assert "x" in text


class TestRaAssertionRules:
    def setup_method(self):
        self.probe = RaAssertionRules()

    def test_probe_metadata(self):
        assert self.probe.name == "ra-assertion-rules"
        assert self.probe.env == "test"

    def test_finds_equalTo(self, tmp_path):
        java = textwrap.dedent("""\
            public class MovementTest {
                @Test
                public void testCreate() {
                    given().when().post("/movements")
                    .then().statusCode(201)
                    .body("status", equalTo("CREATED"));
                }
            }
        """)
        (tmp_path / "MovementTest.java").write_text(java)
        findings = self.probe.scan(tmp_path)

        assert len(findings) == 1
        f = findings[0]
        assert f.data["field"] == "status"
        assert f.data["matcher"] == "equalTo"
        assert f.data["expected"] == "CREATED"
        assert f.data["is_negative_test"] is False
        assert "business-rule" in f.tags

    def test_finds_notNullValue(self, tmp_path):
        java = textwrap.dedent("""\
            public class OrderTest {
                @Test
                public void testId() {
                    given().when().post("/orders")
                    .then().body("id", notNullValue());
                }
            }
        """)
        (tmp_path / "OrderTest.java").write_text(java)
        findings = self.probe.scan(tmp_path)

        assert len(findings) == 1
        assert findings[0].data["matcher"] == "notNullValue"
        assert findings[0].data["field"] == "id"

    def test_negative_test_detection(self, tmp_path):
        java = textwrap.dedent("""\
            public class MovementNegativeTest {
                @Test
                public void createInvalid_returns400() {
                    given().when().post("/movements")
                    .then().statusCode(400)
                    .body("error", equalTo("VALIDATION_ERROR"));
                }
            }
        """)
        (tmp_path / "MovementNegativeTest.java").write_text(java)
        findings = self.probe.scan(tmp_path)

        assert len(findings) == 1
        assert findings[0].data["is_negative_test"] is True
        assert "constraint" in findings[0].tags

    def test_entity_derived_from_class(self, tmp_path):
        java = textwrap.dedent("""\
            public class DocumentTest {
                @Test
                public void test() {
                    given().when().get("/documents/1")
                    .then().body("status", equalTo("APPROVED"));
                }
            }
        """)
        (tmp_path / "DocumentTest.java").write_text(java)
        findings = self.probe.scan(tmp_path)

        assert findings[0].entity.startswith("Document.")

    def test_multiple_body_assertions(self, tmp_path):
        java = textwrap.dedent("""\
            public class StockTest {
                @Test
                public void testStock() {
                    given().when().get("/stock")
                    .then()
                    .body("items", hasSize(3))
                    .body("total", greaterThan(0))
                    .body("warehouseId", notNullValue());
                }
            }
        """)
        (tmp_path / "StockTest.java").write_text(java)
        findings = self.probe.scan(tmp_path)

        assert len(findings) == 3
        matchers = {f.data["matcher"] for f in findings}
        assert "hasSize" in matchers
        assert "greaterThan" in matchers
        assert "notNullValue" in matchers

    def test_rule_text_generated(self, tmp_path):
        java = textwrap.dedent("""\
            public class RuleTest {
                @Test
                public void test() {
                    given().when().get("/x")
                    .then().body("quantity", greaterThan(0));
                }
            }
        """)
        (tmp_path / "RuleTest.java").write_text(java)
        findings = self.probe.scan(tmp_path)

        assert findings[0].data["rule_text"]
        assert "quantity" in findings[0].data["rule_text"]

    def test_empty_dir(self, tmp_path):
        assert self.probe.scan(tmp_path) == []

    def test_scan_sample_restassured(self):
        """Интеграционный тест на полигоне."""
        if not SAMPLE_DIR.exists():
            pytest.skip("Полигон sample-restassured не найден")

        findings = self.probe.scan(SAMPLE_DIR)

        assert len(findings) >= 10
        matchers = {f.data["matcher"] for f in findings}
        assert "equalTo" in matchers
        assert "notNullValue" in matchers

        # Есть и позитивные, и негативные
        neg = [f for f in findings if f.data["is_negative_test"]]
        pos = [f for f in findings if not f.data["is_negative_test"]]
        assert len(neg) > 0
        assert len(pos) > 0
