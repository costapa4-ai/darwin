"""
System Analyzer - Parse command outputs and detect anomalies

This module helps Darwin understand system state by:
- Parsing command outputs into structured data
- Detecting anomalies and issues
- Generating insights from system information
- Identifying trends and patterns
"""

import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SystemHealth:
    """Overall system health assessment."""
    cpu_status: str  # healthy, warning, critical
    memory_status: str
    disk_status: str
    overall: str
    issues: List[str]
    recommendations: List[str]


@dataclass
class Anomaly:
    """Detected system anomaly."""
    type: str  # cpu, memory, disk, process, network
    severity: str  # low, medium, high, critical
    description: str
    value: Any
    threshold: Any
    timestamp: str


class SystemAnalyzer:
    """
    Analyzes system data and detects anomalies.

    Provides structured parsing of common command outputs
    and intelligent anomaly detection.
    """

    # Thresholds for anomaly detection
    THRESHOLDS = {
        "cpu_warning": 70,
        "cpu_critical": 90,
        "memory_warning": 80,
        "memory_critical": 95,
        "disk_warning": 80,
        "disk_critical": 95,
        "load_warning": 2.0,  # per CPU core
        "load_critical": 4.0,
    }

    def __init__(self):
        self.detected_anomalies: List[Anomaly] = []
        self.health_history: List[SystemHealth] = []

    def analyze_system_status(self, status: Dict[str, Any]) -> SystemHealth:
        """
        Analyze system status and produce health assessment.

        Args:
            status: Output from LocalExplorer.get_system_status()

        Returns:
            SystemHealth assessment
        """
        issues = []
        recommendations = []

        # Analyze CPU
        cpu_percent = status.get("cpu", {}).get("percent", 0)
        if cpu_percent >= self.THRESHOLDS["cpu_critical"]:
            cpu_status = "critical"
            issues.append(f"CPU usage critical: {cpu_percent}%")
            recommendations.append("Investigate high CPU processes with 'ps aux --sort=-%cpu'")
        elif cpu_percent >= self.THRESHOLDS["cpu_warning"]:
            cpu_status = "warning"
            issues.append(f"CPU usage elevated: {cpu_percent}%")
        else:
            cpu_status = "healthy"

        # Analyze Memory
        memory_percent = status.get("memory", {}).get("percent_used", 0)
        if memory_percent >= self.THRESHOLDS["memory_critical"]:
            memory_status = "critical"
            issues.append(f"Memory usage critical: {memory_percent}%")
            recommendations.append("Consider closing unused applications or increasing swap")
        elif memory_percent >= self.THRESHOLDS["memory_warning"]:
            memory_status = "warning"
            issues.append(f"Memory usage elevated: {memory_percent}%")
        else:
            memory_status = "healthy"

        # Analyze Disk
        disk_percent = status.get("disk", {}).get("percent_used", 0)
        if disk_percent >= self.THRESHOLDS["disk_critical"]:
            disk_status = "critical"
            issues.append(f"Disk space critical: {disk_percent}% used")
            recommendations.append("Clean up disk space immediately")
        elif disk_percent >= self.THRESHOLDS["disk_warning"]:
            disk_status = "warning"
            issues.append(f"Disk space low: {disk_percent}% used")
            recommendations.append("Consider cleaning up old files or logs")
        else:
            disk_status = "healthy"

        # Determine overall status
        statuses = [cpu_status, memory_status, disk_status]
        if "critical" in statuses:
            overall = "critical"
        elif "warning" in statuses:
            overall = "warning"
        else:
            overall = "healthy"

        health = SystemHealth(
            cpu_status=cpu_status,
            memory_status=memory_status,
            disk_status=disk_status,
            overall=overall,
            issues=issues,
            recommendations=recommendations
        )

        self.health_history.append(health)
        # Keep last 100
        self.health_history = self.health_history[-100:]

        return health

    def detect_anomalies(self, status: Dict[str, Any]) -> List[Anomaly]:
        """
        Detect anomalies in system status.

        Args:
            status: System status dictionary

        Returns:
            List of detected anomalies
        """
        anomalies = []
        now = datetime.now().isoformat()

        # CPU anomaly
        cpu_percent = status.get("cpu", {}).get("percent", 0)
        if cpu_percent >= self.THRESHOLDS["cpu_critical"]:
            anomalies.append(Anomaly(
                type="cpu",
                severity="critical",
                description=f"CPU usage at {cpu_percent}%",
                value=cpu_percent,
                threshold=self.THRESHOLDS["cpu_critical"],
                timestamp=now
            ))
        elif cpu_percent >= self.THRESHOLDS["cpu_warning"]:
            anomalies.append(Anomaly(
                type="cpu",
                severity="high",
                description=f"Elevated CPU usage at {cpu_percent}%",
                value=cpu_percent,
                threshold=self.THRESHOLDS["cpu_warning"],
                timestamp=now
            ))

        # Memory anomaly
        memory_percent = status.get("memory", {}).get("percent_used", 0)
        if memory_percent >= self.THRESHOLDS["memory_critical"]:
            anomalies.append(Anomaly(
                type="memory",
                severity="critical",
                description=f"Memory usage at {memory_percent}%",
                value=memory_percent,
                threshold=self.THRESHOLDS["memory_critical"],
                timestamp=now
            ))
        elif memory_percent >= self.THRESHOLDS["memory_warning"]:
            anomalies.append(Anomaly(
                type="memory",
                severity="high",
                description=f"Elevated memory usage at {memory_percent}%",
                value=memory_percent,
                threshold=self.THRESHOLDS["memory_warning"],
                timestamp=now
            ))

        # Disk anomaly
        disk_percent = status.get("disk", {}).get("percent_used", 0)
        if disk_percent >= self.THRESHOLDS["disk_critical"]:
            anomalies.append(Anomaly(
                type="disk",
                severity="critical",
                description=f"Disk space at {disk_percent}% used",
                value=disk_percent,
                threshold=self.THRESHOLDS["disk_critical"],
                timestamp=now
            ))
        elif disk_percent >= self.THRESHOLDS["disk_warning"]:
            anomalies.append(Anomaly(
                type="disk",
                severity="high",
                description=f"Low disk space: {disk_percent}% used",
                value=disk_percent,
                threshold=self.THRESHOLDS["disk_warning"],
                timestamp=now
            ))

        self.detected_anomalies.extend(anomalies)
        # Keep last 100
        self.detected_anomalies = self.detected_anomalies[-100:]

        return anomalies

    def parse_ps_output(self, output: str) -> List[Dict[str, Any]]:
        """
        Parse 'ps aux' output into structured data.

        Args:
            output: Raw ps aux output

        Returns:
            List of process dictionaries
        """
        processes = []
        lines = output.strip().split('\n')

        if len(lines) < 2:
            return processes

        # Skip header line
        for line in lines[1:]:
            parts = line.split(None, 10)  # Split into max 11 parts
            if len(parts) >= 11:
                processes.append({
                    "user": parts[0],
                    "pid": int(parts[1]) if parts[1].isdigit() else parts[1],
                    "cpu_percent": float(parts[2]) if parts[2].replace('.', '').isdigit() else 0,
                    "mem_percent": float(parts[3]) if parts[3].replace('.', '').isdigit() else 0,
                    "vsz": parts[4],
                    "rss": parts[5],
                    "tty": parts[6],
                    "stat": parts[7],
                    "start": parts[8],
                    "time": parts[9],
                    "command": parts[10] if len(parts) > 10 else ""
                })

        return processes

    def find_resource_hogs(
        self,
        processes: List[Dict[str, Any]],
        cpu_threshold: float = 20.0,
        mem_threshold: float = 20.0
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Find processes using excessive resources.

        Args:
            processes: Parsed process list
            cpu_threshold: CPU percentage threshold
            mem_threshold: Memory percentage threshold

        Returns:
            Dictionary with cpu_hogs and memory_hogs lists
        """
        cpu_hogs = [p for p in processes if p.get("cpu_percent", 0) >= cpu_threshold]
        memory_hogs = [p for p in processes if p.get("mem_percent", 0) >= mem_threshold]

        # Sort by usage descending
        cpu_hogs.sort(key=lambda x: x.get("cpu_percent", 0), reverse=True)
        memory_hogs.sort(key=lambda x: x.get("mem_percent", 0), reverse=True)

        return {
            "cpu_hogs": cpu_hogs[:10],
            "memory_hogs": memory_hogs[:10]
        }

    def parse_df_output(self, output: str) -> List[Dict[str, Any]]:
        """
        Parse 'df -h' output into structured data.

        Args:
            output: Raw df -h output

        Returns:
            List of filesystem dictionaries
        """
        filesystems = []
        lines = output.strip().split('\n')

        if len(lines) < 2:
            return filesystems

        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 6:
                # Extract percentage (remove %)
                use_percent = parts[4].rstrip('%')
                filesystems.append({
                    "filesystem": parts[0],
                    "size": parts[1],
                    "used": parts[2],
                    "available": parts[3],
                    "use_percent": int(use_percent) if use_percent.isdigit() else 0,
                    "mounted_on": parts[5]
                })

        return filesystems

    def parse_git_status(self, output: str) -> Dict[str, Any]:
        """
        Parse 'git status --porcelain' output.

        Args:
            output: Raw git status output

        Returns:
            Structured git status
        """
        modified = []
        added = []
        deleted = []
        untracked = []

        for line in output.strip().split('\n'):
            if not line:
                continue

            status = line[:2]
            filename = line[3:]

            if status[0] == 'M' or status[1] == 'M':
                modified.append(filename)
            elif status[0] == 'A':
                added.append(filename)
            elif status[0] == 'D' or status[1] == 'D':
                deleted.append(filename)
            elif status == '??':
                untracked.append(filename)

        return {
            "modified": modified,
            "added": added,
            "deleted": deleted,
            "untracked": untracked,
            "total_changes": len(modified) + len(added) + len(deleted),
            "has_uncommitted": bool(modified or added or deleted),
            "has_untracked": bool(untracked)
        }

    def generate_system_insight(self, status: Dict[str, Any]) -> str:
        """
        Generate a natural language insight about system state.

        Args:
            status: System status dictionary

        Returns:
            Human-readable insight string
        """
        cpu = status.get("cpu", {}).get("percent", 0)
        memory = status.get("memory", {}).get("percent_used", 0)
        disk = status.get("disk", {}).get("percent_used", 0)
        processes = status.get("processes", {}).get("total", 0)

        insights = []

        # CPU insight
        if cpu < 20:
            insights.append(f"System is idle with CPU at {cpu}%")
        elif cpu < 50:
            insights.append(f"Moderate CPU usage at {cpu}%")
        elif cpu < 80:
            insights.append(f"CPU is busy at {cpu}%")
        else:
            insights.append(f"⚠️ CPU is under heavy load at {cpu}%")

        # Memory insight
        memory_gb = status.get("memory", {}).get("available_gb", 0)
        if memory < 50:
            insights.append(f"Plenty of memory available ({memory_gb}GB free)")
        elif memory < 80:
            insights.append(f"Memory usage is moderate at {memory}%")
        else:
            insights.append(f"⚠️ Memory is getting tight at {memory}%")

        # Disk insight
        disk_free = status.get("disk", {}).get("free_gb", 0)
        if disk < 50:
            insights.append(f"Disk space looks good ({disk_free}GB free)")
        elif disk < 80:
            insights.append(f"Disk is filling up ({disk}% used)")
        else:
            insights.append(f"⚠️ Disk space is low ({disk_free}GB remaining)")

        # Process insight
        if processes > 0:
            insights.append(f"Running {processes} processes")

        return " | ".join(insights)

    def compare_with_baseline(
        self,
        current: Dict[str, Any],
        baseline: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compare current status with a baseline.

        Args:
            current: Current system status
            baseline: Previous baseline status

        Returns:
            Dictionary of changes and deltas
        """
        changes = {
            "cpu_delta": (
                current.get("cpu", {}).get("percent", 0) -
                baseline.get("cpu", {}).get("percent", 0)
            ),
            "memory_delta": (
                current.get("memory", {}).get("percent_used", 0) -
                baseline.get("memory", {}).get("percent_used", 0)
            ),
            "disk_delta": (
                current.get("disk", {}).get("percent_used", 0) -
                baseline.get("disk", {}).get("percent_used", 0)
            ),
            "significant_changes": []
        }

        if abs(changes["cpu_delta"]) > 20:
            direction = "increased" if changes["cpu_delta"] > 0 else "decreased"
            changes["significant_changes"].append(
                f"CPU usage {direction} by {abs(changes['cpu_delta']):.1f}%"
            )

        if abs(changes["memory_delta"]) > 10:
            direction = "increased" if changes["memory_delta"] > 0 else "decreased"
            changes["significant_changes"].append(
                f"Memory usage {direction} by {abs(changes['memory_delta']):.1f}%"
            )

        if changes["disk_delta"] > 1:
            changes["significant_changes"].append(
                f"Disk usage increased by {changes['disk_delta']:.1f}%"
            )

        return changes

    def analyze_project_health(self, project: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a discovered project's health indicators.

        Args:
            project: Project dictionary from LocalExplorer

        Returns:
            Project health analysis
        """
        analysis = {
            "project_name": project.get("name", "Unknown"),
            "path": project.get("path", ""),
            "type": project.get("primary_type", "unknown"),
            "health_score": 100,
            "issues": [],
            "positive_indicators": []
        }

        stats = project.get("stats", {})

        # Check code file count
        code_files = stats.get("code_files", 0)
        if code_files == 0:
            analysis["issues"].append("No code files found")
            analysis["health_score"] -= 20
        elif code_files > 0:
            analysis["positive_indicators"].append(f"Contains {code_files} code files")

        # Check for tests (if test files are mentioned)
        if "test" in str(project).lower():
            analysis["positive_indicators"].append("Has test files")
            analysis["health_score"] += 10
        else:
            analysis["issues"].append("No tests detected")
            analysis["health_score"] -= 10

        # Check for README
        if project.get("readme_preview"):
            analysis["positive_indicators"].append("Has README documentation")
            analysis["health_score"] += 10
        else:
            analysis["issues"].append("Missing README")
            analysis["health_score"] -= 5

        # Check language diversity
        languages = stats.get("languages", {})
        if len(languages) > 1:
            analysis["positive_indicators"].append(
                f"Multi-language project: {', '.join(languages.keys())}"
            )

        # Normalize score
        analysis["health_score"] = max(0, min(100, analysis["health_score"]))

        return analysis


# Global instance
_system_analyzer: Optional[SystemAnalyzer] = None


def get_system_analyzer() -> SystemAnalyzer:
    """Get or create the system analyzer instance."""
    global _system_analyzer
    if _system_analyzer is None:
        _system_analyzer = SystemAnalyzer()
    return _system_analyzer
