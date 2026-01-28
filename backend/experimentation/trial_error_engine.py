"""
Trial & Error Learning Engine

Learns from experiments through trial and error:
- Runs experiments multiple times with variations
- Learns from failures
- Discovers patterns through iteration
- Builds knowledge from experience
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import hashlib

from utils.logger import get_logger

logger = get_logger(__name__)


class TrialErrorLearningEngine:
    """
    Learning engine based on trial and error methodology
    """

    def __init__(
        self,
        sandbox_manager,
        experiment_designer,
        semantic_memory,
        multi_model_router
    ):
        """
        Initialize trial & error learning engine

        Args:
            sandbox_manager: Sandbox manager for execution
            experiment_designer: Experiment designer
            semantic_memory: Semantic memory for storing learnings
            multi_model_router: AI router for analysis
        """
        self.sandbox_manager = sandbox_manager
        self.experiment_designer = experiment_designer
        self.memory = semantic_memory
        self.ai_router = multi_model_router

        # Learning history
        self.trials = []
        self.discoveries = []

        logger.info("TrialErrorLearningEngine initialized")

    async def run_experiment(
        self,
        experiment: Dict[str, Any],
        iterations: int = 1
    ) -> Dict[str, Any]:
        """
        Run an experiment with trial & error learning

        Args:
            experiment: Experiment specification
            iterations: Number of iterations to try

        Returns:
            Learning result
        """
        logger.info(f"Running experiment: {experiment['id']} ({iterations} iterations)")

        result = {
            'experiment_id': experiment['id'],
            'category': experiment['category'],
            'started_at': datetime.utcnow().isoformat(),
            'iterations': iterations,
            'trials': [],
            'success_count': 0,
            'failure_count': 0,
            'learnings': [],
            'final_success': False
        }

        try:
            # Create sandbox for experiment
            sandbox_id = await self.sandbox_manager.create_sandbox()
            logger.info(f"Created sandbox: {sandbox_id}")

            # Run iterations
            for i in range(iterations):
                trial_result = await self._run_trial(
                    sandbox_id,
                    experiment,
                    iteration=i+1
                )

                result['trials'].append(trial_result)

                if trial_result['success']:
                    result['success_count'] += 1
                else:
                    result['failure_count'] += 1

                # Learn from this trial
                learning = await self._learn_from_trial(
                    trial_result,
                    experiment,
                    iteration=i+1
                )

                if learning:
                    result['learnings'].append(learning)

                # Small delay between iterations
                await asyncio.sleep(1)

            # Final analysis
            result['final_success'] = result['success_count'] > 0
            result['success_rate'] = result['success_count'] / iterations

            # Generate overall insights
            if result['learnings']:
                insights = await self._generate_insights(
                    experiment,
                    result['trials'],
                    result['learnings']
                )
                result['insights'] = insights

            # Store in semantic memory
            await self._store_experiment_results(experiment, result)

            # Clean up sandbox
            await self.sandbox_manager.destroy_sandbox(sandbox_id)

            logger.info(
                f"✅ Experiment completed: {result['success_count']}/{iterations} successful"
            )

        except Exception as e:
            logger.error(f"❌ Experiment failed: {e}")
            result['error'] = str(e)

        result['completed_at'] = datetime.utcnow().isoformat()
        self.trials.append(result)

        return result

    async def _run_trial(
        self,
        sandbox_id: str,
        experiment: Dict[str, Any],
        iteration: int
    ) -> Dict[str, Any]:
        """
        Run a single trial of the experiment

        Args:
            sandbox_id: Sandbox ID
            experiment: Experiment specification
            iteration: Iteration number

        Returns:
            Trial result
        """
        logger.info(f"Running trial {iteration}...")

        trial = {
            'iteration': iteration,
            'started_at': datetime.utcnow().isoformat(),
            'success': False,
            'output': None,
            'error': None,
            'execution_time': 0
        }

        try:
            # Execute experiment code in sandbox
            exec_result = await self.sandbox_manager.execute_in_sandbox(
                sandbox_id,
                experiment['code'],
                timeout=30
            )

            trial['success'] = exec_result['success']
            trial['output'] = exec_result.get('output', '')
            trial['error'] = exec_result.get('error', '')
            trial['execution_time'] = exec_result.get('execution_time', 0)

            status = "✅" if trial['success'] else "❌"
            logger.info(f"{status} Trial {iteration}: {'success' if trial['success'] else 'failed'}")

        except Exception as e:
            trial['error'] = str(e)
            logger.error(f"❌ Trial {iteration} error: {e}")

        trial['completed_at'] = datetime.utcnow().isoformat()
        return trial

    async def _learn_from_trial(
        self,
        trial: Dict[str, Any],
        experiment: Dict[str, Any],
        iteration: int
    ) -> Optional[Dict[str, Any]]:
        """
        Extract learnings from a trial

        Args:
            trial: Trial result
            experiment: Experiment specification
            iteration: Iteration number

        Returns:
            Learning or None
        """
        learning = {
            'iteration': iteration,
            'timestamp': datetime.utcnow().isoformat(),
            'type': 'success' if trial['success'] else 'failure',
            'insights': []
        }

        try:
            if trial['success']:
                # Learn from success
                learning['insights'].append(
                    f"Experiment succeeded in {trial['execution_time']:.3f}s"
                )

                # Analyze output for patterns
                if trial['output']:
                    output_analysis = await self._analyze_output(
                        trial['output'],
                        experiment
                    )
                    learning['insights'].extend(output_analysis)

            else:
                # Learn from failure
                learning['insights'].append(
                    f"Experiment failed: {trial['error'][:100]}"
                )

                # Analyze error for understanding
                if trial['error']:
                    error_analysis = await self._analyze_error(
                        trial['error'],
                        experiment
                    )
                    learning['insights'].extend(error_analysis)

            return learning if learning['insights'] else None

        except Exception as e:
            logger.error(f"Error extracting learning: {e}")
            return None

    async def _analyze_output(
        self,
        output: str,
        experiment: Dict[str, Any]
    ) -> List[str]:
        """
        Analyze experiment output for insights

        Args:
            output: Experiment output
            experiment: Experiment specification

        Returns:
            List of insights
        """
        insights = []

        try:
            # Look for performance metrics
            if 'time' in output.lower() or 'sec' in output.lower():
                insights.append("Performance metrics captured")

            # Look for comparison results
            if 'faster' in output.lower() or 'slower' in output.lower():
                insights.append("Comparative analysis performed")

            # Look for test results
            if 'passed' in output.lower() or 'failed' in output.lower():
                insights.append("Test validation completed")

            # Use AI for deeper analysis if needed
            if len(output) > 100:
                prompt = f"""Analyze this experiment output and extract 1-2 key learnings:

