"""Тесты аналитика state-machine."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from probe.analyzers.state_machine import (
    StateMachineAnalyzer,
    _entity_from_workflow,
    _trigger_from_path,
)
from probe.models import Finding


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def make_status_rule(entity: str, status_value: str) -> Finding:
    return Finding(
        probe="ra-assertion-rules",
        env="test",
        entity=f"{entity}.status",
        fact="business_rule",
        data={
            "field": "status",
            "matcher": "equalTo",
            "expected": status_value,
            "rule_text": f"поле status = {status_value}",
            "test_class": "TestClass",
            "test_method": "test_method",
            "is_negative_test": False,
        },
    )


def make_workflow(workflow_name: str, steps: list[dict]) -> Finding:
    return Finding(
        probe="ra-test-sequence",
        env="test",
        entity=f"workflow:{workflow_name}",
        fact="business_workflow",
        data={
            "workflow_name": workflow_name,
            "test_class": f"{workflow_name}Test",
            "step_count": len(steps),
            "steps": steps,
        },
        location=f"src/test/java/{workflow_name}Test.java",
    )


# ---------------------------------------------------------------------------
# Тесты вспомогательных функций
# ---------------------------------------------------------------------------

class TestHelpers:
    def test_entity_from_flow(self):
        assert _entity_from_workflow("MovementFlow") == "Movement"

    def test_entity_from_approval(self):
        assert _entity_from_workflow("DocumentApproval") == "Document"

    def test_entity_from_test(self):
        assert _entity_from_workflow("OrderTest") == "Order"

    def test_entity_no_suffix(self):
        assert _entity_from_workflow("Payment") == "Payment"

    def test_trigger_last_segment(self):
        assert _trigger_from_path("/movements/{id}/approve") == "approve"

    def test_trigger_complete(self):
        assert _trigger_from_path("/movements/{id}/complete") == "complete"

    def test_trigger_no_id(self):
        assert _trigger_from_path("/movements") == "movements"


# ---------------------------------------------------------------------------
# Тесты StateMachineAnalyzer
# ---------------------------------------------------------------------------

class TestStateMachineAnalyzer:
    def setup_method(self):
        self.analyzer = StateMachineAnalyzer()

    def test_name(self):
        assert self.analyzer.name == "state-machine"

    def test_empty_findings(self):
        result = self.analyzer.analyze([])
        assert result.data["machines"] == []

    def test_no_workflow_findings(self):
        findings = [make_status_rule("Movement", "CREATED")]
        result = self.analyzer.analyze(findings)
        assert result.data["machines"] == []

    def test_simple_two_state_machine(self):
        """Простой автомат: DRAFT → APPROVED."""
        findings = [
            make_status_rule("Document", "DRAFT"),
            make_status_rule("Document", "APPROVED"),
            make_workflow("DocumentApproval", [
                {"order": 1, "test_method": "create", "action": "POST /documents",
                 "method": "POST", "path": "/documents", "status_code": 201},
                {"order": 2, "test_method": "approve", "action": "PUT /documents/{id}/approve",
                 "method": "PUT", "path": "/documents/{id}/approve", "status_code": 200},
            ]),
        ]
        result = self.analyzer.analyze(findings)
        machines = result.data["machines"]
        assert len(machines) == 1
        m = machines[0]
        assert m["entity"] == "Document"
        assert m["initial_state"] == "DRAFT"
        assert len(m["transitions"]) == 1
        assert m["transitions"][0]["from"] == "DRAFT"
        assert m["transitions"][0]["to"] == "APPROVED"
        assert m["transitions"][0]["action"] == "approve"

    def test_forbidden_transition_detected(self):
        """Запрещённый переход: 409 после завершения."""
        findings = [
            make_status_rule("Movement", "CREATED"),
            make_status_rule("Movement", "COMPLETED"),
            make_workflow("MovementFlow", [
                {"order": 1, "test_method": "create", "action": "POST /movements",
                 "method": "POST", "path": "/movements", "status_code": 201},
                {"order": 2, "test_method": "complete", "action": "PUT /movements/{id}/complete",
                 "method": "PUT", "path": "/movements/{id}/complete", "status_code": 200},
                {"order": 3, "test_method": "cannot_approve_completed",
                 "action": "PUT /movements/{id}/approve",
                 "method": "PUT", "path": "/movements/{id}/approve", "status_code": 409},
            ]),
        ]
        result = self.analyzer.analyze(findings)
        m = result.data["machines"][0]
        assert len(m["forbidden_transitions"]) == 1
        fb = m["forbidden_transitions"][0]
        assert fb["from"] == "COMPLETED"
        assert fb["error"] == "INVALID_STATE_TRANSITION"
        assert fb["action"] == "approve"

    def test_terminal_states(self):
        """Состояния без исходящих переходов — терминальные."""
        findings = [
            make_status_rule("Movement", "CREATED"),
            make_status_rule("Movement", "APPROVED"),
            make_status_rule("Movement", "COMPLETED"),
            make_workflow("MovementFlow", [
                {"order": 1, "test_method": "create", "action": "POST /movements",
                 "method": "POST", "path": "/movements", "status_code": 201},
                {"order": 2, "test_method": "approve", "action": "PUT /movements/{id}/approve",
                 "method": "PUT", "path": "/movements/{id}/approve", "status_code": 200},
                {"order": 3, "test_method": "complete", "action": "PUT /movements/{id}/complete",
                 "method": "PUT", "path": "/movements/{id}/complete", "status_code": 200},
            ]),
        ]
        result = self.analyzer.analyze(findings)
        m = result.data["machines"][0]
        assert "COMPLETED" in m["terminal_states"]
        assert "CREATED" not in m["terminal_states"]

    def test_summary_contains_entity_info(self):
        findings = [
            make_status_rule("Movement", "CREATED"),
            make_status_rule("Movement", "APPROVED"),
            make_workflow("MovementFlow", [
                {"order": 1, "test_method": "create", "action": "POST /movements",
                 "method": "POST", "path": "/movements", "status_code": 201},
                {"order": 2, "test_method": "approve", "action": "PUT /movements/{id}/approve",
                 "method": "PUT", "path": "/movements/{id}/approve", "status_code": 200},
            ]),
        ]
        result = self.analyzer.analyze(findings)
        assert "Movement" in result.summary
        assert "Автоматов:" in result.summary

    def test_real_findings(self):
        """Интеграционный тест: из 154 findings — автоматы Movement и Document."""
        findings_file = Path("findings/test_findings.json")
        if not findings_file.exists():
            pytest.skip("findings/test_findings.json не найден")

        raw = json.loads(findings_file.read_text(encoding="utf-8"))
        findings = [Finding(**r) for r in raw]

        result = self.analyzer.analyze(findings)
        machines = {m["entity"]: m for m in result.data["machines"]}

        assert "Movement" in machines
        assert "Document" in machines

        # Movement: минимум 2 перехода (approve, complete) и 1 запрещённый
        mv = machines["Movement"]
        assert len(mv["transitions"]) >= 2
        assert len(mv["forbidden_transitions"]) >= 1
        # COMPLETED должен быть терминальным
        assert "COMPLETED" in mv["terminal_states"]

        # Document: минимум 1 переход (approve) и 1 запрещённый (reject после approve)
        doc = machines["Document"]
        assert len(doc["transitions"]) >= 1
        assert len(doc["forbidden_transitions"]) >= 1
