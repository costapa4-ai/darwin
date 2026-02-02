"""
Safe code execution sandbox with defense-in-depth security.

Security layers:
1. Code validation (whitelist-based AST analysis)
2. Restricted builtins (no dangerous functions)
3. Process isolation (separate process)
4. Resource limits (memory, CPU, file size)
5. Timeout enforcement
"""

import multiprocessing
import time
import sys
import io
import traceback
import signal
from typing import Dict
from utils.logger import setup_logger
from utils.security import CodeValidator, create_safe_builtins, set_resource_limits

logger = setup_logger(__name__)


def _execute_code(
    code: str,
    result_queue: multiprocessing.Queue,
    timeout: int,
    max_memory_mb: int
):
    """
    Execute code in isolated process with security restrictions.

    This function runs in a separate process to provide isolation.
    """
    # Set resource limits FIRST (before any code runs)
    set_resource_limits(max_memory_mb=max_memory_mb, max_cpu_seconds=timeout)

    # Set up timeout signal handler
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Execution timed out after {timeout} seconds")

    try:
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout)
    except (AttributeError, ValueError):
        # SIGALRM not available on Windows
        pass

    # Redirect stdout/stderr
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = io.StringIO()
    sys.stderr = io.StringIO()

    start_time = time.time()
    result = {
        'success': False,
        'output': '',
        'error': '',
        'execution_time': 0,
        'memory_used': 0,
        'security_blocked': False
    }

    try:
        # Create SECURE restricted globals
        safe_globals = {
            '__builtins__': create_safe_builtins()
        }

        # Additional safety: Create a restricted locals dict
        safe_locals = {}

        # Execute code with restricted environment
        exec(code, safe_globals, safe_locals)

        result['success'] = True
        result['output'] = sys.stdout.getvalue()

    except TimeoutError as e:
        result['success'] = False
        result['error'] = str(e)
        result['output'] = sys.stdout.getvalue()

    except MemoryError:
        result['success'] = False
        result['error'] = "Memory limit exceeded"
        result['output'] = sys.stdout.getvalue()

    except AttributeError as e:
        # Likely from SafeType blocking dangerous access
        result['success'] = False
        result['error'] = f"Security: {e}"
        result['output'] = sys.stdout.getvalue()
        result['security_blocked'] = True

    except Exception as e:
        result['success'] = False
        result['error'] = f"{type(e).__name__}: {str(e)}"
        result['output'] = sys.stdout.getvalue()

        # Add traceback to stderr
        error_output = sys.stderr.getvalue()
        if not error_output:
            error_output = traceback.format_exc()
        result['error'] += f"\n{error_output}"

    finally:
        # Cancel alarm
        try:
            signal.alarm(0)
        except (AttributeError, ValueError):
            pass

        result['execution_time'] = time.time() - start_time
        sys.stdout = old_stdout
        sys.stderr = old_stderr

        result_queue.put(result)


class SafeExecutor:
    """
    Executes code in isolated environment with multiple security layers.

    Security features:
    1. Whitelist-based code validation (blocks imports, dangerous calls)
    2. Restricted builtins (no eval, exec, open, etc.)
    3. Type wrappers (prevent __class__ escape)
    4. Process isolation (separate process)
    5. Resource limits (memory, CPU, file operations)
    6. Timeout enforcement (signal-based + process timeout)
    """

    def __init__(
        self,
        timeout: int = 30,
        max_memory_mb: int = 256,
        allowed_modules: str = ""
    ):
        """
        Initialize the safe executor.

        Args:
            timeout: Maximum execution time in seconds
            max_memory_mb: Maximum memory usage in MB
            allowed_modules: Comma-separated list of allowed modules (default: none)
        """
        self.timeout = timeout
        self.max_memory_mb = max_memory_mb

        # Parse allowed modules (usually should be empty for safety)
        modules = set(m.strip() for m in allowed_modules.split(',') if m.strip())
        self.validator = CodeValidator(modules)

        logger.info("SafeExecutor initialized with enhanced security", extra={
            "timeout": timeout,
            "max_memory_mb": max_memory_mb,
            "allowed_modules": list(modules),
            "security_features": [
                "whitelist_validation",
                "restricted_builtins",
                "type_wrappers",
                "process_isolation",
                "resource_limits"
            ]
        })

    def execute(self, code: str, task_id: str = None) -> Dict:
        """
        Execute code with comprehensive safety restrictions.

        Returns:
            {
                'success': bool,
                'output': str,
                'error': str,
                'execution_time': float,
                'memory_used': int,
                'security_report': dict (if validation failed)
            }
        """
        # Phase 1: Static code validation (whitelist-based)
        is_valid, error_msg = self.validator.validate(code)
        if not is_valid:
            logger.warning("Code validation BLOCKED", extra={
                "task_id": task_id,
                "error": error_msg
            })

            # Get detailed security report
            security_report = self.validator.get_security_report(code)

            return {
                'success': False,
                'output': '',
                'error': f"Security validation failed: {error_msg}",
                'execution_time': 0,
                'memory_used': 0,
                'security_blocked': True,
                'security_report': security_report
            }

        # Phase 2: Execute in isolated process
        result_queue = multiprocessing.Queue()
        process = multiprocessing.Process(
            target=_execute_code,
            args=(code, result_queue, self.timeout, self.max_memory_mb)
        )

        logger.info("Starting secure code execution", extra={
            "task_id": task_id,
            "code_length": len(code),
            "timeout": self.timeout
        })

        process.start()
        process.join(timeout=self.timeout + 5)  # Extra buffer for process overhead

        if process.is_alive():
            # Timeout occurred - forcefully terminate
            process.terminate()
            process.join(timeout=5)

            if process.is_alive():
                # Still alive - kill it
                process.kill()
                process.join()

            logger.warning("Execution timeout - process terminated", extra={
                "task_id": task_id,
                "timeout": self.timeout
            })

            return {
                'success': False,
                'output': '',
                'error': f"Execution timeout after {self.timeout} seconds (process killed)",
                'execution_time': self.timeout,
                'memory_used': 0,
                'timeout': True
            }

        # Get result from queue
        if not result_queue.empty():
            result = result_queue.get()

            # Sanitize output
            result['output'] = self.validator.sanitize_output(result['output'])
            result['error'] = self.validator.sanitize_output(result['error'])

            log_level = "info" if result['success'] else "warning"
            log_extra = {
                "task_id": task_id,
                "success": result['success'],
                "execution_time": result['execution_time'],
                "security_blocked": result.get('security_blocked', False)
            }

            if result['success']:
                logger.info("Execution completed successfully", extra=log_extra)
            else:
                logger.warning("Execution failed", extra=log_extra)

            return result
        else:
            logger.error("No result from execution process", extra={"task_id": task_id})
            return {
                'success': False,
                'output': '',
                'error': "Process terminated unexpectedly (no result)",
                'execution_time': 0,
                'memory_used': 0
            }

    async def execute_async(self, code: str, task_id: str = None) -> Dict:
        """
        Async wrapper for execute().

        Runs the synchronous execute in a thread pool to avoid blocking.
        """
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.execute, code, task_id)

    def validate_only(self, code: str) -> Dict:
        """
        Only validate code without executing.

        Useful for pre-checking code before execution.
        """
        return self.validator.get_security_report(code)
