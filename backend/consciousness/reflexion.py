"""
Multi-Agent Reflexion System

Implements the Multi-Agent Reflexion (MAR) pattern to reduce confirmation bias
in Darwin's decision-making process.

Based on research:
- Single-agent reflection is vulnerable to "confirmation bias"
- Multi-agent approach separates roles: Actor, Evaluator, Reflector
- This reduces "mode collapse" where agent produces identical solutions

Reference: https://arxiv.org/html/2512.20845
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from enum import Enum
import json

import logging

# Use basic logging to avoid Docker path issues when running locally
logger = logging.getLogger(__name__)


class ReflexionRole(Enum):
    """Roles in the reflexion process"""
    ACTOR = "actor"           # Original decision maker
    EVALUATOR = "evaluator"   # Quality assessor
    REFLECTOR = "reflector"   # Synthesizes feedback, improves


@dataclass
class ReflexionResult:
    """Result of a reflexion cycle"""
    original_action: Dict[str, Any]
    actor_analysis: Optional[str] = None
    evaluation: Optional[Dict[str, Any]] = None
    reflection: Optional[Dict[str, Any]] = None
    improved_action: Optional[Dict[str, Any]] = None
    lessons_learned: List[str] = field(default_factory=list)
    improvement_applied: bool = False
    reflexion_time_ms: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        return result


class ReflexionSystem:
    """
    Multi-Agent Reflexion to reduce confirmation bias in Darwin's decisions.

    The system uses three distinct "personas" to analyze actions:
    1. Actor: Reviews what was done and why
    2. Evaluator: Critically assesses quality, finds issues
    3. Reflector: Synthesizes feedback into improvements

    This separation prevents the same model from confirming its own biases.
    """

    def __init__(self, nucleus=None, multi_model_router=None):
        """
        Initialize the reflexion system.

        Args:
            nucleus: Primary LLM interface
            multi_model_router: Optional multi-model router for role diversity
        """
        self.nucleus = nucleus
        self.multi_model_router = multi_model_router

        # Statistics
        self.total_reflexions = 0
        self.improvements_made = 0
        self.lessons_catalog: List[Dict] = []

        # Configuration
        self.min_confidence_to_skip = 0.95  # Skip reflexion if very confident
        self.max_reflexion_depth = 2  # Max recursive reflexions

    async def should_reflect(self, action: Dict[str, Any]) -> bool:
        """
        Determine if an action warrants reflexion.

        Args:
            action: The action/decision to potentially reflect on

        Returns:
            True if reflexion is recommended
        """
        # Always reflect on high-impact actions
        high_impact_types = [
            'code_change', 'tool_creation', 'architecture_decision',
            'security_related', 'database_change', 'api_change'
        ]

        action_type = action.get('type', '')
        if action_type in high_impact_types:
            return True

        # Reflect if confidence is below threshold
        confidence = action.get('confidence', 0.5)
        if confidence < self.min_confidence_to_skip:
            return True

        # Reflect on novel situations
        if action.get('is_novel', False):
            return True

        return False

    async def reflect(
        self,
        action_result: Dict[str, Any],
        context: Optional[str] = None,
        depth: int = 0
    ) -> ReflexionResult:
        """
        Perform multi-agent reflexion on an action.

        Args:
            action_result: The action/decision to reflect on
            context: Optional additional context
            depth: Current recursion depth

        Returns:
            ReflexionResult with analysis and potential improvements
        """
        start_time = datetime.utcnow()
        self.total_reflexions += 1

        result = ReflexionResult(original_action=action_result)

        try:
            # Step 1: Actor reviews what was done
            result.actor_analysis = await self._actor_review(action_result, context)

            # Step 2: Evaluator critiques the action (different perspective)
            result.evaluation = await self._evaluator_critique(
                action_result,
                result.actor_analysis,
                context
            )

            # Step 3: Reflector synthesizes and improves
            result.reflection = await self._reflector_synthesize(
                action_result,
                result.actor_analysis,
                result.evaluation,
                context
            )

            # Extract improved action and lessons
            if result.reflection:
                result.improved_action = result.reflection.get('improved_action')
                result.lessons_learned = result.reflection.get('lessons', [])
                result.improvement_applied = result.reflection.get('should_apply', False)

                # Store lessons for future reference
                if result.lessons_learned:
                    self._store_lessons(result.lessons_learned, action_result)

                # Track improvements
                if result.improvement_applied:
                    self.improvements_made += 1

            # Recursive reflexion if still uncertain (max depth check)
            if (
                depth < self.max_reflexion_depth and
                result.evaluation and
                result.evaluation.get('confidence', 1.0) < 0.7
            ):
                logger.info(f"Recursive reflexion at depth {depth + 1}")
                deeper_result = await self.reflect(
                    result.improved_action or action_result,
                    context,
                    depth + 1
                )
                # Merge deeper insights
                result.lessons_learned.extend(deeper_result.lessons_learned)
                if deeper_result.improved_action:
                    result.improved_action = deeper_result.improved_action

        except Exception as e:
            logger.error(f"Reflexion failed: {e}")
            result.lessons_learned.append(f"Reflexion error: {str(e)}")

        # Calculate timing
        end_time = datetime.utcnow()
        result.reflexion_time_ms = int((end_time - start_time).total_seconds() * 1000)

        return result

    async def _actor_review(
        self,
        action: Dict[str, Any],
        context: Optional[str]
    ) -> str:
        """
        Actor role: Review what was done and explain the reasoning.

        This is the first perspective - understanding the original intent.
        """
        if not self.nucleus:
            return "No nucleus available for actor review"

        prompt = f"""You are the ACTOR in a reflexion process. Your job is to explain
