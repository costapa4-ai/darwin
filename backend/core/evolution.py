"""Evolution engine for iterative code improvement with Phase 2 enhancements"""
import uuid
from typing import Dict, List, Optional
from .nucleus import Nucleus
from .executor import SafeExecutor
from .memory import MemoryStore
from utils.logger import setup_logger

logger = setup_logger(__name__)


def fitness_function(result: Dict, code_analysis: Optional[Dict] = None) -> float:
    """
    Enhanced fitness score calculation (0-100)
    - 40 points: success
    - 20 points: speed
    - 15 points: memory efficiency
    - 15 points: code quality (if analysis available)
    - 10 points: correctness (if analysis available)
    """
    score = 0.0

    # Success is most important
    if result['success']:
        score += 40.0

    # Speed score (faster = better, cap at 10s)
    exec_time = result.get('execution_time', 10)
    if exec_time > 0:
        time_score = max(0, 20 - (exec_time * 2.0))
        score += time_score

    # Memory score (less = better, normalized to 256MB max)
    memory = result.get('memory_used', 0)
    if memory > 0:
        memory_mb = memory / (1024 * 1024)
        memory_score = max(0, 15 - (memory_mb / 256 * 15))
        score += memory_score
    else:
        # No memory data, give partial credit if successful
        if result['success']:
            score += 7.5

    # Code quality from multi-model analysis
    if code_analysis:
        quality_score = code_analysis.get('quality_score', 50) / 100 * 15
        correctness_score = code_analysis.get('correctness_score', 50) / 100 * 10
        score += quality_score + correctness_score
    else:
        # No analysis, give partial credit if successful
        if result['success']:
            score += 12.5

    return min(100.0, score)


