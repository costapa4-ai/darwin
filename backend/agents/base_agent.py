"""
Base Agent Architecture for Multi-Agent System
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import uuid
from datetime import datetime


class PersonalityTrait(Enum):
    """Agent personality traits"""
    CREATIVE = "creative"
    CAUTIOUS = "cautious"
    FAST = "fast"
    THOROUGH = "thorough"
    EXPERIMENTAL = "experimental"
    CONSERVATIVE = "conservative"


@dataclass
class AgentMemory:
    """Personal memory for each agent"""
    tasks_solved: int = 0
    total_fitness: float = 0.0
    specializations: List[str] = field(default_factory=list)
    favorite_patterns: List[str] = field(default_factory=list)
    learned_insights: List[str] = field(default_factory=list)


@dataclass
class AgentStats:
    """Agent performance statistics"""
    success_rate: float
    avg_fitness: float
    avg_execution_time: float
    tasks_completed: int
    specializations: List[str]


class BaseAgent(ABC):
    """
    Base agent class with personality and memory
    Each agent has a unique problem-solving style
    """

    def __init__(
        self,
        name: str,
        personality: str,
        traits: List[PersonalityTrait],
        specialization: str
    ):
        self.id = str(uuid.uuid4())
        self.name = name
        self.personality = personality
        self.traits = traits
        self.specialization = specialization
        self.memory = AgentMemory()
        self.created_at = datetime.utcnow()

        # Configuration based on personality
        self.config = self._initialize_config()

    @abstractmethod
    def _initialize_config(self) -> Dict:
        """Each personality defines its own configuration"""
        pass

    @abstractmethod
    async def solve(self, task: Dict, nucleus) -> Dict:
        """
        Solve task according to personality

        Args:
            task: Task dictionary
            nucleus: AI nucleus for generation

        Returns:
            Solution dictionary with code and metadata
        """
        pass

    def get_prompt_style(self) -> Dict:
        """
        Returns characteristic prompt style for this agent
        """
        base_style = {
            'temperature': 0.7,
            'system_prompt': f"You are {self.name}, a {self.personality} problem solver.",
            'emphasis': []
        }

        # Modify based on traits
        if PersonalityTrait.CREATIVE in self.traits:
            base_style['temperature'] = 0.9
            base_style['emphasis'].append("Think outside the box")

        if PersonalityTrait.CAUTIOUS in self.traits:
            base_style['temperature'] = 0.3
            base_style['emphasis'].append("Prioritize safety and correctness")

        if PersonalityTrait.FAST in self.traits:
            base_style['emphasis'].append("Optimize for speed")

        if PersonalityTrait.THOROUGH in self.traits:
            base_style['emphasis'].append("Be comprehensive and detailed")

        return base_style

    def learn_from_result(self, result: Dict):
        """
        Update memory based on execution result
        """
        self.memory.tasks_solved += 1

        if result.get('success'):
            fitness = result.get('fitness_score', 0)
            self.memory.total_fitness += fitness

            # Learn successful patterns
            if fitness > 80:
                code = result.get('code', '')
                patterns = self._extract_patterns(code)
                for pattern in patterns:
                    if pattern not in self.memory.favorite_patterns:
                        self.memory.favorite_patterns.append(pattern)
                        if len(self.memory.favorite_patterns) > 10:
                            self.memory.favorite_patterns.pop(0)

    def _extract_patterns(self, code: str) -> List[str]:
        """Identify patterns in code"""
        patterns = []

        if '[' in code and 'for' in code:
            patterns.append('list_comprehension')

        if '@lru_cache' in code or '@cache' in code:
            patterns.append('memoization')

        if 'try:' in code:
            patterns.append('error_handling')

        if 'assert' in code:
            patterns.append('defensive_programming')

        if 'lambda' in code:
            patterns.append('functional_programming')

        if '"""' in code or "'''" in code:
            patterns.append('documentation')

        return patterns

    def get_stats(self) -> AgentStats:
        """Get agent statistics"""
        avg_fitness = (
            self.memory.total_fitness / self.memory.tasks_solved
            if self.memory.tasks_solved > 0 else 0
        )

        return AgentStats(
            success_rate=0.0,  # Calculated externally
            avg_fitness=avg_fitness,
            avg_execution_time=0.0,  # Calculated externally
            tasks_completed=self.memory.tasks_solved,
            specializations=[self.specialization]
        )

    def describe_self(self) -> str:
        """Generate narrative self-description"""
        return f"""
I am {self.name}, a {self.personality} agent.

My approach: {self._get_approach_description()}
My strengths: {', '.join(self._get_strengths())}
Tasks completed: {self.memory.tasks_solved}
Average fitness: {self.get_stats().avg_fitness:.1f}
Favorite patterns: {', '.join(self.memory.favorite_patterns[:3]) if self.memory.favorite_patterns else 'still learning'}
        """.strip()

    @abstractmethod
    def _get_approach_description(self) -> str:
        """Describe problem-solving approach"""
        pass

    @abstractmethod
    def _get_strengths(self) -> List[str]:
        """List agent strengths"""
        pass

    def to_dict(self) -> Dict:
        """Serialize agent to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'personality': self.personality,
            'traits': [t.value for t in self.traits],
            'specialization': self.specialization,
            'memory': {
                'tasks_solved': self.memory.tasks_solved,
                'avg_fitness': self.get_stats().avg_fitness,
                'favorite_patterns': self.memory.favorite_patterns
            },
            'config': self.config,
            'created_at': self.created_at.isoformat()
        }