Experiment: {experiment['category']}
Output:
{output[:500]}

Provide 1-2 concise insights:"""

                result = await self.ai_router.generate(
                    task_description="Analyze experiment output",
                    prompt=prompt,
                    max_tokens=150
                )

                ai_insights = result.get('result', '') if isinstance(result, dict) else str(result)

                if ai_insights:
                    # Parse insights
                    for line in ai_insights.split('\n'):
                        line = line.strip('- •*123.').strip()
                        if line and len(line) > 15:
                            insights.append(line)

        except Exception as e:
            logger.error(f"Error analyzing output: {e}")

        return insights[:3]  # Max 3 insights

    async def _analyze_error(
        self,
        error: str,
        experiment: Dict[str, Any]
    ) -> List[str]:
        """
        Analyze experiment error for understanding

        Args:
            error: Error message
            experiment: Experiment specification

        Returns:
            List of insights
        """
        insights = []

        try:
            # Common error patterns
            if 'timeout' in error.lower():
                insights.append("Execution timed out - code may be inefficient")

            if 'memory' in error.lower():
                insights.append("Memory limit exceeded - optimization needed")

            if 'zerodivisionerror' in error.lower():
                insights.append("Division by zero - edge case handling needed")

            if 'indexerror' in error.lower():
                insights.append("Index out of range - bounds checking needed")

            if 'typeerror' in error.lower():
                insights.append("Type mismatch - validation needed")

            # Generic learning
            if not insights:
                insights.append(f"Error encountered: {error[:50]}")

        except Exception as e:
            logger.error(f"Error analyzing error: {e}")

        return insights

    async def _generate_insights(
        self,
        experiment: Dict[str, Any],
        trials: List[Dict[str, Any]],
        learnings: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Generate overall insights from all trials

        Args:
            experiment: Experiment specification
            trials: All trial results
            learnings: All learnings

        Returns:
            List of insights
        """
        insights = []

        try:
            # Success rate insight
            success_count = sum(1 for t in trials if t['success'])
            total = len(trials)
            success_rate = success_count / total if total > 0 else 0

            if success_rate == 1.0:
                insights.append("All trials succeeded - reliable experiment")
            elif success_rate > 0.5:
                insights.append(f"Mostly successful ({success_count}/{total}) - some edge cases remain")
            elif success_rate > 0:
                insights.append(f"Partially successful ({success_count}/{total}) - needs improvement")
            else:
                insights.append("All trials failed - fundamental issues present")

            # Performance insight
            if trials and trials[0]['success']:
                avg_time = sum(t['execution_time'] for t in trials if t['success']) / success_count
                if avg_time < 0.1:
                    insights.append("Fast execution - efficient code")
                elif avg_time > 5:
                    insights.append("Slow execution - optimization opportunity")

            # Compile all trial insights
            all_insights = []
            for learning in learnings:
                all_insights.extend(learning.get('insights', []))

            # Use AI to synthesize
            if all_insights:
                prompt = f"""Based on these trial results, provide 2-3 high-level insights:

Experiment: {experiment['category']}
Hypothesis: {experiment.get('hypothesis', 'N/A')}

Trial insights:
{chr(10).join(f"- {i}" for i in all_insights[:10])}

Provide 2-3 synthesized insights:"""

                result = await self.ai_router.generate(
                    task_description="Synthesize experiment insights",
                    prompt=prompt,
                    max_tokens=200
                )

                ai_insights = result.get('result', '') if isinstance(result, dict) else str(result)

                if ai_insights:
                    for line in ai_insights.split('\n'):
                        line = line.strip('- •*123.').strip()
                        if line and len(line) > 20:
                            insights.append(line)

        except Exception as e:
            logger.error(f"Error generating insights: {e}")

        return insights[:5]  # Max 5 insights

    async def _store_experiment_results(
        self,
        experiment: Dict[str, Any],
        result: Dict[str, Any]
    ):
        """
        Store experiment results in semantic memory

        Args:
            experiment: Experiment specification
            result: Experiment result
        """
        if not self.memory:
            return

        try:
            task_id = f"experiment_{hashlib.md5(experiment['id'].encode()).hexdigest()[:8]}"

            description = f"Experimental Trial & Error Learning\n"
            description += f"Category: {experiment['category']}\n"
            description += f"Hypothesis: {experiment.get('hypothesis', 'N/A')}\n\n"

            description += f"Results:\n"
            description += f"- Iterations: {result['iterations']}\n"
            description += f"- Success rate: {result['success_rate']:.1%}\n"
            description += f"- Learnings: {len(result['learnings'])}\n\n"

            if result.get('insights'):
                description += "Key Insights:\n"
                for i, insight in enumerate(result['insights'], 1):
                    description += f"{i}. {insight}\n"

            await self.memory.store_execution(
                task_id=task_id,
                task_description=description,
                code=experiment['code'][:500],
                result={'success': result['final_success'], 'type': 'experiment'},
                metadata={
                    'type': 'trial_error_experiment',
                    'category': experiment['category'],
                    'success_rate': result['success_rate'],
                    'iterations': result['iterations'],
                    'learning_source': 'experimental_sandbox'
                }
            )

            logger.info(f"✅ Stored experiment results: {experiment['id']}")

        except Exception as e:
            logger.error(f"Error storing experiment results: {e}")

    async def autonomous_experimentation_cycle(self, num_experiments: int = 3) -> Dict[str, Any]:
        """
        Run autonomous experimentation cycle

        Args:
            num_experiments: Number of experiments to run

        Returns:
            Cycle summary
        """
        logger.info(f"Starting autonomous experimentation cycle ({num_experiments} experiments)")

        cycle_result = {
            'started_at': datetime.utcnow().isoformat(),
            'num_experiments': num_experiments,
            'experiments': [],
            'total_trials': 0,
            'total_success': 0,
            'discoveries': []
        }

        for i in range(num_experiments):
            try:
                # Design experiment
                experiment = await self.experiment_designer.design_experiment()

                # Run with trial & error
                result = await self.run_experiment(experiment, iterations=2)

                cycle_result['experiments'].append({
                    'id': experiment['id'],
                    'category': experiment['category'],
                    'success_rate': result.get('success_rate', 0),
                    'insights': result.get('insights', [])
                })

                cycle_result['total_trials'] += result['iterations']
                cycle_result['total_success'] += result['success_count']

                # Collect discoveries
                if result.get('insights'):
                    cycle_result['discoveries'].extend(result['insights'])

                # Delay between experiments
                await asyncio.sleep(2)

            except Exception as e:
                logger.error(f"Error in experiment {i+1}: {e}")

        cycle_result['completed_at'] = datetime.utcnow().isoformat()
        cycle_result['overall_success_rate'] = (
            cycle_result['total_success'] / cycle_result['total_trials']
            if cycle_result['total_trials'] > 0 else 0
        )

        logger.info(
            f"✅ Experimentation cycle complete: "
            f"{cycle_result['total_success']}/{cycle_result['total_trials']} successful"
        )

        self.discoveries.append(cycle_result)

        return cycle_result

    def get_statistics(self) -> Dict[str, Any]:
        """Get trial & error statistics"""
        total_trials = len(self.trials)
        successful = sum(1 for t in self.trials if t.get('final_success', False))

        return {
            'total_experiments': total_trials,
            'successful_experiments': successful,
            'success_rate': successful / total_trials if total_trials > 0 else 0,
            'total_discoveries': len(self.discoveries),
            'recent_experiments': self.trials[-5:] if self.trials else []
        }
