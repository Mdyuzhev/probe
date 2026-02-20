"""Аналитик конечных автоматов — строит FSM из workflow findings."""

from __future__ import annotations

import re
from collections import defaultdict

from probe.analyzers.base import BaseAnalyzer
from probe.models import AnalysisResult, Finding


def _entity_from_workflow(workflow_name: str) -> str:
    """Извлечь имя сущности из имени workflow: MovementFlow → Movement."""
    return re.sub(r"(Flow|Approval|Test|Workflow)$", "", workflow_name) or workflow_name


def _trigger_from_path(path: str) -> str:
    """Извлечь триггер-действие из пути: /movements/{id}/approve → approve."""
    segments = [s for s in path.strip("/").split("/") if s and not s.startswith("{")]
    return segments[-1] if segments else path


class StateMachineAnalyzer(BaseAnalyzer):
    """Строит конечные автоматы сущностей из workflow findings."""

    name = "state-machine"
    description = "Извлекает FSM (состояния, переходы) из ra-test-sequence и ra-assertion-rules"

    def analyze(self, findings: list[Finding]) -> AnalysisResult:
        # 1. Собрать статусы сущностей из ассертов (порядок = порядок появления в findings)
        entity_statuses: dict[str, list[str]] = defaultdict(list)
        for f in findings:
            if f.probe != "ra-assertion-rules" or f.fact != "business_rule":
                continue
            parts = f.entity.split(".", 1)
            if len(parts) != 2 or parts[1] != "status":
                continue
            entity_name = parts[0]
            value = str(f.data.get("expected", ""))
            if value and re.match(r"^[A-Z][A-Z0-9_]+$", value):
                if value not in entity_statuses[entity_name]:
                    entity_statuses[entity_name].append(value)

        # 2. Обработать workflow-findings и построить автоматы
        machines: list[dict] = []
        for f in findings:
            if f.probe != "ra-test-sequence" or f.fact != "business_workflow":
                continue

            workflow_name = f.data.get("workflow_name", "")
            steps = f.data.get("steps", [])
            entity_name = _entity_from_workflow(workflow_name)
            statuses = entity_statuses.get(entity_name, [])

            transitions: list[dict] = []
            forbidden: list[dict] = []
            state_idx = 0  # индекс текущего состояния в списке statuses

            for step in sorted(steps, key=lambda s: s.get("order", 0)):
                method = step.get("method", "")
                path = step.get("path", "")
                status_code = step.get("status_code", 0)
                order = step.get("order", 0)
                trigger = _trigger_from_path(path)
                evidence = f"workflow:{workflow_name}:step{order}"

                if method == "POST" and status_code in (200, 201):
                    # Создание → начальное состояние
                    state_idx = 0
                elif method in ("PUT", "PATCH") and status_code in (200, 201, 204):
                    # Успешный переход к следующему состоянию
                    if statuses and state_idx < len(statuses) - 1:
                        transitions.append({
                            "from": statuses[state_idx],
                            "to": statuses[state_idx + 1],
                            "trigger": f"{method} {path}",
                            "action": trigger,
                            "evidence": [evidence],
                        })
                        state_idx += 1
                elif status_code == 409:
                    # Запрещённый переход (конфликт состояния)
                    from_state = statuses[state_idx] if state_idx < len(statuses) else "UNKNOWN"
                    forbidden.append({
                        "from": from_state,
                        "trigger": f"{method} {path}",
                        "action": trigger,
                        "error": "INVALID_STATE_TRANSITION",
                        "evidence": [evidence],
                    })

            # Определить упорядоченные состояния из найденных переходов
            seen: list[str] = []
            for t in transitions:
                for s in (t["from"], t["to"]):
                    if s not in seen:
                        seen.append(s)
            ordered_states = seen or statuses

            initial = ordered_states[0] if ordered_states else None
            states_with_outgoing = {t["from"] for t in transitions}
            terminal = [s for s in ordered_states if s not in states_with_outgoing]

            # Непроверенные переходы — все теоретически возможные пары
            tested_pairs = {(t["from"], t["to"]) for t in transitions}
            forbidden_from = {fb["from"] for fb in forbidden}
            unknown = [
                f"{a}→{b}"
                for i, a in enumerate(ordered_states)
                for b in ordered_states
                if a != b and (a, b) not in tested_pairs
            ]

            machines.append({
                "entity": entity_name,
                "workflow": workflow_name,
                "status_field": "status",
                "states": ordered_states,
                "initial_state": initial,
                "terminal_states": terminal,
                "transitions": transitions,
                "forbidden_transitions": forbidden,
                "unknown_transitions": unknown,
            })

        summary_lines = [f"Автоматов: {len(machines)}"]
        for m in machines:
            summary_lines.append(
                f"  {m['entity']}: {len(m['states'])} состояний, "
                f"{len(m['transitions'])} переходов, "
                f"{len(m['forbidden_transitions'])} запрещённых"
            )

        return AnalysisResult(
            analyzer=self.name,
            data={"machines": machines},
            summary="\n".join(summary_lines),
        )
