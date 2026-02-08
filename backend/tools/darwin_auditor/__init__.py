"""
Darwin Auditor - Lightweight Security & Quality Assessment Tool

A focused code analysis tool for Darwin that combines:
- OWASP security checks
- Code quality metrics
- Architecture analysis
- Darwin-specific safety checks

Designed to be used during self-improvement validation cycles.
"""

from .auditor import DarwinAuditor, AuditResult, AuditSeverity
from .security_checks import SecurityChecker, OWASPCategory
from .quality_checks import QualityChecker

__all__ = [
    'DarwinAuditor',
    'AuditResult',
    'AuditSeverity',
    'SecurityChecker',
    'OWASPCategory',
    'QualityChecker'
]
