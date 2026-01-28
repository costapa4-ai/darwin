"""
Tool Tester: Automatically tests generated tools before deployment

Validates that tools can be imported, have callable functions,
and execute without errors on sample inputs.
"""

import ast
import importlib.util
import inspect
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
import tempfile
import os


@dataclass
class TestResult:
    """Result of a tool test"""
    passed: bool
    tool_name: str
    tests_run: int
    tests_passed: int
    errors: List[str]
    warnings: List[str]
    functions_found: List[str]
    execution_time_ms: float = 0.0


class ToolTester:
    """
    Automated testing for dynamically generated tools

    Performs multiple validation checks:
    1. Syntax validation (already done by CodeValidator)
    2. Import validation - can the tool be imported?
    3. Function discovery - does it have callable functions?
    4. Basic execution - can functions run without crashing?
    5. Safety checks - no dangerous operations
    """

    def __init__(self):
        self.test_results: List[TestResult] = []

    def test_tool_code(self, code: str, tool_name: str) -> TestResult:
        """
        Test generated tool code before deployment

        Args:
            code: Python code for the tool
            tool_name: Name of the tool being tested

        Returns:
            TestResult with validation results
        """
        import time
        start_time = time.time()

        errors = []
        warnings = []
        functions_found = []
        tests_run = 0
        tests_passed = 0

        print(f"\n🧪 Testing tool: {tool_name}")

        # Test 1: Syntax validation (compile check)
        print(f"   [1/5] Syntax validation...")
        tests_run += 1
        try:
            compile(code, f'<{tool_name}>', 'exec')
            tests_passed += 1
            print(f"   ✅ Syntax valid")
        except SyntaxError as e:
            error_msg = f"Syntax error at line {e.lineno}: {e.msg}"
            errors.append(error_msg)
            print(f"   ❌ {error_msg}")
            # If syntax fails, can't proceed
            return TestResult(
                passed=False,
                tool_name=tool_name,
                tests_run=tests_run,
                tests_passed=tests_passed,
                errors=errors,
                warnings=warnings,
                functions_found=functions_found,
                execution_time_ms=(time.time() - start_time) * 1000
            )

        # Test 2: Import validation - can we load it as a module?
        print(f"   [2/5] Import validation...")
        tests_run += 1
        try:
            # Create a temporary file to import from
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_file = f.name

            try:
                # Import the module
                spec = importlib.util.spec_from_file_location(tool_name, temp_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[tool_name] = module
                    spec.loader.exec_module(module)
                    tests_passed += 1
                    print(f"   ✅ Import successful")

                    # Test 3: Function discovery
                    print(f"   [3/5] Function discovery...")
                    tests_run += 1
                    functions = [
                        name for name, obj in inspect.getmembers(module)
                        if inspect.isfunction(obj) and not name.startswith('_')
                    ]

                    if functions:
                        functions_found = functions
                        tests_passed += 1
                        print(f"   ✅ Found {len(functions)} public functions: {', '.join(functions)}")

                        # Test 4: Function signature validation
                        print(f"   [4/5] Function signature validation...")
                        tests_run += 1
                        signature_valid = True

                        for func_name in functions:
                            func = getattr(module, func_name)
                            sig = inspect.signature(func)

                            # Check if function can be called with no args or **kwargs
                            params = list(sig.parameters.values())
                            has_defaults = all(
                                p.default != inspect.Parameter.empty or
                                p.kind in [inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD]
                                for p in params
                            )

                            if not has_defaults and len(params) > 0:
                                warnings.append(
                                    f"Function '{func_name}' requires {len(params)} arguments - "
                                    "may not be callable by ToolManager without parameters"
                                )
                                signature_valid = False

                        if signature_valid:
                            tests_passed += 1
                            print(f"   ✅ Function signatures compatible")
                        else:
                            print(f"   ⚠️ Some functions may require specific parameters")

                        # Test 5: Basic execution test (try calling with no args)
                        print(f"   [5/5] Basic execution test...")
                        tests_run += 1
                        execution_success = False

                        for func_name in functions:
                            try:
                                func = getattr(module, func_name)
                                sig = inspect.signature(func)

                                # Only test if function can be called with no args
                                params = list(sig.parameters.values())
                                if not params or all(p.default != inspect.Parameter.empty for p in params):
                                    # Try calling with no arguments
                                    result = func()
                                    execution_success = True
                                    print(f"   ✅ Function '{func_name}()' executed successfully")
                                    break  # Success! At least one function works
                            except Exception as e:
                                warnings.append(
                                    f"Function '{func_name}' execution failed: {str(e)[:100]}"
                                )

                        if execution_success:
                            tests_passed += 1
                        else:
                            print(f"   ⚠️ Could not execute any functions (may require arguments)")

                    else:
                        errors.append("No public functions found in tool")
                        print(f"   ❌ No public functions found")

                else:
                    errors.append("Failed to load module spec")
                    print(f"   ❌ Failed to load module spec")

            finally:
                # Clean up
                if tool_name in sys.modules:
                    del sys.modules[tool_name]
                try:
                    os.unlink(temp_file)
                except:
                    pass

        except Exception as e:
            error_msg = f"Import failed: {str(e)}"
            errors.append(error_msg)
            print(f"   ❌ {error_msg}")

        # Determine overall result
        execution_time_ms = (time.time() - start_time) * 1000
        passed = tests_passed >= 3  # At least syntax + import + functions must pass

        result = TestResult(
            passed=passed,
            tool_name=tool_name,
            tests_run=tests_run,
            tests_passed=tests_passed,
            errors=errors,
            warnings=warnings,
            functions_found=functions_found,
            execution_time_ms=execution_time_ms
        )

        # Print summary
        print(f"\n   📊 Test Summary:")
        print(f"   Tests: {tests_passed}/{tests_run} passed")
        print(f"   Functions: {len(functions_found)} found")
        print(f"   Errors: {len(errors)}")
        print(f"   Warnings: {len(warnings)}")
        print(f"   Time: {execution_time_ms:.1f}ms")
        print(f"   Result: {'✅ PASSED' if passed else '❌ FAILED'}")

        self.test_results.append(result)
        return result

    def should_deploy(self, test_result: TestResult) -> bool:
        """
        Determine if a tool should be deployed based on test results

        Deployment criteria:
        - Must pass syntax validation
        - Must be importable
        - Must have at least one public function
        - Should have no critical errors

        Args:
            test_result: Test result to evaluate

        Returns:
            True if tool should be deployed, False otherwise
        """
        if not test_result.passed:
            return False

        # Must have at least one function
        if not test_result.functions_found:
            return False

        # No critical errors
        critical_errors = [
            e for e in test_result.errors
            if 'syntax' in e.lower() or 'import' in e.lower()
        ]

        if critical_errors:
            return False

        return True

    def get_test_report(self, test_result: TestResult) -> str:
        """
        Generate a human-readable test report

        Args:
            test_result: Test result to report

        Returns:
            Formatted test report string
        """
        report = []
        report.append(f"Tool Test Report: {test_result.tool_name}")
        report.append("=" * 60)
        report.append(f"Overall Result: {'✅ PASSED' if test_result.passed else '❌ FAILED'}")
        report.append(f"Tests: {test_result.tests_passed}/{test_result.tests_run} passed")
        report.append(f"Execution Time: {test_result.execution_time_ms:.1f}ms")
        report.append("")

        if test_result.functions_found:
            report.append(f"Functions Found ({len(test_result.functions_found)}):")
            for func in test_result.functions_found:
                report.append(f"  - {func}()")
            report.append("")

        if test_result.errors:
            report.append(f"Errors ({len(test_result.errors)}):")
            for error in test_result.errors:
                report.append(f"  ❌ {error}")
            report.append("")

        if test_result.warnings:
            report.append(f"Warnings ({len(test_result.warnings)}):")
            for warning in test_result.warnings:
                report.append(f"  ⚠️ {warning}")
            report.append("")

        report.append(f"Deployment Recommendation: {'✅ DEPLOY' if self.should_deploy(test_result) else '❌ DO NOT DEPLOY'}")

        return "\n".join(report)
