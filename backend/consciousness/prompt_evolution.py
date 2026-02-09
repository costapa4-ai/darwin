"""
Prompt Evolution Engine: Autonomous prompt improvement via tournament selection and AI mutation.

Inspired by Promptbreeder (DeepMind) — simplified for Darwin's architecture.
Runs periodically to evolve prompts that have strong performance feedback.
"""

import re
import uuid
import random
from datetime import datetime
from typing import Dict, Any, Optional, List

from utils.logger import get_logger
from consciousness.prompt_registry import PromptRegistry, PromptVariant, PromptSlot

logger = get_logger(__name__)

# Mutation types with instructions
MUTATION_TYPES = {
    'rephrase': 'Rephrase the prompt using different wording while preserving the exact same meaning and intent.',
    'restructure': 'Reorganize the prompt structure (reorder sections, change formatting) to improve clarity.',
    'detail': 'Add more specific details, examples, or constraints to make the prompt more precise.',
    'simplify': 'Simplify the prompt by removing redundant parts while keeping all essential instructions.',
    'persona': 'Adjust the persona/role description to be more effective (e.g., more authoritative, more specific expertise).',
}

MUTATION_META_PROMPT = """You are a prompt engineering expert. Create an improved variant of this prompt template.

CURRENT TEMPLATE:
{current_template}

PERFORMANCE DATA:
- Average score: {avg_score:.3f}
- Success rate: {success_rate:.1%}
- Total uses: {uses}

MUTATION TYPE: {mutation_type} — {mutation_instruction}

CONSTRAINTS:
1. You MUST preserve ALL these placeholders exactly as written: {placeholders}
2. Keep the new template within 30% of the original length
3. The prompt must accomplish the same task
4. Do NOT add new placeholders or remove existing ones
5. Maintain the same output format requirements

Return ONLY the new prompt template. No explanations, no markdown fencing."""


