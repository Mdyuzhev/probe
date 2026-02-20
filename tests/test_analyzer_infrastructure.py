"""Тесты инфраструктуры аналитиков: BaseAnalyzer, AnalysisResult, load_findings."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from probe.analyzers.base import BaseAnalyzer, load_findings
from probe.models import AnalysisResult, Finding


# ---------------------------------------------------------------------------
# Фикстуры
# ---------------------------------------------------------------------------

def make_finding(**kwargs) -> Finding:
    defaults = {
        "probe": "test-probe",
        "env": "test",
        "entity": "GET /api/v1/test",
        "fact": "endpoint_exists",
        "data": {"method": "GET"},
    }
    defaults.update(kwargs)
    return Finding(**defaults)


def make_findings_dir(findings: list[Finding]) -> Path:
    """Создаёт временную директорию с JSON-файлом findings."""
    tmp = Path(tempfile.mkdtemp())
    out = tmp / "test_findings.json"
    out.write_text(
        json.dumps([f.model_dump(mode="json") for f in findings], ensure_ascii=False),
        encoding="utf-8",
    )
    return tmp


# ---------------------------------------------------------------------------
# AnalysisResult
# ---------------------------------------------------------------------------

class TestAnalysisResult:
    def test_create_minimal(self):
        r = AnalysisResult(analyzer="test-analyzer", data={}, summary="ок")
        assert r.analyzer == "test-analyzer"
        assert r.confidence == 1.0
        assert r.timestamp is not None

    def test_confidence_bounds(self):
        r = AnalysisResult(analyzer="a", data={}, summary="x", confidence=0.5)
        assert r.confidence == 0.5

    def test_confidence_out_of_range(self):
        with pytest.raises(Exception):
            AnalysisResult(analyzer="a", data={}, summary="x", confidence=1.5)

    def test_json_serialization(self):
        r = AnalysisResult(analyzer="a", data={"key": "val"}, summary="ok")
        d = r.model_dump(mode="json")
        assert d["analyzer"] == "a"
        assert d["data"] == {"key": "val"}
        assert isinstance(d["timestamp"], str)


# ---------------------------------------------------------------------------
# load_findings
# ---------------------------------------------------------------------------

class TestLoadFindings:
    def test_loads_from_directory(self):
        findings = [make_finding(fact="fact_a"), make_finding(fact="fact_b")]
        tmp_dir = make_findings_dir(findings)
        result = load_findings(tmp_dir)
        assert len(result) == 2
        assert {f.fact for f in result} == {"fact_a", "fact_b"}

    def test_empty_directory(self):
        tmp = Path(tempfile.mkdtemp())
        result = load_findings(tmp)
        assert result == []

    def test_multiple_files(self):
        tmp = Path(tempfile.mkdtemp())
        for i in range(3):
            f = make_finding(fact=f"fact_{i}")
            (tmp / f"file_{i}.json").write_text(
                json.dumps([f.model_dump(mode="json")]), encoding="utf-8"
            )
        result = load_findings(tmp)
        assert len(result) == 3


# ---------------------------------------------------------------------------
# BaseAnalyzer
# ---------------------------------------------------------------------------

class TestBaseAnalyzer:
    def test_not_implemented(self):
        analyzer = BaseAnalyzer()
        with pytest.raises(NotImplementedError):
            analyzer.analyze([])

    def test_subclass_works(self):
        class DummyAnalyzer(BaseAnalyzer):
            name = "dummy"
            description = "Тестовый аналитик"

            def analyze(self, findings: list[Finding]) -> AnalysisResult:
                return AnalysisResult(
                    analyzer=self.name,
                    data={"count": len(findings)},
                    summary=f"Обработано {len(findings)} findings",
                )

        a = DummyAnalyzer()
        findings = [make_finding(), make_finding()]
        result = a.analyze(findings)
        assert result.analyzer == "dummy"
        assert result.data["count"] == 2
