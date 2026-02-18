"""Тесты зонда ra-expected-status."""

import textwrap
from pathlib import Path

import pytest

from probes.test.ra_expected_status import RaExpectedStatus, _status_context


SAMPLE_DIR = Path(__file__).parent.parent / "examples" / "sample-restassured"


class TestStatusContext:
    def test_2xx_happy_path(self):
        assert _status_context(200) == "happy_path"
        assert _status_context(201) == "happy_path"
        assert _status_context(204) == "happy_path"

    def test_400_validation(self):
        assert _status_context(400) == "validation_error"

    def test_401_403_auth(self):
        assert _status_context(401) == "auth"
        assert _status_context(403) == "auth"

    def test_404_not_found(self):
        assert _status_context(404) == "not_found"

    def test_409_422_conflict(self):
        assert _status_context(409) == "conflict"
        assert _status_context(422) == "conflict"

    def test_500_server_error(self):
        assert _status_context(500) == "server_error"

    def test_other(self):
        assert _status_context(301) == "other"


class TestRaExpectedStatus:
    def setup_method(self):
        self.probe = RaExpectedStatus()

    def test_probe_metadata(self):
        assert self.probe.name == "ra-expected-status"
        assert self.probe.env == "test"

    def test_finds_simple_statuscode(self, tmp_path):
        java = textwrap.dedent("""\
            public class SimpleTest {
                @Test
                public void testOk() {
                    given().when().get("/items").then().statusCode(200);
                }
            }
        """)
        (tmp_path / "SimpleTest.java").write_text(java)
        findings = self.probe.scan(tmp_path)

        assert len(findings) == 1
        assert findings[0].data["status_code"] == 200
        assert findings[0].data["is_success"] is True
        assert findings[0].data["context"] == "happy_path"
        assert findings[0].confidence == 1.0

    def test_finds_multiple_statuses(self, tmp_path):
        java = textwrap.dedent("""\
            public class MultiTest {
                @Test
                public void testCreate() {
                    given().when().post("/items").then().statusCode(201);
                }
                @Test
                public void testBadRequest() {
                    given().when().post("/items").then().statusCode(400);
                }
                @Test
                public void testNotFound() {
                    given().when().get("/items/999").then().statusCode(404);
                }
            }
        """)
        (tmp_path / "MultiTest.java").write_text(java)
        findings = self.probe.scan(tmp_path)

        codes = {f.data["status_code"] for f in findings}
        assert 201 in codes
        assert 400 in codes
        assert 404 in codes

    def test_is_success_flag(self, tmp_path):
        java = textwrap.dedent("""\
            public class FlagTest {
                @Test
                public void ok() { given().when().get("/x").then().statusCode(200); }
                @Test
                public void err() { given().when().get("/x").then().statusCode(401); }
            }
        """)
        (tmp_path / "FlagTest.java").write_text(java)
        findings = self.probe.scan(tmp_path)

        by_code = {f.data["status_code"]: f for f in findings}
        assert by_code[200].data["is_success"] is True
        assert by_code[401].data["is_success"] is False

    def test_context_tags_present(self, tmp_path):
        java = textwrap.dedent("""\
            public class TagTest {
                @Test
                public void test() { given().when().post("/x").then().statusCode(403); }
            }
        """)
        (tmp_path / "TagTest.java").write_text(java)
        findings = self.probe.scan(tmp_path)

        assert len(findings) == 1
        assert "auth" in findings[0].tags
        assert "contract" in findings[0].tags

    def test_test_method_captured(self, tmp_path):
        java = textwrap.dedent("""\
            public class MethodTest {
                @Test
                public void specificMethodName() {
                    given().when().get("/x").then().statusCode(200);
                }
            }
        """)
        (tmp_path / "MethodTest.java").write_text(java)
        findings = self.probe.scan(tmp_path)

        assert findings[0].data["test_method"] == "specificMethodName"
        assert findings[0].data["test_class"] == "MethodTest"

    def test_empty_dir(self, tmp_path):
        assert self.probe.scan(tmp_path) == []

    def test_scan_sample_restassured(self):
        """Интеграционный тест на полигоне."""
        if not SAMPLE_DIR.exists():
            pytest.skip("Полигон sample-restassured не найден")

        findings = self.probe.scan(SAMPLE_DIR)
        codes = {f.data["status_code"] for f in findings}

        assert len(findings) >= 15
        # Ключевые коды из полигона
        assert 200 in codes
        assert 201 in codes
        assert 400 in codes
        assert 401 in codes
        assert 403 in codes
        assert 404 in codes

        contexts = {f.data["context"] for f in findings}
        assert "happy_path" in contexts
        assert "auth" in contexts
        assert "not_found" in contexts
