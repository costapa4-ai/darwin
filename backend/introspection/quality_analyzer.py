"""
Quality Analyzer: Learn from rejected code to improve future generation

Analyzes low-quality rejected code to identify patterns and provide
feedback for improving the code generation process.
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import json


@dataclass
class QualityInsight:
    """Insight derived from analyzing low-quality code"""
    pattern: str  # What pattern was identified
    frequency: int  # How often it occurs
    severity: str  # low, medium, high
    recommendation: str  # How to fix it
    examples: List[str]  # Example files with this issue


class QualityAnalyzer:
    """
    Analyzes rejected code to identify quality issues and patterns

    This helps Darwin learn from mistakes and improve code generation
    by understanding what makes code low quality.
    """

    def __init__(self, storage_path: str = "/app/data/quality_analysis"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.insights: List[QualityInsight] = []
        self.analysis_history: List[Dict] = []

        self._load_state()

    def analyze_rejected_code(
        self,
        generated_code: Dict,
        validation: Dict,
        rejection_reason: str
    ) -> Dict[str, Any]:
        """
        Analyze why code was rejected and extract learning insights

        Args:
            generated_code: The rejected code
            validation: Validation results
            rejection_reason: Why it was rejected

        Returns:
            Analysis results with actionable insights
        """
        file_path = generated_code.get('file_path', 'unknown')
        code = generated_code.get('new_code', '')
        score = validation.get('score', 0)
        issues = validation.get('issues', [])

        print(f"\n🔍 Analyzing rejected code: {file_path} (score: {score})")

        analysis = {
            'file_path': file_path,
            'score': score,
            'rejection_reason': rejection_reason,
            'analyzed_at': datetime.now().isoformat(),
            'patterns_found': [],
            'root_causes': [],
            'recommendations': []
        }

        # Analyze common low-quality patterns
        patterns = self._identify_quality_patterns(code, issues, file_path)
        analysis['patterns_found'] = patterns

        # Identify root causes
        root_causes = self._identify_root_causes(score, issues, patterns)
        analysis['root_causes'] = root_causes

        # Generate recommendations
        recommendations = self._generate_recommendations(patterns, root_causes, score)
        analysis['recommendations'] = recommendations

        # Update insights database
        self._update_insights(patterns, file_path)

        # Store analysis
        self.analysis_history.append(analysis)
        self._save_state()

        print(f"   ✅ Analysis complete: {len(patterns)} patterns, {len(root_causes)} root causes")

        return analysis

    def _identify_quality_patterns(
        self,
        code: str,
        issues: List[str],
        file_path: str
    ) -> List[Dict[str, Any]]:
        """Identify specific quality patterns in the code"""
        patterns = []

        # Pattern 1: Empty or minimal code
        lines = [l for l in code.split('\n') if l.strip() and not l.strip().startswith('#')]
        if len(lines) < 10:
            patterns.append({
                'pattern': 'minimal_implementation',
                'description': 'Code has fewer than 10 non-comment lines',
                'severity': 'high',
                'line_count': len(lines)
            })

        # Pattern 2: Missing docstrings
        if '"""' not in code and "'''" not in code:
            patterns.append({
                'pattern': 'missing_docstrings',
                'description': 'No module or function docstrings found',
                'severity': 'medium'
            })

        # Pattern 3: No type hints
        if '->' not in code and ': ' not in code:
            patterns.append({
                'pattern': 'missing_type_hints',
                'description': 'No type hints found in code',
                'severity': 'medium'
            })

        # Pattern 4: No error handling
        if 'try:' not in code and 'except' not in code:
            patterns.append({
                'pattern': 'missing_error_handling',
                'description': 'No error handling (try/except) found',
                'severity': 'high'
            })

        # Pattern 5: No imports (for non-trivial code)
        if 'import ' not in code and len(lines) > 5:
            patterns.append({
                'pattern': 'missing_imports',
                'description': 'No imports found in non-trivial code',
                'severity': 'high'
            })

        # Pattern 6: Template/placeholder code
        placeholder_indicators = ['TODO', 'FIXME', 'pass', '...', 'NotImplemented']
        placeholder_count = sum(1 for indicator in placeholder_indicators if indicator in code)
        if placeholder_count >= 3:
            patterns.append({
                'pattern': 'placeholder_code',
                'description': f'Multiple placeholders found ({placeholder_count})',
                'severity': 'high',
                'placeholder_count': placeholder_count
            })

        # Pattern 7: Duplicate/similar filename
        if 'architecture_apply_pattern' in file_path:
            patterns.append({
                'pattern': 'duplicate_pattern_tool',
                'description': 'Another architecture pattern tool - check for duplicates',
                'severity': 'medium'
            })

        # Pattern 8: Security issues from validation
        security_issues = [i for i in issues if 'security' in i.lower() or 'hardcoded' in i.lower()]
        if security_issues:
            patterns.append({
                'pattern': 'security_issues',
                'description': f'{len(security_issues)} security issues detected',
                'severity': 'high',
                'issues': security_issues[:3]
            })

        # Pattern 9: Syntax errors
        syntax_issues = [i for i in issues if 'syntax' in i.lower() or 'invalid' in i.lower()]
        if syntax_issues:
            patterns.append({
                'pattern': 'syntax_errors',
                'description': f'{len(syntax_issues)} syntax errors detected',
                'severity': 'critical',
                'issues': syntax_issues[:3]
            })

        return patterns

    def _identify_root_causes(
        self,
        score: int,
        issues: List[str],
        patterns: List[Dict]
    ) -> List[str]:
        """Identify root causes of low quality"""
        root_causes = []

        # Extremely low score (< 20)
        if score < 20:
            root_causes.append(
                "Code generation completely failed - likely generated template/stub instead of implementation"
            )

        # Check for specific pattern combinations
        pattern_names = [p['pattern'] for p in patterns]

        if 'minimal_implementation' in pattern_names and 'placeholder_code' in pattern_names:
            root_causes.append(
                "Generated code is just a template/skeleton without actual implementation"
            )

        if 'missing_imports' in pattern_names and 'minimal_implementation' in pattern_names:
            root_causes.append(
                "Code appears incomplete - missing imports suggests incomplete generation"
            )

        if 'syntax_errors' in pattern_names:
            root_causes.append(
                "Code has syntax errors - AI model may have been interrupted or context was too long"
            )

        if 'security_issues' in pattern_names:
            root_causes.append(
                "Code contains security vulnerabilities - AI model needs better security awareness"
            )

        if 'duplicate_pattern_tool' in pattern_names:
            root_causes.append(
                "Creating duplicate architecture pattern tools - need better tool discovery before generation"
            )

        # Multiple severe patterns
        high_severity = [p for p in patterns if p.get('severity') == 'high']
        if len(high_severity) >= 3:
            root_causes.append(
                f"Multiple critical quality issues ({len(high_severity)}) - comprehensive quality failure"
            )

        return root_causes

    def _generate_recommendations(
        self,
        patterns: List[Dict],
        root_causes: List[str],
        score: int
    ) -> List[str]:
        """Generate actionable recommendations for improvement"""
        recommendations = []

        # Score-based recommendations
        if score < 20:
            recommendations.append(
                "CRITICAL: Improve prompt engineering to ensure complete implementation, not just templates"
            )
            recommendations.append(
                "Add validation step: Check if generated code has actual logic, not just structure"
            )

        # Pattern-specific recommendations
        pattern_names = [p['pattern'] for p in patterns]

        if 'minimal_implementation' in pattern_names:
            recommendations.append(
                "Require minimum code length: At least 50 lines of implementation (excluding comments)"
            )

        if 'missing_docstrings' in pattern_names:
            recommendations.append(
                "Add docstring requirement to prompt: 'Include comprehensive docstrings for all modules and functions'"
            )

        if 'missing_type_hints' in pattern_names:
            recommendations.append(
                "Add type hint requirement: 'Use Python type hints for all function parameters and return values'"
            )

        if 'missing_error_handling' in pattern_names:
            recommendations.append(
                "Add error handling requirement: 'Include try/except blocks for all operations that can fail'"
            )

        if 'placeholder_code' in pattern_names:
            recommendations.append(
                "Prohibit placeholder code: 'Do not use TODO, FIXME, or pass statements - provide complete implementation'"
            )

        if 'duplicate_pattern_tool' in pattern_names:
            recommendations.append(
                "Check existing tools before generation: Query tool registry to avoid creating duplicates"
            )

        if 'security_issues' in pattern_names:
            recommendations.append(
                "Enhance security awareness: Add security checklist to code generation prompt"
            )

        if 'syntax_errors' in pattern_names:
            recommendations.append(
                "Reduce prompt complexity: Long prompts may cause truncation or errors"
            )

        return recommendations

    def _update_insights(self, patterns: List[Dict], file_path: str):
        """Update insights database with new patterns"""
        for pattern in patterns:
            pattern_name = pattern['pattern']

            # Find existing insight or create new
            existing = next((i for i in self.insights if i.pattern == pattern_name), None)

            if existing:
                existing.frequency += 1
                if file_path not in existing.examples:
                    existing.examples.append(file_path)
                    # Keep only last 5 examples
                    existing.examples = existing.examples[-5:]
            else:
                # Create new insight
                self.insights.append(QualityInsight(
                    pattern=pattern_name,
                    frequency=1,
                    severity=pattern.get('severity', 'medium'),
                    recommendation=self._get_pattern_recommendation(pattern_name),
                    examples=[file_path]
                ))

    def _get_pattern_recommendation(self, pattern: str) -> str:
        """Get recommendation for a specific pattern"""
        recommendations = {
            'minimal_implementation': 'Ensure code has substantial implementation, not just structure',
            'missing_docstrings': 'Always include module and function docstrings',
            'missing_type_hints': 'Add type hints to all function signatures',
            'missing_error_handling': 'Include error handling for all failure points',
            'missing_imports': 'Import all required dependencies',
            'placeholder_code': 'Avoid TODO/FIXME - provide complete implementation',
            'duplicate_pattern_tool': 'Check for existing similar tools before creating new ones',
            'security_issues': 'Follow security best practices - no hardcoded credentials',
            'syntax_errors': 'Validate syntax before submission'
        }
        return recommendations.get(pattern, 'Improve code quality')

    def get_top_insights(self, limit: int = 10) -> List[Dict]:
        """Get most frequent quality issues"""
        # Sort by frequency
        sorted_insights = sorted(self.insights, key=lambda x: x.frequency, reverse=True)

        return [
            {
                'pattern': i.pattern,
                'frequency': i.frequency,
                'severity': i.severity,
                'recommendation': i.recommendation,
                'example_files': i.examples[:3]
            }
            for i in sorted_insights[:limit]
        ]

    def get_improvement_prompt(self) -> str:
        """
        Generate prompt additions for code generation based on learned insights

        This creates a dynamic prompt that improves based on past failures
        """
        top_issues = self.get_top_insights(limit=5)

        if not top_issues:
            return ""

        prompt = "\n# CODE QUALITY REQUIREMENTS (Based on Past Analysis)\n\n"
        prompt += "To avoid common quality issues, ensure your code:\n\n"

        for idx, issue in enumerate(top_issues, 1):
            prompt += f"{idx}. **{issue['recommendation']}**\n"
            prompt += f"   (This issue occurred {issue['frequency']} times recently)\n\n"

        prompt += "\nThese requirements are based on analysis of previously rejected code.\n"

        return prompt

    def get_statistics(self) -> Dict[str, Any]:
        """Get quality analysis statistics"""
        if not self.analysis_history:
            return {
                'total_analyzed': 0,
                'average_score': 0,
                'most_common_patterns': [],
                'improvement_trend': 'no_data'
            }

        total = len(self.analysis_history)
        avg_score = sum(a['score'] for a in self.analysis_history) / total

        # Get recent trend (last 10 vs previous 10)
        if len(self.analysis_history) >= 20:
            recent_10 = [a['score'] for a in self.analysis_history[-10:]]
            previous_10 = [a['score'] for a in self.analysis_history[-20:-10]]
            recent_avg = sum(recent_10) / 10
            previous_avg = sum(previous_10) / 10

            if recent_avg > previous_avg + 5:
                trend = 'improving'
            elif recent_avg < previous_avg - 5:
                trend = 'declining'
            else:
                trend = 'stable'
        else:
            trend = 'insufficient_data'

        return {
            'total_analyzed': total,
            'average_score': round(avg_score, 1),
            'most_common_patterns': self.get_top_insights(limit=5),
            'improvement_trend': trend,
            'recent_analyses': len([a for a in self.analysis_history if a['score'] < 40])
        }

    def _save_state(self):
        """Save analysis state to disk"""
        try:
            # Save insights
            insights_file = self.storage_path / "quality_insights.json"
            with open(insights_file, 'w') as f:
                json.dump(
                    [
                        {
                            'pattern': i.pattern,
                            'frequency': i.frequency,
                            'severity': i.severity,
                            'recommendation': i.recommendation,
                            'examples': i.examples
                        }
                        for i in self.insights
                    ],
                    f,
                    indent=2
                )

            # Save recent analysis history (last 100)
            history_file = self.storage_path / "analysis_history.json"
            with open(history_file, 'w') as f:
                json.dump(self.analysis_history[-100:], f, indent=2)

        except Exception as e:
            print(f"❌ Failed to save quality analysis state: {e}")

    def _load_state(self):
        """Load analysis state from disk"""
        try:
            # Load insights
            insights_file = self.storage_path / "quality_insights.json"
            if insights_file.exists():
                with open(insights_file, 'r') as f:
                    data = json.load(f)
                    self.insights = [
                        QualityInsight(
                            pattern=i['pattern'],
                            frequency=i['frequency'],
                            severity=i['severity'],
                            recommendation=i['recommendation'],
                            examples=i['examples']
                        )
                        for i in data
                    ]

            # Load history
            history_file = self.storage_path / "analysis_history.json"
            if history_file.exists():
                with open(history_file, 'r') as f:
                    self.analysis_history = json.load(f)

            if self.insights or self.analysis_history:
                print(f"📥 Loaded {len(self.insights)} quality insights and {len(self.analysis_history)} analyses")

        except Exception as e:
            print(f"⚠️ Failed to load quality analysis state: {e}")
            self.insights = []
            self.analysis_history = []
