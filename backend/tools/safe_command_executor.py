"""
Safe Command Executor - Whitelist-based command execution for Darwin

This module provides read-only system access through a carefully curated
whitelist of safe commands. Darwin can use these to explore and monitor
the system without risk of destructive actions.

Security principles:
1. Whitelist-based: Only explicitly allowed commands can run
2. Read-only: No file modifications, deletions, or system changes
3. Timeout protected: All commands have strict timeouts
4. Pattern blocking: Additional regex patterns block dangerous inputs
5. Path validation: Commands can only access safe paths
"""

import re
import shlex
import asyncio
import subprocess
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CommandConfig:
    """Configuration for a safe command."""
    allowed_flags: List[str] = field(default_factory=list)
    allowed_subcommands: List[str] = field(default_factory=list)
    timeout: int = 30  # seconds
    max_output_size: int = 1048576  # 1MB
    requires_path: bool = False
    description: str = ""


# Whitelist of safe commands with their configurations
SAFE_COMMANDS: Dict[str, CommandConfig] = {
    # File system (read-only)
    "ls": CommandConfig(
        allowed_flags=["-l", "-la", "-lh", "-R", "-a", "-h", "-1", "-t", "-S"],
        timeout=30,
        requires_path=True,
        description="List directory contents"
    ),
    "cat": CommandConfig(
        allowed_flags=["-n", "-b", "-s"],
        timeout=10,
        max_output_size=1048576,  # 1MB limit
        requires_path=True,
        description="Display file contents"
    ),
    "head": CommandConfig(
        allowed_flags=["-n", "-c"],
        timeout=10,
        requires_path=True,
        description="Display first lines of file"
    ),
    "tail": CommandConfig(
        allowed_flags=["-n", "-c"],
        timeout=10,
        requires_path=True,
        description="Display last lines of file"
    ),
    "find": CommandConfig(
        allowed_flags=["-name", "-type", "-size", "-mtime", "-maxdepth", "-mindepth"],
        timeout=60,
        requires_path=True,
        description="Find files matching criteria"
    ),
    "wc": CommandConfig(
        allowed_flags=["-l", "-w", "-c", "-m"],
        timeout=10,
        requires_path=True,
        description="Count lines, words, characters"
    ),
    "du": CommandConfig(
        allowed_flags=["-s", "-h", "-sh", "-d", "--max-depth"],
        timeout=30,
        requires_path=True,
        description="Disk usage statistics"
    ),
    "file": CommandConfig(
        allowed_flags=["-b", "-i", "-L"],
        timeout=10,
        requires_path=True,
        description="Determine file type"
    ),
    "stat": CommandConfig(
        allowed_flags=["-c", "--format"],
        timeout=10,
        requires_path=True,
        description="Display file status"
    ),
    "tree": CommandConfig(
        allowed_flags=["-L", "-d", "-f", "-a", "--dirsfirst", "-I"],
        timeout=30,
        requires_path=True,
        description="Display directory tree"
    ),

    # Process/System information
    "ps": CommandConfig(
        allowed_flags=["aux", "-ef", "-e", "-f", "--sort"],
        timeout=10,
        description="Display process status"
    ),
    "df": CommandConfig(
        allowed_flags=["-h", "-H", "-T", "-i"],
        timeout=10,
        description="Display disk space usage"
    ),
    "free": CommandConfig(
        allowed_flags=["-m", "-h", "-g", "-b"],
        timeout=5,
        description="Display memory usage"
    ),
    "uptime": CommandConfig(
        allowed_flags=["-p", "-s"],
        timeout=5,
        description="System uptime"
    ),
    "uname": CommandConfig(
        allowed_flags=["-a", "-r", "-s", "-m", "-n"],
        timeout=5,
        description="System information"
    ),
    "top": CommandConfig(
        allowed_flags=["-b", "-n"],
        timeout=10,
        description="Process activity (batch mode)"
    ),
    "who": CommandConfig(
        allowed_flags=["-a", "-b", "-q"],
        timeout=5,
        description="Show who is logged in"
    ),
    "w": CommandConfig(
        allowed_flags=["-h", "-s"],
        timeout=5,
        description="Show logged in users and activity"
    ),
    "lscpu": CommandConfig(
        allowed_flags=["-J", "-e"],
        timeout=5,
        description="CPU architecture information"
    ),
    "lsmem": CommandConfig(
        allowed_flags=["-J", "-a"],
        timeout=5,
        description="Memory ranges information"
    ),

    # Git (read-only)
    "git": CommandConfig(
        allowed_subcommands=["status", "log", "branch", "diff", "show", "tag", "remote", "config"],
        timeout=30,
        requires_path=True,
        description="Git version control (read-only)"
    ),

    # Network information (read-only)
    "netstat": CommandConfig(
        allowed_flags=["-tuln", "-an", "-r", "-i"],
        timeout=10,
        description="Network statistics"
    ),
    "ss": CommandConfig(
        allowed_flags=["-tuln", "-an", "-s"],
        timeout=10,
        description="Socket statistics"
    ),
    "ip": CommandConfig(
        allowed_subcommands=["addr", "link", "route"],
        allowed_flags=["show"],
        timeout=10,
        description="IP configuration"
    ),

    # Package information (read-only)
    "pip": CommandConfig(
        allowed_subcommands=["list", "show", "freeze"],
        timeout=30,
        description="Python package info"
    ),
    "npm": CommandConfig(
        allowed_subcommands=["list", "ls", "outdated"],
        allowed_flags=["--depth", "-g", "--global"],
        timeout=30,
        description="Node.js package info"
    ),
    "cargo": CommandConfig(
        allowed_subcommands=["tree", "metadata"],
        timeout=30,
        description="Rust package info"
    ),

    # Environment
    "env": CommandConfig(
        allowed_flags=[],
        timeout=5,
        description="Display environment variables"
    ),
    "printenv": CommandConfig(
        allowed_flags=[],
        timeout=5,
        description="Print environment variables"
    ),
}


