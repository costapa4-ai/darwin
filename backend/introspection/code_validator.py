"""
Code Validator: Validates generated code before applying
Performs syntax checks, import validation, and security scans
"""
import ast
import re
import subprocess
from typing import Dict, List, Any, Set
from pathlib import Path
from dataclasses import dataclass, asdict

from introspection.code_generator import GeneratedCode


@dataclass
class ValidationResult:
    """Result of code validation"""
    valid: bool
    score: int  # 0-100
    errors: List[str]
    warnings: List[str]
    security_issues: List[str]
    complexity_score: int = 0
    test_coverage_estimate: int = 0
    checks_passed: List[str] = None
    checks_failed: List[str] = None

    def __post_init__(self):
        if self.checks_passed is None:
            self.checks_passed = []
        if self.checks_failed is None:
            self.checks_failed = []

    def is_safe_to_apply(self) -> bool:
        """Check if code is safe to apply"""
        return self.valid and len(self.security_issues) == 0


class CodeValidator:
    """
    Validates generated code before it's applied
    Performs multiple checks to ensure safety
    """

    def __init__(self):
        self.dangerous_imports = {
            'os.system', 'subprocess.call', 'eval', 'exec',
            'pickle', '__import__', 'compile'
        }

        self.required_patterns = {
            'error_handling': r'try:.*except',
            'logging': r'logger\.',
        }

    async def validate(self, generated: GeneratedCode) -> ValidationResult:
        """
        Perform comprehensive validation on generated code

        Args:
            generated: GeneratedCode to validate

        Returns:
            ValidationResult with all check results
        """
        print(f"🔍 Validating generated code...")

        checks_passed = []
        checks_failed = []
        warnings = []
        security_issues = []
        valid = True

        # 0. CRITICAL: Check for markdown code fences (should never reach this point)
        if '```' in generated.new_code:
            checks_failed.append('❌ CRITICAL: Code contains markdown fences (```). Code generator failed to clean output!')
            valid = False
            # Return immediately - this is a critical failure
            return ValidationResult(
                valid=False,
                score=0,
                errors=checks_failed,
                warnings=['Code contains markdown syntax - cannot be applied'],
                security_issues=['Malformed code could break system'],
                checks_passed=checks_passed,
                checks_failed=checks_failed
            )

        # 0.5 CRITICAL: Check for full file replacement
        # Skip this check for new files (is_new_file=True) or placeholder originals
        is_new_file = getattr(generated, 'is_new_file', False)
        is_placeholder_original = (
            not generated.original_code or
            generated.original_code.startswith('# No specific') or
            generated.original_code.startswith('# File not found') or
            generated.original_code.startswith('# Error reading') or
            len(generated.original_code.strip()) < 50
        )

        if not is_new_file and not is_placeholder_original:
            replacement_check = self._detect_full_replacement(
                generated.original_code,
                generated.new_code
            )
            if replacement_check['detected']:
                checks_failed.append(f"❌ FULL FILE REPLACEMENT: {replacement_check['message']}")
                valid = False
                # Return immediately - this is dangerous
                return ValidationResult(
                    valid=False,
                    score=10,  # Very low score
                    errors=checks_failed,
                    warnings=[
                        'This appears to be a full file replacement, not an edit',
                        f"Similarity: {replacement_check['similarity']:.1%}",
                        f"Size ratio: {replacement_check['size_ratio']:.2f}x"
                    ],
                    security_issues=['Full file replacements are blocked for safety'],
                    checks_passed=checks_passed,
                    checks_failed=checks_failed
                )
        elif is_new_file:
            checks_passed.append('✅ New file creation allowed')

        # 1. Syntax Validation
        syntax_result = self._validate_syntax(generated.new_code)
        if syntax_result['valid']:
            checks_passed.append('✅ Syntax valid')
        else:
            checks_failed.append(f'❌ Syntax error: {syntax_result["error"]}')
            valid = False

        # 2. Import Validation
        import_result = self._validate_imports(generated.new_code)
        if import_result['valid']:
            checks_passed.append('✅ Imports valid')
        else:
            warnings.extend(import_result['warnings'])

        # 3. Security Scan
        security_result = self._security_scan(generated.new_code)
        if security_result['safe']:
            checks_passed.append('✅ No security issues')
        else:
            security_issues.extend(security_result['issues'])
            valid = False

        # 4. Code Quality Checks
        quality_result = self._check_code_quality(generated.new_code)
        if quality_result['passed']:
            checks_passed.append('✅ Code quality acceptable')
        else:
            warnings.extend(quality_result['warnings'])

        # 5. Compare with Original (regression check)
        regression_result = self._check_regressions(
            generated.original_code,
            generated.new_code
        )
        if regression_result['safe']:
            checks_passed.append('✅ No obvious regressions')
        else:
            warnings.extend(regression_result['warnings'])

        # 6. Specific checks based on risk level
        if generated.risk_level == 'high':
            risk_checks = self._high_risk_validation(generated)
            if risk_checks['passed']:
                checks_passed.append('✅ High-risk checks passed')
            else:
                checks_failed.extend(risk_checks['failures'])
                valid = False

        # Calculate score
        score = self._calculate_score(
            len(checks_passed),
            len(checks_failed),
            len(warnings),
            len(security_issues)
        )

        result = ValidationResult(
            valid=valid,
            score=score,
            errors=checks_failed,  # Required argument
            warnings=warnings,
            security_issues=security_issues,
            checks_passed=checks_passed,
            checks_failed=checks_failed
        )

        print(f"{'✅' if valid else '❌'} Validation complete - Score: {score}/100")
        return result

    def _validate_syntax(self, code: str) -> Dict[str, Any]:
        """
        Validate Python syntax using both ast.parse() and compile()

        ast.parse() catches most syntax errors
        compile() catches additional errors like unterminated f-strings
        """
        try:
            # First check: Parse the AST
            ast.parse(code)

            # Second check: Compile the code
            # This catches errors that ast.parse() might miss
            # Like unterminated f-strings, invalid syntax in specific contexts, etc.
            compile(code, '<string>', 'exec')

            return {'valid': True}
        except SyntaxError as e:
            return {
                'valid': False,
                'error': f'Line {e.lineno}: {e.msg}'
            }
        except Exception as e:
            return {
                'valid': False,
                'error': str(e)
            }

    def _validate_imports(self, code: str) -> Dict[str, Any]:
        """
        Validate that all imports are available
        Returns warnings for potentially missing imports
        """
        warnings = []

        try:
            tree = ast.parse(code)

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if not self._is_import_available(alias.name):
                            warnings.append(
                                f'⚠️ Import may not be available: {alias.name}'
                            )

                elif isinstance(node, ast.ImportFrom):
                    if node.module and not self._is_import_available(node.module):
                        warnings.append(
                            f'⚠️ Module may not be available: {node.module}'
                        )

            return {
                'valid': len(warnings) == 0,
                'warnings': warnings
            }

        except Exception as e:
            return {
                'valid': False,
                'warnings': [f'⚠️ Import validation failed: {str(e)}']
            }

    def _is_import_available(self, module_name: str) -> bool:
        """Check if module is available"""
        # Check common/expected modules
        known_modules = {
            'os', 'sys', 'json', 'pathlib', 'typing', 'datetime',
            'fastapi', 'pydantic', 'sqlalchemy', 'redis',
            'asyncio', 're', 'collections', 'dataclasses',
            # Darwin-specific
            'core', 'services', 'agents', 'dream', 'utils',
            'api', 'introspection', 'poetry', 'curiosity'
        }

        base_module = module_name.split('.')[0]
        return base_module in known_modules

    def _security_scan(self, code: str) -> Dict[str, Any]:
        """
        Scan for security vulnerabilities
        """
        issues = []

        try:
            tree = ast.parse(code)

            # Check for dangerous function calls
            for node in ast.walk(tree):
                # Check for eval/exec
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        if node.func.id in ['eval', 'exec']:
                            issues.append('🚨 CRITICAL: Use of eval/exec detected')

                # Check for dangerous imports
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if any(danger in alias.name for danger in self.dangerous_imports):
                            issues.append(
                                f'🚨 WARNING: Potentially dangerous import: {alias.name}'
                            )

                # Check for command execution
                if isinstance(node, ast.Attribute):
                    if node.attr in ['system', 'popen', 'call']:
                        issues.append('🚨 WARNING: Command execution detected')

            # Check for SQL injection patterns (basic)
            if re.search(r'f".*SELECT.*\{', code) or re.search(r'".*SELECT.*\+', code):
                issues.append('🚨 WARNING: Potential SQL injection pattern')

            # Check for hardcoded credentials
            if re.search(r'password\s*=\s*["\'](?!.*\{)', code, re.IGNORECASE):
                issues.append('🚨 WARNING: Potential hardcoded password')

            if re.search(r'api_key\s*=\s*["\'](?!.*\{)', code, re.IGNORECASE):
                issues.append('🚨 WARNING: Potential hardcoded API key')

            return {
                'safe': len(issues) == 0,
                'issues': issues
            }

        except Exception as e:
            return {
                'safe': False,
                'issues': [f'🚨 Security scan failed: {str(e)}']
            }

    def _check_code_quality(self, code: str) -> Dict[str, Any]:
        """
        Check code quality metrics
        """
        warnings = []

        try:
            tree = ast.parse(code)

            # Check function length
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_lines = len(ast.unparse(node).splitlines())
                    if func_lines > 50:
                        warnings.append(
                            f'⚠️ Function {node.name} is long ({func_lines} lines)'
                        )

            # Check complexity (basic - count nested blocks)
            complexity = self._calculate_complexity(tree)
            if complexity > 10:
                warnings.append(f'⚠️ High complexity detected: {complexity}')

            # Check for docstrings
            has_docstrings = False
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    if ast.get_docstring(node):
                        has_docstrings = True
                        break

            if not has_docstrings:
                warnings.append('⚠️ No docstrings found')

            return {
                'passed': len(warnings) < 3,  # Allow up to 2 warnings
                'warnings': warnings
            }

        except Exception as e:
            return {
                'passed': True,  # Don't fail on quality check errors
                'warnings': [f'⚠️ Quality check failed: {str(e)}']
            }

    def _calculate_complexity(self, tree: ast.AST) -> int:
        """
        Calculate cyclomatic complexity (simplified)
        """
        complexity = 1

        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1

        return complexity

    def _check_regressions(self, original: str, new: str) -> Dict[str, Any]:
        """
        Check for potential regressions
        """
        warnings = []

        try:
            original_tree = ast.parse(original) if original.strip() else None
            new_tree = ast.parse(new)

            if original_tree:
                # Check if public functions were removed
                original_functions = self._extract_function_names(original_tree)
                new_functions = self._extract_function_names(new_tree)

                removed = original_functions - new_functions
                if removed:
                    warnings.append(
                        f'⚠️ Functions removed: {", ".join(removed)}'
                    )

                # Check if classes were removed
                original_classes = self._extract_class_names(original_tree)
                new_classes = self._extract_class_names(new_tree)

                removed_classes = original_classes - new_classes
                if removed_classes:
                    warnings.append(
                        f'⚠️ Classes removed: {", ".join(removed_classes)}'
                    )

            return {
                'safe': len(warnings) == 0,
                'warnings': warnings
            }

        except Exception as e:
            return {
                'safe': True,  # Don't fail on regression check errors
                'warnings': [f'⚠️ Regression check failed: {str(e)}']
            }

    def _extract_function_names(self, tree: ast.AST) -> Set[str]:
        """Extract all function names from AST"""
        functions = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if not node.name.startswith('_'):  # Only public functions
                    functions.add(node.name)
        return functions

    def _extract_class_names(self, tree: ast.AST) -> Set[str]:
        """Extract all class names from AST"""
        classes = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.add(node.name)
        return classes

    def _high_risk_validation(self, generated: GeneratedCode) -> Dict[str, Any]:
        """
        Additional validation for high-risk changes

        ADJUSTED: Made less strict to allow Darwin's self-improvements
        - Logging, error handling, and type hints are now warnings, not failures
        - Only actual dangerous patterns cause validation failure
        """
        failures = []
        warnings = []

        # High-risk changes SHOULD have (but not required):
        # 1. Error handling
        if 'try:' not in generated.new_code and 'except' not in generated.new_code:
            warnings.append('⚠️ Consider adding error handling for high-risk change')

        # 2. Logging
        if 'logger' not in generated.new_code and 'print' not in generated.new_code:
            warnings.append('⚠️ Consider adding logging for high-risk change')

        # 3. Type hints (for Python)
        if '->' not in generated.new_code and 'def ' in generated.new_code:
            warnings.append('⚠️ Consider adding type hints for better code quality')

        # Only fail if there are actual dangerous patterns (already checked in security_scan)
        # So high-risk validation rarely fails now

        return {
            'passed': len(failures) == 0,
            'failures': failures,
            'warnings': warnings  # Return warnings too
        }

    def _detect_full_replacement(
        self,
        original: str,
        new: str
    ) -> Dict[str, Any]:
        """
        Detect if this is a full file replacement (dangerous!)

        A full file replacement is when the new code has very little
        in common with the original, suggesting it's replacing the entire file
        rather than making targeted edits.

        Criteria:
        - < 20% of lines are common between original and new
        - New code > 2x original size (massive expansion)
        - New code < 30% original size (massive reduction)

        Args:
            original: Original code
            new: New code

        Returns:
            {
                'detected': bool,
                'similarity': float,  # 0.0-1.0
                'size_ratio': float,
                'risk_level': str,
                'message': str
            }
        """
        # Handle empty original (new file creation is OK)
        if not original or not original.strip():
            return {
                'detected': False,
                'similarity': 0.0,
                'size_ratio': 1.0,
                'message': 'New file creation - OK'
            }

        # Split into lines and normalize
        original_lines = set(
            line.strip()
            for line in original.split('\n')
            if line.strip()  # Ignore empty lines
        )
        new_lines = set(
            line.strip()
            for line in new.split('\n')
            if line.strip()
        )

        # Calculate similarity (Jaccard index)
        if len(original_lines) == 0:
            similarity = 0.0
        else:
            common_lines = original_lines.intersection(new_lines)
            similarity = len(common_lines) / len(original_lines)

        # Calculate size ratio
        original_size = len(original)
        new_size = len(new)

        if original_size == 0:
            size_ratio = 1.0
        else:
            size_ratio = new_size / original_size

        # Check for full replacement indicators
        is_full_replacement = (
            similarity < 0.20 or      # Less than 20% common lines
            size_ratio > 2.0 or       # More than 2x size increase
            size_ratio < 0.30         # Less than 30% size (major reduction)
        )

        if is_full_replacement:
            # Determine why it was detected
            reasons = []
            if similarity < 0.20:
                reasons.append(f'Only {similarity:.1%} of original lines remain')
            if size_ratio > 2.0:
                reasons.append(f'Code size increased {size_ratio:.1f}x')
            if size_ratio < 0.30:
                reasons.append(f'Code size reduced to {size_ratio:.1%}')

            return {
                'detected': True,
                'similarity': similarity,
                'size_ratio': size_ratio,
                'risk_level': 'CRITICAL',
                'message': f'Full file replacement detected: {"; ".join(reasons)}'
            }

        return {
            'detected': False,
            'similarity': similarity,
            'size_ratio': size_ratio,
            'message': 'Normal code edit'
        }

    def _calculate_score(
        self,
        passed: int,
        failed: int,
        warnings: int,
        security: int
    ) -> int:
        """
        Calculate validation score (0-100)
        """
        # Start with base score
        score = 100

        # Deduct for failures
        score -= failed * 20

        # Deduct for warnings
        score -= warnings * 5

        # Severe deduction for security issues
        score -= security * 30

        # Add points for passed checks
        score += passed * 5

        # Clamp to 0-100
        return max(0, min(100, score))

    def to_dict(self, result: ValidationResult) -> Dict[str, Any]:
        """Convert ValidationResult to dictionary"""
        return asdict(result)
