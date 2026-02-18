"""
Gemini AI Model Client
Google Gemini integration
"""
import google.generativeai as genai
from typing import Dict, Any, Optional, List
import time
import json

from .base_client import BaseModelClient, ModelCapability
from utils.logger import get_logger

logger = get_logger(__name__)


class GeminiClient(BaseModelClient):
    """Gemini AI client implementation"""

    def __init__(self, model_name: str = "gemini-2.0-flash", api_key: str = ""):
        super().__init__(model_name, api_key)

        # Configure Gemini
        genai.configure(api_key=api_key)
        self.client = genai.GenerativeModel(model_name)

        # Set capabilities
        self.capabilities = [
            ModelCapability.CODE_GENERATION,
            ModelCapability.SPEED,
            ModelCapability.COST_EFFECTIVE
        ]

        # Gemini Flash 2.0 pricing
        self.input_cost_per_1m = 0.10
        self.output_cost_per_1m = 0.40
        self.cost_per_1k_tokens = 0.00025  # Legacy blended fallback
        self.avg_latency_ms = 800

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 8192
    ) -> str:
        """Generate completion using Gemini"""
        try:
            start_time = time.time()

            # Combine system prompt with user prompt
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"

            # Generate response
            response = self.client.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens
                )
            )

            # Update latency
            self.avg_latency_ms = int((time.time() - start_time) * 1000)

            # Check if response was truncated by token limit
            self.last_truncated = False
            try:
                if response.candidates and hasattr(response.candidates[0], 'finish_reason'):
                    finish_reason = response.candidates[0].finish_reason
                    # Gemini uses enum: 1=STOP (normal), 2=MAX_TOKENS, 3=SAFETY, etc.
                    self.last_truncated = finish_reason == 2 or str(finish_reason) == 'MAX_TOKENS'
                    if self.last_truncated:
                        logger.warning(f"⚠️ Gemini response TRUNCATED (hit max_output_tokens={max_tokens}). Output is incomplete!")
            except Exception:
                pass

            result = response.text

            logger.info(f"Gemini generated {len(result)} chars in {self.avg_latency_ms}ms (truncated={self.last_truncated})")
            return result

        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            raise

    async def analyze_code(self, code: str, task: str) -> Dict[str, Any]:
        """Analyze code using Gemini"""
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
        """Get Gemini capabilities"""
        return self.capabilities

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Estimate cost for Gemini usage"""
        total_tokens = prompt_tokens + completion_tokens
        return (total_tokens / 1000) * self.cost_per_1k_tokens
