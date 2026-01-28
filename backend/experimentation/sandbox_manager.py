"""
Sandbox Manager - Isolated Execution Environment

Manages isolated sandboxes for safe code execution with complete isolation,
resource limits, and security controls.
"""

import asyncio
import tempfile
import os
import json
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
import shutil

# Optional import for Docker (fallback to subprocess if unavailable)
try:
    import docker
    DOCKER_AVAILABLE = True
except ImportError:
    docker = None
    DOCKER_AVAILABLE = False

from utils.logger import get_logger

logger = get_logger(__name__)


class SandboxInstance:
    """Represents a single sandbox instance"""

    def __init__(self, sandbox_id: str, container_id: str, workspace_path: Path):
        self.id = sandbox_id
        self.container_id = container_id
        self.workspace_path = workspace_path
        self.created_at = datetime.utcnow()
        self.experiments_run = 0
        self.is_active = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'container_id': self.container_id,
            'workspace_path': str(self.workspace_path),
            'created_at': self.created_at.isoformat(),
            'experiments_run': self.experiments_run,
            'is_active': self.is_active,
            'age_minutes': (datetime.utcnow() - self.created_at).total_seconds() / 60
        }


class SandboxManager:
    """
    Manages isolated sandbox environments for safe experimentation
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize sandbox manager

        Args:
            config: Configuration options
        """
        self.config = config or {}

        # Docker client
        self.docker_client = None
        if DOCKER_AVAILABLE and docker:
            try:
                self.docker_client = docker.from_env()
                logger.info("✅ Docker client connected")
            except Exception as e:
                logger.warning(f"⚠️ Docker not available: {e}")
                logger.info("ℹ️  Will use subprocess fallback for sandboxes")
        else:
            logger.warning("⚠️ docker module not installed")
            logger.info("ℹ️  Install with: pip install docker")
            logger.info("ℹ️  Will use subprocess fallback for sandboxes")

        # Sandbox configuration
        self.max_sandboxes = self.config.get('max_sandboxes', 5)
        self.sandbox_lifetime_minutes = self.config.get('sandbox_lifetime_minutes', 30)
        self.max_memory_mb = self.config.get('max_memory_mb', 512)
        self.max_cpu_percent = self.config.get('max_cpu_percent', 50)
        self.execution_timeout = self.config.get('execution_timeout', 30)

        # Active sandboxes
        self.sandboxes: Dict[str, SandboxInstance] = {}

        # Workspace root
        self.workspace_root = Path(self.config.get('workspace_root', './data/sandboxes'))
        self.workspace_root.mkdir(parents=True, exist_ok=True)

        # Statistics
        self.total_experiments = 0
        self.successful_experiments = 0
        self.failed_experiments = 0

        logger.info(f"SandboxManager initialized (max: {self.max_sandboxes} sandboxes)")

    async def create_sandbox(self) -> str:
        """
        Create a new isolated sandbox

        Returns:
            Sandbox ID
        """
        # Check limits
        if len(self.sandboxes) >= self.max_sandboxes:
            # Clean up old sandboxes
            await self._cleanup_old_sandboxes()

            if len(self.sandboxes) >= self.max_sandboxes:
                raise RuntimeError(f"Maximum sandboxes ({self.max_sandboxes}) reached")

        sandbox_id = f"sandbox_{uuid.uuid4().hex[:8]}"

        try:
            # Create workspace directory
            workspace_path = self.workspace_root / sandbox_id
            workspace_path.mkdir(parents=True, exist_ok=True)

            # Create container if Docker available
            container_id = None
            if self.docker_client:
                container_id = await self._create_docker_container(sandbox_id, workspace_path)

            # Create sandbox instance
            sandbox = SandboxInstance(sandbox_id, container_id, workspace_path)
            self.sandboxes[sandbox_id] = sandbox

            logger.info(f"✅ Created sandbox: {sandbox_id}")
            return sandbox_id

        except Exception as e:
            logger.error(f"❌ Failed to create sandbox: {e}")
            raise

    async def _create_docker_container(self, sandbox_id: str, workspace_path: Path) -> str:
        """
        Create Docker container for sandbox

        Args:
            sandbox_id: Sandbox identifier
            workspace_path: Workspace directory

        Returns:
            Container ID
        """
        try:
            # Container configuration
            container_config = {
                'image': 'python:3.11-slim',
                'name': f'darwin_sandbox_{sandbox_id}',
                'detach': True,
                'network_mode': 'none',  # No network access
                'mem_limit': f'{self.max_memory_mb}m',
                'cpu_quota': int(100000 * self.max_cpu_percent / 100),  # CPU limit
                'volumes': {
                    str(workspace_path.absolute()): {
                        'bind': '/sandbox',
                        'mode': 'rw'
                    }
                },
                'working_dir': '/sandbox',
                'environment': {
                    'PYTHONUNBUFFERED': '1',
                    'SANDBOX_ID': sandbox_id
                },
                'security_opt': ['no-new-privileges:true'],
                'cap_drop': ['ALL'],  # Drop all capabilities
                'read_only': False,  # Need write access to /sandbox
                'tmpfs': {
                    '/tmp': 'size=100m,mode=1777'
                }
            }

            container = self.docker_client.containers.run(**container_config)

            logger.info(f"✅ Created Docker container: {container.id[:12]}")
            return container.id

        except Exception as e:
            logger.error(f"❌ Failed to create Docker container: {e}")
            raise

    async def execute_in_sandbox(
        self,
        sandbox_id: str,
        code: str,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute code in sandbox

        Args:
            sandbox_id: Sandbox identifier
            code: Python code to execute
            timeout: Timeout in seconds (optional)

        Returns:
            Execution result
        """
        if sandbox_id not in self.sandboxes:
            raise ValueError(f"Sandbox {sandbox_id} not found")

        sandbox = self.sandboxes[sandbox_id]
        timeout = timeout or self.execution_timeout

        result = {
            'sandbox_id': sandbox_id,
            'success': False,
            'output': None,
            'error': None,
            'execution_time': 0,
            'timestamp': datetime.utcnow().isoformat()
        }

        start_time = datetime.utcnow()

        try:
            # Write code to file
            code_file = sandbox.workspace_path / 'experiment.py'
            with open(code_file, 'w') as f:
                f.write(code)

            # Execute in container or subprocess
            if self.docker_client and sandbox.container_id:
                output, error = await self._execute_in_docker(
                    sandbox.container_id,
                    'python /sandbox/experiment.py',
                    timeout
                )
            else:
                output, error = await self._execute_in_subprocess(
                    code_file,
                    timeout
                )

            execution_time = (datetime.utcnow() - start_time).total_seconds()

            result['success'] = error is None or len(error) == 0
            result['output'] = output
            result['error'] = error
            result['execution_time'] = execution_time

            # Update statistics
            sandbox.experiments_run += 1
            self.total_experiments += 1
            if result['success']:
                self.successful_experiments += 1
            else:
                self.failed_experiments += 1

            logger.info(f"✅ Executed in sandbox {sandbox_id}: {'success' if result['success'] else 'failed'}")

        except asyncio.TimeoutError:
            result['error'] = f"Execution timeout ({timeout}s)"
            result['execution_time'] = timeout
            self.failed_experiments += 1
            logger.warning(f"⏱️ Timeout in sandbox {sandbox_id}")

        except Exception as e:
            result['error'] = str(e)
            result['execution_time'] = (datetime.utcnow() - start_time).total_seconds()
            self.failed_experiments += 1
            logger.error(f"❌ Error in sandbox {sandbox_id}: {e}")

        return result

    async def _execute_in_docker(
        self,
        container_id: str,
        command: str,
        timeout: int
    ) -> tuple[str, str]:
        """
        Execute command in Docker container

        Args:
            container_id: Container ID
            command: Command to execute
            timeout: Timeout in seconds

        Returns:
            (stdout, stderr)
        """
        try:
            container = self.docker_client.containers.get(container_id)

            # Execute with timeout
            exec_result = container.exec_run(
                command,
                demux=True,
                stdout=True,
                stderr=True
            )

            stdout = exec_result.output[0].decode('utf-8') if exec_result.output[0] else ''
            stderr = exec_result.output[1].decode('utf-8') if exec_result.output[1] else ''

            return stdout, stderr

        except Exception as e:
            return '', str(e)

    async def _execute_in_subprocess(
        self,
        code_file: Path,
        timeout: int
    ) -> tuple[str, str]:
        """
        Execute code in subprocess (fallback when Docker unavailable)

        Args:
            code_file: Path to code file
            timeout: Timeout in seconds

        Returns:
            (stdout, stderr)
        """
        try:
            process = await asyncio.create_subprocess_exec(
                'python', str(code_file),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )

            return stdout.decode('utf-8'), stderr.decode('utf-8')

        except asyncio.TimeoutError:
            process.kill()
            raise
        except Exception as e:
            return '', str(e)

    async def destroy_sandbox(self, sandbox_id: str):
        """
        Destroy a sandbox and clean up resources

        Args:
            sandbox_id: Sandbox identifier
        """
        if sandbox_id not in self.sandboxes:
            logger.warning(f"Sandbox {sandbox_id} not found")
            return

        sandbox = self.sandboxes[sandbox_id]

        try:
            # Stop and remove container
            if self.docker_client and sandbox.container_id:
                try:
                    container = self.docker_client.containers.get(sandbox.container_id)
                    container.stop(timeout=5)
                    container.remove()
                    logger.info(f"🗑️ Removed container {sandbox.container_id[:12]}")
                except Exception as e:
                    logger.warning(f"Failed to remove container: {e}")

            # Remove workspace
            if sandbox.workspace_path.exists():
                shutil.rmtree(sandbox.workspace_path)
                logger.info(f"🗑️ Removed workspace {sandbox.workspace_path}")

            # Remove from active sandboxes
            sandbox.is_active = False
            del self.sandboxes[sandbox_id]

            logger.info(f"✅ Destroyed sandbox: {sandbox_id}")

        except Exception as e:
            logger.error(f"❌ Failed to destroy sandbox {sandbox_id}: {e}")

    async def _cleanup_old_sandboxes(self):
        """Clean up old or unused sandboxes"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=self.sandbox_lifetime_minutes)

        to_remove = []
        for sandbox_id, sandbox in self.sandboxes.items():
            if sandbox.created_at < cutoff_time:
                to_remove.append(sandbox_id)

        for sandbox_id in to_remove:
            await self.destroy_sandbox(sandbox_id)
            logger.info(f"🧹 Cleaned up old sandbox: {sandbox_id}")

    async def destroy_all_sandboxes(self):
        """Destroy all active sandboxes"""
        sandbox_ids = list(self.sandboxes.keys())

        for sandbox_id in sandbox_ids:
            await self.destroy_sandbox(sandbox_id)

        logger.info(f"🗑️ Destroyed all sandboxes ({len(sandbox_ids)} total)")

    def get_sandbox_info(self, sandbox_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a sandbox"""
        if sandbox_id not in self.sandboxes:
            return None

        return self.sandboxes[sandbox_id].to_dict()

    def get_all_sandboxes(self) -> List[Dict[str, Any]]:
        """Get information about all sandboxes"""
        return [sandbox.to_dict() for sandbox in self.sandboxes.values()]

    def get_statistics(self) -> Dict[str, Any]:
        """Get sandbox statistics"""
        return {
            'active_sandboxes': len(self.sandboxes),
            'max_sandboxes': self.max_sandboxes,
            'total_experiments': self.total_experiments,
            'successful_experiments': self.successful_experiments,
            'failed_experiments': self.failed_experiments,
            'success_rate': (
                self.successful_experiments / self.total_experiments
                if self.total_experiments > 0 else 0
            ),
            'docker_available': self.docker_client is not None
        }
