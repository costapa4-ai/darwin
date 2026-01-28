"""
OpenAI Model Client
OpenAI GPT integration (optional)
"""
import openai
from typing import Dict, Any, Optional, List
import time
import json

from .base_client import BaseModelClient, ModelCapability
from utils.logger import get_logger

logger = get_logger(__name__)


class OpenAIClient(BaseModelClient):
    """OpenAI GPT client implementation"""

    def __init__(self, model_name: str = "gpt-4-turbo-preview", api_key: str = ""):
        super().__init__(model_name, api_key)

        # Initialize OpenAI client
        openai.api_key = api_key
        self.client = openai

        # Set capabilities
        self.capabilities = [
            ModelCapability.CODE_GENERATION,
            ModelCapability.CODE_ANALYSIS,
            ModelCapability.REASONING
        ]

        # Pricing (approximate)
        self.cost_per_1k_tokens = 0.01
        self.avg_latency_ms = 1500

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """Generate completion using OpenAI"""
        try:
            start_time = time.time()

            # Prepare messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            # Create completion
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )

            # Update latency
            self.avg_latency_ms = int((time.time() - start_time) * 1000)

            result = response.choices[0].message.content

            logger.info(f"OpenAI generated response in {self.avg_latency_ms}ms")
            return result

        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            raise

    async def analyze_code(self, code: str, task: str) -> Dict[str, Any]:
        """Analyze code using OpenAI"""
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
        """Get OpenAI capabilities"""
        return self.capabilities

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Estimate cost for OpenAI usage"""
        total_tokens = prompt_tokens + completion_tokens
        return (total_tokens / 1000) * self.cost_per_1k_tokens
