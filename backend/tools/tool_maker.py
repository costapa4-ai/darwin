"""
ToolMaker: Autonomous Tool Creation System

Allows Darwin to autonomously create new tools when capability gaps are detected.

Based on research:
- ToolMaker: Autonomous tool creation from papers/code (arXiv:2502.11705)
- Systems can identify gaps and dynamically create new tools

Key features:
1. Capability gap detection from failed tasks
2. Tool specification generation
3. Code generation with self-testing
4. Closed-loop self-correction for debugging
5. Approval workflow integration
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
import json
import re
import logging

logger = logging.getLogger(__name__)


@dataclass
class ToolSpecification:
    """Specification for a tool to be created"""
    name: str
    description: str
    purpose: str
    input_params: List[Dict[str, str]]  # [{name, type, description}]
    output_type: str
    example_usage: str
    category: str = "utility"
    mode: str = "WAKE"  # WAKE, SLEEP, or BOTH
    created_from: str = ""  # What triggered this tool creation
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        return result


@dataclass
class ToolCreationResult:
    """Result of a tool creation attempt"""
    success: bool
    tool_name: str
    code: Optional[str] = None
    file_path: Optional[str] = None
    test_result: Optional[Dict] = None
    approval_status: str = "pending"  # pending, approved, rejected
    error: Optional[str] = None
    attempts: int = 1
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        return result


class ToolMaker:
    """
    Autonomous tool creation system for Darwin.

    Detects capability gaps and creates new tools to fill them.
    Uses closed-loop self-correction for debugging generated code.
    """

    def __init__(
        self,
        nucleus=None,
        tool_manager=None,
        approval_queue=None,
        tools_dir: str = "/app/tools/generated"
    ):
        """
        Initialize the ToolMaker.

        Args:
            nucleus: LLM interface for code generation
            tool_manager: Tool manager for registering new tools
            approval_queue: Approval queue for human review
            tools_dir: Directory to store generated tools
        """
        self.nucleus = nucleus
        self.tool_manager = tool_manager
        self.approval_queue = approval_queue
        self.tools_dir = tools_dir

        # Configuration
        self.max_creation_attempts = 3
        self.max_debug_iterations = 3

        # Statistics
        self.tools_created = 0
        self.creation_attempts = 0
        self.failed_attempts = 0
        self.gap_detections = 0

        # Track recent gaps to avoid duplicates
        self.recent_gaps: List[Dict] = []

    async def detect_capability_gap(
        self,
        failed_task: Dict[str, Any],
        error_context: Optional[str] = None
    ) -> Optional[ToolSpecification]:
        """
        Analyze a failed task to identify if a new tool would help.

        Args:
            failed_task: Information about the failed task
            error_context: Additional error context

        Returns:
            ToolSpecification if a new tool would help, None otherwise
        """
        self.gap_detections += 1

        if not self.nucleus:
            return None

        # Check if this gap was recently detected
        task_signature = f"{failed_task.get('type', '')}:{failed_task.get('description', '')[:50]}"
        if any(g.get('signature') == task_signature for g in self.recent_gaps[-10:]):
            logger.info(f"Gap already detected recently: {task_signature}")
            return None

        prompt = f"""Analyze this failed task and determine if a new tool would help solve it.

FAILED TASK:
{json.dumps(failed_task, indent=2, default=str)}

{f'ERROR CONTEXT: {error_context}' if error_context else ''}

Consider:
1. Is this a recurring capability gap?
2. Would a reusable tool solve this?
3. Is this something Darwin should be able to do autonomously?
4. Does a similar tool already exist?

If a new tool would help, provide its specification in JSON:
{{
    "tool_needed": true,
    "name": "snake_case_tool_name",
    "description": "What the tool does",
    "purpose": "Why Darwin needs this tool",
    "input_params": [
        {{"name": "param1", "type": "str", "description": "Description"}}
    ],
    "output_type": "Dict[str, Any]",
    "example_usage": "tool_name(param1='value')",
    "category": "utility|analysis|optimization|learning",
    "mode": "WAKE|SLEEP|BOTH"
}}