what was done and why.

ACTION TAKEN:
{json.dumps(action, indent=2, default=str)}

{f'CONTEXT: {context}' if context else ''}

Provide a clear explanation of:
1. What was the goal of this action?
2. What approach was taken?
3. What assumptions were made?
4. What was the expected outcome?

Be honest and thorough. Your explanation will be evaluated by another agent."""

        try:
            response = await self.nucleus.generate(prompt)
            return response.get('text', response) if isinstance(response, dict) else str(response)
        except Exception as e:
            logger.error(f"Actor review failed: {e}")
            return f"Actor review error: {str(e)}"

    async def _evaluator_critique(
        self,
        action: Dict[str, Any],
        actor_analysis: str,
        context: Optional[str]
    ) -> Dict[str, Any]:
        """
        Evaluator role: Critically assess the action for issues.

        This is the second perspective - finding potential problems.
        Uses a deliberately skeptical mindset.
        """
        if not self.nucleus:
            return {"error": "No nucleus available", "confidence": 0.5}

        prompt = f"""You are the EVALUATOR in a reflexion process. Your job is to
CRITICALLY assess an action for potential issues. Be skeptical and thorough.

ACTION TAKEN:
{json.dumps(action, indent=2, default=str)}

ACTOR'S EXPLANATION:
{actor_analysis}

{f'CONTEXT: {context}' if context else ''}

Evaluate the following:
1. CORRECTNESS: Is the action logically correct? Any bugs or errors?
2. COMPLETENESS: Are edge cases handled? Missing considerations?
3. EFFICIENCY: Could this be done more efficiently?
4. SAFETY: Any security or stability concerns?
5. ALIGNMENT: Does this align with Darwin's goals?

Respond in JSON format:
{{
    "issues_found": ["list of specific issues"],
    "severity": "low|medium|high|critical",
    "correctness_score": 0.0-1.0,
    "completeness_score": 0.0-1.0,
    "efficiency_score": 0.0-1.0,
    "safety_score": 0.0-1.0,
    "confidence": 0.0-1.0,
    "recommendations": ["specific suggestions for improvement"]
}}"""

        try:
            response = await self.nucleus.generate(prompt)
            text = response.get('text', response) if isinstance(response, dict) else str(response)

            # Parse JSON response
            try:
                # Try to extract JSON from response
                import re
                json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

            # Fallback structure
            return {
                "issues_found": [],
                "severity": "low",
                "correctness_score": 0.8,
                "completeness_score": 0.8,
                "efficiency_score": 0.8,
                "safety_score": 0.9,
                "confidence": 0.7,
                "recommendations": [],
                "raw_response": text
            }

        except Exception as e:
            logger.error(f"Evaluator critique failed: {e}")
            return {"error": str(e), "confidence": 0.5}

    async def _reflector_synthesize(
        self,
        action: Dict[str, Any],
        actor_analysis: str,
        evaluation: Dict[str, Any],
        context: Optional[str]
    ) -> Dict[str, Any]:
        """
        Reflector role: Synthesize feedback into improvements.

        This is the third perspective - creating actionable improvements.
        """
        if not self.nucleus:
            return {"error": "No nucleus available"}

        # Skip improvement if evaluation shows high confidence and no issues
        if (
            evaluation.get('confidence', 0) > 0.9 and
            evaluation.get('severity', 'high') == 'low' and
            not evaluation.get('issues_found', [])
        ):
            return {
                "should_apply": False,
                "reason": "Original action is high quality, no improvement needed",
                "lessons": ["Action was well-executed; maintain this approach"]
            }

        prompt = f"""You are the REFLECTOR in a reflexion process. Your job is to
