"""
Prompt Registry: Evolvable prompt storage and tracking for Darwin's self-improving prompts.

Follows the FindingsInbox pattern: @dataclass + JSON persistence + global singleton.
Each prompt "slot" holds multiple variants that compete via performance tracking.
"""

import json
import uuid
import re
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from pathlib import Path
from collections import deque

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PromptVariant:
    """A single variant of a prompt template."""
    id: str
    version: str                        # e.g. "1.0" for original, "1.1" for first mutation
    template: str                       # The prompt template with {placeholder} format
    is_original: bool = False           # True for the immutable original
    is_active: bool = False             # Currently being used
    uses: int = 0                       # Total times used
    successes: int = 0                  # Total successful outcomes
    total_score: float = 0.0            # Sum of all scores
    scores: List[float] = field(default_factory=list)  # Last N scores
    parent_id: Optional[str] = None     # ID of variant this was mutated from
    mutation_type: Optional[str] = None # rephrase, restructure, detail, simplify, persona
    rollback_count: int = 0             # Times rolled back from active
    retired: bool = False               # Permanently retired (too many rollbacks)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    MAX_SCORES_KEPT = 50

    @property
    def avg_score(self) -> float:
        if not self.scores:
            return 0.0
        return sum(self.scores) / len(self.scores)

    @property
    def success_rate(self) -> float:
        if self.uses == 0:
            return 0.0
        return self.successes / self.uses

    def record(self, score: float, success: bool):
        """Record an outcome for this variant."""
        self.uses += 1
        self.total_score += score
        if success:
            self.successes += 1
        self.scores.append(score)
        # Keep only last N scores
        if len(self.scores) > self.MAX_SCORES_KEPT:
            self.scores = self.scores[-self.MAX_SCORES_KEPT:]

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'version': self.version,
            'template': self.template,
            'is_original': self.is_original,
            'is_active': self.is_active,
            'uses': self.uses,
            'successes': self.successes,
            'total_score': self.total_score,
            'scores': self.scores[-self.MAX_SCORES_KEPT:],
            'parent_id': self.parent_id,
            'mutation_type': self.mutation_type,
            'rollback_count': self.rollback_count,
            'retired': self.retired,
            'created_at': self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PromptVariant':
        return cls(
            id=data['id'],
            version=data['version'],
            template=data['template'],
            is_original=data.get('is_original', False),
            is_active=data.get('is_active', False),
            uses=data.get('uses', 0),
            successes=data.get('successes', 0),
            total_score=data.get('total_score', 0.0),
            scores=data.get('scores', []),
            parent_id=data.get('parent_id'),
            mutation_type=data.get('mutation_type'),
            rollback_count=data.get('rollback_count', 0),
            retired=data.get('retired', False),
            created_at=data.get('created_at', datetime.utcnow().isoformat()),
        )