If no tool is needed, return:
{{"tool_needed": false, "reason": "explanation"}}"""

        try:
            response = await self.nucleus.generate(prompt)
            text = response.get('text', response) if isinstance(response, dict) else str(response)

            # Parse JSON response
            json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
            if not json_match:
                return None

            result = json.loads(json_match.group())

            if not result.get('tool_needed', False):
                logger.info(f"No tool needed: {result.get('reason', 'unknown')}")
                return None

            # Track this gap
            self.recent_gaps.append({
                'signature': task_signature,
                'timestamp': datetime.utcnow().isoformat()
            })

            # Create specification
            spec = ToolSpecification(
                name=result.get('name', 'unnamed_tool'),
                description=result.get('description', ''),
                purpose=result.get('purpose', ''),
                input_params=result.get('input_params', []),
                output_type=result.get('output_type', 'Any'),
                example_usage=result.get('example_usage', ''),
                category=result.get('category', 'utility'),
                mode=result.get('mode', 'WAKE'),
                created_from=task_signature
            )

            logger.info(f"Detected capability gap: {spec.name}")
            return spec

        except Exception as e:
            logger.error(f"Gap detection failed: {e}")
            return None

    async def create_tool(
        self,
        specification: ToolSpecification
    ) -> ToolCreationResult:
        """
        Generate a new tool from specification.

        Uses closed-loop self-correction for debugging.

        Args:
            specification: The tool specification

        Returns:
            ToolCreationResult with the generated tool or error
        """
        self.creation_attempts += 1

        if not self.nucleus:
            return ToolCreationResult(
                success=False,
                tool_name=specification.name,
                error="No nucleus available for code generation"
            )

        result = ToolCreationResult(
            success=False,
            tool_name=specification.name
        )

        try:
            # Step 1: Generate tool code
            tool_code = await self._generate_tool_code(specification)

            if not tool_code:
                result.error = "Code generation failed"
                self.failed_attempts += 1
                return result

            result.code = tool_code

            # Step 2: Self-test the tool
            test_result = await self._test_tool(tool_code, specification)

            # Step 3: Debug loop if tests fail
            for attempt in range(self.max_debug_iterations):
                if test_result.get('success', False):
                    break

                logger.info(f"Debug iteration {attempt + 1}/{self.max_debug_iterations}")
                tool_code = await self._debug_and_fix(
                    tool_code,
                    test_result.get('error', 'Unknown error'),
                    specification
                )

                if not tool_code:
                    break

                result.code = tool_code
                test_result = await self._test_tool(tool_code, specification)
                result.attempts += 1

            result.test_result = test_result

            # Step 4: Submit for approval if tests pass
            if test_result.get('success', False):
                result.success = True
                result.file_path = f"{self.tools_dir}/{specification.name}.py"

                # Submit to approval queue
                if self.approval_queue:
                    approval_result = await self._submit_for_approval(
                        specification,
                        tool_code
                    )
                    result.approval_status = approval_result.get('status', 'pending')

                self.tools_created += 1
                logger.info(f"Tool created successfully: {specification.name}")
            else:
                result.error = f"Tests failed after {result.attempts} attempts"
                self.failed_attempts += 1
                logger.warning(f"Tool creation failed: {specification.name}")

        except Exception as e:
            result.error = str(e)
            self.failed_attempts += 1
            logger.error(f"Tool creation error: {e}")

        return result

    async def _generate_tool_code(
        self,
        specification: ToolSpecification
    ) -> Optional[str]:
        """Generate Python code for the tool"""
        # Build parameter list
        params = []
        for param in specification.input_params:
            params.append(f"{param['name']}: {param.get('type', 'Any')}")
        params_str = ", ".join(params)

        prompt = f"""Generate a Python tool function for Darwin's autonomous system.

TOOL SPECIFICATION:
- Name: {specification.name}
- Description: {specification.description}
- Purpose: {specification.purpose}
- Parameters: {json.dumps(specification.input_params, indent=2)}
- Output Type: {specification.output_type}
- Example: {specification.example_usage}
- Category: {specification.category}
- Mode: {specification.mode}

REQUIREMENTS:
1. Function must be async (async def)
2. Include comprehensive docstring
3. Handle errors gracefully
4. Return a Dict with 'success' key
5. Include type hints
6. Keep dependencies minimal (use stdlib when possible)
7. Include basic input validation

Generate ONLY the Python code, no explanations:

