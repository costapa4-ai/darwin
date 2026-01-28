"""
Agent Coordinator - Manages multiple agents and their collaboration
"""
from typing import Dict, List, Optional
from .base_agent import BaseAgent
from .personalities.hacker import HackerAgent
from .personalities.academic import AcademicAgent
from .personalities.pragmatic import PragmaticAgent
from .personalities.artist import ArtistAgent
import asyncio
from datetime import datetime


class AgentCoordinator:
    """
    Coordinates multiple agents to solve tasks
    Handles agent selection, collaboration, and performance tracking
    """

    def __init__(self):
        # Initialize all agent personalities
        self.agents: Dict[str, BaseAgent] = {
            'hacker': HackerAgent(),
            'academic': AcademicAgent(),
            'pragmatic': PragmaticAgent(),
            'artist': ArtistAgent()
        }

        self.task_history = []
        self.collaboration_history = []

    def select_agent(
        self,
        task: Dict,
        mode: str = 'auto'
    ) -> BaseAgent:
        """
        Select appropriate agent for task

        Modes:
        - 'auto': Intelligent selection based on task type
        - 'best': Agent with best historical performance
        - 'round_robin': Rotation between agents
        - specific name: Force a specific agent
        """
        if mode in self.agents:
            return self.agents[mode]

        if mode == 'auto':
            return self._auto_select(task)

        elif mode == 'best':
            return self._select_best_performer()

        elif mode == 'round_robin':
            return self._round_robin_select()

        else:
            # Default: pragmatic
            return self.agents['pragmatic']

    def _auto_select(self, task: Dict) -> BaseAgent:
        """
        Intelligent selection based on task characteristics
        """
        task_type = task.get('type', 'general')
        description = task.get('description', '').lower()
        urgency = task.get('urgency', 'normal')

        # Urgency-based selection
        if urgency == 'high':
            return self.agents['hacker']  # Fast

        # Type-based selection
        if task_type == 'algorithm':
            return self.agents['academic']  # Rigorous

        if task_type == 'creative' or 'creative' in description:
            return self.agents['artist']  # Elegant

        # Keyword-based selection
        if any(word in description for word in ['elegant', 'beautiful', 'clean']):
            return self.agents['artist']

        if any(word in description for word in ['fast', 'quick', 'rapid']):
            return self.agents['hacker']

        if any(word in description for word in ['correct', 'rigorous', 'proven']):
            return self.agents['academic']

        # Default: pragmatic for general tasks
        return self.agents['pragmatic']

    def _select_best_performer(self) -> BaseAgent:
        """
        Select agent with best historical performance
        """
        best_agent = max(
            self.agents.values(),
            key=lambda a: a.get_stats().avg_fitness if a.memory.tasks_solved > 0 else 0
        )
        return best_agent

    def _round_robin_select(self) -> BaseAgent:
        """
        Simple rotation between agents
        """
        agent_list = list(self.agents.values())
        index = len(self.task_history) % len(agent_list)
        return agent_list[index]

    async def solve_with_agent(
        self,
        task: Dict,
        nucleus,
        agent_name: Optional[str] = None,
        mode: str = 'auto'
    ) -> Dict:
        """
        Solve task using specific agent or selection mode

        Args:
            task: Task dictionary
            nucleus: AI nucleus for generation
            agent_name: Force specific agent (optional)
            mode: Selection mode if no agent specified

        Returns:
            Solution with agent metadata
        """
        # Select agent
        if agent_name:
            agent = self.agents.get(agent_name, self.agents['pragmatic'])
        else:
            agent = self.select_agent(task, mode=mode)

        # Solve task
        start_time = datetime.utcnow()
        result = await agent.solve(task, nucleus)
        solve_time = (datetime.utcnow() - start_time).total_seconds()

        # Add timing and task info
        result['solve_time'] = solve_time
        result['task_id'] = task.get('id', 'unknown')

        # Record in history
        self.task_history.append({
            'task': task,
            'agent': agent.name,
            'result': result,
            'timestamp': start_time.isoformat()
        })

        # Agent learns from result
        agent.learn_from_result(result)

        return result

    async def solve_collaborative(
        self,
        task: Dict,
        nucleus,
        num_agents: int = 3
    ) -> Dict:
        """
        Multiple agents work together on a task

        Process:
        1. Each agent proposes a solution
        2. Agents review each other's solutions
        3. Vote for best solution
        4. Return consensus winner

        Args:
            task: Task to solve
            nucleus: AI nucleus
            num_agents: Number of agents to involve

        Returns:
            Best solution with collaboration metadata
        """
        # Select diverse agents
        selected_agents = list(self.agents.values())[:num_agents]

        print(f"🤝 Collaborative solving with {num_agents} agents...")

        # Phase 1: Generate solutions in parallel
        print("📝 Phase 1: Generating solutions...")
        solutions = await asyncio.gather(*[
            agent.solve(task, nucleus)
            for agent in selected_agents
        ])

        # Add agent reference to each solution
        for i, sol in enumerate(solutions):
            sol['proposing_agent'] = selected_agents[i].name

        # Phase 2: Each agent evaluates all solutions
        print("🔍 Phase 2: Cross-evaluation...")
        evaluations = []
        for evaluator in selected_agents:
            agent_scores = []
            for solution in solutions:
                score = self._evaluate_solution(evaluator, solution)
                agent_scores.append(score)
            evaluations.append(agent_scores)

        # Phase 3: Calculate consensus
        print("🗳️  Phase 3: Voting...")
        total_scores = [
            sum(eval_list[i] for eval_list in evaluations)
            for i in range(len(solutions))
        ]

        best_index = total_scores.index(max(total_scores))
        best_solution = solutions[best_index]

        # Check for consensus
        max_score = max(total_scores)
        total_possible = sum(total_scores)
        consensus_strength = max_score / total_possible if total_possible > 0 else 0

        # Add collaboration metadata
        collaboration_data = {
            'agents_involved': [a.name for a in selected_agents],
            'num_solutions': len(solutions),
            'voting_scores': total_scores,
            'consensus_strength': consensus_strength,
            'winner_agent': best_solution['proposing_agent'],
            'all_solutions': [
                {
                    'agent': sol['proposing_agent'],
                    'code_preview': sol.get('code', '')[:100],
                    'score': total_scores[i]
                }
                for i, sol in enumerate(solutions)
            ]
        }

        best_solution['collaboration'] = collaboration_data
        best_solution['solving_mode'] = 'collaborative'

        # Record in history
        self.collaboration_history.append({
            'task': task,
            'collaboration': collaboration_data,
            'timestamp': datetime.utcnow().isoformat()
        })

        print(f"✅ Consensus reached! Winner: {best_solution['proposing_agent']}")
        print(f"   Consensus strength: {consensus_strength:.2%}")

        return best_solution

    def _evaluate_solution(
        self,
        evaluator: BaseAgent,
        solution: Dict
    ) -> float:
        """
        Agent evaluates another agent's solution

        Returns score 0-100 based on evaluator's personality
        """
        code = solution.get('code', '')
        score = 50.0  # Base score

        # Hacker: prefers concise code
        if evaluator.personality == 'hacker':
            lines = len([l for l in code.split('\n') if l.strip()])
            if lines < 15:
                score += 25
            if any(word in code for word in ['lambda', 'comprehension']):
                score += 15

        # Academic: prefers documentation and rigor
        elif evaluator.personality == 'academic':
            if '"""' in code or "'''" in code:
                score += 20
            if 'assert' in code or 'raise' in code:
                score += 15
            if ':' in code and '->' in code:  # Type hints
                score += 10

        # Pragmatic: prefers readability
        elif evaluator.personality == 'pragmatic':
            if '#' in code:  # Comments
                score += 15
            lines = len([l for l in code.split('\n') if l.strip()])
            if 10 < lines < 50:  # Reasonable length
                score += 20

        # Artist: prefers elegance
        elif evaluator.personality == 'artist':
            if any(word in code for word in ['lambda', 'map', 'filter', 'reduce']):
                score += 20
            # Check for expressive names (longer than 3 chars)
            words = code.split()
            expressive = sum(1 for w in words if len(w) > 3 and w.isidentifier())
            if expressive > 5:
                score += 15

        return min(100.0, score)

    def get_all_stats(self) -> Dict:
        """
        Get statistics for all agents
        """
        return {
            name: {
                'stats': agent.get_stats().__dict__,
                'description': agent.describe_self(),
                'config': agent.config,
                'info': agent.to_dict()
            }
            for name, agent in self.agents.items()
        }

    def get_leaderboard(self) -> List[Dict]:
        """
        Get agent performance leaderboard
        """
        leaderboard = []

        for name, agent in self.agents.items():
            stats = agent.get_stats()
            leaderboard.append({
                'agent': name,
                'display_name': agent.name,
                'tasks_completed': stats.tasks_completed,
                'avg_fitness': stats.avg_fitness,
                'specialization': agent.specialization
            })

        # Sort by average fitness
        leaderboard.sort(key=lambda x: x['avg_fitness'], reverse=True)

        return leaderboard

    def get_collaboration_stats(self) -> Dict:
        """
        Get collaboration statistics
        """
        if not self.collaboration_history:
            return {
                'total_collaborations': 0,
                'message': 'No collaborations yet'
            }

        total = len(self.collaboration_history)
        avg_consensus = sum(
            c['collaboration']['consensus_strength']
            for c in self.collaboration_history
        ) / total

        # Count wins per agent
        wins = {}
        for collab in self.collaboration_history:
            winner = collab['collaboration']['winner_agent']
            wins[winner] = wins.get(winner, 0) + 1

        return {
            'total_collaborations': total,
            'avg_consensus_strength': avg_consensus,
            'wins_by_agent': wins,
            'most_winning_agent': max(wins.items(), key=lambda x: x[1])[0] if wins else None
        }