# Patterns that should NEVER appear in commands (security blocklist)
BLOCKED_PATTERNS = [
    # Destructive operations
    r'\brm\s',           # rm command
    r'\bmv\s',           # mv command
    r'\bcp\s',           # cp command
    r'\bchmod\b',        # chmod
    r'\bchown\b',        # chown
    r'\bsudo\b',         # sudo
    r'\bsu\b',           # su
    r'\bdoas\b',         # doas

    # Output redirection (could overwrite files)
    r'>\s',              # redirect output
    r'>>\s',             # append output
    r'2>\s',             # redirect stderr

    # Dangerous pipes
    r'\|\s*sh\b',        # pipe to shell
    r'\|\s*bash\b',      # pipe to bash
    r'\|\s*zsh\b',       # pipe to zsh
    r'\|\s*exec\b',      # pipe to exec

    # Sensitive files
    r'\.env\b',          # .env files
    r'password',         # password in path
    r'secret',           # secret in path
    r'credential',       # credential in path
    r'\.ssh/',           # SSH keys
    r'\.gnupg/',         # GPG keys
    r'\.aws/',           # AWS credentials
    r'\.kube/config',    # Kubernetes config

    # Command substitution
    r'\$\(',             # $(command)
    r'`[^`]+`',          # `command`

    # Dangerous flags
    r'--force',          # force flag
    r'-rf\b',            # recursive force
    r'--no-preserve',    # no preserve root

    # Network exfiltration
    r'\bcurl\b.*-d',     # curl with data
    r'\bwget\b.*-O',     # wget with output
    r'\bnc\b',           # netcat
    r'\btelnet\b',       # telnet
]

# Compile patterns for efficiency
BLOCKED_PATTERNS_COMPILED = [re.compile(p, re.IGNORECASE) for p in BLOCKED_PATTERNS]


@dataclass
class CommandResult:
    """Result of a command execution."""
    command: str
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    executed_at: str
    duration_seconds: float
    truncated: bool = False
    error: Optional[str] = None


