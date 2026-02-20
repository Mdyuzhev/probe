"""Тесты зонда ra-test-sequence."""

import textwrap
from pathlib import Path

import pytest

from probes.test.ra_test_sequence import (
    RaTestSequence,
    _workflow_name,
    _extract_ordered_steps,
    _build_step,
)

SAMPLE_DIR = Path(__file__).parent.parent / "examples" / "sample-restassured"


class TestHelpers:
    def test_workflow_name_strips_test(self):
        assert _workflow_name("MovementFlowTest") == "MovementFlow"
        assert _workflow_name("DocumentApprovalTest") == "DocumentApproval"
        assert _workflow_name("SomeFlow") == "SomeFlow"

    def test_extract_ordered_steps_basic(self):
        source = textwrap.dedent("""\
            @TestMethodOrder(MethodOrderer.OrderAnnotation.class)
            public class FlowTest {
                @Test
                @Order(1)
                public void stepOne() {
                    given().spec(s).when().post("/items").then().statusCode(201);
                }
                @Test
                @Order(2)
                public void stepTwo() {
                    given().spec(s).when().get("/items/1").then().statusCode(200);
                }
            }
        """)
        steps = _extract_ordered_steps(source)
        assert len(steps) == 2
        assert steps[0][0] == 1  # order
        assert steps[0][1] == "stepOne"
        assert steps[1][0] == 2
        assert steps[1][1] == "stepTwo"

    def test_extract_ordered_steps_sorted(self):
        source = textwrap.dedent("""\
            @TestMethodOrder(MethodOrderer.OrderAnnotation.class)
            public class FlowTest {
                @Order(3)
                public void stepC() { given().when().get("/c"); }
                @Order(1)
                public void stepA() { given().when().get("/a"); }
                @Order(2)
                public void stepB() { given().when().get("/b"); }
            }
        """)
        steps = _extract_ordered_steps(source)
        orders = [s[0] for s in steps]
        assert orders == [1, 2, 3]

    def test_build_step_extracts_http(self):
        body = '{ given().spec(s).when().post("/movements").then().statusCode(201); }'
        step = _build_step(1, "createMovement", body)
        assert step["method"] == "POST"
        assert step["path"] == "/movements"
        assert step["status_code"] == 201
        assert step["action"] == "POST /movements"

    def test_build_step_no_http(self):
        body = '{ System.out.println("no http"); }'
        step = _build_step(1, "setup", body)
        assert step["action"] == ""
        assert step["status_code"] == 0


class TestRaTestSequence:
    def setup_method(self):
        self.probe = RaTestSequence()

    def test_probe_metadata(self):
        assert self.probe.name == "ra-test-sequence"
        assert self.probe.env == "test"

    def test_ignores_unordered_class(self, tmp_path):
        java = textwrap.dedent("""\
            public class MovementTest {
                @Test
                public void create() {
                    given().when().post("/movements").then().statusCode(201);
                }
            }
        """)
        (tmp_path / "MovementTest.java").write_text(java)
        findings = self.probe.scan(tmp_path)
        assert findings == []

    def test_finds_ordered_workflow(self, tmp_path):
        java = textwrap.dedent("""\
            @TestMethodOrder(MethodOrderer.OrderAnnotation.class)
            public class ReceiptFlowTest {
                @Test
                @Order(1)
                public void createReceipt() {
                    given().spec(s).when().post("/receipts").then().statusCode(201);
                }
                @Test
                @Order(2)
                public void confirmReceipt() {
                    given().spec(s).when().put("/receipts/1/confirm").then().statusCode(200);
                }
            }
        """)
        (tmp_path / "ReceiptFlowTest.java").write_text(java)
        findings = self.probe.scan(tmp_path)

        assert len(findings) == 1
        f = findings[0]
        assert f.fact == "business_workflow"
        assert f.entity == "workflow:ReceiptFlow"
        assert f.data["workflow_name"] == "ReceiptFlow"
        assert f.data["test_class"] == "ReceiptFlowTest"
        assert f.data["step_count"] == 2
        assert "workflow" in f.tags
        assert "sequence" in f.tags

    def test_steps_content(self, tmp_path):
        java = textwrap.dedent("""\
            @TestMethodOrder(MethodOrderer.OrderAnnotation.class)
            public class ShipFlowTest {
                @Order(1)
                public void step1() {
                    given().when().post("/shipments").then().statusCode(201);
                }
                @Order(2)
                public void step2() {
                    given().when().get("/shipments/1").then().statusCode(200);
                }
            }
        """)
        (tmp_path / "ShipFlowTest.java").write_text(java)
        findings = self.probe.scan(tmp_path)

        steps = findings[0].data["steps"]
        assert steps[0]["order"] == 1
        assert steps[0]["method"] == "POST"
        assert steps[1]["order"] == 2
        assert steps[1]["method"] == "GET"

    def test_empty_dir(self, tmp_path):
        assert self.probe.scan(tmp_path) == []

    def test_scan_sample_restassured(self):
        """Интеграционный тест на полигоне."""
        if not SAMPLE_DIR.exists():
            pytest.skip("Полигон sample-restassured не найден")

        findings = self.probe.scan(SAMPLE_DIR)

        # Два класса с @TestMethodOrder: MovementFlowTest, DocumentApprovalTest
        assert len(findings) >= 2

        names = {f.data["workflow_name"] for f in findings}
        assert "MovementFlow" in names
        assert "DocumentApproval" in names

        # MovementFlow: 6 шагов
        mf = next(f for f in findings if f.data["workflow_name"] == "MovementFlow")
        assert mf.data["step_count"] == 6
        actions = [s["action"] for s in mf.data["steps"]]
        assert "POST /movements" in actions

        # Все findings помечены тегами и имеют confidence 1.0
        assert all("workflow" in f.tags for f in findings)
        assert all(f.confidence == 1.0 for f in findings)
