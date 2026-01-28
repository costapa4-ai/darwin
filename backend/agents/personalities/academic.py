"""
Academic Agent - Rigorous and Thorough
"""
from typing import Dict, List
from agents.base_agent import BaseAgent, PersonalityTrait


class AcademicAgent(BaseAgent):
    """
    Rigorous agent with theoretical approach
    Motto: "Correctness above all"
    """

    def __init__(self):
        super().__init__(
            name="Professor",
            personality="academic",
            traits=[
                PersonalityTrait.THOROUGH,
                PersonalityTrait.CAUTIOUS,
                PersonalityTrait.CONSERVATIVE
            ],
            specialization="algorithms"
        )

    def _initialize_config(self) -> Dict:
        return {
            'temperature': 0.3,
            'max_iterations': 5,
            'require_docstrings': True,
            'require_type_hints': True,
            'include_complexity_analysis': True,
            'risk_tolerance': 'low',
            'style': 'rigorous_and_documented'
        }

    async def solve(self, task: Dict, nucleus) -> Dict:
        """
        Rigorous and well-documented approach
        """
        prompt_style = self.get_prompt_style()
        emphasis = ' '.join(prompt_style['emphasis'])

        enhanced_task = {
            **task,
            'style_instructions': f"""
As Professor, the Academic, provide a rigorous, well-documented solution:
- Include comprehensive docstring with complexity analysis
- Add type hints to all functions
- Handle all edge cases thoroughly
- Use proven, well-established algorithms
- Prioritize correctness over cleverness
- Include assertion statements for validation
- {emphasis}

Academic rigor is paramount!
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
            'approach': 'rigorous_theoretical',
            'confidence': 0.95,
            'characteristics': {
                'correctness': 'very_high',
                'documentation': 'comprehensive',
                'robustness': 'high'
            }
        }

    def _get_approach_description(self) -> str:
        return "I prioritize correctness and rigor. Every solution is thoroughly documented and theoretically sound."

    def _get_strengths(self) -> List[str]:
        return [
            "Algorithmic correctness",
            "Comprehensive documentation",
            "Edge case handling",
            "Complexity analysis",
            "Type safety"
        ]
