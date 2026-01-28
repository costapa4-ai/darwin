"""
Local Explorer Tool - Darwin's Eyes on the Local System

Allows Darwin to:
- Explore the local file system
- Discover projects and codebases
- Analyze directory structures
- Find interesting code patterns
- Monitor system resources
- Learn from local repositories

This makes Darwin more "alive" by giving it awareness of its environment.
"""

import os
import glob
import json
import psutil
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict

from utils.logger import get_logger

logger = get_logger(__name__)


class LocalExplorer:
    """
    Darwin's local exploration capabilities.

    Gives Darwin the ability to:
    - See what's on the local machine
    - Find interesting projects to learn from
    - Monitor system health
    - Discover patterns in local code
    """

    # Safe directories Darwin can explore
    SAFE_EXPLORE_PATHS = [
        "/home",
        "/app",
        "/projects",
        "/repos",
        "/code",
        "/opt",
        "/var/www",
    ]

    # Directories to skip
    SKIP_DIRS = {
        ".git", "node_modules", "__pycache__", ".venv", "venv",
        ".cache", ".npm", ".local", "dist", "build", ".next",
        "target", "bin", "obj", ".idea", ".vscode"
    }

    # Interesting file patterns
    CODE_PATTERNS = {
        "python": ["*.py"],
        "javascript": ["*.js", "*.jsx", "*.ts", "*.tsx"],
        "go": ["*.go"],
        "rust": ["*.rs"],
        "java": ["*.java"],
        "config": ["*.json", "*.yaml", "*.yml", "*.toml"],
        "docker": ["Dockerfile*", "docker-compose*.yml"],
        "docs": ["*.md", "README*"],
    }

    def __init__(self, base_paths: Optional[List[str]] = None):
        """Initialize explorer with allowed base paths."""
        self.base_paths = base_paths or self.SAFE_EXPLORE_PATHS
        self.discoveries: List[Dict[str, Any]] = []
        self.last_exploration = None

    def explore_directory(
        self,
        path: str,
        max_depth: int = 3,
        max_files: int = 100
    ) -> Dict[str, Any]:
        """
        Explore a directory and report its structure.

        Args:
            path: Directory path to explore
            max_depth: Maximum depth to traverse
            max_files: Maximum files to list

        Returns:
            Directory exploration report
        """
        path = Path(path)

        if not path.exists():
            return {"error": f"Path does not exist: {path}"}

        if not self._is_safe_path(str(path)):
            return {"error": f"Path not allowed for exploration: {path}"}

        report = {
            "path": str(path),
            "explored_at": datetime.now().isoformat(),
            "structure": {},
            "stats": {
                "total_files": 0,
                "total_dirs": 0,
                "by_type": defaultdict(int),
                "largest_files": [],
                "recent_files": [],
            },
            "interesting_finds": []
        }

        files_found = 0

        for root, dirs, files in os.walk(path):
            # Calculate depth
            depth = len(Path(root).relative_to(path).parts)
            if depth > max_depth:
                dirs[:] = []  # Don't go deeper
                continue

            # Skip unwanted directories
            dirs[:] = [d for d in dirs if d not in self.SKIP_DIRS]

            rel_path = str(Path(root).relative_to(path))

            for file in files:
                if files_found >= max_files:
                    break

                file_path = Path(root) / file
                try:
                    stat = file_path.stat()
                    ext = file_path.suffix.lower()

                    report["stats"]["total_files"] += 1
                    report["stats"]["by_type"][ext] += 1

                    # Track largest files
                    report["stats"]["largest_files"].append({
                        "path": str(file_path),
                        "size": stat.st_size
                    })

                    # Track recent files
                    report["stats"]["recent_files"].append({
                        "path": str(file_path),
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })

                    # Look for interesting patterns
                    if file in ["main.py", "app.py", "index.js", "main.go"]:
                        report["interesting_finds"].append({
                            "type": "entry_point",
                            "path": str(file_path)
                        })
                    elif file in ["requirements.txt", "package.json", "go.mod", "Cargo.toml"]:
                        report["interesting_finds"].append({
                            "type": "dependency_file",
                            "path": str(file_path)
                        })
                    elif "test" in file.lower() or "spec" in file.lower():
                        report["interesting_finds"].append({
                            "type": "test_file",
                            "path": str(file_path)
                        })

                    files_found += 1

                except (OSError, PermissionError):
                    continue

            report["stats"]["total_dirs"] += 1

        # Sort and trim stats
        report["stats"]["largest_files"] = sorted(
            report["stats"]["largest_files"],
            key=lambda x: x["size"],
            reverse=True
        )[:10]

        report["stats"]["recent_files"] = sorted(
            report["stats"]["recent_files"],
            key=lambda x: x["modified"],
            reverse=True
        )[:10]

        report["stats"]["by_type"] = dict(report["stats"]["by_type"])

        self.last_exploration = report
        return report

    def discover_projects(self, base_path: str = "/home") -> List[Dict[str, Any]]:
        """
        Discover software projects in a directory.

        Looks for directories containing project indicators like:
        - package.json (Node.js)
        - requirements.txt / pyproject.toml (Python)
        - go.mod (Go)
        - Cargo.toml (Rust)
        - pom.xml (Java)
        - Dockerfile

        Returns:
            List of discovered projects with metadata
        """
        if not self._is_safe_path(base_path):
            return []

        projects = []
        project_indicators = {
            "package.json": "nodejs",
            "requirements.txt": "python",
            "pyproject.toml": "python",
            "setup.py": "python",
            "go.mod": "go",
            "Cargo.toml": "rust",
            "pom.xml": "java",
            "build.gradle": "java",
            "Dockerfile": "docker",
            "docker-compose.yml": "docker-compose",
            "Makefile": "make",
        }

        for root, dirs, files in os.walk(base_path):
            # Skip unwanted directories
            dirs[:] = [d for d in dirs if d not in self.SKIP_DIRS]

            # Check for project indicators
            found_indicators = []
            for indicator, project_type in project_indicators.items():
                if indicator in files:
                    found_indicators.append({
                        "indicator": indicator,
                        "type": project_type
                    })

            if found_indicators:
                project = {
                    "path": root,
                    "name": os.path.basename(root),
                    "indicators": found_indicators,
                    "primary_type": found_indicators[0]["type"],
                    "discovered_at": datetime.now().isoformat()
                }

                # Try to get more info
                project["stats"] = self._get_project_stats(root)

                # Check for README
                readme_files = [f for f in files if f.lower().startswith("readme")]
                if readme_files:
                    readme_path = os.path.join(root, readme_files[0])
                    try:
                        with open(readme_path, 'r', encoding='utf-8', errors='ignore') as f:
                            project["readme_preview"] = f.read(500)
                    except:
                        pass

                projects.append(project)
                self.discoveries.append(project)

        logger.info(f"Discovered {len(projects)} projects in {base_path}")
        return projects

    def _get_project_stats(self, project_path: str) -> Dict[str, Any]:
        """Get statistics for a project directory."""
        stats = {
            "total_files": 0,
            "code_files": 0,
            "total_lines": 0,
            "languages": defaultdict(int)
        }

        code_extensions = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.go': 'go',
            '.rs': 'rust',
            '.java': 'java',
            '.rb': 'ruby',
            '.php': 'php',
            '.c': 'c',
            '.cpp': 'cpp',
            '.h': 'c_header',
        }

        try:
            for root, dirs, files in os.walk(project_path):
                dirs[:] = [d for d in dirs if d not in self.SKIP_DIRS]

                for file in files:
                    stats["total_files"] += 1
                    ext = os.path.splitext(file)[1].lower()

                    if ext in code_extensions:
                        stats["code_files"] += 1
                        stats["languages"][code_extensions[ext]] += 1

                        # Count lines
                        try:
                            file_path = os.path.join(root, file)
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                stats["total_lines"] += sum(1 for _ in f)
                        except:
                            pass

        except (OSError, PermissionError):
            pass

        stats["languages"] = dict(stats["languages"])
        return stats

    def get_system_status(self) -> Dict[str, Any]:
        """
        Get current system resource status.

        Darwin can use this to understand its environment's health.
        """
        try:
            return {
                "timestamp": datetime.now().isoformat(),
                "cpu": {
                    "percent": psutil.cpu_percent(interval=1),
                    "count": psutil.cpu_count(),
                    "freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
                },
                "memory": {
                    "total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                    "available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
                    "percent_used": psutil.virtual_memory().percent
                },
                "disk": {
                    "total_gb": round(psutil.disk_usage('/').total / (1024**3), 2),
                    "free_gb": round(psutil.disk_usage('/').free / (1024**3), 2),
                    "percent_used": psutil.disk_usage('/').percent
                },
                "network": self._get_network_stats(),
                "processes": {
                    "total": len(psutil.pids()),
                    "python_processes": len([p for p in psutil.process_iter(['name'])
                                            if 'python' in p.info['name'].lower()])
                }
            }
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {"error": str(e)}

    def _get_network_stats(self) -> Dict[str, Any]:
        """Get network interface stats."""
        try:
            net_io = psutil.net_io_counters()
            return {
                "bytes_sent_mb": round(net_io.bytes_sent / (1024**2), 2),
                "bytes_recv_mb": round(net_io.bytes_recv / (1024**2), 2),
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv
            }
        except:
            return {}

    def find_code_patterns(
        self,
        path: str,
        pattern: str,
        file_types: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for code patterns in files.

        Args:
            path: Directory to search
            pattern: Text pattern to find
            file_types: List of extensions to search (e.g., ['.py', '.js'])

        Returns:
            List of matches with context
        """
        if not self._is_safe_path(path):
            return []

        file_types = file_types or ['.py', '.js', '.ts', '.go', '.rs']
        matches = []

        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if d not in self.SKIP_DIRS]

            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext not in file_types:
                    continue

                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()

                    for i, line in enumerate(lines):
                        if pattern.lower() in line.lower():
                            # Get context (2 lines before/after)
                            start = max(0, i - 2)
                            end = min(len(lines), i + 3)
                            context = ''.join(lines[start:end])

                            matches.append({
                                "file": file_path,
                                "line_number": i + 1,
                                "line": line.strip(),
                                "context": context
                            })

                            if len(matches) >= 50:  # Limit results
                                return matches

                except (OSError, PermissionError):
                    continue

        return matches

    def get_git_repos(self, base_path: str = "/home") -> List[Dict[str, Any]]:
        """
        Find git repositories and get their status.
        """
        if not self._is_safe_path(base_path):
            return []

        repos = []

        for root, dirs, files in os.walk(base_path):
            if '.git' in dirs:
                repo_info = {
                    "path": root,
                    "name": os.path.basename(root)
                }

                try:
                    # Get current branch
                    result = subprocess.run(
                        ['git', 'branch', '--show-current'],
                        cwd=root,
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    repo_info["branch"] = result.stdout.strip()

                    # Get recent commits
                    result = subprocess.run(
                        ['git', 'log', '--oneline', '-5'],
                        cwd=root,
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    repo_info["recent_commits"] = result.stdout.strip().split('\n')

                    # Get status
                    result = subprocess.run(
                        ['git', 'status', '--porcelain'],
                        cwd=root,
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    changes = result.stdout.strip().split('\n') if result.stdout.strip() else []
                    repo_info["uncommitted_changes"] = len(changes)

                except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
                    repo_info["error"] = str(e)

                repos.append(repo_info)
                dirs.remove('.git')  # Don't descend into .git

        return repos

    def analyze_codebase(self, path: str) -> Dict[str, Any]:
        """
        Perform a comprehensive analysis of a codebase.

        This is useful for Darwin to understand a project before
        suggesting improvements.
        """
        if not self._is_safe_path(path):
            return {"error": "Path not allowed"}

        analysis = {
            "path": path,
            "analyzed_at": datetime.now().isoformat(),
            "structure": self.explore_directory(path),
            "languages": {},
            "patterns": {
                "has_tests": False,
                "has_ci": False,
                "has_docker": False,
                "has_docs": False,
            },
            "complexity_indicators": [],
            "suggestions": []
        }

        # Check for common patterns
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if d not in self.SKIP_DIRS]

            files_lower = [f.lower() for f in files]

            # Check patterns
            if any('test' in f for f in files_lower):
                analysis["patterns"]["has_tests"] = True
            if '.github' in dirs or '.gitlab-ci.yml' in files:
                analysis["patterns"]["has_ci"] = True
            if 'dockerfile' in files_lower or 'docker-compose' in ''.join(files_lower):
                analysis["patterns"]["has_docker"] = True
            if 'readme.md' in files_lower or 'docs' in dirs:
                analysis["patterns"]["has_docs"] = True

        # Generate suggestions
        if not analysis["patterns"]["has_tests"]:
            analysis["suggestions"].append("Consider adding tests for better code quality")
        if not analysis["patterns"]["has_ci"]:
            analysis["suggestions"].append("Consider adding CI/CD pipeline")
        if not analysis["patterns"]["has_docker"]:
            analysis["suggestions"].append("Consider containerizing the application")
        if not analysis["patterns"]["has_docs"]:
            analysis["suggestions"].append("Consider adding documentation")

        return analysis

    def _is_safe_path(self, path: str) -> bool:
        """Check if path is safe to explore."""
        path = os.path.abspath(path)

        # Allow current directory and subdirectories
        cwd = os.getcwd()
        if path.startswith(cwd):
            return True

        # Check against allowed base paths
        for base in self.base_paths:
            if path.startswith(base):
                return True

        return False

    def get_exploration_summary(self) -> Dict[str, Any]:
        """Get summary of all explorations and discoveries."""
        return {
            "total_discoveries": len(self.discoveries),
            "last_exploration": self.last_exploration,
            "discoveries_by_type": self._group_discoveries_by_type()
        }

    def _group_discoveries_by_type(self) -> Dict[str, int]:
        """Group discoveries by project type."""
        by_type = defaultdict(int)
        for d in self.discoveries:
            by_type[d.get("primary_type", "unknown")] += 1
        return dict(by_type)


# Tool metadata for Darwin's tool registry
TOOL_METADATA = {
    "name": "local_explorer",
    "description": "Explore local file system, discover projects, analyze codebases",
    "category": "EXPLORATION",
    "mode": "BOTH",  # Available in wake and sleep
    "capabilities": [
        "explore_directory",
        "discover_projects",
        "get_system_status",
        "find_code_patterns",
        "get_git_repos",
        "analyze_codebase"
    ]
}


# Convenience function for Darwin to use
async def explore_environment() -> Dict[str, Any]:
    """
    High-level function for Darwin to explore its environment.

    Returns a comprehensive view of the local system.
    """
    explorer = LocalExplorer()

    return {
        "system_status": explorer.get_system_status(),
        "discovered_projects": explorer.discover_projects("/home"),
        "git_repos": explorer.get_git_repos("/home"),
        "exploration_summary": explorer.get_exploration_summary()
    }
