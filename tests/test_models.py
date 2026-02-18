"""Тесты моделей данных PROBE."""

import pytest
from probe.models import Dossier, Finding, Diff


def make_finding(**kwargs) -> Finding:
    """Создать finding с минимальными обязательными полями."""
    defaults = {
        "probe": "test-probe",
        "env": "test",
        "entity": "GET /api/v1/test",
        "fact": "endpoint_exists",
        "data": {"method": "GET", "path": "/api/v1/test"},
    }
    defaults.update(kwargs)
    return Finding(**defaults)


class TestFinding:
    def test_create_minimal(self):
        f = make_finding()
        assert f.probe == "test-probe"
        assert f.env == "test"
        assert f.confidence == 1.0
        assert f.tags == []
        assert f.ts is not None

    def test_confidence_bounds(self):
        f = make_finding(confidence=0.5)
        assert f.confidence == 0.5

    def test_confidence_out_of_range(self):
        with pytest.raises(Exception):
            make_finding(confidence=1.5)

    def test_json_serialization(self):
        f = make_finding(tags=["api", "get"])
        d = f.model_dump(mode="json")
        assert d["probe"] == "test-probe"
        assert d["tags"] == ["api", "get"]
        assert isinstance(d["ts"], str)


class TestDossier:
    def test_create_empty(self):
        d = Dossier(target="/some/path", env="test")
        assert d.findings == []

    def test_by_probe(self):
        d = Dossier(target="/path", env="test")
        d.findings.append(make_finding(probe="probe-a"))
        d.findings.append(make_finding(probe="probe-b"))
        d.findings.append(make_finding(probe="probe-a"))
        assert len(d.by_probe("probe-a")) == 2
        assert len(d.by_probe("probe-b")) == 1

    def test_by_fact(self):
        d = Dossier(target="/path", env="test")
        d.findings.append(make_finding(fact="endpoint_exists"))
        d.findings.append(make_finding(fact="status_code"))
        assert len(d.by_fact("endpoint_exists")) == 1

    def test_by_tag(self):
        d = Dossier(target="/path", env="test")
        d.findings.append(make_finding(tags=["api", "get"]))
        d.findings.append(make_finding(tags=["db"]))
        assert len(d.by_tag("api")) == 1
        assert len(d.by_tag("db")) == 1
        assert len(d.by_tag("missing")) == 0


class TestDiff:
    def test_create_empty(self):
        diff = Diff()
        assert diff.added == []
        assert diff.removed == []
        assert diff.changed == []
