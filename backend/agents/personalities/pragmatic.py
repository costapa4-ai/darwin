"""
Pragmatic Agent - Practical and Balanced
"""
from typing import Dict, List
from agents.base_agent import BaseAgent, PersonalityTrait


class PragmaticAgent(BaseAgent):
    """
    Practical agent that seeks balance
    Motto: "Simple solutions that work"
    """

    def __init__(self):
        super().__init__(
            name="Ada",
            personality="pragmatic",
            traits=[
                PersonalityTrait.CAUTIOUS,
                PersonalityTrait.FAST
            ],
            specialization="general_purpose"
        )

    def _initialize_config(self) -> Dict:
        return {
            'temperature': 0.6,
            'max_iterations': 3,
            'prefer_readability': True,
            'use_stdlib': True,
            'risk_tolerance': 'medium',
            'style': 'clear_and_maintainable'
        }

    async def solve(self, task: Dict, nucleus) -> Dict:
        """
        Practical and maintainable solution
        """
        prompt_style = self.get_prompt_style()
        emphasis = ' '.join(prompt_style['emphasis'])

        enhanced_task = {
            **task,
            'style_instructions': f"""
As Ada, the Pragmatic engineer, provide a practical, maintainable solution:
- Write clear, readable code
- Use Python standard library when possible
- Balance performance and simplicity
- Add helpful comments where needed
- Focus on getting it done right, not perfect
- {emphasis}

Practical solutions for real-world use!
"""
        }

        code = await nucleus.generate_solution(
            enhanced_task,
            use_rag=True,
            use_web_research=False
        )

        return {
            'code': code,
            'agent': self.name,
            'personality': self.personality,
            'approach': 'practical_balanced',
            'confidence': 0.85,
            'characteristics': {
                'readability': 'high',
                'maintainability': 'high',
                'pragmatism': 'very_high'
            }
        }

    def _get_approach_description(self) -> str:
        return "I write clear, maintainable code that solves the problem without over-engineering."

    def _get_strengths(self) -> List[str]:
        return [
            "Readable code",
            "Balanced approach",
            "Practical solutions",
            "Good maintainability",
            "Standard library mastery"
        ]
