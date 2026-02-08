"""
Quality Checks - Code quality and architecture analysis.

Analyzes:
- Cyclomatic complexity
- Code duplication patterns
- Module coupling
- Dead code detection
- Documentation coverage
- Type hint coverage
"""

import ast
import re
import subprocess
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import defaultdict


@dataclass
class QualityFinding:
    """A code quality finding."""
    category: str  # complexity, duplication, coupling, dead_code, documentation, typing
    severity: str  # critical, high, medium, low, info
    title: str
    description: str
    file_path: str
    line_number: Optional[int] = None
    metric_value: Optional[float] = None
    threshold: Optional[float] = None
    recommendation: Optional[str] = None


@dataclass
class ModuleMetrics:
    """Metrics for a single module/file."""
    file_path: str
    lines_of_code: int = 0
    cyclomatic_complexity: float = 0.0
    functions: int = 0
    classes: int = 0
    imports: int = 0
    type_hint_coverage: float = 0.0
    docstring_coverage: float = 0.0
    max_function_complexity: int = 0
    max_function_name: str = ""


class QualityChecker:
    """
    Code quality analyzer for Python projects.

    Checks:
    - Complexity (cyclomatic, cognitive)
    - Code smells
    - Documentation coverage
    - Type hint coverage
    - Module coupling
    """

    # Thresholds
    MAX_FUNCTION_COMPLEXITY = 10
    MAX_FILE_COMPLEXITY = 50
    MAX_FUNCTION_LENGTH = 50
    MAX_CLASS_LENGTH = 300
    MAX_IMPORTS = 20
    MIN_DOCSTRING_COVERAGE = 0.5
    MIN_TYPE_HINT_COVERAGE = 0.3

    def __init__(self, project_root: str = "/app"):
        self.project_root = Path(project_root)
        self.findings: List[QualityFinding] = []
        self.module_metrics: Dict[str, ModuleMetrics] = {}

    def check_file(self, file_path: str) -> Tuple[List[QualityFinding], ModuleMetrics]:
        """Analyze a single Python file for quality issues."""
        findings = []
        metrics = ModuleMetrics(file_path=file_path)

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')
        except Exception as e:
            return [QualityFinding(
                category="error",
                severity="info",
                title="Could not read file",
                description=str(e),
                file_path=file_path
            )], metrics

        metrics.lines_of_code = len([l for l in lines if l.strip() and not l.strip().startswith('#')])

        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            return [QualityFinding(
                category="syntax",
                severity="critical",
                title="Syntax error",
                description=str(e),
                file_path=file_path,
                line_number=e.lineno
            )], metrics

        # Analyze AST
        visitor = QualityVisitor(file_path, lines)
        visitor.visit(tree)

        # Update metrics
        metrics.functions = visitor.function_count
        metrics.classes = visitor.class_count
        metrics.imports = visitor.import_count
        metrics.cyclomatic_complexity = sum(visitor.function_complexities.values())
        metrics.type_hint_coverage = visitor.type_hint_coverage
        metrics.docstring_coverage = visitor.docstring_coverage

        if visitor.function_complexities:
            max_func = max(visitor.function_complexities.items(), key=lambda x: x[1])
            metrics.max_function_complexity = max_func[1]
            metrics.max_function_name = max_func[0]

        # Generate findings from visitor data
        findings.extend(visitor.findings)

        # Check complexity thresholds
        if metrics.cyclomatic_complexity > self.MAX_FILE_COMPLEXITY:
            findings.append(QualityFinding(
                category="complexity",
                severity="high",
                title="High file complexity",
                description=f"File has cyclomatic complexity of {metrics.cyclomatic_complexity}",
                file_path=file_path,
                metric_value=metrics.cyclomatic_complexity,
                threshold=self.MAX_FILE_COMPLEXITY,
                recommendation="Split into smaller modules"
            ))

        # Check for too many imports
        if metrics.imports > self.MAX_IMPORTS:
            findings.append(QualityFinding(
                category="coupling",
                severity="medium",
                title="Too many imports",
                description=f"File has {metrics.imports} imports, indicating high coupling",
                file_path=file_path,
                metric_value=metrics.imports,
                threshold=self.MAX_IMPORTS,
                recommendation="Consider splitting module or using dependency injection"
            ))

        # Check documentation coverage
        if metrics.docstring_coverage < self.MIN_DOCSTRING_COVERAGE and metrics.functions > 2:
            findings.append(QualityFinding(
                category="documentation",
                severity="low",
                title="Low documentation coverage",
                description=f"Only {metrics.docstring_coverage:.0%} of functions have docstrings",
                file_path=file_path,
                metric_value=metrics.docstring_coverage,
                threshold=self.MIN_DOCSTRING_COVERAGE,
                recommendation="Add docstrings to public functions"
            ))

        # Check type hint coverage
        if metrics.type_hint_coverage < self.MIN_TYPE_HINT_COVERAGE and metrics.functions > 2:
            findings.append(QualityFinding(
                category="typing",
                severity="low",
                title="Low type hint coverage",
                description=f"Only {metrics.type_hint_coverage:.0%} of functions have type hints",
                file_path=file_path,
                metric_value=metrics.type_hint_coverage,
                threshold=self.MIN_TYPE_HINT_COVERAGE,
                recommendation="Add type hints to function signatures"
            ))

        return findings, metrics

    def run_radon(self, target_path: str = None) -> List[QualityFinding]:
        """Run Radon complexity analysis."""
        target = target_path or str(self.project_root)
        findings = []

        try:
            # Cyclomatic complexity
            result = subprocess.run(
                ['radon', 'cc', target, '-j', '-a'],
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.stdout:
                data = json.loads(result.stdout)
                for file_path, functions in data.items():
                    if isinstance(functions, list):
                        for func in functions:
                            if isinstance(func, dict):
                                complexity = func.get('complexity', 0)
                                if complexity > self.MAX_FUNCTION_COMPLEXITY:
                                    severity = "critical" if complexity > 20 else "high" if complexity > 15 else "medium"
                                    findings.append(QualityFinding(
                                        category="complexity",
                                        severity=severity,
                                        title=f"High complexity: {func.get('name', '?')}",
                                        description=f"Cyclomatic complexity is {complexity}",
                                        file_path=file_path,
                                        line_number=func.get('lineno'),
                                        metric_value=complexity,
                                        threshold=self.MAX_FUNCTION_COMPLEXITY,
                                        recommendation="Refactor into smaller functions"
                                    ))

        except FileNotFoundError:
            pass  # Radon not installed
        except Exception:
            pass

        return findings

    def check_code_smells(self, file_path: str, content: str, lines: List[str]) -> List[QualityFinding]:
        """Detect common code smells."""
        findings = []

        # Long lines
        for i, line in enumerate(lines, 1):
            if len(line) > 120 and not line.strip().startswith('#'):
                findings.append(QualityFinding(
                    category="style",
                    severity="info",
                    title="Line too long",
                    description=f"Line has {len(line)} characters (max 120)",
                    file_path=file_path,
                    line_number=i,
                    recommendation="Break into multiple lines"
                ))

        # TODO/FIXME/HACK comments
        for i, line in enumerate(lines, 1):
            for marker in ['TODO', 'FIXME', 'HACK', 'XXX']:
                if marker in line:
                    findings.append(QualityFinding(
                        category="maintenance",
                        severity="info",
                        title=f"{marker} comment found",
                        description=line.strip()[:80],
                        file_path=file_path,
                        line_number=i,
                        recommendation="Address the technical debt"
                    ))
                    break

        # Magic numbers
        magic_pattern = r'(?<!["\'])(?<!\w)\b(?!0|1|2|10|100|1000)\d{2,}\b(?!["\'])'
        for i, line in enumerate(lines, 1):
            if re.search(magic_pattern, line) and not line.strip().startswith('#'):
                findings.append(QualityFinding(
                    category="readability",
                    severity="info",
                    title="Magic number detected",
                    description=line.strip()[:60],
                    file_path=file_path,
                    line_number=i,
                    recommendation="Use named constant"
                ))

        # God class detection (rough heuristic)
        if content.count('def ') > 20 and content.count('class ') == 1:
            findings.append(QualityFinding(
                category="design",
                severity="medium",
                title="Potential God class",
                description="Class has many methods, consider splitting",
                file_path=file_path,
                recommendation="Apply Single Responsibility Principle"
            ))

        return findings

    def check_project(self, exclude_dirs: Set[str] = None) -> List[QualityFinding]:
        """Run all quality checks on the entire project."""
        exclude = exclude_dirs or {'venv', 'node_modules', '.git', '__pycache__', 'backups', 'dreams'}

        all_findings = []

        # Run Radon
        all_findings.extend(self.run_radon())

        # Check all Python files
        for py_file in self.project_root.rglob('*.py'):
            if any(excl in py_file.parts for excl in exclude):
                continue

            file_findings, metrics = self.check_file(str(py_file))
            all_findings.extend(file_findings)
            self.module_metrics[str(py_file)] = metrics

        self.findings = all_findings
        return all_findings

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics."""
        total_loc = sum(m.lines_of_code for m in self.module_metrics.values())
        avg_complexity = sum(m.cyclomatic_complexity for m in self.module_metrics.values()) / max(len(self.module_metrics), 1)

        by_severity = defaultdict(int)
        by_category = defaultdict(int)

        for f in self.findings:
            by_severity[f.severity] += 1
            by_category[f.category] += 1

        return {
            "total_files": len(self.module_metrics),
            "total_lines_of_code": total_loc,
            "average_complexity": round(avg_complexity, 2),
            "total_findings": len(self.findings),
            "by_severity": dict(by_severity),
            "by_category": dict(by_category),
            "most_complex_files": sorted(
                [(m.file_path, m.cyclomatic_complexity) for m in self.module_metrics.values()],
                key=lambda x: -x[1]
            )[:5]
        }


class QualityVisitor(ast.NodeVisitor):
    """AST visitor for extracting quality metrics."""

    def __init__(self, file_path: str, lines: List[str]):
        self.file_path = file_path
        self.lines = lines
        self.findings: List[QualityFinding] = []

        self.function_count = 0
        self.class_count = 0
        self.import_count = 0
        self.function_complexities: Dict[str, int] = {}

        self.functions_with_docstrings = 0
        self.functions_with_type_hints = 0

        self._current_class = None

    @property
    def docstring_coverage(self) -> float:
        return self.functions_with_docstrings / max(self.function_count, 1)

    @property
    def type_hint_coverage(self) -> float:
        return self.functions_with_type_hints / max(self.function_count, 1)

    def visit_FunctionDef(self, node):
        self._analyze_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        self._analyze_function(node)
        self.generic_visit(node)

    def _analyze_function(self, node):
        self.function_count += 1

        # Get full function name
        func_name = f"{self._current_class}.{node.name}" if self._current_class else node.name

        # Calculate cyclomatic complexity
        complexity = self._calculate_complexity(node)
        self.function_complexities[func_name] = complexity

        # Check for docstring
        if ast.get_docstring(node):
            self.functions_with_docstrings += 1

        # Check for type hints
        has_return_hint = node.returns is not None
        has_arg_hints = any(arg.annotation for arg in node.args.args)
        if has_return_hint or has_arg_hints:
            self.functions_with_type_hints += 1

        # Check function length
        func_lines = node.end_lineno - node.lineno + 1 if hasattr(node, 'end_lineno') else 0
        if func_lines > 50:
            self.findings.append(QualityFinding(
                category="complexity",
                severity="medium",
                title=f"Long function: {func_name}",
                description=f"Function has {func_lines} lines",
                file_path=self.file_path,
                line_number=node.lineno,
                metric_value=func_lines,
                threshold=50,
                recommendation="Break into smaller functions"
            ))

        # High complexity
        if complexity > 10:
            severity = "critical" if complexity > 20 else "high" if complexity > 15 else "medium"
            self.findings.append(QualityFinding(
                category="complexity",
                severity=severity,
                title=f"Complex function: {func_name}",
                description=f"Cyclomatic complexity is {complexity}",
                file_path=self.file_path,
                line_number=node.lineno,
                metric_value=complexity,
                threshold=10,
                recommendation="Refactor into smaller functions"
            ))

    def _calculate_complexity(self, node) -> int:
        """Calculate cyclomatic complexity of a function."""
        complexity = 1  # Base complexity

        for child in ast.walk(node):
            # Decision points
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.With):
                complexity += 1
            elif isinstance(child, ast.Assert):
                complexity += 1
            elif isinstance(child, ast.comprehension):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                # and/or add complexity
                complexity += len(child.values) - 1
            elif isinstance(child, ast.IfExp):  # Ternary
                complexity += 1

        return complexity

    def visit_ClassDef(self, node):
        self.class_count += 1
        old_class = self._current_class
        self._current_class = node.name

        # Check class length
        class_lines = node.end_lineno - node.lineno + 1 if hasattr(node, 'end_lineno') else 0
        if class_lines > 300:
            self.findings.append(QualityFinding(
                category="design",
                severity="medium",
                title=f"Large class: {node.name}",
                description=f"Class has {class_lines} lines",
                file_path=self.file_path,
                line_number=node.lineno,
                metric_value=class_lines,
                threshold=300,
                recommendation="Consider splitting into smaller classes"
            ))

        self.generic_visit(node)
        self._current_class = old_class

    def visit_Import(self, node):
        self.import_count += len(node.names)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        self.import_count += len(node.names)
        self.generic_visit(node)
