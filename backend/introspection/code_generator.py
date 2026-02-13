"""
Code Generator: Generates code to implement Self-Analysis insights
Uses AI to create code changes based on improvement suggestions
"""
import difflib
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime
import json

from introspection.self_analyzer import CodeInsight

logger = logging.getLogger(__name__)


@dataclass
class GeneratedCode:
    """Represents code generated to implement an improvement"""
    insight_id: str
    insight_title: str
    file_path: str
    original_code: str
    new_code: str
    diff_html: str
    diff_unified: str
    explanation: str
    risk_level: str  # 'low', 'medium', 'high'
    estimated_time_minutes: int
    tests_code: Optional[str] = None
    generated_at: str = None
    is_new_file: bool = False  # Whether this is a new file creation
    tool_test_passed: Optional[bool] = None  # NEW: Whether tool passed automated tests
    tool_test_report: Optional[str] = None  # NEW: Detailed test report

    def __post_init__(self):
        if self.generated_at is None:
            self.generated_at = datetime.now().isoformat()


class CodeGenerator:
    """
    Generates code to implement Self-Analysis insights
    Uses AI (Nucleus) to create actual code changes
    """

    # Critical files that should NOT be modified directly
    # Darwin should create new tools/modules instead
    PROTECTED_FILES = {
        'main.py',                          # Application entry point
        'config.py',                        # Configuration
        'docker-compose.yml',               # Docker orchestration
        'Dockerfile',                       # Docker build
        'requirements.txt',                 # Dependencies
        '.env',                             # Environment variables
        'pyproject.toml',                   # Project metadata
        'api/routes.py',                    # Core API routes (can add new route files)
        'core/redis_client.py',            # Core Redis connection
        'core/semantic_memory.py',         # Core memory system
        'introspection/code_generator.py', # This file (self-protection)
        'introspection/code_validator.py', # Validation system
        'consciousness/consciousness_engine.py',  # Core consciousness
        'consciousness/tool_registry.py',   # Tool registry system
        'ai/multi_model_router.py',        # AI routing
        'utils/logger.py',                  # Logging infrastructure
    }

    def __init__(self, nucleus=None, multi_model_router=None, tool_registry=None):
        """
        Args:
            nucleus: AI service for code generation (Nucleus instance)
            multi_model_router: Multi-model router for AI generation
            tool_registry: Tool registry to check for existing tools
        """
        self.nucleus = nucleus
        self.multi_model_router = multi_model_router
        self.tool_registry = tool_registry
        self.project_root = Path("/app")
        self._register_prompts()

    def _register_prompts(self):
        """Register evolvable prompts with the PromptRegistry."""
        try:
            from consciousness.prompt_registry import get_prompt_registry
            registry = get_prompt_registry()
            if not registry:
                return

            registry.register_prompt(
                slot_id="code_generator.generation",
                name="Code Generation Prompt",
                module="introspection.code_generator",
                function="_create_generation_prompt",
                category="code_generation",
                feedback_strength="strong",
                placeholders=[
                    "insight_title", "insight_type", "insight_priority",
                    "insight_description", "current_code", "proposed_change",
                    "benefits", "requirements_section",
                ],
                original_template=(
                    "You are an expert Python developer improving the Darwin System codebase.\n\n"
                    "## Task: Implement the following improvement\n\n"
                    "### Insight Details:\n"
                    "- **Title:** {insight_title}\n"
                    "- **Type:** {insight_type}\n"
                    "- **Priority:** {insight_priority}\n\n"
                    "### Problem:\n{insight_description}\n\n"
                    "### Current Code:\n```python\n{current_code}\n```\n\n"
                    "### Proposed Solution:\n{proposed_change}\n\n"
                    "### Expected Benefits:\n{benefits}\n\n"
                    "{requirements_section}\n\n"
                    "### Output Format:\n"
                    "Return ONLY the complete Python code in a code block. "
                    "No explanations, no TODO comments, no placeholders.\n"
                    "The code must be immediately usable and functional.\n\n"
                    "```python\n# Your complete implementation here\n```"
                ),
            )

            registry.register_prompt(
                slot_id="code_generator.correction",
                name="Code Correction Prompt",
                module="introspection.code_generator",
                function="correct_code_with_ai",
                category="code_generation",
                feedback_strength="strong",
                placeholders=["code", "errors_text", "warnings_text"],
                original_template=(
                    "You are an expert Python developer. The following code was generated "
                    "but has validation errors that need to be fixed.\n\n"
                    "## Original Code:\n```python\n{code}\n```\n\n"
                    "## Validation Errors (MUST FIX):\n{errors_text}\n\n"
                    "## Validation Warnings (should fix if possible):\n{warnings_text}\n\n"
                    "## Task:\nFix ALL the validation errors in the code. The most common issues are:\n"
                    "1. Syntax errors (unclosed parentheses, brackets, quotes)\n"
                    "2. Import errors\n"
                    "3. Indentation problems\n"
                    "4. Missing function definitions\n\n"
                    "## Requirements:\n"
                    "1. Return the COMPLETE corrected Python code\n"
                    "2. Preserve ALL functionality - do not remove features\n"
                    "3. Fix ALL syntax errors\n"
                    "4. Ensure all imports are valid\n"
                    "5. Ensure all parentheses, brackets, and quotes are properly closed\n"
                    "6. Double-check line endings and indentation\n\n"
                    "## Output Format:\n"
                    "Return ONLY the corrected Python code in a code block. No explanations needed.\n\n"
                    "```python\n# Your corrected code here\n```"
                ),
            )
        except Exception as e:
            print(f"⚠️ Could not register code generator prompts: {e}")

    def _check_duplicate_tool(self, insight: CodeInsight) -> Optional[str]:
        """
        Check if similar tool already exists to prevent duplicates

        Returns:
            Error message if duplicate found, None otherwise
        """
        # Check for duplicate architecture pattern tools
        title_lower = (insight.title or '').lower()
        code_location = insight.code_location or ''

        # DEBUG: Log what we're checking
        print(f"🔍 Duplicate check - Title: '{insight.title}', Location: '{code_location}'")

        # Check if this is an architecture pattern tool (check title AND location)
        is_arch_pattern = ('architecture_apply_pattern' in title_lower or
                          'architecture_apply_pattern' in code_location.lower() or
                          'apply pattern from' in title_lower)

        if is_arch_pattern:
            print(f"   ✓ Detected architecture pattern tool")

            # Try to get list of existing tools
            if self.tool_registry:
                try:
                    existing_tools = self.tool_registry.list_tools()
                    print(f"   📊 Found {len(existing_tools)} total tools in registry")

                    # Count architecture pattern tools
                    arch_pattern_tools = [
                        tool['name'] for tool in existing_tools
                        if 'architecture_apply_pattern' in tool['name'].lower()
                    ]

                    print(f"   📊 Found {len(arch_pattern_tools)} architecture pattern tools (threshold: 3)")

                    if len(arch_pattern_tools) >= 3:
                        print(f"🚫 DUPLICATE PREVENTED: Already have {len(arch_pattern_tools)} architecture pattern tools!")
                        print(f"   Existing: {', '.join(arch_pattern_tools[:5])}")
                        return f"Duplicate tool prevented: Already have {len(arch_pattern_tools)} architecture pattern tools. " \
                               f"These tools are rarely useful and clutter the system. " \
                               f"Focus on creating unique, practical tools instead."
                except Exception as e:
                    print(f"   ⚠️  Warning: Could not check tool registry: {e}")
                    import traceback
                    traceback.print_exc()

            # Also check filesystem
            try:
                tools_dir = Path("/app/tools")
                if tools_dir.exists():
                    existing_files = list(tools_dir.glob("architecture_apply_pattern*.py"))
                    if len(existing_files) >= 3:
                        print(f"⚠️  DUPLICATE PREVENTED: Already have {len(existing_files)} architecture pattern files")
                        return f"Duplicate tool: Already have {len(existing_files)} architecture pattern tools in filesystem."
            except Exception as e:
                print(f"   Warning: Could not check filesystem: {e}")

        # Check for other duplicate patterns (can expand this)
        # Future: Add more duplicate detection rules here

        return None

    async def generate_code_for_insight(self, insight: CodeInsight) -> Optional[GeneratedCode]:
        """
        Generate code to implement a specific insight

        Args:
            insight: CodeInsight from Self-Analysis

        Returns:
            GeneratedCode with original, new code, and diff
            None if generation should be skipped (e.g., duplicate)
        """
        print(f"🔧 Generating code for: {insight.title}")

        # 0. Check for duplicates BEFORE generating
        duplicate_error = self._check_duplicate_tool(insight)
        if duplicate_error:
            print(f"❌ Skipping generation: {duplicate_error}")
            # Return None to indicate skipping
            return None

        # 1. Read current code
        original_code = self._read_current_code(insight.code_location)

        # 2. Generate new code using AI (prefer multi_model_router)
        if self.multi_model_router or self.nucleus:
            new_code, explanation = await self._generate_with_ai(insight, original_code)
        else:
            # Fallback: template-based generation
            new_code, explanation = self._generate_with_template(insight, original_code)

        # 2.5 IMPORTANT: Clean markdown code fences (```python, ```)
        new_code = self._clean_markdown_fences(new_code)

        # 3. Create diffs
        diff_unified = self._create_unified_diff(original_code, new_code, insight.code_location)
        diff_html = self._create_html_diff(original_code, new_code)

        # 4. Assess risk
        risk_level = self._assess_risk(insight, original_code, new_code)

        # 5. Estimate implementation time
        estimated_time = self._estimate_time(insight, original_code, new_code)

        # 6. Generate tests (if needed)
        tests_code = None
        if self._needs_tests(insight):
            tests_code = await self._generate_tests(insight, new_code)

        # Determine file path
        file_path = self._determine_file_path(insight)

        # 🆕 NEW: Check if this is a new file
        is_new_file = not Path(file_path).exists()

        return GeneratedCode(
            insight_id=f"insight_{hash(insight.title)}",
            insight_title=insight.title,
            file_path=file_path,
            original_code=original_code,
            new_code=new_code,
            diff_html=diff_html,
            diff_unified=diff_unified,
            explanation=explanation,
            risk_level=risk_level,
            estimated_time_minutes=estimated_time,
            tests_code=tests_code,
            is_new_file=is_new_file  # 🆕 NEW
        )

    def _determine_file_path(self, insight: CodeInsight) -> str:
        """
        Determine the appropriate file path for generated code

        Args:
            insight: CodeInsight to generate code for

        Returns:
            File path where code should be saved (relative to project_root=/app)

        PROTECTION: Critical files are protected. Instead of modifying them,
        Darwin creates new tools/modules in the tools/ directory.
        """
        # If code_location is specified, check if it's protected
        if insight.code_location and insight.code_location != "unknown":
            # Clean up any incorrect paths
            path = insight.code_location
            # Remove leading 'backend/' if present (main.py is at root)
            if path.startswith('backend/'):
                path = path.replace('backend/', '', 1)

            # CHECK PROTECTION: Is this a critical file?
            if self._is_protected_file(path):
                print(f"   🛡️ PROTECTED: {path} is a critical file")
                print(f"   ✨ Creating new tool instead of modifying core infrastructure")
                # Log safety event
                try:
                    from consciousness.safety_logger import get_safety_logger
                    get_safety_logger().log('protected_file_redirect', 'code_generator', {
                        'file': path, 'insight': insight.title[:100],
                    }, severity='warning')
                except Exception:
                    pass
                # Redirect to create a new tool instead
                return self._create_tool_path_from_insight(insight)

            return path

        # For tool creation (new files), generate path in tools/ directory
        if insight.title.startswith("Create "):
            tool_name = insight.title.replace("Create ", "").strip()
            # Convert to snake_case filename
            filename = tool_name.lower().replace(" ", "_").replace("-", "_")
            # Remove non-alphanumeric characters except underscore
            filename = ''.join(c for c in filename if c.isalnum() or c == '_')
            return f"tools/{filename}.py"

        # For optimizations/features, check if target would be protected
        if hasattr(insight, 'component') and insight.component:
            component = insight.component
            target_path = None

            if component == 'backend':
                target_path = "main.py"
            elif component == 'docker':
                target_path = "Dockerfile"
            elif component == 'api':
                target_path = f"api/{insight.title.lower().replace(' ', '_')}_routes.py"
            elif component == 'core':
                target_path = f"core/{insight.title.lower().replace(' ', '_')}.py"
            elif component == 'consciousness':
                target_path = f"consciousness/{insight.title.lower().replace(' ', '_')}.py"
            elif component == 'learning':
                target_path = f"learning/{insight.title.lower().replace(' ', '_')}.py"

            # CHECK PROTECTION for inferred paths
            if target_path and self._is_protected_file(target_path):
                print(f"   🛡️ PROTECTED: {target_path} is a critical file")
                print(f"   ✨ Creating new tool instead of modifying core infrastructure")
                return self._create_tool_path_from_insight(insight)

            if target_path:
                return target_path

        # Default: Create new tool (safer than modifying main.py)
        print(f"   ✨ Creating new tool for: {insight.title}")
        return self._create_tool_path_from_insight(insight)

    def _is_protected_file(self, file_path: str) -> bool:
        """
        Check if a file path matches any protected file patterns

        Args:
            file_path: File path to check (relative to project root)

        Returns:
            True if file is protected, False otherwise
        """
        # Normalize path for comparison
        normalized = file_path.strip().replace('\\', '/')

        # Remove leading slash if present
        if normalized.startswith('/'):
            normalized = normalized[1:]

        # Check exact matches
        if normalized in self.PROTECTED_FILES:
            return True

        # Check if trying to modify any file in protected directories
        protected_dirs = ['ai/', 'core/', 'utils/']
        for protected_dir in protected_dirs:
            if normalized.startswith(protected_dir):
                # Allow new files in these directories, but protect existing core files
                base_name = normalized.split('/')[-1]
                if base_name in ['__init__.py', 'redis_client.py', 'semantic_memory.py',
                                'logger.py', 'multi_model_router.py']:
                    return True

        return False

    def _create_tool_path_from_insight(self, insight: CodeInsight) -> str:
        """
        Create a new tool file path based on insight details

        Args:
            insight: CodeInsight to create tool for

        Returns:
            Path to new tool file in tools/ directory
        """
        # Generate tool name from insight title
        tool_name = insight.title

        # Remove common prefixes
        for prefix in ["Create ", "Add ", "Implement ", "Improve ", "Optimize "]:
            if tool_name.startswith(prefix):
                tool_name = tool_name[len(prefix):]
                break

        # Convert to snake_case filename
        filename = tool_name.lower()
        filename = filename.replace(" ", "_").replace("-", "_")
        # Remove non-alphanumeric characters except underscore
        filename = ''.join(c for c in filename if c.isalnum() or c == '_')

        # Add component prefix if available
        if hasattr(insight, 'component') and insight.component:
            component = insight.component.lower()
            if component not in filename:
                filename = f"{component}_{filename}"

        return f"tools/{filename}.py"

    def _is_truncated(self, code: str) -> bool:
        """
        Detect if generated code was truncated mid-output.

        Checks for signs of incomplete code:
        - Unclosed parentheses, brackets, braces
        - Incomplete string literals
        - Code ending mid-statement (no newline at end)
        - Missing closing of class/function definitions

        Returns:
            True if code appears truncated
        """
        if not code or len(code) < 50:
            return False

        # Count bracket balance
        open_parens = code.count('(') - code.count(')')
        open_brackets = code.count('[') - code.count(']')
        open_braces = code.count('{') - code.count('}')

        if open_parens > 0 or open_brackets > 0 or open_braces > 0:
            print(f"   ⚠️ Truncation detected: unbalanced brackets (parens={open_parens}, brackets={open_brackets}, braces={open_braces})")
            return True

        # Check for unclosed triple-quoted strings
        triple_double = code.count('"""')
        triple_single = code.count("'''")
        if triple_double % 2 != 0 or triple_single % 2 != 0:
            print(f"   ⚠️ Truncation detected: unclosed triple-quoted string")
            return True

        # Check if code ends abruptly (no newline, ends mid-line with common incomplete patterns)
        last_line = code.rstrip().split('\n')[-1].strip()
        incomplete_endings = [',', '(', '[', '{', ':', '+', '-', '*', '/', '=', 'and', 'or', 'not', 'in', '\\']
        if last_line and any(last_line.endswith(e) for e in incomplete_endings):
            print(f"   ⚠️ Truncation detected: code ends with incomplete statement: '{last_line[-30:]}'")
            return True

        return False

    def _clean_markdown_fences(self, code: str) -> str:
        """
        Remove markdown code fences from generated code.

        AI models often wrap code in ```python or ``` blocks which break syntax.
        This method strips those fences to get clean Python code.

        Args:
            code: Generated code that might contain markdown fences

        Returns:
            Clean code without markdown fences
        """
        lines = code.split('\n')
        cleaned_lines = []

        for line in lines:
            stripped = line.strip()
            # Skip lines that are just markdown fences
            if stripped in ['```', '```python', '```py', '```javascript', '```js']:
                continue
            cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)

    def _read_current_code(self, code_location: Optional[str]) -> str:
        """Read current code from file"""
        if not code_location:
            return "# No specific file location provided"

        try:
            file_path = self.project_root / code_location
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                return f"# File not found: {code_location}"
        except Exception as e:
            return f"# Error reading file: {str(e)}"

    async def _generate_with_ai(self, insight: CodeInsight, current_code: str) -> tuple[str, str]:
        """Generate code using AI (MultiModelRouter)"""
        prompt = self._create_generation_prompt(insight, current_code)

        try:
            # Use multi_model_router if available
            if self.multi_model_router:
                # IMPORTANT: Code generation requires high quality - force COMPLEX routing
                # This ensures we use Claude Sonnet instead of Ollama for code generation
                result = await self.multi_model_router.generate(
                    task_description=f"[CRITICAL] Generate production Python code to implement: {insight.title}. Requires careful architecture and implementation.",
                    prompt=prompt,
                    max_tokens=8192,
                    context={
                        'code_length': 150,  # Signal large code generation to trigger COMPLEX
                        'task_type': 'code_generation',
                        'priority': insight.priority
                    }
                )

                # Extract code from result
                response = result.get('result', '') if isinstance(result, dict) else str(result)

                # Try to extract code block from markdown
                code = self._extract_code_from_response(response, current_code)

                # Check if code was truncated and retry with higher token limit
                if self._is_truncated(code):
                    print(f"   🔄 Code appears truncated, retrying with max_tokens=16384...")
                    result = await self.multi_model_router.generate(
                        task_description=f"[CRITICAL] Generate COMPLETE production Python code for: {insight.title}. Previous attempt was truncated. Output the FULL code.",
                        prompt=prompt,
                        max_tokens=16384,
                        context={
                            'code_length': 300,  # Force COMPLEX routing
                            'task_type': 'code_generation',
                            'priority': 'high'
                        }
                    )
                    response = result.get('result', '') if isinstance(result, dict) else str(result)
                    code = self._extract_code_from_response(response, current_code)

                    if self._is_truncated(code):
                        print(f"   ⚠️ Code still truncated after retry - proceeding with best effort")

                explanation = f"AI-generated implementation of: {insight.title}"

                return code, explanation

            # Fallback if no router
            print(f"⚠️ No multi_model_router available")
            return self._generate_with_template(insight, current_code)

        except Exception as e:
            print(f"❌ AI generation failed: {e}")
            # Fallback to template
            return self._generate_with_template(insight, current_code)

    def _extract_code_from_response(self, response: str, fallback: str) -> str:
        """Extract Python code from AI response (handles markdown code blocks)"""
        import re

        # Try to find Python code block
        code_block_pattern = r'```(?:python)?\s*\n(.*?)\n```'
        matches = re.findall(code_block_pattern, response, re.DOTALL)

        if matches:
            # Return the first code block found
            return matches[0].strip()

        # If no code block, check if the response looks like code
        lines = response.split('\n')
        code_lines = [l for l in lines if l.strip() and not l.strip().startswith('#')]

        if len(code_lines) > 0:
            # Response seems to contain code
            return response.strip()

        # No code found, return fallback
        return fallback

    async def correct_code_with_ai(
        self,
        code: str,
        validation_errors: List[str],
        validation_warnings: List[str],
        insight_title: str,
        max_retries: int = 2
    ) -> tuple[str, bool]:
        """
        Ask Claude to review and correct code that failed validation.

        Args:
            code: The generated code that has errors
            validation_errors: List of validation errors
            validation_warnings: List of validation warnings
            insight_title: Title of the insight being implemented
            max_retries: Maximum correction attempts

        Returns:
            Tuple of (corrected_code, success_bool)
        """
        if not self.multi_model_router:
            print("   ⚠️ No AI router available for code correction")
            return code, False

        print(f"   🔧 Asking Claude to fix {len(validation_errors)} errors and {len(validation_warnings)} warnings...")

        # Format errors for the prompt
        errors_text = "\n".join([f"  - {e}" for e in validation_errors]) if validation_errors else "None"
        warnings_text = "\n".join([f"  - {w}" for w in validation_warnings]) if validation_warnings else "None"

        # Try evolvable prompt from registry
        correction_prompt = None
        try:
            from consciousness.prompt_registry import get_prompt_registry
            registry = get_prompt_registry()
            if registry:
                correction_prompt = registry.get_prompt(
                    "code_generator.correction",
                    code=code,
                    errors_text=errors_text,
                    warnings_text=warnings_text,
                )
        except Exception as e:
            print(f"⚠️ Prompt registry fallback for correction: {e}")

        if not correction_prompt:
            correction_prompt = f"""You are an expert Python developer. The following code was generated but has validation errors that need to be fixed.

## Original Code:
```python
{code}
```

## Validation Errors (MUST FIX):
{errors_text}

## Validation Warnings (should fix if possible):
{warnings_text}

## Task:
Fix ALL the validation errors in the code. The most common issues are:
1. Syntax errors (unclosed parentheses, brackets, quotes)
2. Import errors
3. Indentation problems
4. Missing function definitions

## Requirements:
1. Return the COMPLETE corrected Python code
2. Preserve ALL functionality - do not remove features
3. Fix ALL syntax errors
4. Ensure all imports are valid
5. Ensure all parentheses, brackets, and quotes are properly closed
6. Double-check line endings and indentation

## Output Format:
Return ONLY the corrected Python code in a code block. No explanations needed.

```python
# Your corrected code here
```
"""

        try:
            result = await self.multi_model_router.generate(
                task_description=f"[CRITICAL] Fix validation errors in Python code for: {insight_title}",
                prompt=correction_prompt,
                max_tokens=8192,  # Must be large enough for complete corrected code
                context={
                    'code_length': 200,  # Force COMPLEX routing
                    'task_type': 'code_correction',
                    'priority': 'high'
                }
            )

            response = result.get('result', '') if isinstance(result, dict) else str(result)
            corrected_code = self._extract_code_from_response(response, code)

            # Basic validation: check if corrected code is substantially different and not empty
            if corrected_code and len(corrected_code) > 100 and corrected_code != code:
                print(f"   ✅ Claude provided corrected code ({len(corrected_code)} chars)")
                return corrected_code, True
            else:
                print(f"   ⚠️ Claude's correction was empty or unchanged")
                return code, False

        except Exception as e:
            print(f"   ❌ Code correction failed: {e}")
            return code, False

    async def generate_and_validate_with_retry(
        self,
        insight: CodeInsight,
        max_correction_attempts: int = 2
    ) -> Optional['GeneratedCode']:
        """
        Generate code for an insight with automatic validation and correction.

        This method:
        1. Generates code using AI
        2. Validates the code
        3. If validation fails, asks Claude to fix it
        4. Repeats up to max_correction_attempts times

        Args:
            insight: The CodeInsight to implement
            max_correction_attempts: Max times to try correcting the code

        Returns:
            GeneratedCode object with final (hopefully valid) code
        """
        from introspection.code_validator import CodeValidator

        print(f"🔧 Generating code for: {insight.title}")

        # Check for duplicates first
        duplicate_error = self._check_duplicate_tool(insight)
        if duplicate_error:
            print(f"❌ Skipping: {duplicate_error}")
            return None

        # Read original code
        original_code = self._read_current_code(insight.code_location)

        # Generate initial code
        if self.multi_model_router or self.nucleus:
            new_code, explanation = await self._generate_with_ai(insight, original_code)
        else:
            new_code, explanation = self._generate_with_template(insight, original_code)

        new_code = self._clean_markdown_fences(new_code)

        # Validate and correct loop
        validator = CodeValidator()
        attempt = 0

        while attempt <= max_correction_attempts:
            # Create temporary GeneratedCode for validation
            temp_generated = GeneratedCode(
                insight_id=f"insight_{hash(insight.title)}",
                insight_title=insight.title,
                file_path=self._determine_file_path(insight),
                original_code=original_code,
                new_code=new_code,
                diff_html="",
                diff_unified="",
                explanation=explanation,
                risk_level=self._assess_risk(insight, original_code, new_code),
                estimated_time_minutes=self._estimate_time(insight, original_code, new_code),
                is_new_file=not Path(self._determine_file_path(insight)).exists()
            )

            # Validate
            validation = await validator.validate(temp_generated)

            print(f"   📊 Validation attempt {attempt + 1}: Score {validation.score}/100, Valid: {validation.valid}")

            if validation.valid and validation.score >= 70:
                # Good enough! Create final result
                print(f"   ✅ Code passed validation!")
                break
            elif attempt < max_correction_attempts:
                # Try to correct
                print(f"   🔄 Attempting correction (attempt {attempt + 1}/{max_correction_attempts})...")

                all_issues = validation.errors + validation.warnings
                corrected_code, success = await self.correct_code_with_ai(
                    code=new_code,
                    validation_errors=validation.errors,
                    validation_warnings=validation.warnings[:3],  # Limit warnings to top 3
                    insight_title=insight.title
                )

                if success:
                    new_code = self._clean_markdown_fences(corrected_code)
                    explanation = f"AI-generated (corrected after {attempt + 1} attempts): {insight.title}"
                else:
                    print(f"   ⚠️ Correction attempt {attempt + 1} failed, trying again...")
            else:
                print(f"   ⚠️ Max correction attempts reached. Submitting with current quality.")

            attempt += 1

        # Record outcome for prompt evolution
        # Score: 1.0 = passed first try, 0.7 = 1 correction, 0.4 = 2 corrections, 0.0 = failed
        passed = validation.valid and validation.score >= 70
        try:
            from consciousness.prompt_registry import get_prompt_registry
            registry = get_prompt_registry()
            if registry:
                if passed:
                    gen_score = max(0.0, 1.0 - (attempt * 0.3))
                else:
                    gen_score = 0.0
                registry.record_outcome("code_generator.generation", gen_score, passed)
                # Record correction outcome if corrections were attempted
                if attempt > 0:
                    registry.record_outcome(
                        "code_generator.correction",
                        1.0 if passed else 0.0,
                        passed,
                    )
        except Exception as e:
            logger.debug(f"Prompt evolution record_outcome: {e}")

        # Log safety event for validation outcome
        try:
            from consciousness.safety_logger import get_safety_logger
            sl = get_safety_logger()
            if not passed:
                sl.log('code_validation_fail', 'code_generator', {
                    'insight': insight.title[:100],
                    'score': validation.score,
                    'attempts': attempt + 1,
                    'errors': validation.errors[:3],
                }, severity='warning')
            elif attempt > 0:
                sl.log('code_validation_corrected', 'code_generator', {
                    'insight': insight.title[:100],
                    'score': validation.score,
                    'attempts': attempt + 1,
                })
        except Exception:
            pass

        # Create final diffs
        file_path = self._determine_file_path(insight)
        diff_unified = self._create_unified_diff(original_code, new_code, file_path)
        diff_html = self._create_html_diff(original_code, new_code)

        # Generate tests if needed
        tests_code = None
        if self._needs_tests(insight):
            tests_code = await self._generate_tests(insight, new_code)

        return GeneratedCode(
            insight_id=f"insight_{hash(insight.title)}",
            insight_title=insight.title,
            file_path=file_path,
            original_code=original_code,
            new_code=new_code,
            diff_html=diff_html,
            diff_unified=diff_unified,
            explanation=explanation,
            risk_level=self._assess_risk(insight, original_code, new_code),
            estimated_time_minutes=self._estimate_time(insight, original_code, new_code),
            tests_code=tests_code,
            is_new_file=not Path(file_path).exists()
        )

    def _generate_with_template(self, insight: CodeInsight, current_code: str) -> tuple[str, str]:
        """
        Fallback: Generate code using templates
        Used when AI is not available
        """
        explanation = f"Template-based implementation of: {insight.title}"

        # Different templates based on insight type
        if "connection pooling" in insight.title.lower():
            new_code = self._template_connection_pooling(current_code)

        elif "type hints" in insight.title.lower():
            new_code = self._template_add_type_hints(current_code)

        elif "logging" in insight.title.lower():
            new_code = self._template_add_logging(current_code)

        elif "error handling" in insight.title.lower():
            new_code = self._template_add_error_handling(current_code)

        else:
            # Generic template: add TODO comment
            new_code = f"# TODO: Implement {insight.title}\n# {insight.description}\n\n{current_code}"

        return new_code, explanation

    def _create_generation_prompt(self, insight: CodeInsight, current_code: str) -> str:
        """Create AI prompt for code generation with learned quality requirements"""

        # Get learned quality requirements from past rejected code
        quality_requirements = ""
        try:
            from introspection.quality_analyzer import QualityAnalyzer
            analyzer = QualityAnalyzer()
            quality_requirements = analyzer.get_improvement_prompt()
        except Exception as e:
            print(f"⚠️ Could not load quality requirements: {e}")

        base_requirements = """### Requirements - IMPORTANT:
1. Generate COMPLETE, FUNCTIONAL, PRODUCTION-READY Python code
2. DO NOT use TODO comments or placeholders - implement everything fully
3. Include proper error handling with try/except blocks
4. Add comprehensive docstrings and inline comments
5. Use type hints for all functions and variables
6. Follow PEP 8 style guidelines
7. Ensure backward compatibility
8. Make code robust and maintainable
9. If creating new functions, implement them completely
10. If modifying existing code, provide the full improved version
11. **CRITICAL**: All functions must accept optional parameters for tool registry compatibility:
    - Add `top_k: int = None` parameter to all function signatures
    - Add `**kwargs` at the end of all function signatures
    - Document these as "for compatibility with tool registry"
    - Example: `def my_function(arg1: str, top_k: int = None, **kwargs) -> str:`"""

        # Add learned requirements if available
        if quality_requirements:
            requirements_section = base_requirements + "\n\n" + quality_requirements
        else:
            requirements_section = base_requirements

        benefits = ', '.join(insight.benefits) if insight.benefits else 'Improve code quality and functionality'

        # Try evolvable prompt from registry
        try:
            from consciousness.prompt_registry import get_prompt_registry
            registry = get_prompt_registry()
            if registry:
                return registry.get_prompt(
                    "code_generator.generation",
                    insight_title=insight.title,
                    insight_type=insight.type,
                    insight_priority=insight.priority,
                    insight_description=insight.description,
                    current_code=current_code,
                    proposed_change=insight.proposed_change,
                    benefits=benefits,
                    requirements_section=requirements_section,
                )
        except Exception as e:
            print(f"⚠️ Prompt registry fallback for generation: {e}")

        # Fallback: original hardcoded prompt
        return f"""You are an expert Python developer improving the Darwin System codebase.

## Task: Implement the following improvement

### Insight Details:
- **Title:** {insight.title}
- **Type:** {insight.type}
- **Priority:** {insight.priority}

### Problem:
{insight.description}

### Current Code:
```python
{current_code}
```

### Proposed Solution:
{insight.proposed_change}

### Expected Benefits:
{benefits}

{requirements_section}

### Output Format:
Return ONLY the complete Python code in a code block. No explanations, no TODO comments, no placeholders.
The code must be immediately usable and functional.

```python
# Your complete implementation here
```
"""

    def _create_unified_diff(self, original: str, new: str, filename: str) -> str:
        """Create unified diff format"""
        original_lines = original.splitlines(keepends=True)
        new_lines = new.splitlines(keepends=True)

        diff = difflib.unified_diff(
            original_lines,
            new_lines,
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
            lineterm=''
        )

        return ''.join(diff)

    def _create_html_diff(self, original: str, new: str) -> str:
        """Create HTML diff for frontend display"""
        original_lines = original.splitlines()
        new_lines = new.splitlines()

        differ = difflib.HtmlDiff()
        html_diff = differ.make_table(
            original_lines,
            new_lines,
            fromdesc="Original",
            todesc="Proposed",
            context=True,
            numlines=3
        )

        return html_diff

    def _assess_risk(self, insight: CodeInsight, original: str, new: str) -> str:
        """
        Assess risk level of the change

        Returns: 'low', 'medium', or 'high'

        Adjusted to be less conservative for Darwin's self-improvement:
        - backend/core changes get +1 instead of +2 (Darwin modifies itself)
        - Medium threshold increased from 6 to 8
        - High threshold starts at 10+ instead of 7+
        """
        risk_score = 0

        # Factor 1: Priority (high priority = potentially risky)
        if insight.priority == 'high':
            risk_score += 2
        elif insight.priority == 'medium':
            risk_score += 1

        # Factor 2: Code change size
        original_lines = len(original.splitlines())
        new_lines = len(new.splitlines())
        lines_changed = abs(new_lines - original_lines)

        if lines_changed > 100:
            risk_score += 3
        elif lines_changed > 50:
            risk_score += 2
        elif lines_changed > 20:
            risk_score += 1

        # Factor 3: Component affected (REDUCED PENALTY)
        if insight.component in ['backend', 'core']:
            risk_score += 1  # Reduced from +2 (Darwin self-improves backend)
        elif insight.component == 'docker':
            risk_score += 1

        # Factor 4: Type of change
        if insight.type in ['refactor', 'optimization']:
            risk_score += 1  # Reduced from +2 (common for AI)
        elif insight.type == 'feature':
            risk_score += 1

        # Factor 5: Breaking changes indicators
        if self._has_breaking_changes(original, new):
            risk_score += 3

        # Classify risk (ADJUSTED THRESHOLDS)
        if risk_score <= 4:
            return 'low'
        elif risk_score <= 8:
            return 'medium'
        else:
            return 'high'

    def _has_breaking_changes(self, original: str, new: str) -> bool:
        """Check for potential breaking changes"""
        breaking_indicators = [
            'def __init__',  # Constructor changes
            'class ',  # Class definition changes
            'import ',  # Import changes
            'raise ',  # New exceptions
        ]

        for indicator in breaking_indicators:
            original_count = original.count(indicator)
            new_count = new.count(indicator)
            if original_count != new_count:
                return True

        return False

    def _estimate_time(self, insight: CodeInsight, original: str, new: str) -> int:
        """
        Estimate implementation time in minutes

        Returns: estimated minutes
        """
        base_time = 5  # Base 5 minutes

        # Add time based on complexity
        lines_changed = abs(len(new.splitlines()) - len(original.splitlines()))
        base_time += lines_changed // 10  # 1 minute per 10 lines

        # Add time based on priority
        if insight.priority == 'high':
            base_time += 10
        elif insight.priority == 'medium':
            base_time += 5

        # Add time for testing
        if self._needs_tests(insight):
            base_time += 15

        return min(base_time, 60)  # Cap at 60 minutes

    def _needs_tests(self, insight: CodeInsight) -> bool:
        """Determine if change needs tests"""
        return insight.type in ['feature', 'optimization', 'refactor']

    async def _generate_tests(self, insight: CodeInsight, new_code: str) -> Optional[str]:
        """Generate test code for the change"""
        if not self.multi_model_router:
            return None

        prompt = f"""Generate pytest tests for this code change.

## Change Description:
{insight.description}

## New Code:
```python
{new_code}
```

Generate comprehensive pytest tests that validate:
1. Basic functionality works
2. Edge cases are handled
3. Error conditions are tested

Return ONLY the test code, no explanations.
"""

        try:
            result = await self.multi_model_router.generate(
                task_description=f"Generate tests for: {insight.title}",
                prompt=prompt,
                max_tokens=4096
            )
            # Extract code from result
            response = result.get('result', '') if isinstance(result, dict) else str(result)
            return self._extract_code_from_response(response, None)
        except Exception as e:
            print(f"❌ Test generation failed: {e}")
            return None

    # Template implementations for common changes

    def _template_connection_pooling(self, current_code: str) -> str:
        """Template for adding connection pooling"""
        if 'sqlite3.connect' in current_code:
            new_code = current_code.replace(
                'import sqlite3',
                'from sqlalchemy import create_engine\nfrom sqlalchemy.orm import sessionmaker\nfrom sqlalchemy.pool import QueuePool'
            )
            new_code = new_code.replace(
                'sqlite3.connect(',
                '# Connection pooling added\ncreate_engine(\n            "sqlite:///'
            )
            return new_code
        return current_code

    def _template_add_type_hints(self, current_code: str) -> str:
        """Template for adding type hints"""
        lines = current_code.splitlines()
        new_lines = []

        for line in lines:
            if line.strip().startswith('def ') and '->' not in line:
                # Add return type hint
                if ':' in line and '(' in line:
                    line = line.rstrip() + ' -> Any:'
            new_lines.append(line)

        new_code = '\n'.join(new_lines)

        # Add typing imports if not present
        if 'from typing import' not in new_code:
            new_code = 'from typing import Any, Dict, List, Optional\n\n' + new_code

        return new_code

    def _template_add_logging(self, current_code: str) -> str:
        """Template for adding logging"""
        if 'from utils.logger import' not in current_code:
            new_code = 'from utils.logger import setup_logger\n\n' + current_code

            # Add logger initialization
            if 'class ' in new_code:
                new_code = new_code.replace(
                    'class ',
                    'logger = setup_logger(__name__)\n\nclass ',
                    1
                )
            return new_code
        return current_code

    def _template_add_error_handling(self, current_code: str) -> str:
        """Template for adding error handling"""
        # Wrap main logic in try-except
        lines = current_code.splitlines()
        new_lines = []
        in_function = False
        indent = ''

        for i, line in enumerate(lines):
            if line.strip().startswith('def '):
                in_function = True
                indent = ' ' * (len(line) - len(line.lstrip()) + 4)
                new_lines.append(line)
                continue

            if in_function and line.strip() and not line.strip().startswith('#'):
                new_lines.append(f"{indent}try:")
                new_lines.append(f"{indent}    {line.strip()}")
                # Add remaining lines
                for j in range(i + 1, len(lines)):
                    if lines[j].strip():
                        new_lines.append(f"{indent}    {lines[j].strip()}")
                new_lines.append(f"{indent}except Exception as e:")
                new_lines.append(f"{indent}    logger.error(f'Error: {{e}}')")
                new_lines.append(f"{indent}    raise")
                break

            new_lines.append(line)

        return '\n'.join(new_lines)

    def to_dict(self, generated: GeneratedCode) -> Dict[str, Any]:
        """Convert GeneratedCode to dictionary"""
        return asdict(generated)
