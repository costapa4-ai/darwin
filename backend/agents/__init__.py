"""
Multi-Agent System for Darwin Phase 3
"""
from .base_agent import BaseAgent, PersonalityTrait, AgentMemory, AgentStats
from .agent_coordinator import AgentCoordinator

__all__ = [
    'BaseAgent',
    'PersonalityTrait',
    'AgentMemory',
    'AgentStats',
    'AgentCoordinator'
]