@dataclass
class PromptSlot:
    """A named slot that holds competing prompt variants."""
    id: str                             # e.g. "code_generator.generation"
    name: str                           # Human-readable name
    module: str                         # e.g. "introspection.code_generator"
    function: str                       # e.g. "_create_generation_prompt"
    category: str                       # "code_generation", "debugging", "evaluation", "reflection"
    feedback_strength: str              # "strong", "moderate", "weak"
    placeholders: List[str]             # Required placeholders in template
    variants: List[PromptVariant] = field(default_factory=list)
    active_variant_id: Optional[str] = None
    min_uses_before_evolution: int = 10
    max_variants: int = 8

    @property
    def active_variant(self) -> Optional[PromptVariant]:
        """Get the currently active variant."""
        for v in self.variants:
            if v.id == self.active_variant_id and not v.retired:
                return v
        return None

    @property
    def original_variant(self) -> Optional[PromptVariant]:
        """Get the original (immutable) variant."""
        for v in self.variants:
            if v.is_original:
                return v
        return None

    def get_variant(self, variant_id: str) -> Optional[PromptVariant]:
        for v in self.variants:
            if v.id == variant_id:
                return v
        return None

    def add_variant(self, variant: PromptVariant) -> bool:
        """Add a variant, retiring worst if at capacity."""
        if len([v for v in self.variants if not v.retired]) >= self.max_variants:
            self._retire_worst()
        self.variants.append(variant)
        return True

    def _retire_worst(self):
        """Retire the worst-performing non-original, non-active variant."""
        candidates = [
            v for v in self.variants
            if not v.is_original and not v.is_active and not v.retired and v.uses > 0
        ]
        if not candidates:
            return
        # Sort by avg_score ascending — worst first
        candidates.sort(key=lambda v: v.avg_score)
        candidates[0].retired = True
        logger.info(f"Retired variant {candidates[0].id} from slot {self.id} "
                     f"(avg_score={candidates[0].avg_score:.3f})")

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'module': self.module,
            'function': self.function,
            'category': self.category,
            'feedback_strength': self.feedback_strength,
            'placeholders': self.placeholders,
            'variants': [v.to_dict() for v in self.variants],
            'active_variant_id': self.active_variant_id,
            'min_uses_before_evolution': self.min_uses_before_evolution,
            'max_variants': self.max_variants,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PromptSlot':
        slot = cls(
            id=data['id'],
            name=data['name'],
            module=data['module'],
            function=data['function'],
            category=data['category'],
            feedback_strength=data['feedback_strength'],
            placeholders=data['placeholders'],
            active_variant_id=data.get('active_variant_id'),
            min_uses_before_evolution=data.get('min_uses_before_evolution', 10),
            max_variants=data.get('max_variants', 8),
        )
        slot.variants = [PromptVariant.from_dict(v) for v in data.get('variants', [])]
        return slot


