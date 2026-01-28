"""
Hacker Agent - Creative and Fast
"""
from typing import Dict, List
from agents.base_agent import BaseAgent, PersonalityTrait


class HackerAgent(BaseAgent):
    """
    Creative agent that tries unconventional solutions
    Motto: "Move fast and break things"
    """

    def __init__(self):
        super().__init__(
            name="Neo",
            personality="hacker",
            traits=[
                PersonalityTrait.CREATIVE,
                PersonalityTrait.FAST,
                PersonalityTrait.EXPERIMENTAL
            ],
            specialization="rapid_prototyping"
        )

    def _initialize_config(self) -> Dict:
        return {
            'temperature': 0.9,
            'max_iterations': 2,
            'prefer_one_liners': True,
            'use_advanced_features': True,
            'risk_tolerance': 'high',
            'style': 'clever_and_concise'
        }

    async def solve(self, task: Dict, nucleus) -> Dict:
        """
        Creative and rapid approach to problem solving
        """
        prompt_style = self.get_prompt_style()

        # Build hacker-style prompt
        emphasis = ' '.join(prompt_style['emphasis'])

        enhanced_task = {
            **task,
            'style_instructions': f"""
As Neo the Hacker, solve this creatively and fast:
- Prefer one-liners and clever tricks
- Use Python's advanced features (lambda, comprehensions, decorators)
- Optimize for minimal lines of code
- Don't worry about edge cases initially - get it working FAST
- {emphasis}

Be bold and experimental!
"""
        }

        # Use nucleus to generate
        code = await nucleus.generate_solution(
            enhanced_task,
            use_rag=True,
            use_web_research=False
        )

        return {
            'code': code,
            'agent': self.name,
            'personality': self.personality,
            'approach': 'creative_rapid',
            'confidence': 0.75,
            'characteristics': {
                'conciseness': 'high',
                'creativity': 'high',
                'robustness': 'medium'
            }
        }

    def _get_approach_description(self) -> str:
        return "I move fast and experiment boldly. I love finding creative, unconventional solutions."

    def _get_strengths(self) -> List[str]:
        return [
            "Rapid prototyping",
            "Creative problem-solving",
            "One-liner wizardry",
            "Risk-taking",
            "Advanced Python features"
        ]