class PromptEvolutionEngine:
    """
    Evolves prompts through tournament selection and AI-driven mutation.

    Algorithm (runs every ~6 hours):
    1. Gather slots with enough usage data
    2. Safety: rollback any variant scoring >10% below original
    3. Promote: if challenger outperforms active by >5% and >= 80% of original
    4. Mutate: generate 1-2 new variants from best performer
    5. Explore: 20% chance to activate an untested variant
    """

    def __init__(
        self,
        multi_model_router=None,
        registry: Optional[PromptRegistry] = None,
        max_mutations_per_cycle: int = 3,
    ):
        self.multi_model_router = multi_model_router
        self.registry = registry
        self.max_mutations_per_cycle = max_mutations_per_cycle
        self.last_evolution_time: Optional[datetime] = None

    async def evolve(self) -> Dict[str, Any]:
        """
        Run one evolution cycle across all eligible prompt slots.

        Returns:
            Summary of actions taken.
        """
        if not self.registry:
            return {'error': 'No prompt registry available'}

        if not self.multi_model_router:
            return {'error': 'No AI router available for mutations'}

        results = {
            'timestamp': datetime.utcnow().isoformat(),
            'rollbacks': [],
            'promotions': [],
            'mutations': [],
            'explorations': [],
            'slots_evaluated': 0,
        }

        candidates = self.registry.get_evolution_candidates()
        results['slots_evaluated'] = len(candidates)

        if not candidates:
            logger.info("Prompt evolution: no slots ready for evolution")
            return results

        mutations_this_cycle = 0

        for slot in candidates:
            active = slot.active_variant
            original = slot.original_variant
            if not active or not original:
                continue

            # Step 1: Safety rollback
            if not active.is_original and active.uses >= slot.min_uses_before_evolution:
                if original.uses > 0 and active.avg_score < original.avg_score * 0.90:
                    logger.warning(
                        f"Rolling back slot {slot.id}: active avg={active.avg_score:.3f} "
                        f"< original avg={original.avg_score:.3f} * 0.90"
                    )
                    self.registry.rollback_to_original(slot.id)
                    results['rollbacks'].append({
                        'slot': slot.id,
                        'variant': active.id,
                        'active_score': round(active.avg_score, 3),
                        'original_score': round(original.avg_score, 3),
                    })
                    continue

            # Step 2: Promotion — find challenger that outperforms active
            challengers = [
                v for v in slot.variants
                if not v.retired
                and v.id != active.id
                and v.uses >= slot.min_uses_before_evolution
            ]

            for challenger in challengers:
                # Challenger must beat active by >5% AND score >= 80% of original
                beats_active = challenger.avg_score > active.avg_score * 1.05
                meets_baseline = (
                    original.uses == 0  # No data on original yet
                    or challenger.avg_score >= original.avg_score * 0.80
                )

                if beats_active and meets_baseline:
                    logger.info(
                        f"Promoting variant {challenger.id} in slot {slot.id}: "
                        f"challenger avg={challenger.avg_score:.3f} vs active avg={active.avg_score:.3f}"
                    )
                    self.registry.activate_variant(slot.id, challenger.id)
                    results['promotions'].append({
                        'slot': slot.id,
                        'promoted': challenger.id,
                        'challenger_score': round(challenger.avg_score, 3),
                        'previous_score': round(active.avg_score, 3),
                    })
                    break  # Only one promotion per slot per cycle

            # Step 3: Mutate — generate new variants from best performer
            if mutations_this_cycle < self.max_mutations_per_cycle:
                best = self._find_best_variant(slot)
                if best:
                    mutation_type = random.choice(list(MUTATION_TYPES.keys()))
                    new_variant = await self._mutate(slot, best, mutation_type)
                    if new_variant:
                        self.registry.add_variant(slot.id, new_variant)
                        mutations_this_cycle += 1
                        results['mutations'].append({
                            'slot': slot.id,
                            'parent': best.id,
                            'new_variant': new_variant.id,
                            'mutation_type': mutation_type,
                        })

            # Step 4: Exploration — 20% chance to activate an untested variant
            if random.random() < 0.20:
                untested = [
                    v for v in slot.variants
                    if not v.retired and v.uses == 0 and not v.is_active
                ]
                if untested:
                    explore_variant = random.choice(untested)
                    self.registry.activate_variant(slot.id, explore_variant.id)
                    results['explorations'].append({
                        'slot': slot.id,
                        'variant': explore_variant.id,
                    })

        self.last_evolution_time = datetime.utcnow()
        self.registry._save()

        logger.info(
            f"Prompt evolution complete: {len(results['rollbacks'])} rollbacks, "
            f"{len(results['promotions'])} promotions, {len(results['mutations'])} mutations, "
            f"{len(results['explorations'])} explorations"
        )

        return results

    def _find_best_variant(self, slot: PromptSlot) -> Optional[PromptVariant]:
        """Find the best-performing variant in a slot (with enough data)."""
        candidates = [
            v for v in slot.variants
            if not v.retired and v.uses >= 3  # At least 3 uses for signal
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda v: v.avg_score)

    async def _mutate(
        self,
        slot: PromptSlot,
        parent: PromptVariant,
        mutation_type: str,
    ) -> Optional[PromptVariant]:
        """Generate a new variant by mutating the parent template."""
        instruction = MUTATION_TYPES.get(mutation_type, MUTATION_TYPES['rephrase'])
        placeholders_str = ', '.join(f'{{{p}}}' for p in slot.placeholders)

        prompt = MUTATION_META_PROMPT.format(
            current_template=parent.template,
            avg_score=parent.avg_score,
            success_rate=parent.success_rate,
            uses=parent.uses,
            mutation_type=mutation_type,
            mutation_instruction=instruction,
            placeholders=placeholders_str,
        )

        try:
            result = await self.multi_model_router.generate(
                task_description=f"Prompt engineering: {mutation_type} mutation for {slot.name}",
                prompt=prompt,
                max_tokens=4096,
                context={
                    'task_type': 'prompt_mutation',
                    'priority': 'low',
                }
            )

            response = result.get('result', '') if isinstance(result, dict) else str(result)
            new_template = response.strip()

            # Remove any markdown fencing the model might add
            new_template = re.sub(r'^```\w*\n?', '', new_template)
            new_template = re.sub(r'\n?```$', '', new_template)
            new_template = new_template.strip()

            # Validate the mutation
            if not self._validate_mutation(slot, parent, new_template):
                return None

            # Determine version number
            version_num = len(slot.variants) + 1
            variant_id = str(uuid.uuid4())[:8]

            variant = PromptVariant(
                id=variant_id,
                version=f"1.{version_num}",
                template=new_template,
                parent_id=parent.id,
                mutation_type=mutation_type,
            )

            logger.info(
                f"Created variant {variant_id} for slot {slot.id} "
                f"via {mutation_type} mutation ({len(new_template)} chars)"
            )
            return variant

        except Exception as e:
            logger.error(f"Mutation failed for slot {slot.id}: {e}")
            return None

    def _validate_mutation(
        self,
        slot: PromptSlot,
        parent: PromptVariant,
        new_template: str,
    ) -> bool:
        """Validate a mutated template meets safety constraints."""
        if not new_template or len(new_template) < 50:
            logger.warning(f"Mutation rejected for {slot.id}: too short ({len(new_template)} chars)")
            return False

        # Check all placeholders are present
        for placeholder in slot.placeholders:
            pattern = '{' + placeholder + '}'
            if pattern not in new_template:
                logger.warning(
                    f"Mutation rejected for {slot.id}: "
                    f"missing placeholder {pattern}"
                )
                return False

        # Check length within 30% of parent
        parent_len = len(parent.template)
        if parent_len > 0:
            ratio = len(new_template) / parent_len
            if ratio < 0.70 or ratio > 1.30:
                logger.warning(
                    f"Mutation rejected for {slot.id}: "
                    f"length ratio {ratio:.2f} outside [0.70, 1.30]"
                )
                return False

        return True
