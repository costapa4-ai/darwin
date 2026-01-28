"""Safe code execution sandbox"""
import multiprocessing
import time
import sys
import io
import traceback
from typing import Dict
from utils.logger import setup_logger
from utils.security import CodeValidator

logger = setup_logger(__name__)


def _execute_code(code: str, result_queue: multiprocessing.Queue, timeout: int):
    """Execute code in isolated process"""
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
        'memory_used': 0
    }

    try:
        # Create restricted globals
        safe_globals = {
            '__builtins__': {
                'print': print,
                'len': len,
                'range': range,
                'str': str,
                'int': int,
                'float': float,
                'bool': bool,
                'list': list,
                'dict': dict,
                'tuple': tuple,
                'set': set,
                'abs': abs,
                'max': max,
                'min': min,
                'sum': sum,
                'sorted': sorted,
                'enumerate': enumerate,
                'zip': zip,
                'map': map,
                'filter': filter,
                'all': all,
                'any': any,
                'True': True,
                'False': False,
                'None': None,
                '__name__': '__main__',  # Allow if __name__ == "__main__" pattern
            }
        }

        # Execute code
        exec(code, safe_globals)

        result['success'] = True
        result['output'] = sys.stdout.getvalue()

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
        result['execution_time'] = time.time() - start_time
        sys.stdout = old_stdout
        sys.stderr = old_stderr

        result_queue.put(result)


class SafeExecutor:
    """Executes code in isolated environment with resource limits"""

    def __init__(self, timeout: int = 30, max_memory_mb: int = 256, allowed_modules: str = ""):
        self.timeout = timeout
        self.max_memory_mb = max_memory_mb

        # Parse allowed modules
        modules = set(m.strip() for m in allowed_modules.split(',') if m.strip())
        self.validator = CodeValidator(modules)

        logger.info("SafeExecutor initialized", extra={
            "timeout": timeout,
            "max_memory_mb": max_memory_mb,
            "allowed_modules": list(modules)
        })

    def execute(self, code: str, task_id: str = None) -> Dict:
        """
        Execute code with safety restrictions

        Returns:
            {
                'success': bool,
                'output': str,
                'error': str,
                'execution_time': float,
                'memory_used': int
            }
        """
        # Validate code first
        is_valid, error_msg = self.validator.validate(code)
        if not is_valid:
            logger.warning("Code validation failed", extra={
                "task_id": task_id,
                "error": error_msg
            })
            return {
                'success': False,
                'output': '',
                'error': f"Security validation failed: {error_msg}",
                'execution_time': 0,
                'memory_used': 0
            }

        # Execute in separate process
        result_queue = multiprocessing.Queue()
        process = multiprocessing.Process(
            target=_execute_code,
            args=(code, result_queue, self.timeout)
        )

        logger.info("Starting code execution", extra={"task_id": task_id})

        process.start()
        process.join(timeout=self.timeout)

        if process.is_alive():
            # Timeout occurred
            process.terminate()
            process.join()

            logger.warning("Execution timeout", extra={
                "task_id": task_id,
                "timeout": self.timeout
            })

            return {
                'success': False,
                'output': '',
                'error': f"Execution timeout after {self.timeout} seconds",
                'execution_time': self.timeout,
                'memory_used': 0
            }

        # Get result from queue
        if not result_queue.empty():
            result = result_queue.get()

            # Sanitize output
            result['output'] = self.validator.sanitize_output(result['output'])
            result['error'] = self.validator.sanitize_output(result['error'])

            logger.info("Execution completed", extra={
                "task_id": task_id,
                "success": result['success'],
                "execution_time": result['execution_time']
            })

            return result
        else:
            logger.error("No result from execution process", extra={"task_id": task_id})
            return {
                'success': False,
                'output': '',
                'error': "Process terminated unexpectedly",
                'execution_time': 0,
                'memory_used': 0
            }