```python
async def {specification.name}({params_str}) -> Dict[str, Any]:
    ...
```"""

        try:
            response = await self.nucleus.generate(prompt, max_tokens=8192)
            text = response.get('text', response) if isinstance(response, dict) else str(response)

            # Extract code from response
            code_match = re.search(r'```python\n(.*?)```', text, re.DOTALL)
            if code_match:
                return code_match.group(1).strip()

            # Try to find code without markdown
            if 'async def' in text:
                start = text.find('async def')
                return text[start:].strip()

            return None

        except Exception as e:
            logger.error(f"Code generation failed: {e}")
            return None

    async def _test_tool(
        self,
        code: str,
        specification: ToolSpecification
    ) -> Dict[str, Any]:
        """Test the generated tool code"""
        try:
            # Syntax check
            compile(code, '<string>', 'exec')

            # Check for required elements
            if 'async def' not in code:
                return {"success": False, "error": "Function must be async"}

            if specification.name not in code:
                return {"success": False, "error": f"Function name '{specification.name}' not found"}

            if 'return' not in code:
                return {"success": False, "error": "Function must have a return statement"}

            # Check for type hints
            if '-> Dict' not in code and '-> dict' not in code:
                return {"success": False, "error": "Missing return type hint (Dict)"}

            # Check for docstring
            if '"""' not in code and "'''" not in code:
                return {"success": False, "error": "Missing docstring"}

            # Check for error handling
            if 'try:' not in code or 'except' not in code:
                return {"success": False, "error": "Missing error handling (try/except)"}

            # Check for success key in return
            if "'success'" not in code and '"success"' not in code:
                return {"success": False, "error": "Return dict should have 'success' key"}

            return {"success": True, "message": "All validation checks passed"}

        except SyntaxError as e:
            return {"success": False, "error": f"Syntax error: {e}"}
        except Exception as e:
            return {"success": False, "error": f"Validation error: {e}"}

    async def _debug_and_fix(
        self,
        code: str,
        error: str,
        specification: ToolSpecification
    ) -> Optional[str]:
        """Debug and fix code based on error"""
        if not self.nucleus:
            return None

        prompt = f"""Fix this Python tool code based on the error.

CURRENT CODE:
```python
{code}
```

ERROR:
{error}

TOOL SPECIFICATION:
- Name: {specification.name}
- Description: {specification.description}

REQUIREMENTS:
1. Function must be async
2. Must have docstring
3. Must have error handling (try/except)
4. Must return Dict with 'success' key
5. Must have type hints

Return ONLY the fixed Python code:

```python
async def {specification.name}(...) -> Dict[str, Any]:
    ...
```"""

        try:
            response = await self.nucleus.generate(prompt, max_tokens=8192)
            text = response.get('text', response) if isinstance(response, dict) else str(response)

            # Extract code
            code_match = re.search(r'```python\n(.*?)```', text, re.DOTALL)
            if code_match:
                return code_match.group(1).strip()

            if 'async def' in text:
                start = text.find('async def')
                return text[start:].strip()

            return None

        except Exception as e:
            logger.error(f"Debug failed: {e}")
            return None

    async def _submit_for_approval(
        self,
        specification: ToolSpecification,
        code: str
    ) -> Dict[str, Any]:
        """Submit the tool for human approval"""
        if not self.approval_queue:
            return {"status": "no_queue"}

        try:
            # Create approval entry
            approval_entry = {
                "type": "new_tool",
                "tool_name": specification.name,
                "description": specification.description,
                "category": specification.category,
                "mode": specification.mode,
                "code": code,
                "file_path": f"{self.tools_dir}/{specification.name}.py",
                "specification": specification.to_dict(),
                "created_at": datetime.utcnow().isoformat()
            }

            result = self.approval_queue.add_tool(approval_entry)
            return result or {"status": "pending"}

        except Exception as e:
            logger.error(f"Approval submission failed: {e}")
            return {"status": "error", "error": str(e)}

    def get_statistics(self) -> Dict[str, Any]:
        """Get ToolMaker statistics"""
        return {
            "tools_created": self.tools_created,
            "creation_attempts": self.creation_attempts,
            "failed_attempts": self.failed_attempts,
            "success_rate": (
                self.tools_created / self.creation_attempts
                if self.creation_attempts > 0 else 0
            ),
            "gap_detections": self.gap_detections,
            "recent_gaps": len(self.recent_gaps)
        }
