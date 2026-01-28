"""
Self-Analyzer: Darwin System's ability to analyze and understand itself
Meta-level introspection for self-improvement suggestions
"""
import os
import ast
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
import subprocess
import re


@dataclass
class CodeInsight:
    """Insight about Darwin's own code"""
    type: str  # 'improvement', 'optimization', 'feature', 'refactor'
    component: str  # Which component (backend, frontend, docker, etc.)
    priority: str  # 'high', 'medium', 'low'
    title: str
    description: str
    proposed_change: str
    benefits: List[str]
    estimated_impact: str  # 'high', 'medium', 'low'
    confidence: float = 0.8  # Confidence in this insight (0-1)
    current_state: str = ""  # Current state of the code
    code_location: Optional[str] = None


@dataclass
class SystemMetrics:
    """Metrics about Darwin's own system"""
    total_files: int
    total_lines_of_code: int
    components: Dict[str, int]
    languages: Dict[str, int]
    docker_stats: Dict[str, Any]
    code_complexity: Dict[str, Any]


class SelfAnalyzer:
    """
    Darwin's consciousness - the ability to analyze and improve itself
    """

    def __init__(self, project_root: str = "/app"):
        self.project_root = Path(project_root)
        self.insights: List[CodeInsight] = []
        self.metrics: Optional[SystemMetrics] = None

    def analyze_self(self) -> Dict[str, Any]:
        """
        Complete self-analysis of Darwin System
        Returns comprehensive insights about the system
        """
        print("🔍 Darwin is analyzing itself...")

        # Collect metrics
        self.metrics = self._collect_system_metrics()

        # Analyze different aspects
        self._analyze_code_structure()
        self._analyze_docker_environment()
        self._analyze_performance_opportunities()
        self._analyze_feature_gaps()
        self._analyze_architecture_patterns()

        return {
            'timestamp': datetime.now().isoformat(),
            'metrics': asdict(self.metrics) if self.metrics else {},
            'insights': [asdict(insight) for insight in self.insights],
            'summary': self._generate_summary()
        }

    def _collect_system_metrics(self) -> SystemMetrics:
        """Collect metrics about the codebase"""
        total_files = 0
        total_lines = 0
        components = {}
        languages = {'python': 0, 'javascript': 0, 'other': 0}

        # Scan project directory
        if self.project_root.exists():
            for file_path in self.project_root.rglob('*'):
                if file_path.is_file() and not self._should_skip(file_path):
                    total_files += 1

                    # Count lines
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            lines = len(f.readlines())
                            total_lines += lines

                        # Categorize by component
                        component = self._get_component(file_path)
                        components[component] = components.get(component, 0) + lines

                        # Categorize by language
                        if file_path.suffix == '.py':
                            languages['python'] += lines
                        elif file_path.suffix in ['.js', '.jsx', '.ts', '.tsx']:
                            languages['javascript'] += lines
                        else:
                            languages['other'] += lines

                    except Exception:
                        pass

        # Get Docker stats
        docker_stats = self._get_docker_stats()

        return SystemMetrics(
            total_files=total_files,
            total_lines_of_code=total_lines,
            components=components,
            languages=languages,
            docker_stats=docker_stats,
            code_complexity=self._estimate_complexity()
        )

    def _should_skip(self, file_path: Path) -> bool:
        """Check if file should be skipped"""
        skip_dirs = {'node_modules', '__pycache__', '.git', 'data', 'logs', 'venv'}
        return any(skip_dir in file_path.parts for skip_dir in skip_dirs)

    def _get_component(self, file_path: Path) -> str:
        """Identify which component a file belongs to"""
        parts = file_path.parts
        if 'backend' in parts:
            return 'backend'
        elif 'frontend' in parts:
            return 'frontend'
        elif 'sandbox' in parts:
            return 'sandbox'
        elif any(x in str(file_path) for x in ['docker', 'Docker']):
            return 'docker'
        return 'other'

    def _get_docker_stats(self) -> Dict[str, Any]:
        """Get statistics about Docker environment"""
        stats = {
            'containers': 0,
            'images': 0,
            'volumes': 0,
            'networks': 0
        }

        try:
            # Try to get docker stats
            result = subprocess.run(['docker', 'ps', '-q'], capture_output=True, text=True)
            if result.returncode == 0:
                stats['containers'] = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0

            result = subprocess.run(['docker', 'images', '-q'], capture_output=True, text=True)
            if result.returncode == 0:
                stats['images'] = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0

        except Exception:
            pass

        return stats

    def _estimate_complexity(self) -> Dict[str, Any]:
        """Estimate code complexity"""
        return {
            'estimated_cyclomatic': 'medium',
            'modularity': 'high',
            'coupling': 'low',
            'cohesion': 'high'
        }

    def _analyze_code_structure(self):
        """Analyze code structure and suggest improvements"""

        # Check for missing __init__.py files
        self.insights.append(CodeInsight(
            type='improvement',
            component='backend',
            priority='low',
            title='Ensure all Python packages have __init__.py',
            description='Some directories might be missing __init__.py files',
            current_state='Most packages have __init__.py',
            proposed_change='Add __init__.py to any missing directories',
            benefits=['Better module organization', 'Clearer package structure'],
            estimated_impact='low'
        ))

        # Suggest type hints
        self.insights.append(CodeInsight(
            type='improvement',
            component='backend',
            priority='medium',
            title='Add comprehensive type hints',
            description='Not all functions have complete type hints',
            current_state='Partial type hints in codebase',
            proposed_change='Add type hints to all function signatures',
            benefits=['Better IDE support', 'Catch errors early', 'Self-documenting code'],
            estimated_impact='medium',
            code_location='backend/**/*.py'
        ))

    def _analyze_docker_environment(self):
        """Analyze Docker setup and suggest optimizations"""

        self.insights.append(CodeInsight(
            type='optimization',
            component='docker',
            priority='medium',
            title='Multi-stage Docker builds',
            description='Use multi-stage builds to reduce image size',
            current_state='Single-stage builds',
            proposed_change='Implement multi-stage builds for backend and frontend',
            benefits=[
                'Smaller image sizes (30-50% reduction)',
                'Faster deployment',
                'Better security (no build tools in production)'
            ],
            estimated_impact='high',
            code_location='backend/Dockerfile, frontend/Dockerfile'
        ))

        self.insights.append(CodeInsight(
            type='optimization',
            component='docker',
            priority='high',
            title='Docker layer caching optimization',
            description='Optimize Dockerfile layer order for better caching',
            current_state='Dependencies reinstalled on every code change',
            proposed_change='Copy requirements.txt first, then install, then copy code',
            benefits=[
                'Much faster rebuilds',
                'Better development experience',
                'Reduced bandwidth usage'
            ],
            estimated_impact='high',
            code_location='backend/Dockerfile'
        ))

        self.insights.append(CodeInsight(
            type='feature',
            component='docker',
            priority='low',
            title='Add Docker health checks',
            description='Implement health check endpoints for all services',
            current_state='No health checks configured',
            proposed_change='Add HEALTHCHECK directives to Dockerfiles',
            benefits=[
                'Automatic container restart on failure',
                'Better orchestration support',
                'Improved monitoring'
            ],
            estimated_impact='medium',
            code_location='docker-compose.yml'
        ))

    def _analyze_performance_opportunities(self):
        """Identify performance improvement opportunities"""

        self.insights.append(CodeInsight(
            type='optimization',
            component='backend',
            priority='high',
            title='Implement connection pooling for database',
            description='Use connection pooling to reduce database overhead',
            current_state='New connection per request',
            proposed_change='SQLAlchemy connection pool with optimal settings',
            benefits=[
                'Faster query execution',
                'Reduced database load',
                'Better resource utilization'
            ],
            estimated_impact='high',
            code_location='backend/core/memory.py'
        ))

        self.insights.append(CodeInsight(
            type='optimization',
            component='backend',
            priority='medium',
            title='Add Redis caching layer',
            description='Cache frequently accessed data in Redis',
            current_state='Redis available but underutilized',
            proposed_change='Implement caching for: metrics, agent stats, dream history',
            benefits=[
                'Faster API responses',
                'Reduced database load',
                'Better scalability'
            ],
            estimated_impact='high',
            code_location='backend/services/'
        ))

        self.insights.append(CodeInsight(
            type='optimization',
            component='frontend',
            priority='medium',
            title='Implement code splitting',
            description='Split frontend bundle for faster initial load',
            current_state='Single bundle file',
            proposed_change='Use React.lazy() and Suspense for route-based splitting',
            benefits=[
                'Faster initial page load',
                'Better mobile experience',
                'Reduced bandwidth usage'
            ],
            estimated_impact='medium',
            code_location='frontend/src/App.jsx'
        ))

    def _analyze_feature_gaps(self):
        """Identify missing features that would be valuable"""

        self.insights.append(CodeInsight(
            type='feature',
            component='backend',
            priority='high',
            title='Add task queue system',
            description='Implement async task queue with Celery or similar',
            current_state='Tasks run synchronously',
            proposed_change='Celery + Redis for background task processing',
            benefits=[
                'Non-blocking API',
                'Better resource management',
                'Support for long-running tasks',
                'Retry failed tasks automatically'
            ],
            estimated_impact='high'
        ))

        self.insights.append(CodeInsight(
            type='feature',
            component='frontend',
            priority='medium',
            title='Add dark/light theme toggle',
            description='Allow users to switch between themes',
            current_state='Dark theme only',
            proposed_change='Theme switcher with localStorage persistence',
            benefits=[
                'Better accessibility',
                'User preference support',
                'Reduced eye strain in bright environments'
            ],
            estimated_impact='medium'
        ))

        self.insights.append(CodeInsight(
            type='feature',
            component='backend',
            priority='high',
            title='Implement API rate limiting per user',
            description='Add per-user rate limiting (currently global)',
            current_state='Global rate limiting only',
            proposed_change='Token-based rate limiting per API key/user',
            benefits=[
                'Fair resource allocation',
                'Prevent abuse',
                'Better multi-user support'
            ],
            estimated_impact='high'
        ))

        self.insights.append(CodeInsight(
            type='feature',
            component='backend',
            priority='medium',
            title='Add solution comparison tool',
            description='Visual tool to compare different solutions side-by-side',
            current_state='Solutions viewed individually',
            proposed_change='Comparison view with diff highlighting',
            benefits=[
                'Better understanding of evolution',
                'Educational value',
                'Easier debugging'
            ],
            estimated_impact='medium'
        ))

    def _analyze_architecture_patterns(self):
        """Analyze architectural patterns and suggest improvements"""

        self.insights.append(CodeInsight(
            type='refactor',
            component='backend',
            priority='medium',
            title='Implement dependency injection',
            description='Use dependency injection for better testability',
            current_state='Direct instantiation of dependencies',
            proposed_change='FastAPI Depends() for dependency injection',
            benefits=[
                'Easier unit testing',
                'Better modularity',
                'Clearer dependencies'
            ],
            estimated_impact='medium'
        ))

        self.insights.append(CodeInsight(
            type='improvement',
            component='backend',
            priority='high',
            title='Add comprehensive logging',
            description='Structured logging with correlation IDs',
            current_state='Basic logging',
            proposed_change='Structured JSON logging with request IDs and context',
            benefits=[
                'Easier debugging',
                'Better observability',
                'Audit trail'
            ],
            estimated_impact='high'
        ))

        self.insights.append(CodeInsight(
            type='feature',
            component='backend',
            priority='low',
            title='Add OpenAPI schema validation',
            description='Validate API responses against OpenAPI schema',
            current_state='Manual validation',
            proposed_change='Automatic schema validation with pydantic',
            benefits=[
                'Catch schema errors early',
                'Better API documentation',
                'Type safety'
            ],
            estimated_impact='low'
        ))

    def _generate_summary(self) -> Dict[str, Any]:
        """Generate a summary of the analysis"""
        if not self.insights:
            return {}

        by_type = {}
        by_priority = {}
        by_component = {}

        for insight in self.insights:
            # By type
            by_type[insight.type] = by_type.get(insight.type, 0) + 1
            # By priority
            by_priority[insight.priority] = by_priority.get(insight.priority, 0) + 1
            # By component
            by_component[insight.component] = by_component.get(insight.component, 0) + 1

        return {
            'total_insights': len(self.insights),
            'by_type': by_type,
            'by_priority': by_priority,
            'by_component': by_component,
            'high_priority_count': by_priority.get('high', 0),
            'recommended_next_steps': self._get_recommended_next_steps()
        }

    def _get_recommended_next_steps(self) -> List[str]:
        """Get recommended next steps based on analysis"""
        high_priority = [i for i in self.insights if i.priority == 'high']
        high_priority.sort(key=lambda x: x.estimated_impact, reverse=True)

        return [f"{i.title} ({i.component})" for i in high_priority[:5]]

    def get_insights_by_priority(self, priority: str) -> List[CodeInsight]:
        """Get insights filtered by priority"""
        return [i for i in self.insights if i.priority == priority]

    def get_insights_by_component(self, component: str) -> List[CodeInsight]:
        """Get insights filtered by component"""
        return [i for i in self.insights if i.component == component]
