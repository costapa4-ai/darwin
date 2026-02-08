"""
Security Checks - OWASP-focused security analysis for Python code.

Loads patterns dynamically from:
- /data/security/owasp_patterns.json (base OWASP patterns)
- /data/security/darwin_patterns.json (patterns Darwin discovers)

Darwin can extend the pattern database through learning expeditions.
"""

import ast
import re
import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Dict, Any, Optional, Set


class OWASPCategory(Enum):
    """OWASP Top 10 2021 Categories."""
    A01_BROKEN_ACCESS_CONTROL = "A01:2021-Broken Access Control"
    A02_CRYPTOGRAPHIC_FAILURES = "A02:2021-Cryptographic Failures"
    A03_INJECTION = "A03:2021-Injection"
    A04_INSECURE_DESIGN = "A04:2021-Insecure Design"
    A05_SECURITY_MISCONFIGURATION = "A05:2021-Security Misconfiguration"
    A06_VULNERABLE_COMPONENTS = "A06:2021-Vulnerable and Outdated Components"
    A07_AUTH_FAILURES = "A07:2021-Identification and Authentication Failures"
    A08_DATA_INTEGRITY = "A08:2021-Software and Data Integrity Failures"
    A09_LOGGING_FAILURES = "A09:2021-Security Logging and Monitoring Failures"
    A10_SSRF = "A10:2021-Server-Side Request Forgery"


@dataclass
class SecurityFinding:
    """A security finding from the audit."""
    category: OWASPCategory
    severity: str  # critical, high, medium, low, info
    title: str
    description: str
    file_path: str
    line_number: Optional[int] = None
    code_snippet: Optional[str] = None
    recommendation: Optional[str] = None
    cwe_id: Optional[str] = None
    confidence: str = "medium"  # high, medium, low
    pattern_id: Optional[str] = None  # ID of the pattern that matched


@dataclass
class SecurityPattern:
    """A security detection pattern."""
    id: str
    pattern: str
    title: str
    owasp: str
    cwe: str
    severity: str
    confidence: str = "medium"
    source: str = "owasp"  # owasp or darwin


