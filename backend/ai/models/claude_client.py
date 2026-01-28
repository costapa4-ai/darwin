"""
Claude AI Model Client
Anthropic Claude integration
"""
import anthropic
from typing import Dict, Any, Optional, List
import time

from .base_client import BaseModelClient, ModelCapability
from utils.logger import get_logger

logger = get_logger(__name__)


class ClaudeClient(BaseModelClient):
    """Claude AI client implementation"""

    def __init__(self, model_name: str = "claude-sonnet-4-5-20250929", api_key: str = ""):
        super().__init__(model_name, api_key)

        # Initialize Anthropic client
        self.client = anthropic.Anthropic(api_key=api_key)

        # Set capabilities
        self.capabilities = [
            ModelCapability.CODE_GENERATION,
            ModelCapability.CODE_ANALYSIS,
            ModelCapability.REASONING,
            ModelCapability.CREATIVITY
        ]

        # Pricing (approximate)
        self.cost_per_1k_tokens = 0.015  # $15 per million tokens
        self.avg_latency_ms = 2000

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """Generate completion using Claude"""
        try:
            start_time = time.time()

            # Prepare messages
            messages = [{"role": "user", "content": prompt}]

            # Create completion
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt or "",
                messages=messages
            )

            # Update latency
            self.avg_latency_ms = int((time.time() - start_time) * 1000)

            # Extract text
            result = response.content[0].text

            logger.info(f"Claude generated response in {self.avg_latency_ms}ms")
            return result

        except Exception as e:
            logger.error(f"Claude generation failed: {e}")
            raise

    async def analyze_code(self, code: str, task: str) -> Dict[str, Any]:
        """Analyze code using Claude"""
        try:
            analysis_prompt = f"""Analyze this code for the task: "{task}"

Code:
```python
{code}
```

Provide analysis in JSON format:
{{
  "correctness_score": 0-100,
  "quality_score": 0-100,
  "efficiency_score": 0-100,
  "issues": ["list of issues"],
  "suggestions": ["list of improvements"],
  "overall_assessment": "brief summary"
}}
"""

            response = await self.generate(
                prompt=analysis_prompt,
                system_prompt="You are a code analysis expert. Respond only with valid JSON.",
                temperature=0.3
            )

            # Parse JSON response
            import json
            analysis = json.loads(response)

            return analysis

        except Exception as e:
            logger.error(f"Code analysis failed: {e}")
            return {
                "correctness_score": 50,
                "quality_score": 50,
                "efficiency_score": 50,
                "issues": [str(e)],
                "suggestions": [],
                "overall_assessment": "Analysis failed"
            }

    def get_capabilities(self) -> List[ModelCapability]:
        """Get Claude capabilities"""
        return self.capabilities

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Estimate cost for Claude usage"""
        total_tokens = prompt_tokens + completion_tokens
        return (total_tokens / 1000) * self.cost_per_1k_tokens