class EvolutionEngine:
    """
    Enhanced evolution engine with:
    - Multi-model code analysis
    - Semantic memory integration
    - Meta-learning optimization
    """

    def __init__(
        self,
        nucleus: Nucleus,
        executor: SafeExecutor,
        memory: MemoryStore,
        meta_learner=None
    ):
        self.nucleus = nucleus
        self.executor = executor
        self.memory = memory
        self.meta_learner = meta_learner
        self.active_tasks = {}

        logger.info("EvolutionEngine initialized", extra={
            "meta_learning_enabled": meta_learner is not None
        })

    async def evolve_task(
        self,
        task: Dict,
        max_generations: int = 5,
        population_size: int = 3,
        callback=None,
        use_rag: bool = True,
        use_web_research: bool = False,
        use_multi_model_analysis: bool = True
    ) -> Dict:
        """
        Enhanced evolution with Phase 2 features

        Args:
            task: Task definition with 'id', 'description', 'type'
            max_generations: Maximum number of generations
            population_size: Number of solutions per generation
            callback: Optional async callback for progress updates
            use_rag: Use semantic memory for context
            use_web_research: Use web research
            use_multi_model_analysis: Use multi-model code analysis

        Returns:
            Best solution found with comprehensive metadata
        """
        task_id = task['id']
        logger.info("Starting enhanced evolution", extra={
            "task_id": task_id,
            "max_generations": max_generations,
            "population_size": population_size,
            "rag_enabled": use_rag,
            "web_research_enabled": use_web_research,
            "multi_model_analysis": use_multi_model_analysis
        })

        best_solution = None
        best_fitness = 0.0
        generation_history = []

        # Check for similar historical tasks
        similar = self.memory.get_similar_tasks(task['description'], limit=3)
        if similar and callback:
            await callback({
                'type': 'similar_tasks_found',
                'data': {'count': len(similar), 'tasks': similar}
            })

        for gen in range(max_generations):
            logger.info(f"Generation {gen + 1}/{max_generations}", extra={
                "task_id": task_id,
                "generation": gen + 1
            })

            if callback:
                await callback({
                    'type': 'generation_started',
                    'data': {
                        'task_id': task_id,
                        'generation': gen + 1,
                        'population_size': population_size
                    }
                })

            # Create population with RAG and web research
            population = await self._create_population(
                task, gen, population_size, best_solution,
                use_rag=use_rag,
                use_web_research=use_web_research
            )

            # Evaluate population
            results = []
            for idx, solution in enumerate(population):
                result = self.executor.execute(solution['code'], task_id=task_id)

                # Multi-model code analysis if enabled
                code_analysis = None
                if use_multi_model_analysis and self.nucleus.router and result['success']:
                    try:
                        analysis = await self.nucleus.router.analyze_with_multiple(
                            solution['code'],
                            task['description']
                        )
                        code_analysis = analysis.get('aggregated_scores', {})
                    except Exception as e:
                        logger.error(f"Multi-model analysis failed: {e}")

                # Calculate enhanced fitness
                fitness = fitness_function(result, code_analysis)

                solution_data = {
                    'id': str(uuid.uuid4()),
                    'task_id': task_id,
                    'task_description': task['description'],
                    'task_type': task['type'],
                    'code': solution['code'],
                    'success': result['success'],
                    'execution_time': result['execution_time'],
                    'memory_used': result.get('memory_used', 0),
                    'fitness_score': fitness,
                    'generation_number': gen + 1,
                    'output': result.get('output', ''),
                    'error': result.get('error', ''),
                    'code_analysis': code_analysis,
                    'metadata': {
                        'population_index': idx,
                        'variation_type': solution.get('variation_type', 'initial'),
                        'model_used': solution.get('model_used', 'unknown')
                    }
                }

                # Save to memory
                self.memory.save_execution(solution_data)

                # Save to semantic memory if available
                if self.nucleus.semantic_memory:
                    try:
                        await self.nucleus.semantic_memory.store_execution(
                            task_id=solution_data['id'],
                            task_description=task['description'],
                            code=solution['code'],
                            result=result,
                            metadata=solution_data['metadata']
                        )
                    except Exception as e:
                        logger.error(f"Failed to store in semantic memory: {e}")

                # Record in meta-learner if available
                if self.meta_learner:
                    try:
                        await self.meta_learner.record_execution(
                            task_id=solution_data['id'],
                            task_description=task['description'],
                            code=solution['code'],
                            result=result,
                            model_used=solution_data['metadata'].get('model_used', 'unknown'),
                            generation_time=solution.get('generation_time', 0)
                        )
                    except Exception as e:
                        logger.error(f"Failed to record in meta-learner: {e}")

                results.append(solution_data)

                # Track best
                if fitness > best_fitness:
                    best_fitness = fitness
                    best_solution = solution_data

                if callback:
                    await callback({
                        'type': 'solution_executed',
                        'data': {
                            'task_id': task_id,
                            'generation': gen + 1,
                            'solution_index': idx + 1,
                            'success': result['success'],
                            'fitness': fitness,
                            'output': result.get('output', '')[:200],
                            'code_quality': code_analysis.get('quality') if code_analysis else None
                        }
                    })

            generation_history.append({
                'generation': gen + 1,
                'results': results,
                'best_fitness': max(r['fitness_score'] for r in results)
            })

            # Check if we have a perfect solution
            if best_fitness >= 95.0:
                logger.info("Near-perfect solution found, stopping early", extra={
                    "task_id": task_id,
                    "fitness": best_fitness,
                    "generation": gen + 1
                })
                break

        if callback:
            await callback({
                'type': 'evolution_complete',
                'data': {
                    'task_id': task_id,
                    'best_fitness': best_fitness,
                    'generations': len(generation_history),
                    'best_solution': best_solution
                }
            })

        logger.info("Evolution complete", extra={
            "task_id": task_id,
            "best_fitness": best_fitness,
            "total_generations": len(generation_history)
        })

        return {
            'best_solution': best_solution,
            'best_fitness': best_fitness,
            'generations': generation_history,
            'task_id': task_id
        }

    async def _create_population(
        self,
        task: Dict,
        generation: int,
        size: int,
        best_previous: Dict = None,
        use_rag: bool = True,
        use_web_research: bool = False
    ) -> List[Dict]:
        """
        Create population of solutions with Phase 2 enhancements

        Args:
            task: Task dictionary
            generation: Current generation number
            size: Population size
            best_previous: Best solution from previous generation
            use_rag: Use semantic memory
            use_web_research: Use web research

        Returns:
            List of solution dictionaries
        """
        import time
        population = []

        if generation == 0:
            # Initial generation - create diverse solutions with RAG/research
            for i in range(size):
                start_time = time.time()
                code = await self.nucleus.generate_solution(
                    task,
                    use_rag=use_rag,
                    use_web_research=use_web_research and i == 0  # Only first solution uses web research
                )
                generation_time = time.time() - start_time

                population.append({
                    'code': code,
                    'variation_type': 'initial_rag' if use_rag else 'initial',
                    'generation_time': generation_time,
                    'model_used': self.nucleus.router.select_model(task['description']) if self.nucleus.router else self.nucleus.provider
                })
        else:
            # Evolve from best previous solution
            if best_previous:
                # Get analysis of best solution
                analysis = await self.nucleus.analyze_result(
                    best_previous['code'],
                    {
                        'success': best_previous['success'],
                        'execution_time': best_previous['execution_time'],
                        'output': best_previous.get('output', ''),
                        'error': best_previous.get('error', '')
                    },
                    task
                )

                # Create variations
                for i in range(size):
                    start_time = time.time()
                    evolved_code = await self.nucleus.evolve_code(
                        best_previous['code'],
                        {**analysis, **best_previous},
                        task
                    )
                    generation_time = time.time() - start_time

                    population.append({
                        'code': evolved_code,
                        'variation_type': 'evolved',
                        'generation_time': generation_time,
                        'model_used': self.nucleus.router.select_model(task['description']) if self.nucleus.router else self.nucleus.provider
                    })
            else:
                # Fallback to new solutions
                for i in range(size):
                    start_time = time.time()
                    code = await self.nucleus.generate_solution(task, use_rag=use_rag)
                    generation_time = time.time() - start_time

                    population.append({
                        'code': code,
                        'variation_type': 'fallback',
                        'generation_time': generation_time,
                        'model_used': self.nucleus.router.select_model(task['description']) if self.nucleus.router else self.nucleus.provider
                    })

        return population