class PatternLoader:
    """Loads and manages security patterns from JSON files."""

    def __init__(self, patterns_dir: str = "/app/data/security"):
        self.patterns_dir = Path(patterns_dir)
        self.owasp_file = self.patterns_dir / "owasp_patterns.json"
        self.darwin_file = self.patterns_dir / "darwin_patterns.json"

        self.owasp_data: Dict = {}
        self.darwin_data: Dict = {}
        self.patterns: List[SecurityPattern] = []
        self.recommendations: Dict[str, str] = {}
        self.categories: Dict[str, Dict] = {}

        self._load_patterns()

    def _load_patterns(self):
        """Load patterns from JSON files."""
        # Load OWASP patterns
        if self.owasp_file.exists():
            try:
                with open(self.owasp_file, 'r') as f:
                    self.owasp_data = json.load(f)

                self.categories = self.owasp_data.get('categories', {})
                self.recommendations = self.owasp_data.get('recommendations', {})

                # Parse patterns
                for category, patterns in self.owasp_data.get('patterns', {}).items():
                    for p in patterns:
                        self.patterns.append(SecurityPattern(
                            id=p['id'],
                            pattern=p['pattern'],
                            title=p['title'],
                            owasp=p['owasp'],
                            cwe=p['cwe'],
                            severity=p['severity'],
                            confidence=p.get('confidence', 'medium'),
                            source='owasp'
                        ))
            except Exception as e:
                print(f"Warning: Could not load OWASP patterns: {e}")

        # Load Darwin-discovered patterns
        if self.darwin_file.exists():
            try:
                with open(self.darwin_file, 'r') as f:
                    self.darwin_data = json.load(f)

                for p in self.darwin_data.get('patterns', []):
                    self.patterns.append(SecurityPattern(
                        id=p['id'],
                        pattern=p['pattern'],
                        title=p['title'],
                        owasp=p['owasp'],
                        cwe=p['cwe'],
                        severity=p['severity'],
                        confidence=p.get('confidence', 'medium'),
                        source='darwin'
                    ))

                # Merge Darwin's recommendations
                self.recommendations.update(self.darwin_data.get('recommendations', {}))

            except Exception as e:
                print(f"Warning: Could not load Darwin patterns: {e}")

    def get_owasp_version(self) -> str:
        """Get the OWASP Top 10 version being used."""
        return self.owasp_data.get('version', 'unknown')

    def get_pattern_count(self) -> Dict[str, int]:
        """Get count of patterns by source."""
        owasp_count = sum(1 for p in self.patterns if p.source == 'owasp')
        darwin_count = sum(1 for p in self.patterns if p.source == 'darwin')
        return {'owasp': owasp_count, 'darwin': darwin_count, 'total': len(self.patterns)}

    def add_darwin_pattern(
        self,
        pattern_id: str,
        pattern: str,
        title: str,
        owasp: str,
        cwe: str,
        severity: str,
        confidence: str = "medium",
        learned_from: str = None
    ) -> bool:
        """Add a new pattern discovered by Darwin."""
        try:
            # Load current Darwin patterns
            if self.darwin_file.exists():
                with open(self.darwin_file, 'r') as f:
                    data = json.load(f)
            else:
                data = {
                    "version": "1.0",
                    "last_updated": datetime.now().isoformat(),
                    "description": "Security patterns discovered by Darwin",
                    "patterns": [],
                    "learned_from": [],
                    "recommendations": {}
                }

            # Check for duplicate ID
            existing_ids = {p['id'] for p in data.get('patterns', [])}
            if pattern_id in existing_ids:
                return False

            # Add new pattern
            new_pattern = {
                "id": pattern_id,
                "pattern": pattern,
                "title": title,
                "owasp": owasp,
                "cwe": cwe,
                "severity": severity,
                "confidence": confidence,
                "added_at": datetime.now().isoformat()
            }
            data['patterns'].append(new_pattern)
            data['last_updated'] = datetime.now().isoformat()

            if learned_from:
                data['learned_from'].append({
                    "pattern_id": pattern_id,
                    "source": learned_from,
                    "timestamp": datetime.now().isoformat()
                })

            # Save
            self.patterns_dir.mkdir(parents=True, exist_ok=True)
            with open(self.darwin_file, 'w') as f:
                json.dump(data, f, indent=2)

            # Add to in-memory patterns
            self.patterns.append(SecurityPattern(
                id=pattern_id,
                pattern=pattern,
                title=title,
                owasp=owasp,
                cwe=cwe,
                severity=severity,
                confidence=confidence,
                source='darwin'
            ))

            return True

        except Exception as e:
            print(f"Error adding Darwin pattern: {e}")
            return False

    def add_recommendation(self, cwe: str, recommendation: str) -> bool:
        """Add or update a recommendation for a CWE."""
        try:
            if self.darwin_file.exists():
                with open(self.darwin_file, 'r') as f:
                    data = json.load(f)
            else:
                data = {"recommendations": {}}

            if 'recommendations' not in data:
                data['recommendations'] = {}

            data['recommendations'][cwe] = recommendation
            data['last_updated'] = datetime.now().isoformat()

            with open(self.darwin_file, 'w') as f:
                json.dump(data, f, indent=2)

            self.recommendations[cwe] = recommendation
            return True

        except Exception as e:
            print(f"Error adding recommendation: {e}")
            return False

    def update_owasp_patterns(self, new_data: Dict) -> bool:
        """Update OWASP patterns (e.g., when a new Top 10 is released)."""
        try:
            # Backup existing
            if self.owasp_file.exists():
                backup_path = self.owasp_file.with_suffix('.json.bak')
                with open(self.owasp_file, 'r') as f:
                    backup_data = f.read()
                with open(backup_path, 'w') as f:
                    f.write(backup_data)

            # Write new data
            new_data['last_updated'] = datetime.now().isoformat()
            with open(self.owasp_file, 'w') as f:
                json.dump(new_data, f, indent=2)

            # Reload
            self._load_patterns()
            return True

        except Exception as e:
            print(f"Error updating OWASP patterns: {e}")
            return False


