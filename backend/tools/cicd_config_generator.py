"""
CI/CD Configuration Generator Tool

This module provides functionality to generate CI/CD pipeline configurations
for various platforms including GitHub Actions, GitLab CI, and Jenkins.
It supports multiple languages, testing frameworks, and deployment targets.
"""

import json
import os
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum


class CICDPlatform(Enum):
    """Supported CI/CD platforms."""
    GITHUB_ACTIONS = "github_actions"
    GITLAB_CI = "gitlab_ci"
    JENKINS = "jenkins"
    CIRCLE_CI = "circle_ci"


class Language(Enum):
    """Supported programming languages."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    GO = "go"
    RUST = "rust"


@dataclass
class CICDConfig:
    """Configuration for CI/CD pipeline generation."""
    platform: CICDPlatform
    language: Language
    python_version: str = "3.9"
    node_version: str = "18"
    java_version: str = "11"
    go_version: str = "1.20"
    rust_version: str = "stable"
    test_command: Optional[str] = None
    build_command: Optional[str] = None
    lint_command: Optional[str] = None
    install_command: Optional[str] = None
    branches: List[str] = field(default_factory=lambda: ["main", "develop"])
    enable_caching: bool = True
    enable_linting: bool = True
    enable_testing: bool = True
    enable_coverage: bool = True
    enable_security_scan: bool = False
    deploy_enabled: bool = False
    deploy_target: Optional[str] = None
    environment_variables: Dict[str, str] = field(default_factory=dict)
    matrix_builds: bool = False
    matrix_versions: List[str] = field(default_factory=list)


class CICDConfigGenerator:
    """
    Generator for CI/CD pipeline configurations across multiple platforms.
    
    This class provides methods to generate configuration files for various
    CI/CD platforms with support for multiple programming languages and
    deployment scenarios.
    """
    
    def __init__(self):
        """Initialize the CI/CD configuration generator."""
        self.templates = self._initialize_templates()
    
    def _initialize_templates(self) -> Dict[str, Dict[str, Any]]:
        """
        Initialize configuration templates for different platforms.
        
        Returns:
            Dictionary containing templates for each platform
        """
        return {
            "github_actions": {
                "python": self._get_github_python_template,
                "javascript": self._get_github_javascript_template,
                "typescript": self._get_github_typescript_template,
                "java": self._get_github_java_template,
                "go": self._get_github_go_template,
                "rust": self._get_github_rust_template,
            },
            "gitlab_ci": {
                "python": self._get_gitlab_python_template,
                "javascript": self._get_gitlab_javascript_template,
                "typescript": self._get_gitlab_typescript_template,
                "java": self._get_gitlab_java_template,
                "go": self._get_gitlab_go_template,
                "rust": self._get_gitlab_rust_template,
            },
            "jenkins": {
                "python": self._get_jenkins_python_template,
                "javascript": self._get_jenkins_javascript_template,
                "typescript": self._get_jenkins_typescript_template,
                "java": self._get_jenkins_java_template,
                "go": self._get_jenkins_go_template,
                "rust": self._get_jenkins_rust_template,
            },
            "circle_ci": {
                "python": self._get_circleci_python_template,
                "javascript": self._get_circleci_javascript_template,
            }
        }
    
    def generate_config(self, config: CICDConfig) -> str:
        """
        Generate CI/CD configuration based on provided settings.
        
        Args:
            config: CICDConfig object containing pipeline settings
            
        Returns:
            Generated configuration as a string
            
        Raises:
            ValueError: If platform or language is not supported
        """
        try:
            platform_key = config.platform.value
            language_key = config.language.value
            
            if platform_key not in self.templates:
                raise ValueError(f"Unsupported platform: {config.platform}")
            
            if language_key not in self.templates[platform_key]:
                raise ValueError(
                    f"Language {config.language} not supported for {config.platform}"
                )
            
            template_func = self.templates[platform_key][language_key]
            return template_func(config)
        
        except Exception as e:
            raise RuntimeError(f"Failed to generate CI/CD config: {str(e)}") from e
    
    def _get_github_python_template(self, config: CICDConfig) -> str:
        """Generate GitHub Actions configuration for Python projects."""
        branches_str = json.dumps(config.branches)
        
        matrix_section = ""
        if config.matrix_builds and config.matrix_versions:
            versions_str = json.dumps(config.matrix_versions)
            matrix_section = f"""
    strategy:
      matrix:
        python-version: {versions_str}"""
            python_version = "${{ matrix.python-version }}"
        else:
            python_version = config.python_version
        
        install_cmd = config.install_command or "pip install -r requirements.txt"
        test_cmd = config.test_command or "pytest"
        lint_cmd = config.lint_command or "flake8 . && black --check ."
        
        lint_step = ""
        if config.enable_linting:
            lint_step = f"""
      - name: Lint code
        run: |
          pip install flake8 black
          {lint_cmd}
"""
        
        coverage_step = ""
        if config.enable_coverage:
            coverage_step = """
      - name: Generate coverage report
        run: |
          pip install pytest-cov
          pytest --cov=. --cov-report=xml
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
"""
        
        security_step = ""
        if config.enable_security_scan:
            security_step = """
      - name: Security scan
        run: |
          pip install safety bandit
          safety check
          bandit -r . -f json -o bandit-report.json
"""
        
        cache_step = ""
        if config.enable_caching:
            cache_step = """
      - name: Cache dependencies
        uses: actions/cache@v3
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
          restore-keys: |
            ${{ runner.os }}-pip-
"""
        
        deploy_job = ""
        if config.deploy_enabled and config.deploy_target:
            deploy_job = f"""
  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v3
      
      - name: Deploy to {config.deploy_target}
        run: |
          echo "Deploying to {config.deploy_target}"
          # Add deployment commands here
"""
        
        env_section = ""
        if config.environment_variables:
            env_lines = [f"  {k}: {v}" for k, v in config.environment_variables.items()]
            env_section = "env:\n" + "\n".join(env_lines) + "\n"
        
        return f