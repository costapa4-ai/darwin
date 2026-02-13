"""
Ollama AI Model Client
Local LLM integration for cost-free, low-latency tasks
"""
import asyncio
import aiohttp
import json
import re
import time
from typing import Dict, Any, Optional, List

from .base_client import BaseModelClient, ModelCapability
from utils.logger import get_logger

logger = get_logger(__name__)


class OllamaClient(BaseModelClient):
    """
    Ollama client for local LLM inference.

    Perfect for:
    - Simple chat responses
    - Basic code formatting
    - Status summaries
    - Curiosity generation
    - Light classification tasks

    Benefits:
    - Zero cost (runs locally)
    - Low latency (no network)
    - Privacy (data stays local)
    - Always available (no rate limits)
    """

    # Regex to strip <think>...</think> blocks from qwen3 responses
    _THINK_RE = re.compile(r'<think>.*?</think>\s*', re.DOTALL)

    def __init__(
        self,
        model_name: str = "qwen3:8b",
        base_url: str = "http://ollama:11434",
        api_key: str = ""  # Not used but required by interface
    ):
        super().__init__(model_name, api_key)

        self.base_url = base_url.rstrip('/')

        # Set capabilities - Ollama is fast and free but less capable
        self.capabilities = [
            ModelCapability.SPEED,
            ModelCapability.COST_EFFECTIVE,
            ModelCapability.CODE_GENERATION,  # Basic code gen
        ]

        # Pricing: FREE!
        self.cost_per_1k_tokens = 0.0
        self.avg_latency_ms = 200  # Local inference is fast

        logger.info(f"Ollama client initialized: {model_name} @ {base_url}")

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 8192,
        **kwargs
    ) -> str:
        """Generate completion using local Ollama"""
        try:
            start_time = time.time()

            # Build messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            # Add /no_think to disable qwen3 thinking mode (saves 30-50% gen time on CPU)
            user_content = f"/no_think\n{prompt}" if 'qwen3' in self.model_name else prompt
            messages.append({"role": "user", "content": user_content})

            # Call Ollama API
            async with aiohttp.ClientSession(
                read_bufsize=2**20  # 1MB read buffer for large responses
            ) as session:
                async with session.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model_name,
                        "messages": messages,
                        "stream": False,
                        "options": {
                            "temperature": temperature,
                            "num_predict": max_tokens,
                            "num_ctx": 4096
                        }
                    },
                    timeout=aiohttp.ClientTimeout(total=kwargs.get('timeout', 45))
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Ollama HTTP {response.status}: {error_text[:500]}")
                        raise Exception(f"Ollama error {response.status}: {error_text[:200]}")

                    # Read full response body before parsing
                    raw_body = await response.read()
                    data = json.loads(raw_body)
                    result = data.get("message", {}).get("content", "")

                    # Strip <think>...</think> blocks from qwen3 responses
                    if '<think>' in result:
                        result = self._THINK_RE.sub('', result).strip()

                    # Check if response was truncated by token limit
                    done_reason = data.get("done_reason", "")
                    eval_count = data.get("eval_count", 0)
                    self.last_truncated = done_reason == "length" or (eval_count >= max_tokens and eval_count > 0)
                    if self.last_truncated:
                        logger.warning(
                            f"⚠️ Ollama response TRUNCATED (done_reason={done_reason}, "
                            f"eval_count={eval_count}, num_predict={max_tokens}). Output is incomplete!"
                        )

            # Update latency
            self.avg_latency_ms = int((time.time() - start_time) * 1000)

            logger.info(f"Ollama ({self.model_name}) generated {len(result)} chars in {self.avg_latency_ms}ms (truncated={self.last_truncated})")
            return result

        except asyncio.TimeoutError:
            logger.warning(f"Ollama timed out after 45s (model={self.model_name}), using cloud fallback")
            raise Exception(f"Ollama timed out after 45s")
        except aiohttp.ClientError as e:
            logger.error(f"Ollama connection error: {e}")
            raise Exception(f"Cannot connect to Ollama at {self.base_url}. Is it running?")
        except Exception as e:
            logger.error(f"Ollama generation failed ({type(e).__name__}): {e}")
            raise

    async def analyze_code(self, code: str, task: str) -> Dict[str, Any]:
        """Analyze code using Ollama (basic analysis)"""
        try:
            analysis_prompt = f"""Analyze this Python code for the task: "{task}"

Code:
```python
{code}
```

Respond with JSON only:
{{
  "correctness_score": <0-100>,
  "quality_score": <0-100>,
  "efficiency_score": <0-100>,
  "issues": ["issue1", "issue2"],
  "suggestions": ["suggestion1"],
  "overall_assessment": "brief summary"
}}"""

            response = await self.generate(
                prompt=analysis_prompt,
                system_prompt="You are a code reviewer. Respond with valid JSON only, no markdown.",
                temperature=0.3
            )

            # Try to extract JSON from response
            response = response.strip()
            if response.startswith("```"):
                # Remove markdown code blocks
                lines = response.split("\n")
                response = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

            analysis = json.loads(response)
            return analysis

        except json.JSONDecodeError as e:
            logger.warning(f"Ollama returned invalid JSON: {e}")
            return {
                "correctness_score": 60,
                "quality_score": 60,
                "efficiency_score": 60,
                "issues": ["Could not parse analysis"],
                "suggestions": [],
                "overall_assessment": "Basic analysis - JSON parsing failed"
            }
        except Exception as e:
            logger.error(f"Ollama code analysis failed: {e}")
            return {
                "correctness_score": 50,
                "quality_score": 50,
                "efficiency_score": 50,
                "issues": [str(e)],
                "suggestions": [],
                "overall_assessment": "Analysis failed"
            }

    def get_capabilities(self) -> List[ModelCapability]:
        """Get Ollama capabilities"""
        return self.capabilities

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Ollama is FREE - no cost"""
        return 0.0

    async def health_check(self) -> bool:
        """Check if Ollama is available"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    return response.status == 200
        except:
            return False

    async def list_models(self) -> List[str]:
        """List available Ollama models"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return [m["name"] for m in data.get("models", [])]
        except:
            pass
        return []

    async def pull_model(self, model_name: str) -> bool:
        """Pull a model if not available"""
        try:
            logger.info(f"Pulling Ollama model: {model_name}")
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/pull",
                    json={"name": model_name},
                    timeout=aiohttp.ClientTimeout(total=600)  # 10 min for large models
                ) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Failed to pull model {model_name}: {e}")
            return False
