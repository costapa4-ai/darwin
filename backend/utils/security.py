"""Security utilities for safe code execution"""
import ast
from typing import Set


class CodeValidator:
    """Validates Python code for security concerns"""

    DANGEROUS_IMPORTS = {
        'subprocess', 'os.system', 'eval', 'exec', 'compile',
        'socket', 'urllib', 'requests', 'http', '__import__'
    }

    DANGEROUS_CALLS = {
        'eval', 'exec', 'compile', '__import__', 'open',
        'input', 'raw_input'
    }

    def __init__(self, allowed_modules: Set[str]):
        self.allowed_modules = allowed_modules

    def validate(self, code: str) -> tuple[bool, str]:
        """
        Validate code for security issues

        Returns:
            (is_valid, error_message)
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, f"Syntax error: {e}"

        for node in ast.walk(tree):
            # Check imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name not in self.allowed_modules:
                        return False, f"Module '{alias.name}' not allowed"

            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module not in self.allowed_modules:
                    return False, f"Module '{node.module}' not allowed"

            # Check function calls
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in self.DANGEROUS_CALLS:
                        return False, f"Function '{node.func.id}' not allowed"

        return True, ""

    def sanitize_output(self, output: str, max_length: int = 10000) -> str:
        """Sanitize and truncate output"""
        if len(output) > max_length:
            return output[:max_length] + f"\n... (truncated {len(output) - max_length} chars)"
        return output