synthesize the feedback and create an improved version of the action.

ORIGINAL ACTION:
{json.dumps(action, indent=2, default=str)}

ACTOR'S EXPLANATION:
{actor_analysis}

EVALUATOR'S CRITIQUE:
{json.dumps(evaluation, indent=2, default=str)}

{f'CONTEXT: {context}' if context else ''}

Your task:
1. Address each issue found by the evaluator
2. Incorporate the recommendations
3. Preserve what was good about the original
4. Extract lessons for future similar situations

Respond in JSON format:
{{
    "should_apply": true/false,
    "reason": "why to apply or not apply the improvement",
    "improved_action": {{...the improved action object...}},
    "changes_made": ["list of changes"],
    "lessons": ["generalizable lessons for the future"]
}}"""

        try:
            response = await self.nucleus.generate(prompt)
            text = response.get('text', response) if isinstance(response, dict) else str(response)

            # Parse JSON response
            try:
                import re
                json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

            # Fallback structure
            return {
                "should_apply": False,
                "reason": "Could not parse improvement",
                "lessons": ["Reflexion processing needs improvement"],
                "raw_response": text
            }

        except Exception as e:
            logger.error(f"Reflector synthesis failed: {e}")
            return {"error": str(e)}

    def _store_lessons(self, lessons: List[str], action: Dict[str, Any]):
        """Store lessons learned for future reference."""
        for lesson in lessons:
            self.lessons_catalog.append({
                "lesson": lesson,
                "action_type": action.get('type', 'unknown'),
                "timestamp": datetime.utcnow().isoformat()
            })

        # Keep catalog manageable
        if len(self.lessons_catalog) > 1000:
            self.lessons_catalog = self.lessons_catalog[-500:]

    def get_relevant_lessons(self, action_type: str, limit: int = 5) -> List[str]:
        """Get lessons relevant to a specific action type."""
        relevant = [
            entry['lesson']
            for entry in self.lessons_catalog
            if entry.get('action_type') == action_type
        ]
        return relevant[-limit:] if relevant else []

    def get_statistics(self) -> Dict[str, Any]:
        """Get reflexion system statistics."""
        return {
            "total_reflexions": self.total_reflexions,
            "improvements_made": self.improvements_made,
            "improvement_rate": (
                self.improvements_made / self.total_reflexions
                if self.total_reflexions > 0 else 0
            ),
            "lessons_cataloged": len(self.lessons_catalog),
            "recent_lessons": self.lessons_catalog[-10:]
        }


# Quick self-reflection for simpler cases (no multi-agent)
class QuickReflection:
    """
    Lightweight reflection for simpler cases.

    Uses Introspection of Thought (INoT) pattern where
    self-critique happens within a single LLM call.

    Reference: https://arxiv.org/abs/2507.08664
    """

    def __init__(self, nucleus=None):
        self.nucleus = nucleus

    async def quick_check(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Quick self-check using INoT pattern.

        This is 58% more token-efficient than full reflexion.
        """
        if not self.nucleus:
            return {"approved": True, "reason": "No nucleus for reflection"}

        prompt = f"""<reflection>
Analyze this action and provide a quick assessment.

ACTION: {json.dumps(action, indent=2, default=str)}

Think step by step:
1. Is this action correct?
2. Any obvious issues?
3. Should it proceed?

Output format:
APPROVED: yes/no
CONFIDENCE: 0.0-1.0
ISSUES: [list or "none"]
SUGGESTION: [brief improvement or "none"]
</reflection>"""

        try:
            response = await self.nucleus.generate(prompt)
            text = response.get('text', response) if isinstance(response, dict) else str(response)

            # Parse simple format
            approved = 'APPROVED: yes' in text.lower() or 'approved: yes' in text.lower()
            confidence = 0.8  # Default

            return {
                "approved": approved,
                "confidence": confidence,
                "raw_check": text
            }

        except Exception as e:
            logger.error(f"Quick reflection failed: {e}")
            return {"approved": True, "reason": f"Check failed: {e}"}