class SecurityChecker:
    """
    OWASP-focused security checker for Python code.

    Combines pattern-based analysis with AST inspection.
    Patterns are loaded dynamically from JSON files.
    """

    def __init__(self, project_root: str = "/app", patterns_dir: str = None):
        self.project_root = Path(project_root)
        self.findings: List[SecurityFinding] = []

        # Load patterns
        patterns_path = patterns_dir or str(self.project_root / "data" / "security")
        self.pattern_loader = PatternLoader(patterns_path)

        # OWASP code to category mapping
        self._owasp_map = {
            "A01": OWASPCategory.A01_BROKEN_ACCESS_CONTROL,
            "A02": OWASPCategory.A02_CRYPTOGRAPHIC_FAILURES,
            "A03": OWASPCategory.A03_INJECTION,
            "A04": OWASPCategory.A04_INSECURE_DESIGN,
            "A05": OWASPCategory.A05_SECURITY_MISCONFIGURATION,
            "A06": OWASPCategory.A06_VULNERABLE_COMPONENTS,
            "A07": OWASPCategory.A07_AUTH_FAILURES,
            "A08": OWASPCategory.A08_DATA_INTEGRITY,
            "A09": OWASPCategory.A09_LOGGING_FAILURES,
            "A10": OWASPCategory.A10_SSRF,
        }

    def get_pattern_stats(self) -> Dict[str, Any]:
        """Get statistics about loaded patterns."""
        return {
            'owasp_version': self.pattern_loader.get_owasp_version(),
            'pattern_counts': self.pattern_loader.get_pattern_count(),
            'categories': list(self.pattern_loader.categories.keys()),
            'total_recommendations': len(self.pattern_loader.recommendations)
        }

    def add_pattern(self, **kwargs) -> bool:
        """Add a new security pattern (for Darwin to use)."""
        return self.pattern_loader.add_darwin_pattern(**kwargs)

    def check_file(self, file_path: str) -> List[SecurityFinding]:
        """Run all security checks on a single file."""
        findings = []

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')
        except Exception as e:
            return [SecurityFinding(
                category=OWASPCategory.A04_INSECURE_DESIGN,
                severity="info",
                title="Could not read file",
                description=f"Error reading file: {e}",
                file_path=file_path
            )]

        # Pattern-based checks using loaded patterns
        for pattern in self.pattern_loader.patterns:
            try:
                regex = re.compile(pattern.pattern, re.IGNORECASE)
                for i, line in enumerate(lines, 1):
                    if regex.search(line):
                        # Skip comments
                        stripped = line.strip()
                        if stripped.startswith('#'):
                            continue

                        category = self._owasp_map.get(
                            pattern.owasp,
                            OWASPCategory.A04_INSECURE_DESIGN
                        )

                        findings.append(SecurityFinding(
                            category=category,
                            severity=pattern.severity,
                            title=pattern.title,
                            description=f"Pattern '{pattern.id}' matched",
                            file_path=file_path,
                            line_number=i,
                            code_snippet=line.strip()[:100],
                            cwe_id=pattern.cwe,
                            confidence=pattern.confidence,
                            pattern_id=pattern.id,
                            recommendation=self.pattern_loader.recommendations.get(pattern.cwe)
                        ))
            except re.error as e:
                pass  # Invalid regex pattern

        # AST-based checks for complex patterns
        try:
            tree = ast.parse(content)
            findings.extend(self._ast_checks(tree, file_path, lines))
        except SyntaxError:
            pass  # Skip AST checks for files with syntax errors

        return findings

    def _ast_checks(self, tree: ast.AST, file_path: str, lines: List[str]) -> List[SecurityFinding]:
        """AST-based security checks for complex patterns."""
        findings = []

        for node in ast.walk(tree):
            # Check for unsafe deserialization
            if isinstance(node, ast.Call):
                func_name = self._get_func_name(node)

                if func_name in ('pickle.loads', 'pickle.load', 'cPickle.loads', 'cPickle.load'):
                    findings.append(SecurityFinding(
                        category=OWASPCategory.A08_DATA_INTEGRITY,
                        severity="high",
                        title="Unsafe pickle deserialization",
                        description="pickle.load can execute arbitrary code",
                        file_path=file_path,
                        line_number=node.lineno,
                        code_snippet=lines[node.lineno - 1].strip() if node.lineno <= len(lines) else "",
                        cwe_id="CWE-502",
                        recommendation=self.pattern_loader.recommendations.get("CWE-502", "Use JSON or other safe serialization")
                    ))

            # Check for assert used for security
            if isinstance(node, ast.Assert):
                src = lines[node.lineno - 1] if node.lineno <= len(lines) else ""
                if any(kw in src.lower() for kw in ['auth', 'permission', 'access', 'role']):
                    findings.append(SecurityFinding(
                        category=OWASPCategory.A01_BROKEN_ACCESS_CONTROL,
                        severity="high",
                        title="Assert used for access control",
                        description="assert statements are removed with -O flag",
                        file_path=file_path,
                        line_number=node.lineno,
                        code_snippet=src.strip()[:100],
                        cwe_id="CWE-617",
                        recommendation="Use proper if/raise for security checks"
                    ))

        return findings

    def _get_func_name(self, node: ast.Call) -> str:
        """Extract function name from Call node."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            parts = []
            current = node.func
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            return '.'.join(reversed(parts))
        return ""

    def run_bandit(self, target_path: str = None) -> List[SecurityFinding]:
        """Run Bandit security scanner and convert results."""
        target = target_path or str(self.project_root)
        findings = []

        try:
            result = subprocess.run(
                ['bandit', '-r', target, '-f', 'json', '-q'],
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.stdout:
                data = json.loads(result.stdout)
                for issue in data.get('results', []):
                    owasp_cat = self._bandit_to_owasp(issue.get('test_id', ''))

                    findings.append(SecurityFinding(
                        category=owasp_cat,
                        severity=issue.get('issue_severity', 'medium').lower(),
                        title=issue.get('issue_text', 'Security issue'),
                        description=f"Bandit {issue.get('test_id')}: {issue.get('issue_text')}",
                        file_path=issue.get('filename', ''),
                        line_number=issue.get('line_number'),
                        code_snippet=issue.get('code', '')[:100],
                        confidence=issue.get('issue_confidence', 'medium').lower(),
                        cwe_id=str(issue.get('issue_cwe', {}).get('id')) if issue.get('issue_cwe') else None
                    ))

        except FileNotFoundError:
            pass  # Bandit not installed
        except Exception:
            pass

        return findings

    def _bandit_to_owasp(self, test_id: str) -> OWASPCategory:
        """Map Bandit test IDs to OWASP categories."""
        # Comprehensive mapping
        mappings = {
            'B101': OWASPCategory.A04_INSECURE_DESIGN,
            'B102': OWASPCategory.A03_INJECTION,
            'B103': OWASPCategory.A05_SECURITY_MISCONFIGURATION,
            'B104': OWASPCategory.A05_SECURITY_MISCONFIGURATION,
            'B105': OWASPCategory.A02_CRYPTOGRAPHIC_FAILURES,
            'B106': OWASPCategory.A02_CRYPTOGRAPHIC_FAILURES,
            'B107': OWASPCategory.A02_CRYPTOGRAPHIC_FAILURES,
            'B108': OWASPCategory.A03_INJECTION,
            'B110': OWASPCategory.A09_LOGGING_FAILURES,
            'B301': OWASPCategory.A08_DATA_INTEGRITY,
            'B302': OWASPCategory.A08_DATA_INTEGRITY,
            'B303': OWASPCategory.A02_CRYPTOGRAPHIC_FAILURES,
            'B304': OWASPCategory.A02_CRYPTOGRAPHIC_FAILURES,
            'B305': OWASPCategory.A02_CRYPTOGRAPHIC_FAILURES,
            'B306': OWASPCategory.A03_INJECTION,
            'B307': OWASPCategory.A03_INJECTION,
            'B310': OWASPCategory.A10_SSRF,
            'B311': OWASPCategory.A02_CRYPTOGRAPHIC_FAILURES,
            'B323': OWASPCategory.A07_AUTH_FAILURES,
            'B324': OWASPCategory.A02_CRYPTOGRAPHIC_FAILURES,
            'B501': OWASPCategory.A07_AUTH_FAILURES,
            'B502': OWASPCategory.A07_AUTH_FAILURES,
            'B503': OWASPCategory.A07_AUTH_FAILURES,
            'B504': OWASPCategory.A07_AUTH_FAILURES,
            'B505': OWASPCategory.A02_CRYPTOGRAPHIC_FAILURES,
            'B506': OWASPCategory.A08_DATA_INTEGRITY,
            'B602': OWASPCategory.A03_INJECTION,
            'B603': OWASPCategory.A03_INJECTION,
            'B604': OWASPCategory.A03_INJECTION,
            'B605': OWASPCategory.A03_INJECTION,
            'B606': OWASPCategory.A03_INJECTION,
            'B607': OWASPCategory.A03_INJECTION,
            'B608': OWASPCategory.A03_INJECTION,
        }
        return mappings.get(test_id, OWASPCategory.A04_INSECURE_DESIGN)

    def check_dependencies(self) -> List[SecurityFinding]:
        """Check for vulnerable dependencies using safety."""
        findings = []
        requirements_files = list(self.project_root.glob('**/requirements*.txt'))

        for req_file in requirements_files:
            try:
                result = subprocess.run(
                    ['safety', 'check', '-r', str(req_file), '--json'],
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                if result.stdout:
                    data = json.loads(result.stdout)
                    for vuln in data:
                        if isinstance(vuln, list) and len(vuln) >= 5:
                            findings.append(SecurityFinding(
                                category=OWASPCategory.A06_VULNERABLE_COMPONENTS,
                                severity="high",
                                title=f"Vulnerable dependency: {vuln[0]}",
                                description=f"{vuln[0]} {vuln[2]} has known vulnerability: {vuln[3]}",
                                file_path=str(req_file),
                                recommendation=f"Upgrade to version {vuln[4]} or later",
                                cwe_id="CWE-1035"
                            ))

            except FileNotFoundError:
                pass
            except Exception:
                pass

        return findings

    def check_project(self, exclude_dirs: Set[str] = None) -> List[SecurityFinding]:
        """Run all security checks on the entire project."""
        exclude = exclude_dirs or {'venv', 'node_modules', '.git', '__pycache__', 'backups'}

        all_findings = []

        # Run Bandit
        all_findings.extend(self.run_bandit())

        # Run custom pattern checks on Python files
        for py_file in self.project_root.rglob('*.py'):
            if any(excl in py_file.parts for excl in exclude):
                continue
            all_findings.extend(self.check_file(str(py_file)))

        # Check dependencies
        all_findings.extend(self.check_dependencies())

        # Deduplicate findings
        seen = set()
        unique_findings = []
        for f in all_findings:
            key = (f.file_path, f.line_number, f.title)
            if key not in seen:
                seen.add(key)
                unique_findings.append(f)

        self.findings = unique_findings
        return unique_findings


# Convenience functions for Darwin
async def learn_security_pattern(
    pattern_id: str,
    pattern: str,
    title: str,
    owasp_category: str,
    cwe: str,
    severity: str = "medium",
    confidence: str = "medium",
    learned_from: str = None
) -> Dict[str, Any]:
    """
    Learn a new security pattern from an expedition or research.

    This function is designed to be called by Darwin after learning
    about a new vulnerability pattern.

    Args:
        pattern_id: Unique ID for the pattern (e.g., "DARWIN001")
        pattern: Regex pattern to detect the vulnerability
        title: Human-readable title
        owasp_category: OWASP category code (e.g., "A03")
        cwe: CWE identifier (e.g., "CWE-89")
        severity: critical, high, medium, low
        confidence: high, medium, low
        learned_from: Source of the learning (e.g., "OWASP expedition")

    Returns:
        Success status and message
    """
    checker = SecurityChecker()

    success = checker.add_pattern(
        pattern_id=pattern_id,
        pattern=pattern,
        title=title,
        owasp=owasp_category,
        cwe=cwe,
        severity=severity,
        confidence=confidence,
        learned_from=learned_from
    )

    if success:
        return {
            "success": True,
            "message": f"Learned new security pattern: {title}",
            "pattern_id": pattern_id,
            "stats": checker.get_pattern_stats()
        }
    else:
        return {
            "success": False,
            "message": f"Failed to add pattern (may already exist): {pattern_id}"
        }
