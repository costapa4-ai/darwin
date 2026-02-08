"""
Darwin Auditor - Main orchestrator for security and quality analysis.

Combines:
- OWASP security checks
- Code quality metrics
- Architecture analysis
- Darwin-specific safety checks
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Dict, Any, Optional, Set

from .security_checks import SecurityChecker, SecurityFinding, OWASPCategory
from .quality_checks import QualityChecker, QualityFinding


class AuditSeverity(Enum):
    """Audit finding severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class AuditResult:
    """Complete audit result."""
    timestamp: str
    project_path: str
    duration_seconds: float = 0.0

    # Security findings
    security_findings: List[SecurityFinding] = field(default_factory=list)
    security_by_owasp: Dict[str, int] = field(default_factory=dict)
    security_by_severity: Dict[str, int] = field(default_factory=dict)

    # Quality findings
    quality_findings: List[QualityFinding] = field(default_factory=list)
    quality_by_category: Dict[str, int] = field(default_factory=dict)
    quality_by_severity: Dict[str, int] = field(default_factory=dict)

    # Metrics
    total_files: int = 0
    total_lines_of_code: int = 0
    average_complexity: float = 0.0

    # Score (0-100)
    security_score: int = 100
    quality_score: int = 100
    overall_score: int = 100

    # Summary
    critical_issues: int = 0
    high_issues: int = 0
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "timestamp": self.timestamp,
            "project_path": self.project_path,
            "duration_seconds": self.duration_seconds,
            "scores": {
                "security": self.security_score,
                "quality": self.quality_score,
                "overall": self.overall_score
            },
            "summary": {
                "total_files": self.total_files,
                "total_lines_of_code": self.total_lines_of_code,
                "critical_issues": self.critical_issues,
                "high_issues": self.high_issues,
                "average_complexity": self.average_complexity
            },
            "security": {
                "total_findings": len(self.security_findings),
                "by_owasp": self.security_by_owasp,
                "by_severity": self.security_by_severity,
                "findings": [self._finding_to_dict(f) for f in self.security_findings[:50]]
            },
            "quality": {
                "total_findings": len(self.quality_findings),
                "by_category": self.quality_by_category,
                "by_severity": self.quality_by_severity,
                "findings": [self._qfinding_to_dict(f) for f in self.quality_findings[:50]]
            },
            "recommendations": self.recommendations
        }
        return result

    def _finding_to_dict(self, f: SecurityFinding) -> Dict:
        return {
            "category": f.category.value if hasattr(f.category, 'value') else str(f.category),
            "severity": f.severity,
            "title": f.title,
            "description": f.description,
            "file_path": f.file_path,
            "line_number": f.line_number,
            "code_snippet": f.code_snippet,
            "recommendation": f.recommendation,
            "cwe_id": f.cwe_id
        }

    def _qfinding_to_dict(self, f: QualityFinding) -> Dict:
        return {
            "category": f.category,
            "severity": f.severity,
            "title": f.title,
            "description": f.description,
            "file_path": f.file_path,
            "line_number": f.line_number,
            "metric_value": f.metric_value,
            "threshold": f.threshold,
            "recommendation": f.recommendation
        }


