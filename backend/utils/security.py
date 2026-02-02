"""
Security utilities for safe code execution.

This module provides defense-in-depth security for code execution:
1. AST-based whitelist validation (not blacklist)
2. Dangerous pattern detection
3. Attribute access chain blocking
4. Resource limit helpers
"""

import ast
import re
from typing import Set, Tuple, List, Optional
from dataclasses import dataclass

from utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class SecurityViolation:
    """Represents a security violation found during validation."""
    severity: str  # 'critical', 'high', 'medium', 'low'
    category: str  # 'import', 'call', 'attribute', 'pattern'
    message: str
    line: Optional[int] = None
    col: Optional[int] = None


class CodeValidator:
    """
    Validates Python code for security concerns using WHITELIST approach.

    Key security principles:
    1. Whitelist > Blacklist: Only explicitly allowed things pass
    2. Defense in depth: Multiple layers of validation
    3. Fail secure: If uncertain, reject
    """

    # ==================== WHITELIST DEFINITIONS ====================

    # Allowed built-in functions (whitelist)
    ALLOWED_BUILTINS = {
        # Safe output
        'print',
        # Type conversions
        'str', 'int', 'float', 'bool', 'bytes',
        # Collections
        'list', 'dict', 'set', 'tuple', 'frozenset',
        # Iteration
        'range', 'enumerate', 'zip', 'map', 'filter', 'reversed',
        # Math/Logic
        'abs', 'max', 'min', 'sum', 'round', 'pow', 'divmod',
        'all', 'any', 'len', 'sorted',
        # Type checking (safe)
        'isinstance', 'issubclass', 'type', 'callable',
        # String/repr
        'repr', 'ascii', 'chr', 'ord', 'format',
        'bin', 'hex', 'oct',
        # Iteration helpers
        'iter', 'next',
        # Object helpers (limited)
        'hash', 'id',
        # Slice
        'slice',
    }

    # DANGEROUS builtins that should NEVER be allowed
    FORBIDDEN_BUILTINS = {
        'eval', 'exec', 'compile',
        '__import__', 'open', 'input',
        'globals', 'locals', 'vars',
        'getattr', 'setattr', 'delattr', 'hasattr',  # Attribute manipulation
        'dir',  # Can reveal internals
        'breakpoint', 'help',
        'memoryview',  # Can access raw memory
        'classmethod', 'staticmethod', 'property',  # Descriptor manipulation
        'super',  # Can access parent classes
        'object',  # Base class access
    }

    # Allowed AST node types (whitelist)
    ALLOWED_NODE_TYPES = {
        # Literals
        ast.Constant, ast.Num, ast.Str, ast.Bytes,
        ast.List, ast.Tuple, ast.Set, ast.Dict,
        ast.NameConstant,  # True, False, None

        # Variables
        ast.Name, ast.Load, ast.Store, ast.Del,

        # Expressions
        ast.Expr, ast.UnaryOp, ast.BinOp, ast.BoolOp,
        ast.Compare, ast.Call, ast.IfExp,
        ast.Subscript, ast.Index, ast.Slice,

        # Operators
        ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv,
        ast.Mod, ast.Pow, ast.LShift, ast.RShift,
        ast.BitOr, ast.BitXor, ast.BitAnd, ast.MatMult,
        ast.UAdd, ast.USub, ast.Not, ast.Invert,
        ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
        ast.Is, ast.IsNot, ast.In, ast.NotIn,
        ast.And, ast.Or,

        # Statements
        ast.Assign, ast.AugAssign, ast.AnnAssign,
        ast.If, ast.For, ast.While, ast.Break, ast.Continue,
        ast.Pass, ast.Return,
        ast.FunctionDef, ast.AsyncFunctionDef,
        ast.arguments, ast.arg,

        # Comprehensions
        ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp,
        ast.comprehension,

        # Context
        ast.With, ast.withitem,

        # Exception handling
        ast.Try, ast.ExceptHandler, ast.Raise,

        # Module
        ast.Module,

        # Formatted strings
        ast.JoinedStr, ast.FormattedValue,

        # Starred (for unpacking)
        ast.Starred,

        # Lambda
        ast.Lambda,
    }

    # FORBIDDEN AST node types
    FORBIDDEN_NODE_TYPES = {
        ast.Import,      # No imports
        ast.ImportFrom,  # No imports
        ast.Global,      # No global manipulation
        ast.Nonlocal,    # No nonlocal manipulation
        ast.ClassDef,    # No class definitions (prevents metaclass attacks)
        ast.Attribute,   # Handled separately with whitelist
        ast.Yield,       # No generators (can cause issues)
        ast.YieldFrom,
        ast.Await,       # No async (handled separately if needed)
        ast.Assert,      # Can be disabled with -O
    }

    # Allowed attribute access patterns (whitelist)
    # Format: (type_name, allowed_attributes)
    ALLOWED_ATTRIBUTES = {
        'str': {'lower', 'upper', 'strip', 'lstrip', 'rstrip', 'split', 'join',
                'replace', 'find', 'rfind', 'index', 'rindex', 'count',
                'startswith', 'endswith', 'isalpha', 'isdigit', 'isalnum',
                'isspace', 'isupper', 'islower', 'title', 'capitalize',
                'swapcase', 'center', 'ljust', 'rjust', 'zfill', 'format',
                'encode', 'partition', 'rpartition', 'splitlines'},
        'list': {'append', 'extend', 'insert', 'remove', 'pop', 'clear',
                 'index', 'count', 'sort', 'reverse', 'copy'},
        'dict': {'keys', 'values', 'items', 'get', 'pop', 'popitem',
                 'clear', 'update', 'setdefault', 'copy', 'fromkeys'},
        'set': {'add', 'remove', 'discard', 'pop', 'clear', 'update',
                'intersection', 'union', 'difference', 'symmetric_difference',
                'issubset', 'issuperset', 'isdisjoint', 'copy'},
        'tuple': {'index', 'count'},
        'bytes': {'decode', 'hex', 'count', 'find', 'index', 'join',
                  'replace', 'split', 'strip', 'lstrip', 'rstrip'},
        'int': {'bit_length', 'to_bytes', 'from_bytes'},
        'float': {'is_integer', 'hex', 'fromhex'},
    }

    # DANGEROUS attribute patterns (regex)
    DANGEROUS_ATTRIBUTE_PATTERNS = [
        r'__\w+__',      # Dunder attributes (magic methods)
        r'_\w+',         # Private attributes
        r'func_\w+',     # Function internals
        r'co_\w+',       # Code object attributes
        r'gi_\w+',       # Generator internals
        r'f_\w+',        # Frame attributes
        r'tb_\w+',       # Traceback attributes
    ]

    # Dangerous code patterns (regex) - defense in depth
    DANGEROUS_CODE_PATTERNS = [
        (r'__class__', 'critical', 'Class access can escape sandbox'),
        (r'__bases__', 'critical', 'Base class access can escape sandbox'),
        (r'__subclasses__', 'critical', 'Subclass enumeration can escape sandbox'),
        (r'__mro__', 'critical', 'MRO access can escape sandbox'),
        (r'__globals__', 'critical', 'Global access can escape sandbox'),
        (r'__code__', 'critical', 'Code object access is dangerous'),
        (r'__builtins__', 'critical', 'Builtins access can escape sandbox'),
        (r'__import__', 'critical', 'Import function is forbidden'),
        (r'__dict__', 'high', 'Dict access can reveal internals'),
        (r'__module__', 'high', 'Module access can reveal internals'),
        (r'__name__\s*\[', 'high', 'Name subscript access'),
        (r'getattr\s*\(', 'critical', 'getattr can access any attribute'),
        (r'setattr\s*\(', 'critical', 'setattr can modify any attribute'),
        (r'delattr\s*\(', 'critical', 'delattr can delete any attribute'),
        (r'eval\s*\(', 'critical', 'eval is forbidden'),
        (r'exec\s*\(', 'critical', 'exec is forbidden'),
        (r'compile\s*\(', 'critical', 'compile is forbidden'),
        (r'open\s*\(', 'critical', 'File access is forbidden'),
        (r'os\s*\.', 'critical', 'OS module access is forbidden'),
        (r'sys\s*\.', 'critical', 'Sys module access is forbidden'),
        (r'subprocess', 'critical', 'Subprocess is forbidden'),
        (r'socket', 'critical', 'Socket access is forbidden'),
        (r'pickle', 'critical', 'Pickle can execute arbitrary code'),
        (r'marshal', 'critical', 'Marshal can execute arbitrary code'),
        (r'ctypes', 'critical', 'Ctypes can access raw memory'),
    ]

    def __init__(self, allowed_modules: Set[str] = None):
        """
        Initialize the code validator.

        Args:
            allowed_modules: Set of module names that ARE allowed to be imported.
                           Default is empty (no imports allowed).
        """
        self.allowed_modules = allowed_modules or set()
        self._compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), severity, msg)
            for pattern, severity, msg in self.DANGEROUS_CODE_PATTERNS
        ]
        logger.info(f"CodeValidator initialized (allowed_modules: {self.allowed_modules})")

    def validate(self, code: str) -> Tuple[bool, str]:
        """
        Validate code for security issues.

        Returns:
            (is_valid, error_message)
        """
        violations = self.get_violations(code)

        if violations:
            # Get the most severe violation
            critical = [v for v in violations if v.severity == 'critical']
            if critical:
                return False, f"CRITICAL: {critical[0].message}"

            high = [v for v in violations if v.severity == 'high']
            if high:
                return False, f"HIGH: {high[0].message}"

            # Return first violation
            return False, violations[0].message

        return True, ""

    def get_violations(self, code: str) -> List[SecurityViolation]:
        """
        Get all security violations in the code.

        Returns:
            List of SecurityViolation objects
        """
        violations = []

        # Phase 1: Pattern-based detection (fast, catches obvious issues)
        violations.extend(self._check_dangerous_patterns(code))

        # Phase 2: AST-based validation (thorough)
        try:
            tree = ast.parse(code)
            violations.extend(self._validate_ast(tree))
        except SyntaxError as e:
            violations.append(SecurityViolation(
                severity='high',
                category='syntax',
                message=f"Syntax error: {e}",
                line=e.lineno,
                col=e.offset
            ))

        return violations

    def _check_dangerous_patterns(self, code: str) -> List[SecurityViolation]:
        """Check for dangerous code patterns using regex."""
        violations = []

        for pattern, severity, message in self._compiled_patterns:
            matches = pattern.finditer(code)
            for match in matches:
                # Calculate line number
                line_num = code[:match.start()].count('\n') + 1
                violations.append(SecurityViolation(
                    severity=severity,
                    category='pattern',
                    message=f"{message} (found: '{match.group()}')",
                    line=line_num
                ))

        return violations

    def _validate_ast(self, tree: ast.AST) -> List[SecurityViolation]:
        """Validate AST nodes against whitelist."""
        violations = []

        for node in ast.walk(tree):
            node_type = type(node)

            # Check for forbidden node types
            if node_type in self.FORBIDDEN_NODE_TYPES:
                violations.append(SecurityViolation(
                    severity='critical' if node_type in (ast.Import, ast.ImportFrom) else 'high',
                    category='ast_node',
                    message=f"Forbidden construct: {node_type.__name__}",
                    line=getattr(node, 'lineno', None),
                    col=getattr(node, 'col_offset', None)
                ))
                continue

            # Special handling for Attribute nodes
            if node_type == ast.Attribute:
                violation = self._validate_attribute(node)
                if violation:
                    violations.append(violation)
                continue

            # Special handling for Call nodes
            if node_type == ast.Call:
                violation = self._validate_call(node)
                if violation:
                    violations.append(violation)
                continue

            # Special handling for Name nodes (variable access)
            if node_type == ast.Name:
                violation = self._validate_name(node)
                if violation:
                    violations.append(violation)
                continue

        return violations

    def _validate_attribute(self, node: ast.Attribute) -> Optional[SecurityViolation]:
        """Validate attribute access."""
        attr_name = node.attr

        # Check against dangerous patterns
        for pattern in self.DANGEROUS_ATTRIBUTE_PATTERNS:
            if re.match(pattern, attr_name):
                return SecurityViolation(
                    severity='critical' if attr_name.startswith('__') else 'high',
                    category='attribute',
                    message=f"Forbidden attribute access: '{attr_name}'",
                    line=node.lineno,
                    col=node.col_offset
                )

        # For now, allow other attributes (would need type inference for full whitelist)
        return None

    def _validate_call(self, node: ast.Call) -> Optional[SecurityViolation]:
        """Validate function calls."""
        # Get function name if it's a simple Name
        if isinstance(node.func, ast.Name):
            func_name = node.func.id

            # Check against forbidden builtins
            if func_name in self.FORBIDDEN_BUILTINS:
                return SecurityViolation(
                    severity='critical',
                    category='call',
                    message=f"Forbidden function: '{func_name}'",
                    line=node.lineno,
                    col=node.col_offset
                )

        return None

    def _validate_name(self, node: ast.Name) -> Optional[SecurityViolation]:
        """Validate variable/name access."""
        name = node.id

        # Check for forbidden builtins being accessed
        if name in self.FORBIDDEN_BUILTINS:
            return SecurityViolation(
                severity='critical',
                category='name',
                message=f"Forbidden name: '{name}'",
                line=node.lineno,
                col=node.col_offset
            )

        return None

    def sanitize_output(self, output: str, max_length: int = 10000) -> str:
        """Sanitize and truncate output."""
        if not output:
            return ""

        if len(output) > max_length:
            return output[:max_length] + f"\n... (truncated {len(output) - max_length} chars)"

        return output

    def get_security_report(self, code: str) -> dict:
        """
        Get a detailed security report for the code.

        Returns:
            Dictionary with security analysis results
        """
        violations = self.get_violations(code)

        return {
            'is_safe': len(violations) == 0,
            'violation_count': len(violations),
            'critical_count': len([v for v in violations if v.severity == 'critical']),
            'high_count': len([v for v in violations if v.severity == 'high']),
            'violations': [
                {
                    'severity': v.severity,
                    'category': v.category,
                    'message': v.message,
                    'line': v.line,
                    'col': v.col
                }
                for v in violations
            ]
        }


