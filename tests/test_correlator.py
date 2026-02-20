"""Тесты Correlator — синтез findings в Product Map."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from probe.correlator import correlate, load_findings
from probe.models import Dossier, Finding

SAMPLE_DIR = Path(__file__).parent.parent / "examples" / "sample-restassured"


def _make_dossier(*findings: Finding) -> Dossier:
    d = Dossier(target="/test", env="test")
    d.findings = list(findings)
    return d


def _endpoint_finding(entity: str, test_class: str = "SomeTest") -> Finding:
    return Finding(
        probe="ra-endpoint-census", env="test", entity=entity,
        fact="endpoint_tested",
        data={"method": entity.split()[0], "path": entity.split()[1],
              "test_class": test_class, "test_method": "testMethod"},
        tags=["api", "endpoint"],
    )


def _auth_finding(entity: str, role: str = "OPERATOR",
                  is_public: bool = False, test_class: str = "SomeTest") -> Finding:
    fact = "public_endpoint" if is_public else "auth_required"
    return Finding(
        probe="ra-auth-patterns", env="test", entity=entity,
        fact=fact,
        data={"auth_type": "none" if is_public else "bearer", "role": "" if is_public else role,
              "is_public": is_public, "test_class": test_class, "test_method": "t"},
        tags=["auth"],
    )


def _status_finding(test_class: str, code: int) -> Finding:
    return Finding(
        probe="ra-expected-status", env="test",
        entity=f"{test_class}::someMethod",
        fact="expected_status",
        data={"status_code": code, "is_success": code < 400,
              "test_class": test_class, "test_method": "someMethod", "context": "happy_path"},
        tags=["status"],
    )


def _rule_finding(field: str, rule_text: str, test_class: str = "RuleTest") -> Finding:
    return Finding(
        probe="ra-assertion-rules", env="test",
        entity=f"Entity.{field}",
        fact="business_rule",
        data={"field": field, "matcher": "equalTo", "expected": "val",
              "rule_text": rule_text, "test_class": test_class,
              "test_method": "t", "is_negative_test": False},
        tags=["rule", "business-rule"],
        location=f"{test_class}.java:10",
    )


def _workflow_finding(name: str, steps: list) -> Finding:
    return Finding(
        probe="ra-test-sequence", env="test",
        entity=f"workflow:{name}",
        fact="business_workflow",
        data={"workflow_name": name, "test_class": f"{name}Test",
              "step_count": len(steps), "steps": steps},
        tags=["workflow", "sequence"],
        location=f"{name}Test.java",
    )


class TestCorrelateHeader:
    def test_contains_target(self):
        d = _make_dossier()
        result = correlate(d)
        assert "/test" in result

    def test_contains_findings_count(self):
        d = _make_dossier(_endpoint_finding("GET /items"))
        result = correlate(d)
        assert "1" in result

    def test_returns_string(self):
        assert isinstance(correlate(_make_dossier()), str)


class TestApiSurface:
    def test_endpoint_in_table(self):
        d = _make_dossier(_endpoint_finding("GET /movements"))
        result = correlate(d)
        assert "GET /movements" in result
        assert "API Surface" in result

    def test_auth_role_shown(self):
        d = _make_dossier(
            _endpoint_finding("POST /movements", "MovTest"),
            _auth_finding("POST /movements", role="OPERATOR", test_class="MovTest"),
        )
        result = correlate(d)
        assert "OPERATOR" in result

    def test_public_shown(self):
        d = _make_dossier(
            _endpoint_finding("GET /public", "PubTest"),
            _auth_finding("GET /public", is_public=True, test_class="PubTest"),
        )
        result = correlate(d)
        assert "public" in result

    def test_statuses_via_test_class(self):
        d = _make_dossier(
            _endpoint_finding("POST /items", "ItemTest"),
            _status_finding("ItemTest", 201),
            _status_finding("ItemTest", 400),
        )
        result = correlate(d)
        assert "201" in result
        assert "400" in result

    def test_empty_findings_no_table(self):
        result = correlate(_make_dossier())
        assert "API Surface" not in result


class TestBusinessRules:
    def test_rule_numbered(self):
        d = _make_dossier(
            _rule_finding("status", "поле status = CREATED"),
            _rule_finding("id", "поле id не пустое (not null)"),
        )
        result = correlate(d)
        assert "R01" in result
        assert "R02" in result
        assert "Бизнес-правила" in result

    def test_rule_text_shown(self):
        d = _make_dossier(_rule_finding("qty", "поле qty > 0"))
        result = correlate(d)
        assert "поле qty > 0" in result

    def test_no_rules_no_section(self):
        d = _make_dossier(_endpoint_finding("GET /x"))
        result = correlate(d)
        assert "Бизнес-правила" not in result


class TestWorkflows:
    def test_workflow_section(self):
        steps = [
            {"order": 1, "action": "POST /items", "method": "POST",
             "path": "/items", "status_code": 201, "test_method": "step1"},
            {"order": 2, "action": "GET /items/1", "method": "GET",
             "path": "/items/1", "status_code": 200, "test_method": "step2"},
        ]
        d = _make_dossier(_workflow_finding("ItemFlow", steps))
        result = correlate(d)
        assert "Workflows" in result
        assert "ItemFlow" in result
        assert "POST /items" in result
        assert "GET /items/1" in result

    def test_no_workflows_no_section(self):
        d = _make_dossier(_endpoint_finding("GET /x"))
        result = correlate(d)
        assert "Workflows" not in result


class TestRoleMatrix:
    def test_role_matrix_section(self):
        d = _make_dossier(
            _auth_finding("GET /movements", role="OPERATOR"),
            _auth_finding("GET /reports", role="MANAGER"),
            _auth_finding("GET /reports", role="OPERATOR"),
        )
        result = correlate(d)
        assert "Ролевая модель" in result
        assert "OPERATOR" in result
        assert "MANAGER" in result

    def test_public_in_matrix(self):
        d = _make_dossier(_auth_finding("GET /pub", is_public=True))
        result = correlate(d)
        assert "PUBLIC" in result


class TestLoadFindings:
    def test_load_from_file(self, tmp_path):
        f = _endpoint_finding("GET /x")
        data = [f.model_dump(mode="json")]
        (tmp_path / "test_findings.json").write_text(
            json.dumps(data, ensure_ascii=False), encoding="utf-8"
        )
        dossier = load_findings(tmp_path / "test_findings.json")
        assert len(dossier.findings) == 1
        assert dossier.findings[0].entity == "GET /x"

    def test_load_from_dir(self, tmp_path):
        f1 = _endpoint_finding("GET /a")
        f2 = _endpoint_finding("POST /b")
        (tmp_path / "a.json").write_text(json.dumps([f1.model_dump(mode="json")]))
        (tmp_path / "b.json").write_text(json.dumps([f2.model_dump(mode="json")]))
        dossier = load_findings(tmp_path)
        assert len(dossier.findings) == 2

    def test_out_path_writes_file(self, tmp_path):
        d = _make_dossier(_endpoint_finding("GET /x"))
        out = tmp_path / "map.md"
        correlate(d, out_path=out)
        assert out.exists()
        assert "Product Map" in out.read_text(encoding="utf-8")


class TestIntegration:
    def test_scan_and_correlate(self):
        """Полный цикл: scan полигона → correlate → Product Map."""
        if not SAMPLE_DIR.exists():
            pytest.skip("Полигон sample-restassured не найден")

        from probe.runner import run_probes
        from probes.test.ra_endpoint_census import RaEndpointCensus
        from probes.test.ra_expected_status import RaExpectedStatus
        from probes.test.ra_assertion_rules import RaAssertionRules
        from probes.test.ra_auth_patterns import RaAuthPatterns
        from probes.test.ra_test_sequence import RaTestSequence

        probes = [RaEndpointCensus(), RaExpectedStatus(),
                  RaAssertionRules(), RaAuthPatterns(), RaTestSequence()]
        dossier = run_probes(probes, SAMPLE_DIR, "test")
        result = correlate(dossier)

        assert "Product Map" in result
        assert "API Surface" in result
        assert "Бизнес-правила" in result
        assert "Workflows" in result
        assert "Ролевая модель" in result
        assert "OPERATOR" in result
        assert "MovementFlow" in result
        assert len(result) > 500