class DarwinAuditor:
    """
    Main auditor class for Darwin self-assessment.

    Usage:
        auditor = DarwinAuditor(project_root="/app")
        result = auditor.run_full_audit()
        print(f"Security Score: {result.security_score}/100")
        print(f"Quality Score: {result.quality_score}/100")
    """

    def __init__(
        self,
        project_root: str = "/app",
        exclude_dirs: Set[str] = None
    ):
        self.project_root = Path(project_root)
        self.exclude_dirs = exclude_dirs or {
            'venv', 'node_modules', '.git', '__pycache__',
            'backups', 'dreams', 'data', '.pytest_cache',
            'htmlcov', '.mypy_cache', 'dist', 'build'
        }

        self.security_checker = SecurityChecker(project_root)
        self.quality_checker = QualityChecker(project_root)

    def run_full_audit(self) -> AuditResult:
        """Run complete security and quality audit."""
        import time
        start_time = time.time()

        result = AuditResult(
            timestamp=datetime.now().isoformat(),
            project_path=str(self.project_root)
        )

        # Run security checks
        security_findings = self.security_checker.check_project(self.exclude_dirs)
        result.security_findings = security_findings

        # Aggregate security findings
        for f in security_findings:
            cat = f.category.value if hasattr(f.category, 'value') else str(f.category)
            result.security_by_owasp[cat] = result.security_by_owasp.get(cat, 0) + 1
            result.security_by_severity[f.severity] = result.security_by_severity.get(f.severity, 0) + 1

        # Run quality checks
        quality_findings = self.quality_checker.check_project(self.exclude_dirs)
        result.quality_findings = quality_findings

        # Aggregate quality findings
        for f in quality_findings:
            result.quality_by_category[f.category] = result.quality_by_category.get(f.category, 0) + 1
            result.quality_by_severity[f.severity] = result.quality_by_severity.get(f.severity, 0) + 1

        # Get quality summary
        quality_summary = self.quality_checker.get_summary()
        result.total_files = quality_summary['total_files']
        result.total_lines_of_code = quality_summary['total_lines_of_code']
        result.average_complexity = quality_summary['average_complexity']

        # Calculate scores
        result.security_score = self._calculate_security_score(security_findings)
        result.quality_score = self._calculate_quality_score(quality_findings, quality_summary)
        result.overall_score = (result.security_score * 0.6 + result.quality_score * 0.4)

        # Count critical issues
        result.critical_issues = (
            result.security_by_severity.get('critical', 0) +
            result.quality_by_severity.get('critical', 0)
        )
        result.high_issues = (
            result.security_by_severity.get('high', 0) +
            result.quality_by_severity.get('high', 0)
        )

        # Generate recommendations
        result.recommendations = self._generate_recommendations(result)

        result.duration_seconds = time.time() - start_time

        return result

    def run_security_only(self) -> List[SecurityFinding]:
        """Run only security checks."""
        return self.security_checker.check_project(self.exclude_dirs)

    def run_quality_only(self) -> List[QualityFinding]:
        """Run only quality checks."""
        return self.quality_checker.check_project(self.exclude_dirs)

    def check_file(self, file_path: str) -> Dict[str, Any]:
        """Check a single file for security and quality issues."""
        security = self.security_checker.check_file(file_path)
        quality, metrics = self.quality_checker.check_file(file_path)

        return {
            "file_path": file_path,
            "security_findings": len(security),
            "quality_findings": len(quality),
            "metrics": {
                "lines_of_code": metrics.lines_of_code,
                "complexity": metrics.cyclomatic_complexity,
                "functions": metrics.functions,
                "classes": metrics.classes,
                "type_hint_coverage": f"{metrics.type_hint_coverage:.0%}",
                "docstring_coverage": f"{metrics.docstring_coverage:.0%}"
            },
            "security": [self._finding_summary(f) for f in security],
            "quality": [self._qfinding_summary(f) for f in quality]
        }

    def check_code_snippet(self, code: str, filename: str = "snippet.py") -> Dict[str, Any]:
        """Check a code snippet for security and quality issues."""
        import tempfile
        import os

        # Write to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = f.name

        try:
            result = self.check_file(temp_path)
            result['file_path'] = filename
            return result
        finally:
            os.unlink(temp_path)

    def _calculate_security_score(self, findings: List[SecurityFinding]) -> int:
        """Calculate security score (0-100) based on findings."""
        score = 100

        for f in findings:
            if f.severity == 'critical':
                score -= 15
            elif f.severity == 'high':
                score -= 8
            elif f.severity == 'medium':
                score -= 3
            elif f.severity == 'low':
                score -= 1

        return max(0, min(100, score))

    def _calculate_quality_score(
        self,
        findings: List[QualityFinding],
        summary: Dict[str, Any]
    ) -> int:
        """Calculate quality score (0-100) based on findings and metrics."""
        score = 100

        # Deduct for findings
        for f in findings:
            if f.severity == 'critical':
                score -= 10
            elif f.severity == 'high':
                score -= 5
            elif f.severity == 'medium':
                score -= 2
            elif f.severity == 'low':
                score -= 0.5

        # Deduct for high average complexity
        avg_complexity = summary.get('average_complexity', 0)
        if avg_complexity > 20:
            score -= 15
        elif avg_complexity > 15:
            score -= 10
        elif avg_complexity > 10:
            score -= 5

        return max(0, min(100, int(score)))

    def _generate_recommendations(self, result: AuditResult) -> List[str]:
        """Generate prioritized recommendations based on findings."""
        recommendations = []

        # Critical security issues first
        if result.security_by_severity.get('critical', 0) > 0:
            recommendations.append(
                f"URGENT: Fix {result.security_by_severity['critical']} critical security vulnerabilities immediately"
            )

        # OWASP-specific recommendations
        if result.security_by_owasp.get(OWASPCategory.A03_INJECTION.value, 0) > 0:
            recommendations.append(
                "Use parameterized queries and avoid shell=True to prevent injection attacks"
            )

        if result.security_by_owasp.get(OWASPCategory.A02_CRYPTOGRAPHIC_FAILURES.value, 0) > 0:
            recommendations.append(
                "Move secrets to environment variables and use strong cryptographic algorithms"
            )

        if result.security_by_owasp.get(OWASPCategory.A07_AUTH_FAILURES.value, 0) > 0:
            recommendations.append(
                "Enable SSL verification and use secure authentication practices"
            )

        # Quality recommendations
        if result.average_complexity > 15:
            recommendations.append(
                f"Reduce code complexity (current average: {result.average_complexity:.1f})"
            )

        complexity_issues = result.quality_by_category.get('complexity', 0)
        if complexity_issues > 10:
            recommendations.append(
                f"Refactor {complexity_issues} overly complex functions into smaller units"
            )

        # Documentation
        doc_issues = result.quality_by_category.get('documentation', 0)
        if doc_issues > 5:
            recommendations.append(
                "Improve documentation coverage for public APIs"
            )

        # Limit recommendations
        return recommendations[:7]

    def _finding_summary(self, f: SecurityFinding) -> Dict:
        return {
            "severity": f.severity,
            "title": f.title,
            "line": f.line_number,
            "cwe": f.cwe_id
        }

    def _qfinding_summary(self, f: QualityFinding) -> Dict:
        return {
            "severity": f.severity,
            "title": f.title,
            "line": f.line_number,
            "category": f.category
        }

    def save_report(self, result: AuditResult, output_path: str = None) -> str:
        """Save audit report to JSON file."""
        if output_path is None:
            output_path = self.project_root / "data" / "audits" / f"audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(result.to_dict(), f, indent=2)

        return str(output_path)


# Convenience function for Darwin's tool registry
async def run_darwin_audit(
    project_root: str = "/app",
    save_report: bool = True
) -> Dict[str, Any]:
    """
    Run Darwin self-audit and return results.

    This function is designed to be called from Darwin's consciousness engine
    during self-improvement cycles.
    """
    auditor = DarwinAuditor(project_root=project_root)
    result = auditor.run_full_audit()

    report_path = None
    if save_report:
        report_path = auditor.save_report(result)

    return {
        "success": True,
        "security_score": result.security_score,
        "quality_score": result.quality_score,
        "overall_score": result.overall_score,
        "critical_issues": result.critical_issues,
        "high_issues": result.high_issues,
        "total_findings": len(result.security_findings) + len(result.quality_findings),
        "recommendations": result.recommendations,
        "report_path": report_path,
        "summary": {
            "files_analyzed": result.total_files,
            "lines_of_code": result.total_lines_of_code,
            "security_findings": len(result.security_findings),
            "quality_findings": len(result.quality_findings),
            "top_owasp_categories": sorted(
                result.security_by_owasp.items(),
                key=lambda x: -x[1]
            )[:3]
        }
    }
