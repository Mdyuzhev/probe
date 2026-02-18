"""Тесты зонда ra-endpoint-census."""

import textwrap
from pathlib import Path

import pytest

from probes.test.ra_endpoint_census import RaEndpointCensus, _normalize_url


SAMPLE_DIR = Path(__file__).parent.parent / "examples" / "sample-restassured"


class TestNormalizeUrl:
    def test_simple_path(self):
        assert _normalize_url("/api/v1/movements") == "/api/v1/movements"

    def test_strips_host(self):
        assert _normalize_url("http://localhost:8080/api/v1/test") == "/api/v1/test"

    def test_collapses_slashes(self):
        assert _normalize_url("//api//v1//") == "/api/v1/"

    def test_empty_becomes_slash(self):
        assert _normalize_url("") == "/"


class TestRaEndpointCensus:
    def setup_method(self):
        self.probe = RaEndpointCensus()

    def test_probe_metadata(self):
        assert self.probe.name == "ra-endpoint-census"
        assert self.probe.env == "test"

    def test_scan_inline_java(self, tmp_path):
        """Зонд находит эндпоинты из минимального Java-файла."""
        java = textwrap.dedent("""\
            public class SimpleTest {
                @Test
                public void testGet() {
                    given().when().get("/api/v1/items").then().statusCode(200);
                }
                @Test
                public void testPost() {
                    given().when().post("/api/v1/items").then().statusCode(201);
                }
            }
        """)
        (tmp_path / "SimpleTest.java").write_text(java)
        findings = self.probe.scan(tmp_path)

        methods = {f.data["method"] for f in findings}
        paths = {f.data["path"] for f in findings}

        assert "GET" in methods
        assert "POST" in methods
        assert "/api/v1/items" in paths

    def test_scan_path_param(self, tmp_path):
        """Зонд распознаёт path-параметры в фигурных скобках."""
        java = textwrap.dedent("""\
            public class ParamTest {
                @Test
                public void testGetById() {
                    given().when().get("/api/v1/items/{id}").then().statusCode(200);
                }
            }
        """)
        (tmp_path / "ParamTest.java").write_text(java)
        findings = self.probe.scan(tmp_path)

        assert len(findings) == 1
        assert findings[0].data["has_path_params"] is True
        assert "path-param" in findings[0].tags

    def test_scan_put_delete(self, tmp_path):
        """Зонд находит PUT и DELETE методы."""
        java = textwrap.dedent("""\
            public class CrudTest {
                @Test
                public void testUpdate() {
                    given().when().put("/items/{id}").then().statusCode(200);
                }
                @Test
                public void testDelete() {
                    given().when().delete("/items/{id}").then().statusCode(204);
                }
            }
        """)
        (tmp_path / "CrudTest.java").write_text(java)
        findings = self.probe.scan(tmp_path)

        methods = {f.data["method"] for f in findings}
        assert "PUT" in methods
        assert "DELETE" in methods

    def test_findings_valid_model(self, tmp_path):
        """Все findings соответствуют модели Finding."""
        java = textwrap.dedent("""\
            public class ValidTest {
                @Test
                public void test() {
                    given().when().get("/check").then().statusCode(200);
                }
            }
        """)
        (tmp_path / "ValidTest.java").write_text(java)
        findings = self.probe.scan(tmp_path)

        assert len(findings) >= 1
        f = findings[0]
        assert f.probe == "ra-endpoint-census"
        assert f.env == "test"
        assert f.fact == "endpoint_tested"
        assert "method" in f.data
        assert "path" in f.data
        assert 0.0 <= f.confidence <= 1.0

    def test_scan_empty_dir(self, tmp_path):
        """Пустая директория → пустой список."""
        findings = self.probe.scan(tmp_path)
        assert findings == []

    def test_scan_sample_restassured(self):
        """Интеграционный тест: зонд находит ≥10 эндпоинтов в полигоне."""
        if not SAMPLE_DIR.exists():
            pytest.skip("Полигон sample-restassured не найден")

        findings = self.probe.scan(SAMPLE_DIR)

        assert len(findings) >= 10, f"Ожидалось ≥10 findings, получено {len(findings)}"
        # Проверяем наличие ключевых эндпоинтов
        methods_found = {f.data["method"] for f in findings}
        assert "GET" in methods_found
        assert "POST" in methods_found
        assert "PUT" in methods_found

    def test_test_class_field(self, tmp_path):
        """Поле test_class содержит имя Java-класса."""
        java = textwrap.dedent("""\
            public class MyFeatureTest {
                @Test
                public void myTest() {
                    given().when().get("/feature").then().statusCode(200);
                }
            }
        """)
        (tmp_path / "MyFeatureTest.java").write_text(java)
        findings = self.probe.scan(tmp_path)

        assert findings[0].data["test_class"] == "MyFeatureTest"