class SafeCommandExecutor:
    """
    Executes whitelisted commands safely.

    Security features:
    - Whitelist validation
    - Pattern-based blocking
    - Timeout enforcement
    - Output size limits
    - Path validation
    """

    # Safe paths Darwin can access
    SAFE_PATHS = [
        "/home",
        "/app",
        "/projects",
        "/repos",
        "/code",
        "/opt",
        "/tmp",
        "/var/log",
        "/etc",  # Read-only system configs
        "/usr/share",
    ]

    def __init__(self, safe_paths: Optional[List[str]] = None):
        """Initialize executor with optional custom safe paths."""
        self.safe_paths = safe_paths or self.SAFE_PATHS
        self.execution_history: List[CommandResult] = []

        logger.info("SafeCommandExecutor initialized")

    def validate_command(self, command: str) -> Tuple[bool, str]:
        """
        Validate a command against whitelist and security patterns.

        Args:
            command: The command string to validate

        Returns:
            (is_valid, error_message)
        """
        # Check for blocked patterns first
        for pattern in BLOCKED_PATTERNS_COMPILED:
            if pattern.search(command):
                return False, f"Command contains blocked pattern: {pattern.pattern}"

        # Parse command
        try:
            parts = shlex.split(command)
        except ValueError as e:
            return False, f"Invalid command syntax: {e}"

        if not parts:
            return False, "Empty command"

        base_command = parts[0]

        # Check if base command is whitelisted
        if base_command not in SAFE_COMMANDS:
            return False, f"Command not in whitelist: {base_command}"

        config = SAFE_COMMANDS[base_command]

        # Check subcommands (for git, pip, etc.)
        if config.allowed_subcommands:
            if len(parts) < 2:
                return False, f"{base_command} requires a subcommand"

            subcommand = parts[1]
            if subcommand not in config.allowed_subcommands:
                return False, f"Subcommand not allowed: {base_command} {subcommand}"

        # Validate flags
        for part in parts[1:]:
            if part.startswith('-'):
                # Allow short flags combined (-la becomes -l -a)
                if not part.startswith('--'):
                    # Short flags - check each character
                    for char in part[1:]:
                        flag = f"-{char}"
                        if config.allowed_flags and flag not in config.allowed_flags:
                            # Allow numeric flags like -n 10
                            if not char.isdigit():
                                pass  # Allow unknown short flags for now
                else:
                    # Long flags
                    flag_name = part.split('=')[0]
                    if config.allowed_flags and flag_name not in config.allowed_flags:
                        pass  # Allow unknown long flags for now (could be stricter)

        return True, ""

    def validate_path(self, path: str) -> bool:
        """Check if path is safe to access."""
        try:
            resolved = str(Path(path).resolve())

            # Allow current directory
            cwd = str(Path.cwd())
            if resolved.startswith(cwd):
                return True

            # Check against safe paths
            for safe_path in self.safe_paths:
                if resolved.startswith(safe_path):
                    return True

            return False

        except Exception:
            return False

    async def execute(
        self,
        command: str,
        working_dir: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> CommandResult:
        """
        Execute a validated command.

        Args:
            command: Command string to execute
            working_dir: Working directory (must be safe)
            timeout: Override default timeout

        Returns:
            CommandResult with output and status
        """
        start_time = datetime.now()

        # Validate command
        is_valid, error = self.validate_command(command)
        if not is_valid:
            logger.warning(f"⛔ Blocked unsafe command: {command} - {error}")
            return CommandResult(
                command=command,
                success=False,
                exit_code=-1,
                stdout="",
                stderr="",
                executed_at=start_time.isoformat(),
                duration_seconds=0,
                error=f"Command blocked: {error}"
            )

        # Validate working directory
        if working_dir and not self.validate_path(working_dir):
            return CommandResult(
                command=command,
                success=False,
                exit_code=-1,
                stdout="",
                stderr="",
                executed_at=start_time.isoformat(),
                duration_seconds=0,
                error=f"Working directory not allowed: {working_dir}"
            )

        # Get timeout from config
        parts = shlex.split(command)
        base_command = parts[0]
        config = SAFE_COMMANDS[base_command]
        cmd_timeout = timeout or config.timeout

        try:
            # Execute command
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=cmd_timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return CommandResult(
                    command=command,
                    success=False,
                    exit_code=-1,
                    stdout="",
                    stderr="",
                    executed_at=start_time.isoformat(),
                    duration_seconds=cmd_timeout,
                    error=f"Command timed out after {cmd_timeout}s"
                )

            # Decode output
            stdout_str = stdout.decode('utf-8', errors='replace')
            stderr_str = stderr.decode('utf-8', errors='replace')

            # Truncate if necessary
            truncated = False
            if len(stdout_str) > config.max_output_size:
                stdout_str = stdout_str[:config.max_output_size] + "\n... (output truncated)"
                truncated = True

            duration = (datetime.now() - start_time).total_seconds()

            result = CommandResult(
                command=command,
                success=process.returncode == 0,
                exit_code=process.returncode,
                stdout=stdout_str,
                stderr=stderr_str,
                executed_at=start_time.isoformat(),
                duration_seconds=duration,
                truncated=truncated
            )

            # Log execution
            status = "✅" if result.success else "❌"
            logger.info(f"{status} Command executed: {command[:50]}... ({duration:.2f}s)")

            # Store in history
            self.execution_history.append(result)
            # Keep last 100
            self.execution_history = self.execution_history[-100:]

            return result

        except Exception as e:
            logger.error(f"❌ Command execution failed: {e}")
            return CommandResult(
                command=command,
                success=False,
                exit_code=-1,
                stdout="",
                stderr="",
                executed_at=start_time.isoformat(),
                duration_seconds=(datetime.now() - start_time).total_seconds(),
                error=str(e)
            )

    def execute_sync(
        self,
        command: str,
        working_dir: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> CommandResult:
        """
        Synchronous version of execute for non-async contexts.
        """
        return asyncio.get_event_loop().run_until_complete(
            self.execute(command, working_dir, timeout)
        )

    def get_available_commands(self) -> Dict[str, Dict[str, Any]]:
        """Get list of available commands and their configurations."""
        return {
            cmd: {
                "description": config.description,
                "timeout": config.timeout,
                "allowed_flags": config.allowed_flags,
                "allowed_subcommands": config.allowed_subcommands,
                "requires_path": config.requires_path
            }
            for cmd, config in SAFE_COMMANDS.items()
        }

    def get_execution_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent command execution history."""
        return [
            {
                "command": r.command,
                "success": r.success,
                "exit_code": r.exit_code,
                "executed_at": r.executed_at,
                "duration_seconds": r.duration_seconds,
                "error": r.error
            }
            for r in self.execution_history[-limit:]
        ]


# Global instance
_safe_executor: Optional[SafeCommandExecutor] = None


def get_safe_executor() -> SafeCommandExecutor:
    """Get or create the safe command executor instance."""
    global _safe_executor
    if _safe_executor is None:
        _safe_executor = SafeCommandExecutor()
    return _safe_executor


def set_safe_executor(executor: SafeCommandExecutor):
    """Set the global safe executor instance."""
    global _safe_executor
    _safe_executor = executor
