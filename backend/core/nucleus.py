"""AI nucleus - Core intelligence using Claude/Gemini with RAG and Multi-Model support"""
import anthropic
import google.generativeai as genai
from typing import Dict, Optional
from utils.logger import setup_logger

logger = setup_logger(__name__)


class Nucleus:
    """
    Enhanced AI nucleus with:
    - RAG (Retrieval Augmented Generation) support
    - Multi-model routing capability
    - Semantic memory integration
    """

    def __init__(
        self,
        provider: str,
        api_key: str,
        model: Optional[str] = None,
        semantic_memory=None,
        multi_model_router=None,
        web_researcher=None
    ):
        self.provider = provider.lower()
        self.api_key = api_key
        self.semantic_memory = semantic_memory
        self.router = multi_model_router
        self.web_researcher = web_researcher

        # Use router if available, otherwise use direct provider
        if self.router:
            logger.info("Nucleus initialized with multi-model router")
        elif self.provider == "claude":
            self.client = anthropic.Anthropic(api_key=api_key)
            self.model = model or "claude-sonnet-4-5-20250929"
        elif self.provider == "gemini":
            genai.configure(api_key=api_key)
            # Use Gemini 2.0 Flash (latest as of Oct 2025)
            # Available models: gemini-2.0-flash, gemini-1.5-flash, gemini-1.5-pro
            self.model = model or "gemini-2.0-flash"
            self.client = genai.GenerativeModel(self.model)
        else:
            raise ValueError(f"Unknown AI provider: {provider}")

        logger.info(f"Nucleus initialized with {provider}", extra={
            "provider": provider,
            "model": self.model if not self.router else "multi-model",
            "rag_enabled": self.semantic_memory is not None,
            "web_research_enabled": self.web_researcher is not None
        })

    async def generate_solution(self, task: Dict, use_rag: bool = True, use_web_research: bool = False) -> str:
        """
        Generate Python code to solve a task with RAG and web research support

        Args:
            task: Task dictionary
            use_rag: Use semantic memory for context
            use_web_research: Use web research for additional context

        Returns:
            Generated code
        """
        # Get RAG context from semantic memory
        rag_context = ""
        if use_rag and self.semantic_memory:
            try:
                rag_context = await self.semantic_memory.get_rag_context(
                    task.get('description', ''),
                    max_examples=3
                )
                if rag_context:
                    logger.info("RAG context retrieved from semantic memory")
            except Exception as e:
                logger.error(f"Failed to get RAG context: {e}")

        # Get web research context
        web_context = ""
        if use_web_research and self.web_researcher:
            try:
                web_context = await self.web_researcher.research_task(
                    task.get('description', '')
                )
                if web_context:
                    logger.info("Web research context retrieved")
            except Exception as e:
                logger.error(f"Failed to get web research context: {e}")

        # Build enhanced prompt with context
        prompt = self._build_generation_prompt(task, rag_context, web_context)

        try:
            # Use router if available
            if self.router:
                result = await self.router.generate(
                    task_description=task.get('description', ''),
                    prompt=prompt,
                    max_tokens=8192
                )
                code = self._extract_code(result["result"])
                logger.info(f"Solution generated using {result['model_used']}", extra={
                    "task_id": task.get('id'),
                    "code_length": len(code),
                    "model": result['model_used']
                })
            # Fallback to direct provider
            elif self.provider == "claude":
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=8192,
                    messages=[{
                        "role": "user",
                        "content": prompt
                    }]
                )
                code = self._extract_code(response.content[0].text)
                logger.info("Solution generated", extra={
                    "task_id": task.get('id'),
                    "code_length": len(code)
                })

            elif self.provider == "gemini":
                response = self.client.generate_content(prompt)
                code = self._extract_code(response.text)
                logger.info("Solution generated", extra={
                    "task_id": task.get('id'),
                    "code_length": len(code)
                })

            return code

        except Exception as e:
            logger.error(f"Error generating solution: {e}", extra={
                "task_id": task.get('id'),
                "provider": self.provider
            })
            raise

    def analyze_result(self, code: str, result: Dict, task: Dict) -> Dict:
        """Analyze execution result and suggest improvements"""
        prompt = f"""Analyze this code execution result and provide improvement suggestions.

Task: {task.get('description', 'Unknown')}

Code:
```python
{code}
```

Execution Result:
- Success: {result['success']}
- Execution Time: {result['execution_time']:.4f}s
- Output: {result.get('output', 'No output')[:500]}
- Error: {result.get('error', 'No errors')[:500]}

Provide a brief analysis (2-3 sentences) focusing on:
1. What worked well
2. What could be improved
3. Specific optimization suggestions

Keep response concise and actionable."""

        try:
            if self.provider == "claude":
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=512,
                    messages=[{"role": "user", "content": prompt}]
                )
                analysis = response.content[0].text

            elif self.provider == "gemini":
                response = self.client.generate_content(prompt)
                analysis = response.text

            return {
                'analysis': analysis,
                'suggestions': self._extract_suggestions(analysis)
            }

        except Exception as e:
            logger.error(f"Error analyzing result: {e}")
            return {
                'analysis': "Analysis unavailable",
                'suggestions': []
            }

    def evolve_code(self, code: str, feedback: Dict, task: Dict) -> str:
        """Create improved version of code based on feedback"""
        prompt = f"""Improve this Python code based on the feedback provided.

Task: {task.get('description', 'Unknown')}

Current Code:
```python
{code}
```

Feedback:
{feedback.get('analysis', 'No specific feedback')}

Execution Stats:
- Time: {feedback.get('execution_time', 0):.4f}s
- Success: {feedback.get('success', False)}

Create an improved version that:
1. Maintains the same functionality
2. Improves performance if possible
3. Fixes any errors
4. Uses better algorithms or patterns

Return ONLY the improved Python code, no explanations."""

        try:
            if self.provider == "claude":
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=8192,
                    messages=[{"role": "user", "content": prompt}]
                )
                improved_code = self._extract_code(response.content[0].text)

            elif self.provider == "gemini":
                response = self.client.generate_content(prompt)
                improved_code = self._extract_code(response.text)

            logger.info("Code evolved", extra={
                "task_id": task.get('id'),
                "original_length": len(code),
                "new_length": len(improved_code)
            })

            return improved_code

        except Exception as e:
            logger.error(f"Error evolving code: {e}")
            # Return original code if evolution fails
            return code

    def _build_generation_prompt(self, task: Dict, rag_context: str = "", web_context: str = "") -> str:
        """
        Build enhanced prompt for code generation with RAG and web research context

        Args:
            task: Task dictionary
            rag_context: Context from semantic memory
            web_context: Context from web research

        Returns:
            Enhanced prompt
        """
        task_type = task.get('type', 'general')
        description = task.get('description', '')
        parameters = task.get('parameters', {})

        prompt_parts = []

        # Add RAG context if available
        if rag_context:
            prompt_parts.append("# Context from Past Solutions\n")
            prompt_parts.append(rag_context)
            prompt_parts.append("\n---\n")

        # Add web research context if available
        if web_context:
            prompt_parts.append("# Web Research Context\n")
            prompt_parts.append(web_context)
            prompt_parts.append("\n---\n")

        # Main prompt
        prompt_parts.append(f"""Generate Python code to solve this task.

Task Type: {task_type}
Description: {description}

Requirements:
1. Write clean, efficient Python code
2. Include a main function or executable code
3. Add brief comments for complex logic
4. Handle edge cases
5. Print the result to stdout
6. Learn from any provided context and examples above

Parameters: {parameters if parameters else 'None'}

Return ONLY the Python code, without any markdown formatting or explanations.
The code should be ready to execute.""")

        return "\n".join(prompt_parts)

    def _extract_code(self, text: str) -> str:
        """Extract Python code from AI response"""
        # Remove markdown code blocks if present
        if "```python" in text:
            start = text.find("```python") + 9
            end = text.find("```", start)
            code = text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            code = text[start:end].strip()
        else:
            code = text.strip()

        return code

    async def generate(self, prompt: str, max_tokens: int = 512) -> str:
        """
        Simple text generation with a prompt.

        Args:
            prompt: The text prompt to send to the AI
            max_tokens: Maximum tokens in response

        Returns:
            Generated text response
        """
        try:
            if self.router:
                result = await self.router.generate(
                    task_description="text generation",
                    prompt=prompt,
                    max_tokens=max_tokens
                )
                return result["result"]

            elif self.provider == "claude":
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.content[0].text

            elif self.provider == "gemini":
                response = self.client.generate_content(prompt)
                return response.text

            else:
                raise ValueError(f"Unknown provider: {self.provider}")

        except Exception as e:
            logger.error(f"Error in generate: {e}", extra={"provider": self.provider})
            raise

    def _extract_suggestions(self, analysis: str) -> list:
        """Extract actionable suggestions from analysis"""
        # Simple extraction - look for numbered points or bullet points
        suggestions = []
        lines = analysis.split('\n')

        for line in lines:
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                # Remove numbering or bullets
                clean_line = line.lstrip('0123456789.-•) ').strip()
                if clean_line:
                    suggestions.append(clean_line)

        return suggestions[:5]  # Limit to top 5 suggestions
