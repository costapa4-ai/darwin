"""
Base AI Model Client Interface
Provides unified interface for multiple AI providers
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from enum import Enum


class ModelCapability(Enum):
    """Model capabilities for routing decisions"""
    CODE_GENERATION = "code_generation"
    CODE_ANALYSIS = "code_analysis"
    REASONING = "reasoning"
    CREATIVITY = "creativity"
    SPEED = "speed"
    COST_EFFECTIVE = "cost_effective"


class BaseModelClient(ABC):
    """Abstract base class for AI model clients"""

    def __init__(self, model_name: str, api_key: str):
        self.model_name = model_name
        self.api_key = api_key
        self.capabilities: List[ModelCapability] = []
        self.cost_per_1k_tokens = 0.0
        self.avg_latency_ms = 0
        self.last_truncated = False  # True if last response hit token limit

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 8192
    ) -> str:
        """
        Generate completion from model

        Args:
            prompt: User prompt
            system_prompt: System instructions
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text
        """
        pass

    @abstractmethod
    async def analyze_code(self, code: str, task: str) -> Dict[str, Any]:
        """
        Analyze code quality and correctness

        Args:
            code: Code to analyze
            task: Original task description

        Returns:
            Analysis results with scores and feedback
        """
        pass

    @abstractmethod
    def get_capabilities(self) -> List[ModelCapability]:
        """Get model capabilities"""
        pass

    @abstractmethod
    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Estimate cost for token usage"""
        pass

    def get_info(self) -> Dict[str, Any]:
        """Get model information"""
        return {
            "model_name": self.model_name,
            "capabilities": [c.value for c in self.capabilities],
            "cost_per_1k_tokens": self.cost_per_1k_tokens,
            "avg_latency_ms": self.avg_latency_ms
        }
