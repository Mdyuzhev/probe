"""Тесты зонда ra-auth-patterns."""

import textwrap
from pathlib import Path

import pytest

from probes.test.ra_auth_patterns import RaAuthPatterns, _parse_auth, _role_from_var

SAMPLE_DIR = Path(__file__).parent.parent / "examples" / "sample-restassured"


class TestHelpers:
    def test_role_from_var_operator(self):
        assert _role_from_var("operatorToken") == "OPERATOR"

    def test_role_from_var_manager(self):
        assert _role_from_var("MANAGER_TOKEN") == "MANAGER"

    def test_role_from_var_unknown(self):
        assert _role_from_var("someRandomVar") == ""

    def test_parse_auth_bearer_spec(self):
        body = '{ given().spec(operatorSpec).when().get("/x").then(); }'
        auth = _parse_auth(body)
        assert auth["auth_type"] == "bearer"
        assert auth["role"] == "OPERATOR"
        assert auth["is_public"] is False

    def test_parse_auth_basic(self):
        body = '{ given().auth().basic("admin", "secret").when().get("/x"); }'
        auth = _parse_auth(body)
        assert auth["auth_type"] == "basic"
        assert auth["username"] == "admin"

    def test_parse_auth_bearer_literal(self):
        body = '{ given().header("Authorization", "Bearer expired.token").when().get("/x"); }'
        auth = _parse_auth(body)
        assert auth["auth_type"] == "bearer"
        assert auth["token_variable"] == "literal"

    def test_parse_auth_public(self):
        body = '{ given().spec(baseSpec).when().get("/public"); }'
        auth = _parse_auth(body)
        assert auth["is_public"] is True
        assert auth["auth_type"] == "none"

    def test_parse_auth_no_spec_public(self):
        body = '{ given().when().get("/public"); }'
        auth = _parse_auth(body)
        assert auth["is_public"] is True


class TestRaAuthPatterns:
    def setup_method(self):
        self.probe = RaAuthPatterns()

    def test_probe_metadata(self):
        assert self.probe.name == "ra-auth-patterns"
        assert self.probe.env == "test"

    def test_finds_bearer_spec(self, tmp_path):
        java = textwrap.dedent("""\
            public class MovementTest extends BaseTest {
                @Test
                public void create_success() {
                    given()
                        .spec(operatorSpec)
                    .when()
                        .post("/movements")
                    .then()
                        .statusCode(201);
                }
            }
        """)
        (tmp_path / "MovementTest.java").write_text(java)
        findings = self.probe.scan(tmp_path)

        assert len(findings) == 1
        f = findings[0]
        assert f.fact == "auth_required"
        assert f.data["auth_type"] == "bearer"
        assert f.data["role"] == "OPERATOR"
        assert "POST" in f.entity

    def test_finds_basic_auth(self, tmp_path):
        java = textwrap.dedent("""\
            public class AdminTest extends BaseTest {
                @Test
                public void adminBasic_allowed() {
                    given()
                        .auth().basic("admin", "secret")
                    .when()
                        .get("/admin/users")
                    .then()
                        .statusCode(200);
                }
            }
        """)
        (tmp_path / "AdminTest.java").write_text(java)
        findings = self.probe.scan(tmp_path)

        assert len(findings) == 1
        f = findings[0]
        assert f.data["auth_type"] == "basic"
        assert f.data["username"] == "admin"

    def test_finds_public_endpoint(self, tmp_path):
        java = textwrap.dedent("""\
            public class PublicTest extends BaseTest {
                @Test
                public void noAuth_public_allowed() {
                    given()
                        .spec(baseSpec)
                    .when()
                        .get("/reports/daily")
                    .then()
                        .statusCode(200);
                }
            }
        """)
        (tmp_path / "PublicTest.java").write_text(java)
        findings = self.probe.scan(tmp_path)

        assert len(findings) == 1
        f = findings[0]
        assert f.fact == "public_endpoint"
        assert f.data["is_public"] is True

    def test_noauth_401_not_public(self, tmp_path):
        java = textwrap.dedent("""\
            public class NegTest extends BaseTest {
                @Test
                public void noAuth_returns401() {
                    given()
                        .spec(baseSpec)
                    .when()
                        .post("/movements")
                    .then()
                        .statusCode(401);
                }
            }
        """)
        (tmp_path / "NegTest.java").write_text(java)
        findings = self.probe.scan(tmp_path)

        assert len(findings) == 1
        assert findings[0].fact == "auth_required"
        assert findings[0].data["is_public"] is False

    def test_role_tag(self, tmp_path):
        java = textwrap.dedent("""\
            public class ManagerTest extends BaseTest {
                @Test
                public void managerAccess() {
                    given().spec(managerSpec).when().get("/reports").then().statusCode(200);
                }
            }
        """)
        (tmp_path / "ManagerTest.java").write_text(java)
        findings = self.probe.scan(tmp_path)

        assert any("role:manager" in f.tags for f in findings)

    def test_empty_dir(self, tmp_path):
        assert self.probe.scan(tmp_path) == []

    def test_scan_sample_restassured(self):
        """Интеграционный тест на полигоне."""
        if not SAMPLE_DIR.exists():
            pytest.skip("Полигон sample-restassured не найден")

        findings = self.probe.scan(SAMPLE_DIR)

        assert len(findings) >= 5

        facts = {f.fact for f in findings}
        assert "auth_required" in facts
        assert "public_endpoint" in facts

        roles = {f.data["role"] for f in findings if f.data["role"]}
        assert "OPERATOR" in roles
        assert "MANAGER" in roles or "ADMIN" in roles

        auth_types = {f.data["auth_type"] for f in findings}
        assert "bearer" in auth_types
        assert "basic" in auth_types
