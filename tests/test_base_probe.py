"""Тесты базового класса зонда."""

import pytest
from probe.models import Finding
from probes.base import BaseProbe


class ConcreteProbe(BaseProbe):
    """Минимальная реализация зонда для тестирования."""
    name = "test-probe"
    env = "test"

    def scan(self, target) -> list[Finding]:
        return [
            Finding(
                probe=self.name,
                env=self.env,
                entity="test-entity",
                fact="test_fact",
                data={"key": "value"},
            )
        ]


class TestBaseProbe:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            BaseProbe()  # type: ignore

    def test_concrete_probe_scan(self):
        probe = ConcreteProbe()
        findings = probe.scan("/some/path")
        assert len(findings) == 1
        assert findings[0].probe == "test-probe"
        assert findings[0].fact == "test_fact"

    def test_repr(self):
        probe = ConcreteProbe()
        assert "test-probe" in repr(probe)