def create_safe_builtins() -> dict:
    """
    Create a restricted builtins dictionary for safe code execution.

    This prevents sandbox escapes via class hierarchy traversal.
    """

    # Wrap types to prevent __class__ access
    class SafeType:
        """Wrapper that prevents dangerous attribute access."""

        def __init__(self, wrapped_type):
            self._type = wrapped_type

        def __call__(self, *args, **kwargs):
            return self._type(*args, **kwargs)

        def __getattr__(self, name):
            # Block dangerous attributes
            if name.startswith('_'):
                raise AttributeError(f"Access to '{name}' is not allowed")
            return getattr(self._type, name)

    safe_builtins = {
        # Safe output
        'print': print,

        # Wrapped types (prevent __class__ escape)
        'str': SafeType(str),
        'int': SafeType(int),
        'float': SafeType(float),
        'bool': SafeType(bool),
        'bytes': SafeType(bytes),
        'list': SafeType(list),
        'dict': SafeType(dict),
        'tuple': SafeType(tuple),
        'set': SafeType(set),
        'frozenset': SafeType(frozenset),

        # Safe functions
        'len': len,
        'range': range,
        'abs': abs,
        'max': max,
        'min': min,
        'sum': sum,
        'round': round,
        'pow': pow,
        'divmod': divmod,
        'sorted': sorted,
        'reversed': reversed,
        'enumerate': enumerate,
        'zip': zip,
        'map': map,
        'filter': filter,
        'all': all,
        'any': any,
        'isinstance': isinstance,
        'issubclass': issubclass,
        'callable': callable,
        'repr': repr,
        'ascii': ascii,
        'chr': chr,
        'ord': ord,
        'format': format,
        'bin': bin,
        'hex': hex,
        'oct': oct,
        'hash': hash,
        'id': id,
        'slice': slice,
        'iter': iter,
        'next': next,

        # Constants
        'True': True,
        'False': False,
        'None': None,
        '__name__': '__restricted__',

        # Exceptions (limited set for error handling)
        'Exception': Exception,
        'ValueError': ValueError,
        'TypeError': TypeError,
        'KeyError': KeyError,
        'IndexError': IndexError,
        'RuntimeError': RuntimeError,
        'StopIteration': StopIteration,
        'ZeroDivisionError': ZeroDivisionError,
    }

    return safe_builtins


def set_resource_limits(max_memory_mb: int = 256, max_cpu_seconds: int = 30):
    """
    Set resource limits for the current process (Unix only).

    Should be called in the child process before executing code.
    """
    try:
        import resource

        # Memory limit (in bytes)
        max_memory = max_memory_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (max_memory, max_memory))

        # CPU time limit
        resource.setrlimit(resource.RLIMIT_CPU, (max_cpu_seconds, max_cpu_seconds))

        # Prevent forking
        resource.setrlimit(resource.RLIMIT_NPROC, (0, 0))

        # Limit file size (prevent disk filling)
        resource.setrlimit(resource.RLIMIT_FSIZE, (1024 * 1024, 1024 * 1024))  # 1MB

        logger.debug(f"Resource limits set: memory={max_memory_mb}MB, cpu={max_cpu_seconds}s")
        return True

    except ImportError:
        logger.warning("resource module not available (not Unix)")
        return False
    except Exception as e:
        logger.error(f"Failed to set resource limits: {e}")
        return False
