"""
Curiosity Engine - Autonomous question generation and learning
"""
from typing import Dict, List, Optional
from datetime import datetime


class CuriosityEngine:
    """
    System asks questions, detects anomalies, and explores proactively
    """

    def __init__(self):
        self.questions_asked = []
        self.anomalies_detected = []
        self.curiosity_level = self._genome_get('cognition.curiosity_level', 0.7)

    @staticmethod
    def _genome_get(key: str, default=None):
        """Read a value from the genome, with fallback."""
        try:
            from consciousness.genome_manager import get_genome
            val = get_genome().get(key)
            return val if val is not None else default
        except Exception:
            return default

    async def process_result(self, result: Dict) -> Optional[Dict]:
        """
        Analyze result and generate questions if interesting

        Returns:
            Curiosity response with questions and suggestions, or None
        """
        curiosity_triggered = False
        questions = []

        # Detect anomalies
        if self._is_anomalous(result):
            anomaly = self._analyze_anomaly(result)
            self.anomalies_detected.append(anomaly)
            questions.extend(self._generate_anomaly_questions(anomaly))
            curiosity_triggered = True

        # Detect unexpected patterns
        if self._is_unexpected(result):
            questions.extend(self._generate_curiosity_questions(result))
            curiosity_triggered = True

        if curiosity_triggered:
            response = {
                'curiosity_triggered': True,
                'questions': questions,
                'suggested_explorations': self._suggest_explorations(result),
                'timestamp': datetime.utcnow().isoformat()
            }

            self.questions_asked.extend(questions)
            return response

        return None

    def _is_anomalous(self, result: Dict) -> bool:
        """Detect if result is anomalous"""
        fitness = result.get('fitness_score', 0)
        if fitness > 95 or fitness < 20:
            return True

        exec_time = result.get('execution_time', 0)
        if exec_time > 10 or exec_time < 0.001:
            return True

        return False

    def _analyze_anomaly(self, result: Dict) -> Dict:
        """Analyze anomaly details"""
        return {
            'type': 'performance_anomaly',
            'fitness': result.get('fitness_score', 0),
            'execution_time': result.get('execution_time', 0),
            'detected_at': datetime.utcnow().isoformat()
        }

    def _is_unexpected(self, result: Dict) -> bool:
        """Detect unexpected patterns"""
        # Simplified: trigger on high fitness
        return result.get('fitness_score', 0) > 90

    def _generate_anomaly_questions(self, anomaly: Dict) -> List[str]:
        """Generate questions about anomaly"""
        fitness = anomaly.get('fitness', 0)

        if fitness > 95:
            return [
                f"Why did this solution achieve {fitness:.1f}% fitness?",
                "What makes this approach exceptionally good?",
                "Can this pattern be reused elsewhere?"
            ]
        elif fitness < 20:
            return [
                f"Why did this solution score only {fitness:.1f}%?",
                "What went wrong in this approach?",
                "How can we prevent similar failures?"
            ]

        return []

    def _generate_curiosity_questions(self, result: Dict) -> List[str]:
        """Generate general curiosity questions"""
        return [
            "What patterns led to this success?",
            "How does this compare to similar solutions?",
            "What can I learn from this execution?"
        ]

    def _suggest_explorations(self, result: Dict) -> List[str]:
        """Suggest exploration topics"""
        return [
            "Analyze similar solutions",
            "Test with different parameters",
            "Explore alternative approaches"
        ]

    def get_recent_questions(self, limit: int = 10) -> List[str]:
        """Get recent questions asked"""
        return self.questions_asked[-limit:]

    def get_anomalies(self, limit: int = 10) -> List[Dict]:
        """Get recent anomalies"""
        return self.anomalies_detected[-limit:]

    def get_stats(self) -> Dict:
        """Get curiosity engine statistics"""
        return {
            'total_questions': len(self.questions_asked),
            'total_anomalies': len(self.anomalies_detected),
            'curiosity_level': self.curiosity_level,
            'recent_questions': self.get_recent_questions(5),
            'recent_anomalies_count': len(self.get_anomalies(5))
        }
