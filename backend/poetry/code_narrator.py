"""
Code Narrator - Generates poetic narratives about code
"""
from typing import Dict, List
from datetime import datetime
import random


class CodeNarrator:
    """
    Generates poetic narratives and documentation about code evolution
    """

    def __init__(self):
        self.stories_generated = 0

    def narrate_solution(self, task: Dict, solution: Dict) -> str:
        """
        Create poetic narrative about a solution
        """
        code = solution.get('code', '')
        agent = solution.get('agent', 'Unknown')
        fitness = solution.get('fitness_score', 0)

        # Extract function name
        import re
        func_match = re.search(r'def\s+(\w+)\s*\(', code)
        func_name = func_match.group(1) if func_match else 'the_solution'

        narrative = f"""
## The Tale of {func_name}

On this {datetime.utcnow().strftime('%A')}, {agent} embarked on a quest to {task.get('description', 'solve the unknown')}.

After careful contemplation, {func_name} emerged — a solution of {len(code.split())} words,
achieving a fitness of {fitness:.1f}.

{self._generate_code_poetry(code)}

And so, {func_name} joined the library of wisdom, ready to serve future generations.
        """.strip()

        self.stories_generated += 1
        return narrative

    def _generate_code_poetry(self, code: str) -> str:
        """Generate poem about the code"""
        if 'for' in code and 'in' in code:
            poem = "It dances through collections,\nEach element a story,\nIn loops of iteration."
        elif 'if' in code and 'else' in code:
            poem = "Decisions branch like rivers,\nTruth and falsehood diverging,\nTo meet at function's end."
        elif 'return' in code:
            lines = len(code.split('\n'))
            poem = f"In {lines} lines it speaks,\nA truth crystallized in syntax,\nReturning light from logic."
        else:
            poem = "Code flows like water,\nPurpose meeting form,\nA solution manifested."

        return f"__{poem}__"

    def generate_haiku(self, execution: Dict) -> str:
        """
        Generate haiku about execution
        """
        success = execution.get('success', False)
        time = execution.get('execution_time', 0)

        if success:
            haikus = [
                f"Code compiles and runs\n{time:.2f} seconds of grace\nSuccess blooms at last",
                "Logic flows correct\nBits align in harmony\nPerfect execution",
                "The function returns\nCarrying truth in its wake\nSilent victory"
            ]
        else:
            haikus = [
                "Error at runtime\nException breaks the silence\nWe learn and try more",
                "The code stumbles, falls\nBut failure teaches wisdom\nNext time, we prevail",
                "Timeout reached at last\nComputation's endless dream\nMust wake and retry"
            ]

        return random.choice(haikus)

    def create_evolution_story(self, generations: List[Dict]) -> str:
        """
        Tell story of evolution through generations
        """
        if not generations:
            return "No story to tell yet."

        story = "# The Evolution Chronicle\n\n"

        for i, gen in enumerate(generations, 1):
            fitness = gen.get('best_fitness', 0)

            if i == 1:
                story += f"## Generation {i}: The Beginning\n\n"
                story += f"In the primordial code, the first solution emerged with fitness {fitness:.1f}.\n"
                story += "Naive, perhaps, but full of potential.\n\n"

            elif i > 1 and fitness > generations[i-2].get('best_fitness', 0):
                improvement = fitness - generations[i-2].get('best_fitness', 0)
                story += f"## Generation {i}: Breakthrough\n\n"
                story += f"A leap forward! Fitness soared by {improvement:.1f} points to {fitness:.1f}.\n"
                story += "Progress was made.\n\n"

            else:
                story += f"## Generation {i}: Refinement\n\n"
                story += f"Subtle improvements brought fitness to {fitness:.1f}.\n"
                story += "Sometimes evolution is about perfecting what works.\n\n"

        final = generations[-1]
        story += "## Epilogue\n\n"
        story += f"After {len(generations)} generations, the optimal solution emerged.\n"
        story += f"Final fitness: {final.get('best_fitness', 0):.1f}. A journey from chaos to elegance.\n"

        return story
