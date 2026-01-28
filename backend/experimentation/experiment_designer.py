"""
Experiment Designer - Generates Creative Experiments

Designs experiments for Darwin to learn from, including:
- Algorithm variations
- Performance optimizations
- Novel approaches
- Edge case testing
"""

import random
from typing import Dict, Any, List, Optional
from datetime import datetime

from utils.logger import get_logger

logger = get_logger(__name__)


class ExperimentDesigner:
    """
    Designs and generates experiments for learning
    """

    def __init__(self, semantic_memory, multi_model_router):
        """
        Initialize experiment designer

        Args:
            semantic_memory: Semantic memory for context
            multi_model_router: AI router for generation
        """
        self.memory = semantic_memory
        self.ai_router = multi_model_router

        # Experiment templates
        self.experiment_categories = [
            'algorithm_optimization',
            'data_structure_comparison',
            'concurrency_patterns',
            'error_handling',
            'performance_testing',
            'edge_cases',
            'novel_approaches',
            'api_exploration',
            'pattern_discovery'
        ]

        # Generated experiments
        self.generated_experiments = []

        logger.info("ExperimentDesigner initialized")

    async def design_experiment(self, category: Optional[str] = None) -> Dict[str, Any]:
        """
        Design a new experiment

        Args:
            category: Experiment category (random if None)

        Returns:
            Experiment specification
        """
        category = category or random.choice(self.experiment_categories)

        logger.info(f"Designing experiment: {category}")

        experiment = {
            'id': f"exp_{datetime.utcnow().timestamp()}_{random.randint(1000, 9999)}",
            'category': category,
            'created_at': datetime.utcnow().isoformat(),
            'hypothesis': None,
            'code': None,
            'expected_learning': None,
            'risk_level': 'low'
        }

        try:
            # Generate experiment based on category
            if category == 'algorithm_optimization':
                experiment = await self._design_algorithm_experiment(experiment)
            elif category == 'data_structure_comparison':
                experiment = await self._design_data_structure_experiment(experiment)
            elif category == 'concurrency_patterns':
                experiment = await self._design_concurrency_experiment(experiment)
            elif category == 'error_handling':
                experiment = await self._design_error_handling_experiment(experiment)
            elif category == 'performance_testing':
                experiment = await self._design_performance_experiment(experiment)
            elif category == 'edge_cases':
                experiment = await self._design_edge_case_experiment(experiment)
            elif category == 'novel_approaches':
                experiment = await self._design_novel_approach_experiment(experiment)
            elif category == 'api_exploration':
                experiment = await self._design_api_exploration_experiment(experiment)
            elif category == 'pattern_discovery':
                experiment = await self._design_pattern_discovery_experiment(experiment)

            self.generated_experiments.append(experiment)
            logger.info(f"✅ Designed experiment: {experiment['id']}")

        except Exception as e:
            logger.error(f"❌ Failed to design experiment: {e}")
            experiment['error'] = str(e)

        return experiment

    async def _design_algorithm_experiment(self, experiment: Dict) -> Dict:
        """Design algorithm optimization experiment"""

        algorithms = [
            ('sorting', ['bubble_sort', 'quick_sort', 'merge_sort', 'tim_sort']),
            ('searching', ['linear_search', 'binary_search', 'interpolation_search']),
            ('hashing', ['chaining', 'open_addressing', 'cuckoo_hashing'])
        ]

        algo_type, variants = random.choice(algorithms)

        prompt = f"""Design a Python experiment to compare {algo_type} algorithms: {', '.join(variants)}.

Generate complete Python code that:
1. Implements 2-3 variants
2. Tests with different input sizes
3. Measures time and memory
4. Prints clear comparison results

Make it educational and safe to run. Include print statements showing what's being tested."""

        result = await self.ai_router.generate(
            task_description=f"Design {algo_type} experiment",
            prompt=prompt,
            max_tokens=800
        )

        code = result.get('result', '') if isinstance(result, dict) else str(result)

        # Extract code from markdown if present
        code = self._extract_code_from_markdown(code)

        experiment['hypothesis'] = f"Different {algo_type} algorithms will show performance differences"
        experiment['code'] = code
        experiment['expected_learning'] = f"Understand {algo_type} algorithm trade-offs"
        experiment['risk_level'] = 'low'

        return experiment

    async def _design_data_structure_experiment(self, experiment: Dict) -> Dict:
        """Design data structure comparison experiment"""

        comparisons = [
            ('list vs deque', 'append/prepend operations'),
            ('dict vs set', 'lookup performance'),
            ('list vs array', 'memory efficiency'),
            ('tuple vs namedtuple', 'readability and access')
        ]

        structures, operation = random.choice(comparisons)

        code = f"""import time
import sys
from collections import deque, namedtuple

# Experiment: {structures} for {operation}

def experiment():
    print("=== Data Structure Comparison: {structures} ===")
    print("Operation: {operation}")

    # Test size
    n = 10000

    # Test 1: First structure
    print("\\nTesting first structure...")
    start = time.perf_counter()

    # Implementation for first structure
    data1 = []
    for i in range(n):
        data1.append(i)

    time1 = time.perf_counter() - start
    mem1 = sys.getsizeof(data1)

    print(f"Time: {{time1:.6f}}s")
    print(f"Memory: {{mem1}} bytes")

    # Test 2: Second structure
    print("\\nTesting second structure...")
    start = time.perf_counter()

    # Implementation for second structure
    data2 = deque()
    for i in range(n):
        data2.append(i)

    time2 = time.perf_counter() - start
    mem2 = sys.getsizeof(data2)

    print(f"Time: {{time2:.6f}}s")
    print(f"Memory: {{mem2}} bytes")

    # Comparison
    print("\\n=== Results ===")
    faster = "First" if time1 < time2 else "Second"
    speedup = max(time1, time2) / min(time1, time2)
    print(f"{{faster}} structure is {{speedup:.2f}}x faster")

    efficient = "First" if mem1 < mem2 else "Second"
    print(f"{{efficient}} structure uses less memory")

    return {{'time1': time1, 'time2': time2, 'mem1': mem1, 'mem2': mem2}}

if __name__ == '__main__':
    result = experiment()
    print("\\nExperiment completed successfully!")
"""

        experiment['hypothesis'] = f"{structures} will show different performance characteristics"
        experiment['code'] = code
        experiment['expected_learning'] = f"Learn when to use each data structure"
        experiment['risk_level'] = 'low'

        return experiment

    async def _design_concurrency_experiment(self, experiment: Dict) -> Dict:
        """Design concurrency pattern experiment"""

        code = """import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

# Experiment: Concurrency Patterns Comparison

async def async_task(task_id, duration):
    \"\"\"Async task simulation\"\"\"
    print(f"Async task {task_id} started")
    await asyncio.sleep(duration)
    print(f"Async task {task_id} completed")
    return task_id

def sync_task(task_id, duration):
    \"\"\"Sync task simulation\"\"\"
    print(f"Sync task {task_id} started")
    time.sleep(duration)
    print(f"Sync task {task_id} completed")
    return task_id

async def experiment():
    print("=== Concurrency Patterns Experiment ===")

    num_tasks = 5
    task_duration = 0.1

    # Test 1: Sequential execution
    print("\\n--- Sequential Execution ---")
    start = time.perf_counter()
    for i in range(num_tasks):
        sync_task(i, task_duration)
    sequential_time = time.perf_counter() - start
    print(f"Time: {sequential_time:.3f}s")

    # Test 2: Async concurrent execution
    print("\\n--- Async Concurrent Execution ---")
    start = time.perf_counter()
    tasks = [async_task(i, task_duration) for i in range(num_tasks)]
    await asyncio.gather(*tasks)
    async_time = time.perf_counter() - start
    print(f"Time: {async_time:.3f}s")

    # Test 3: Thread pool execution
    print("\\n--- Thread Pool Execution ---")
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(sync_task, i, task_duration) for i in range(num_tasks)]
        for future in futures:
            future.result()
    thread_time = time.perf_counter() - start
    print(f"Time: {thread_time:.3f}s")

    # Results
    print("\\n=== Results ===")
    print(f"Sequential: {sequential_time:.3f}s (baseline)")
    print(f"Async: {async_time:.3f}s ({sequential_time/async_time:.1f}x speedup)")
    print(f"Threads: {thread_time:.3f}s ({sequential_time/thread_time:.1f}x speedup)")

    return {
        'sequential': sequential_time,
        'async': async_time,
        'threads': thread_time
    }

if __name__ == '__main__':
    asyncio.run(experiment())
    print("\\nExperiment completed!")
"""

        experiment['hypothesis'] = "Concurrent execution patterns will show significant speedup"
        experiment['code'] = code
        experiment['expected_learning'] = "Understand async vs threading trade-offs"
        experiment['risk_level'] = 'low'

        return experiment

    async def _design_error_handling_experiment(self, experiment: Dict) -> Dict:
        """Design error handling experiment"""

        code = """# Experiment: Error Handling Patterns

def experiment():
    print("=== Error Handling Patterns ===")

    results = []

    # Pattern 1: Try-Except
    print("\\n--- Try-Except Pattern ---")
    try:
        result = 10 / 0
    except ZeroDivisionError as e:
        print(f"Caught: {type(e).__name__}")
        result = None
    print(f"Result: {result}")
    results.append(('try_except', result is None))

    # Pattern 2: Try-Except-Else
    print("\\n--- Try-Except-Else Pattern ---")
    try:
        result = 10 / 2
    except ZeroDivisionError:
        print("Error occurred")
        result = None
    else:
        print("Success - no error")
        result = result * 2
    print(f"Result: {result}")
    results.append(('try_except_else', result == 10.0))

    # Pattern 3: Try-Except-Finally
    print("\\n--- Try-Except-Finally Pattern ---")
    resource = "opened"
    try:
        result = 10 / 2
    except ZeroDivisionError:
        print("Error occurred")
        result = None
    finally:
        print("Cleaning up resource...")
        resource = "closed"
    print(f"Result: {result}, Resource: {resource}")
    results.append(('try_except_finally', resource == "closed"))

    # Pattern 4: Multiple exceptions
    print("\\n--- Multiple Exceptions ---")
    errors_caught = []
    test_cases = [
        (lambda: 10 / 0, "division"),
        (lambda: int("invalid"), "conversion"),
        (lambda: [][5], "index")
    ]

    for func, desc in test_cases:
        try:
            func()
        except (ZeroDivisionError, ValueError, IndexError) as e:
            errors_caught.append(type(e).__name__)
            print(f"{desc}: Caught {type(e).__name__}")

    results.append(('multiple_exceptions', len(errors_caught) == 3))

    # Results
    print("\\n=== Results ===")
    for pattern, success in results:
        status = "✓" if success else "✗"
        print(f"{status} {pattern}: {'passed' if success else 'failed'}")

    return results

if __name__ == '__main__':
    result = experiment()
    print("\\nExperiment completed!")
"""

        experiment['hypothesis'] = "Different error handling patterns have different use cases"
        experiment['code'] = code
        experiment['expected_learning'] = "Master Python error handling patterns"
        experiment['risk_level'] = 'low'

        return experiment

    async def _design_performance_experiment(self, experiment: Dict) -> Dict:
        """Design performance testing experiment"""

        operations = ['list_comprehension', 'generator', 'map_filter', 'loops']
        operation = random.choice(operations)

        code = f"""import time
import sys

# Experiment: Performance - {operation}

def experiment():
    print("=== Performance Test: {operation} ===")

    n = 100000

    # Method 1: List comprehension
    print("\\n--- List Comprehension ---")
    start = time.perf_counter()
    result1 = [x * 2 for x in range(n)]
    time1 = time.perf_counter() - start
    mem1 = sys.getsizeof(result1)
    print(f"Time: {{time1:.6f}}s, Memory: {{mem1}} bytes")

    # Method 2: Generator
    print("\\n--- Generator ---")
    start = time.perf_counter()
    result2 = (x * 2 for x in range(n))
    time2 = time.perf_counter() - start
    mem2 = sys.getsizeof(result2)
    # Force evaluation
    list(result2)
    time2_eval = time.perf_counter() - start
    print(f"Creation time: {{time2:.6f}}s, Eval time: {{time2_eval:.6f}}s")
    print(f"Memory: {{mem2}} bytes (generator object)")

    # Method 3: Map
    print("\\n--- Map Function ---")
    start = time.perf_counter()
    result3 = list(map(lambda x: x * 2, range(n)))
    time3 = time.perf_counter() - start
    mem3 = sys.getsizeof(result3)
    print(f"Time: {{time3:.6f}}s, Memory: {{mem3}} bytes")

    # Method 4: For loop
    print("\\n--- For Loop ---")
    start = time.perf_counter()
    result4 = []
    for x in range(n):
        result4.append(x * 2)
    time4 = time.perf_counter() - start
    mem4 = sys.getsizeof(result4)
    print(f"Time: {{time4:.6f}}s, Memory: {{mem4}} bytes")

    # Results
    print("\\n=== Results ===")
    times = [time1, time2_eval, time3, time4]
    fastest_idx = times.index(min(times))
    methods = ['List comp', 'Generator', 'Map', 'For loop']
    print(f"Fastest: {{methods[fastest_idx]}} ({{min(times):.6f}}s)")

    return {{'times': times, 'fastest': methods[fastest_idx]}}

if __name__ == '__main__':
    result = experiment()
    print("\\nExperiment completed!")
"""

        experiment['hypothesis'] = f"{operation} will show unique performance characteristics"
        experiment['code'] = code
        experiment['expected_learning'] = "Understand Python performance optimization"
        experiment['risk_level'] = 'low'

        return experiment

    async def _design_edge_case_experiment(self, experiment: Dict) -> Dict:
        """Design edge case testing experiment"""

        code = """# Experiment: Edge Case Testing

def experiment():
    print("=== Edge Case Testing ===")

    test_results = []

    # Edge Case 1: Empty collections
    print("\\n--- Empty Collections ---")
    try:
        empty_list = []
        empty_dict = {}
        empty_str = ""

        print(f"max([]) would raise: ValueError")
        print(f"empty_dict['key'] would raise: KeyError")
        print(f"empty_str[0] would raise: IndexError")

        # Safe handling
        max_val = max(empty_list, default=None)
        dict_val = empty_dict.get('key', 'default')
        str_val = empty_str[0] if empty_str else None

        print(f"Safe results: {max_val}, {dict_val}, {str_val}")
        test_results.append(('empty_collections', True))
    except Exception as e:
        print(f"Failed: {e}")
        test_results.append(('empty_collections', False))

    # Edge Case 2: None values
    print("\\n--- None Values ---")
    try:
        val = None
        # None is False-y but not same as False
        is_none = val is None  # Correct
        equals_none = val == None  # Works but not idiomatic

        print(f"is None: {is_none}")
        print(f"== None: {equals_none}")
        print(f"bool(None): {bool(val)}")

        test_results.append(('none_values', is_none))
    except Exception as e:
        print(f"Failed: {e}")
        test_results.append(('none_values', False))

    # Edge Case 3: Integer overflow (Python handles gracefully)
    print("\\n--- Large Numbers ---")
    try:
        large_num = 10 ** 100
        larger_num = large_num * large_num
        print(f"Python handles arbitrary precision: {len(str(larger_num))} digits")
        test_results.append(('large_numbers', True))
    except Exception as e:
        print(f"Failed: {e}")
        test_results.append(('large_numbers', False))

    # Edge Case 4: Division edge cases
    print("\\n--- Division Edge Cases ---")
    try:
        results = []
        results.append(('10 / 3', 10 / 3))  # Float division
        results.append(('10 // 3', 10 // 3))  # Integer division
        results.append(('10 % 3', 10 % 3))  # Modulo
        results.append(('float("inf")', float('inf')))  # Infinity

        for desc, val in results:
            print(f"{desc} = {val}")

        test_results.append(('division_cases', True))
    except Exception as e:
        print(f"Failed: {e}")
        test_results.append(('division_cases', False))

    # Results
    print("\\n=== Results ===")
    passed = sum(1 for _, success in test_results if success)
    print(f"Passed: {passed}/{len(test_results)}")

    for case, success in test_results:
        status = "✓" if success else "✗"
        print(f"{status} {case}")

    return test_results

if __name__ == '__main__':
    result = experiment()
    print("\\nExperiment completed!")
"""

        experiment['hypothesis'] = "Edge cases require special handling patterns"
        experiment['code'] = code
        experiment['expected_learning'] = "Learn robust edge case handling"
        experiment['risk_level'] = 'low'

        return experiment

    async def _design_novel_approach_experiment(self, experiment: Dict) -> Dict:
        """Design novel approach experiment"""

        prompt = """Design a creative Python experiment that explores an unusual or novel approach to a common problem.

Examples:
- Using decorators for memoization
- Context managers for resource handling
- Metaclasses for automatic registration
- Descriptors for validation

Generate complete, safe Python code that demonstrates the approach."""

        result = await self.ai_router.generate(
            task_description="Design novel approach experiment",
            prompt=prompt,
            max_tokens=800
        )

        code = result.get('result', '') if isinstance(result, dict) else str(result)
        code = self._extract_code_from_markdown(code)

        experiment['hypothesis'] = "Novel approaches can provide elegant solutions"
        experiment['code'] = code
        experiment['expected_learning'] = "Discover creative Python patterns"
        experiment['risk_level'] = 'medium'

        return experiment

    async def _design_api_exploration_experiment(self, experiment: Dict) -> Dict:
        """Design API exploration experiment"""

        apis = ['collections', 'itertools', 'functools', 'operator']
        api = random.choice(apis)

        code = f"""# Experiment: Exploring {api} module

import {api}

def experiment():
    print("=== {api.title()} Module Exploration ===")

    # List available functions/classes
    print("\\nAvailable in {api}:")
    items = [item for item in dir({api}) if not item.startswith('_')]
    for item in items[:10]:  # First 10
        print(f"  - {{item}}")

    # Demonstrate 2-3 key features
    print("\\n--- Feature Demonstrations ---")

    # Add specific demonstrations based on module
    print("\\nExploration completed!")

    return {{'module': '{api}', 'items_found': len(items)}}

if __name__ == '__main__':
    result = experiment()
    print(f"\\nFound {{result['items_found']}} items in {{result['module']}}")
"""

        experiment['hypothesis'] = f"{api} module contains useful utilities"
        experiment['code'] = code
        experiment['expected_learning'] = f"Discover {api} capabilities"
        experiment['risk_level'] = 'low'

        return experiment

    async def _design_pattern_discovery_experiment(self, experiment: Dict) -> Dict:
        """Design pattern discovery experiment"""

        patterns = [
            'singleton', 'factory', 'observer', 'strategy', 'decorator'
        ]
        pattern = random.choice(patterns)

        prompt = f"""Design a Python experiment demonstrating the {pattern} design pattern.

Create simple, educational code showing:
1. Problem it solves
2. Implementation
3. Usage example
4. Benefits

Keep it concise and safe to run."""

        result = await self.ai_router.generate(
            task_description=f"Design {pattern} pattern experiment",
            prompt=prompt,
            max_tokens=800
        )

        code = result.get('result', '') if isinstance(result, dict) else str(result)
        code = self._extract_code_from_markdown(code)

        experiment['hypothesis'] = f"{pattern} pattern provides specific benefits"
        experiment['code'] = code
        experiment['expected_learning'] = f"Understand {pattern} design pattern"
        experiment['risk_level'] = 'low'

        return experiment

    def _extract_code_from_markdown(self, text: str) -> str:
        """Extract code from markdown code blocks"""
        # Remove markdown code fences
        text = text.replace('```python', '').replace('```', '')
        return text.strip()

    def get_experiment_stats(self) -> Dict[str, Any]:
        """Get experiment generation statistics"""
        category_counts = {}
        for exp in self.generated_experiments:
            cat = exp['category']
            category_counts[cat] = category_counts.get(cat, 0) + 1

        return {
            'total_generated': len(self.generated_experiments),
            'by_category': category_counts,
            'categories_available': self.experiment_categories
        }
