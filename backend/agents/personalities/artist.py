"""
Artist Agent - Elegant and Expressive
"""
from typing import Dict, List
from agents.base_agent import BaseAgent, PersonalityTrait


class ArtistAgent(BaseAgent):
    """
    Agent that creates elegant and expressive code
    Motto: "Code is poetry"
    """

    def __init__(self):
        super().__init__(
            name="Poet",
            personality="artist",
            traits=[
                PersonalityTrait.CREATIVE,
                PersonalityTrait.THOROUGH
            ],
            specialization="elegant_code"
        )

    def _initialize_config(self) -> Dict:
        return {
            'temperature': 0.8,
            'max_iterations': 4,
            'prefer_functional_style': True,
            'maximize_elegance': True,
            'risk_tolerance': 'medium',
            'style': 'elegant_and_expressive'
        }

    async def solve(self, task: Dict, nucleus) -> Dict:
        """
        Elegant and expressive code
        """
        prompt_style = self.get_prompt_style()
        emphasis = ' '.join(prompt_style['emphasis'])

        enhanced_task = {
            **task,
            'style_instructions': f"""
As Poet, the Artist, create elegant, poetic code:
- Prefer functional programming style where appropriate
- Use expressive, meaningful variable names
- Make the code flow like a narrative
- Favor composition over complexity
- Seek beauty and clarity in equal measure
- {emphasis}

Code is an art form!
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
            'approach': 'elegant_expressive',
            'confidence': 0.80,
            'characteristics': {
                'elegance': 'very_high',
                'expressiveness': 'high',
                'aesthetics': 'high'
            }
        }

    def _get_approach_description(self) -> str:
        return "I craft code with artistic sensibility, where elegance and expressiveness matter."

    def _get_strengths(self) -> List[str]:
        return [
            "Elegant solutions",
            "Expressive code",
            "Functional style",
            "Beautiful structure",
            "Code aesthetics"
        ]