class PromptRegistry:
    """
    Central registry for evolvable prompts.
    Stores prompt variants, tracks performance, and supports evolution.
    """

    def __init__(self, storage_path: str = "./data/prompt_evolution"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.slots: Dict[str, PromptSlot] = {}
        self._load()
        logger.info(f"PromptRegistry initialized with {len(self.slots)} slots")

    def register_prompt(
        self,
        slot_id: str,
        name: str,
        module: str,
        function: str,
        category: str,
        feedback_strength: str,
        placeholders: List[str],
        original_template: str,
        min_uses_before_evolution: int = 10,
    ) -> PromptSlot:
        """
        Register a prompt slot with its original template.
        If slot already exists (from persistence), preserve its state.
        Only updates the original template if it changed.
        """
        if slot_id in self.slots:
            slot = self.slots[slot_id]
            # Update original template if it changed (code was updated)
            original = slot.original_variant
            if original and original.template != original_template:
                original.template = original_template
                logger.info(f"Updated original template for slot {slot_id}")
                self._save()
            return slot

        # Create new slot with original variant
        variant_id = str(uuid.uuid4())[:8]
        original_variant = PromptVariant(
            id=variant_id,
            version="1.0",
            template=original_template,
            is_original=True,
            is_active=True,
        )

        slot = PromptSlot(
            id=slot_id,
            name=name,
            module=module,
            function=function,
            category=category,
            feedback_strength=feedback_strength,
            placeholders=placeholders,
            variants=[original_variant],
            active_variant_id=variant_id,
            min_uses_before_evolution=min_uses_before_evolution,
        )

        self.slots[slot_id] = slot
        self._save()
        logger.info(f"Registered prompt slot: {slot_id} ({name})")
        return slot

    def get_prompt(self, slot_id: str, **kwargs) -> str:
        """
        Get the active prompt template for a slot, formatted with kwargs.
        Falls back gracefully if slot doesn't exist.

        Args:
            slot_id: The prompt slot identifier
            **kwargs: Values for template placeholders

        Returns:
            Formatted prompt string

        Raises:
            KeyError: If slot_id not found (caller should handle with fallback)
        """
        slot = self.slots.get(slot_id)
        if not slot:
            raise KeyError(f"Prompt slot '{slot_id}' not registered")

        variant = slot.active_variant
        if not variant:
            raise KeyError(f"No active variant for slot '{slot_id}'")

        try:
            return variant.template.format(**kwargs)
        except KeyError as e:
            logger.warning(f"Missing placeholder {e} in slot {slot_id}, falling back to original")
            original = slot.original_variant
            if original and original != variant:
                return original.template.format(**kwargs)
            raise

    def record_outcome(self, slot_id: str, score: float, success: bool):
        """
        Record the outcome of using a prompt.

        Args:
            slot_id: The prompt slot identifier
            score: Performance score (0.0 to 1.0)
            success: Whether the outcome was successful
        """
        slot = self.slots.get(slot_id)
        if not slot:
            return

        variant = slot.active_variant
        if not variant:
            return

        variant.record(score, success)

        # Periodic save (every 5 uses)
        if variant.uses % 5 == 0:
            self._save()

    def get_evolution_candidates(self) -> List[PromptSlot]:
        """Get slots that have enough data for evolution decisions."""
        candidates = []
        for slot in self.slots.values():
            active = slot.active_variant
            if active and active.uses >= slot.min_uses_before_evolution:
                candidates.append(slot)
        return candidates

    def add_variant(self, slot_id: str, variant: PromptVariant) -> bool:
        """Add a new variant to a slot."""
        slot = self.slots.get(slot_id)
        if not slot:
            return False
        result = slot.add_variant(variant)
        self._save()
        return result

    def activate_variant(self, slot_id: str, variant_id: str) -> bool:
        """Set a variant as the active one for a slot."""
        slot = self.slots.get(slot_id)
        if not slot:
            return False

        variant = slot.get_variant(variant_id)
        if not variant or variant.retired:
            return False

        # Deactivate current
        current = slot.active_variant
        if current:
            current.is_active = False

        # Activate new
        variant.is_active = True
        slot.active_variant_id = variant_id
        self._save()
        logger.info(f"Activated variant {variant_id} for slot {slot_id}")
        return True

    def rollback_to_original(self, slot_id: str) -> bool:
        """Roll back to the original prompt variant."""
        slot = self.slots.get(slot_id)
        if not slot:
            return False

        original = slot.original_variant
        if not original:
            return False

        # Mark current as rolled back
        current = slot.active_variant
        if current and not current.is_original:
            current.is_active = False
            current.rollback_count += 1
            if current.rollback_count >= 3:
                current.retired = True
                logger.warning(f"Variant {current.id} retired after {current.rollback_count} rollbacks")

        # Activate original
        original.is_active = True
        slot.active_variant_id = original.id
        self._save()
        logger.info(f"Rolled back slot {slot_id} to original variant")
        return True

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics for monitoring."""
        stats = {
            'total_slots': len(self.slots),
            'total_variants': sum(len(s.variants) for s in self.slots.values()),
            'active_mutations': sum(
                1 for s in self.slots.values()
                if s.active_variant and not s.active_variant.is_original
            ),
            'slots': {}
        }
        for slot_id, slot in self.slots.items():
            active = slot.active_variant
            original = slot.original_variant
            stats['slots'][slot_id] = {
                'active_variant': active.id if active else None,
                'is_original_active': active.is_original if active else True,
                'active_avg_score': round(active.avg_score, 3) if active else 0,
                'active_uses': active.uses if active else 0,
                'original_avg_score': round(original.avg_score, 3) if original else 0,
                'variant_count': len([v for v in slot.variants if not v.retired]),
                'retired_count': len([v for v in slot.variants if v.retired]),
            }
        return stats

    def _save(self):
        """Persist registry to JSON."""
        filepath = self.storage_path / "prompt_registry.json"
        data = {
            'version': '1.0',
            'saved_at': datetime.utcnow().isoformat(),
            'slots': {sid: slot.to_dict() for sid, slot in self.slots.items()}
        }
        try:
            filepath.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Failed to save prompt registry: {e}")

    def _load(self):
        """Load registry from JSON."""
        filepath = self.storage_path / "prompt_registry.json"
        if not filepath.exists():
            return

        try:
            data = json.loads(filepath.read_text())
            for sid, slot_data in data.get('slots', {}).items():
                self.slots[sid] = PromptSlot.from_dict(slot_data)
            logger.info(f"Loaded {len(self.slots)} prompt slots from disk")
        except Exception as e:
            logger.error(f"Failed to load prompt registry: {e}")


# Global singleton
_prompt_registry: Optional[PromptRegistry] = None


def get_prompt_registry() -> Optional[PromptRegistry]:
    """Get the global prompt registry instance."""
    return _prompt_registry


def set_prompt_registry(registry: PromptRegistry):
    """Set the global prompt registry instance."""
    global _prompt_registry
    _prompt_registry = registry
