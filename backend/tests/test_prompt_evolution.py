"""Tests for the Prompt Evolution Engine."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from consciousness.prompt_registry import (
    PromptRegistry,
    PromptVariant,
    PromptSlot,
)
from consciousness.prompt_evolution import (
    PromptEvolutionEngine,
    MUTATION_TYPES,
)


@pytest.fixture
def tmp_storage(tmp_path):
    return str(tmp_path / "prompt_evolution")


@pytest.fixture
def registry(tmp_storage):
    return PromptRegistry(storage_path=tmp_storage)


ORIGINAL_TEMPLATE = (
    "You are an expert developer. Generate high-quality code.\n\n"
    "Task: {title}\n\nCurrent code:\n{code}\n\n"
    "Return ONLY the complete Python code."
)

MUTATED_TEMPLATE = (
    "You are a skilled Python developer. Write production-ready code.\n\n"
    "Objective: {title}\n\nExisting code:\n{code}\n\n"
    "Return ONLY the complete implementation."
)


@pytest.fixture
def slot_with_data(registry):
    """Create a registry with a slot that has enough usage data."""
    registry.register_prompt(
        slot_id="test.gen",
        name="Test Gen",
        module="test",
        function="gen",
        category="code_generation",
        feedback_strength="strong",
        placeholders=["title", "code"],
        original_template=ORIGINAL_TEMPLATE,
    )
    # Record enough outcomes for evolution
    for _ in range(15):
        registry.record_outcome("test.gen", 0.7, True)
    return registry


@pytest.fixture
def mock_router():
    """Create a mock multi-model router."""
    router = AsyncMock()
    router.generate = AsyncMock(return_value={
        'result': MUTATED_TEMPLATE,
    })
    return router


class TestPromptEvolutionEngine:
    @pytest.mark.asyncio
    async def test_evolve_no_registry(self):
        engine = PromptEvolutionEngine()
        result = await engine.evolve()
        assert 'error' in result

    @pytest.mark.asyncio
    async def test_evolve_no_router(self, registry):
        engine = PromptEvolutionEngine(registry=registry)
        result = await engine.evolve()
        assert 'error' in result

    @pytest.mark.asyncio
    async def test_evolve_no_candidates(self, registry, mock_router):
        """No slots have enough data — nothing to evolve."""
        registry.register_prompt(
            slot_id="test.empty",
            name="Empty",
            module="m", function="f", category="c",
            feedback_strength="strong",
            placeholders=["x"],
            original_template="Template {x}",
        )
        engine = PromptEvolutionEngine(
            multi_model_router=mock_router,
            registry=registry,
        )
        result = await engine.evolve()
        assert result['slots_evaluated'] == 0

    @pytest.mark.asyncio
    async def test_evolve_creates_mutation(self, slot_with_data, mock_router):
        engine = PromptEvolutionEngine(
            multi_model_router=mock_router,
            registry=slot_with_data,
            max_mutations_per_cycle=1,
        )
        # Seed randomness for reproducibility
        with patch('consciousness.prompt_evolution.random') as mock_random:
            mock_random.choice.return_value = 'rephrase'
            mock_random.random.return_value = 0.5  # Don't explore
            result = await engine.evolve()

        assert result['slots_evaluated'] == 1
        assert len(result['mutations']) == 1

        # Verify variant was added
        slot = slot_with_data.slots["test.gen"]
        assert len(slot.variants) == 2  # original + mutation

    @pytest.mark.asyncio
    async def test_rollback_on_poor_performance(self, slot_with_data, mock_router):
        """Active variant scoring <90% of original triggers rollback."""
        slot = slot_with_data.slots["test.gen"]

        # Add and activate a bad variant
        bad = PromptVariant(
            id="bad1", version="1.1",
            template=MUTATED_TEMPLATE,
        )
        slot_with_data.add_variant("test.gen", bad)
        slot_with_data.activate_variant("test.gen", "bad1")

        # Record poor scores for the bad variant (below 90% of original)
        for _ in range(12):
            bad.record(0.3, False)  # avg 0.3 vs original's 0.7

        engine = PromptEvolutionEngine(
            multi_model_router=mock_router,
            registry=slot_with_data,
        )
        with patch('consciousness.prompt_evolution.random') as mock_random:
            mock_random.choice.return_value = 'rephrase'
            mock_random.random.return_value = 0.5
            result = await engine.evolve()

        assert len(result['rollbacks']) == 1
        assert slot.active_variant.is_original is True

    @pytest.mark.asyncio
    async def test_promotion(self, slot_with_data, mock_router):
        """A challenger that beats active by >5% gets promoted."""
        slot = slot_with_data.slots["test.gen"]

        # Add a challenger with great scores
        challenger = PromptVariant(
            id="champ", version="1.1",
            template=MUTATED_TEMPLATE,
        )
        slot_with_data.add_variant("test.gen", challenger)

        # Give it enough good data
        for _ in range(12):
            challenger.record(0.95, True)

        engine = PromptEvolutionEngine(
            multi_model_router=mock_router,
            registry=slot_with_data,
        )
        with patch('consciousness.prompt_evolution.random') as mock_random:
            mock_random.choice.return_value = 'rephrase'
            mock_random.random.return_value = 0.5
            result = await engine.evolve()

        assert len(result['promotions']) == 1
        assert slot.active_variant_id == "champ"


class TestMutationValidation:
    def test_validate_missing_placeholder(self, slot_with_data, mock_router):
        engine = PromptEvolutionEngine(
            multi_model_router=mock_router,
            registry=slot_with_data,
        )
        slot = slot_with_data.slots["test.gen"]
        parent = slot.original_variant

        # Missing {code} placeholder — same length range
        bad_template = (
            "You are an expert. Generate high-quality output.\n\n"
            "Task: {title}\n\nPlease provide results.\n\n"
            "Return ONLY the complete output."
        )
        assert engine._validate_mutation(slot, parent, bad_template) is False

    def test_validate_too_short(self, slot_with_data, mock_router):
        engine = PromptEvolutionEngine(
            multi_model_router=mock_router,
            registry=slot_with_data,
        )
        slot = slot_with_data.slots["test.gen"]
        parent = slot.original_variant

        assert engine._validate_mutation(slot, parent, "short") is False

    def test_validate_too_long(self, slot_with_data, mock_router):
        engine = PromptEvolutionEngine(
            multi_model_router=mock_router,
            registry=slot_with_data,
        )
        slot = slot_with_data.slots["test.gen"]
        parent = slot.original_variant

        # Way too long (>130% of parent)
        too_long = ("x" * 500) + " {title} {code}"
        assert engine._validate_mutation(slot, parent, too_long) is False

    def test_validate_valid_mutation(self, slot_with_data, mock_router):
        engine = PromptEvolutionEngine(
            multi_model_router=mock_router,
            registry=slot_with_data,
        )
        slot = slot_with_data.slots["test.gen"]
        parent = slot.original_variant

        assert engine._validate_mutation(slot, parent, MUTATED_TEMPLATE) is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
