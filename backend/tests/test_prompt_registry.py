"""Tests for the Prompt Registry system."""
import json
import pytest
import tempfile
import shutil
from pathlib import Path

from consciousness.prompt_registry import (
    PromptRegistry,
    PromptVariant,
    PromptSlot,
    set_prompt_registry,
    get_prompt_registry,
)


@pytest.fixture
def tmp_storage(tmp_path):
    """Create a temporary storage directory."""
    return str(tmp_path / "prompt_evolution")


@pytest.fixture
def registry(tmp_storage):
    """Create a fresh PromptRegistry."""
    return PromptRegistry(storage_path=tmp_storage)


@pytest.fixture
def registered_slot(registry):
    """Register a sample prompt slot."""
    registry.register_prompt(
        slot_id="test.generation",
        name="Test Generation",
        module="test_module",
        function="test_func",
        category="code_generation",
        feedback_strength="strong",
        placeholders=["title", "code"],
        original_template="Generate code for {title}:\n```python\n{code}\n```",
    )
    return registry


class TestPromptVariant:
    def test_record_outcome(self):
        v = PromptVariant(id="v1", version="1.0", template="test")
        v.record(0.8, True)
        v.record(0.6, False)

        assert v.uses == 2
        assert v.successes == 1
        assert v.avg_score == pytest.approx(0.7)
        assert v.success_rate == pytest.approx(0.5)

    def test_score_truncation(self):
        v = PromptVariant(id="v1", version="1.0", template="test")
        for i in range(60):
            v.record(float(i) / 60, True)
        assert len(v.scores) == 50

    def test_serialization_roundtrip(self):
        v = PromptVariant(
            id="v1", version="1.0", template="hello {name}",
            is_original=True, is_active=True,
        )
        v.record(0.9, True)
        data = v.to_dict()
        v2 = PromptVariant.from_dict(data)
        assert v2.id == "v1"
        assert v2.is_original is True
        assert v2.uses == 1
        assert v2.scores == [0.9]


class TestPromptSlot:
    def test_active_variant(self):
        v = PromptVariant(id="v1", version="1.0", template="t", is_original=True, is_active=True)
        slot = PromptSlot(
            id="s1", name="S1", module="m", function="f",
            category="c", feedback_strength="strong",
            placeholders=[], variants=[v], active_variant_id="v1",
        )
        assert slot.active_variant is v
        assert slot.original_variant is v

    def test_retire_worst(self):
        orig = PromptVariant(id="orig", version="1.0", template="t", is_original=True, is_active=True)
        bad = PromptVariant(id="bad", version="1.1", template="t")
        bad.record(0.1, False)
        good = PromptVariant(id="good", version="1.2", template="t")
        good.record(0.9, True)

        slot = PromptSlot(
            id="s1", name="S1", module="m", function="f",
            category="c", feedback_strength="strong",
            placeholders=[], variants=[orig, bad, good],
            active_variant_id="orig", max_variants=3,
        )
        slot._retire_worst()
        assert bad.retired is True
        assert good.retired is False


class TestPromptRegistry:
    def test_register_and_get(self, registered_slot):
        result = registered_slot.get_prompt(
            "test.generation", title="My Task", code="print('hi')"
        )
        assert "My Task" in result
        assert "print('hi')" in result

    def test_get_unknown_slot_raises(self, registry):
        with pytest.raises(KeyError):
            registry.get_prompt("nonexistent.slot")

    def test_record_outcome(self, registered_slot):
        registered_slot.record_outcome("test.generation", 0.8, True)
        registered_slot.record_outcome("test.generation", 0.5, False)

        slot = registered_slot.slots["test.generation"]
        active = slot.active_variant
        assert active.uses == 2
        assert active.successes == 1

    def test_persistence(self, tmp_storage):
        # Create and populate
        r1 = PromptRegistry(storage_path=tmp_storage)
        r1.register_prompt(
            slot_id="test.persist",
            name="Persist Test",
            module="m", function="f", category="c",
            feedback_strength="strong",
            placeholders=["x"],
            original_template="Template: {x}",
        )
        r1.record_outcome("test.persist", 0.9, True)
        r1._save()

        # Reload
        r2 = PromptRegistry(storage_path=tmp_storage)
        assert "test.persist" in r2.slots
        slot = r2.slots["test.persist"]
        assert slot.active_variant.uses == 1

    def test_rollback_to_original(self, registered_slot):
        # Add and activate a non-original variant
        new_variant = PromptVariant(
            id="new1", version="1.1",
            template="Better code for {title}:\n{code}",
        )
        registered_slot.add_variant("test.generation", new_variant)
        registered_slot.activate_variant("test.generation", "new1")

        # Verify new variant is active
        slot = registered_slot.slots["test.generation"]
        assert slot.active_variant_id == "new1"

        # Rollback
        registered_slot.rollback_to_original("test.generation")
        assert slot.active_variant.is_original is True

    def test_rollback_retires_after_three(self, registered_slot):
        # Add a single bad variant and roll it back 3 times
        v = PromptVariant(
            id="bad_v", version="1.1",
            template="Bad template {title} {code}",
        )
        registered_slot.add_variant("test.generation", v)

        for i in range(3):
            registered_slot.activate_variant("test.generation", "bad_v")
            registered_slot.rollback_to_original("test.generation")

        # Variant should be retired after 3 rollbacks
        slot = registered_slot.slots["test.generation"]
        bad = slot.get_variant("bad_v")
        assert bad.rollback_count == 3
        assert bad.retired is True

    def test_evolution_candidates(self, registered_slot):
        # Not enough uses yet
        candidates = registered_slot.get_evolution_candidates()
        assert len(candidates) == 0

        # Add enough uses
        for _ in range(10):
            registered_slot.record_outcome("test.generation", 0.8, True)

        candidates = registered_slot.get_evolution_candidates()
        assert len(candidates) == 1

    def test_get_stats(self, registered_slot):
        stats = registered_slot.get_stats()
        assert stats['total_slots'] == 1
        assert stats['total_variants'] == 1
        assert "test.generation" in stats['slots']

    def test_duplicate_registration_preserves_state(self, registered_slot):
        # Record some data
        for _ in range(5):
            registered_slot.record_outcome("test.generation", 0.9, True)

        # Re-register same slot
        registered_slot.register_prompt(
            slot_id="test.generation",
            name="Test Generation",
            module="test_module",
            function="test_func",
            category="code_generation",
            feedback_strength="strong",
            placeholders=["title", "code"],
            original_template="Generate code for {title}:\n```python\n{code}\n```",
        )

        # State should be preserved
        slot = registered_slot.slots["test.generation"]
        assert slot.active_variant.uses == 5

    def test_singleton(self, registry):
        set_prompt_registry(registry)
        assert get_prompt_registry() is registry
        set_prompt_registry(None)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
