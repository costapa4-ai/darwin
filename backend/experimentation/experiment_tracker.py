"""
Experiment Tracker - Tracks and Analyzes Experiments

Maintains history of experiments and provides analytics.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict

from utils.logger import get_logger

logger = get_logger(__name__)


class ExperimentTracker:
    """Tracks experiments and provides analytics"""

    def __init__(self):
        self.experiments = []
        self.state_file = Path("./data/experiments.json")

        # Load existing experiments
        self._load_state()

        logger.info(f"ExperimentTracker initialized ({len(self.experiments)} experiments loaded)")

    def track(self, experiment: Dict[str, Any], result: Dict[str, Any]):
        """Track an experiment"""
        record = {
            'experiment_id': experiment['id'],
            'category': experiment['category'],
            'timestamp': datetime.utcnow().isoformat(),
            'success': result.get('final_success', False),
            'success_rate': result.get('success_rate', 0),
            'iterations': result.get('iterations', 0),
            'learnings_count': len(result.get('learnings', []))
        }

        self.experiments.append(record)
        self._save_state()

    def get_statistics(self, period_days: Optional[int] = None) -> Dict[str, Any]:
        """Get experiment statistics"""
        experiments = self.experiments

        if period_days:
            cutoff = datetime.utcnow() - timedelta(days=period_days)
            experiments = [
                e for e in experiments
                if datetime.fromisoformat(e['timestamp']) >= cutoff
            ]

        if not experiments:
            return {'total': 0}

        # Calculate stats
        total = len(experiments)
        successful = sum(1 for e in experiments if e['success'])

        by_category = defaultdict(int)
        for exp in experiments:
            by_category[exp['category']] += 1

        return {
            'total': total,
            'successful': successful,
            'success_rate': successful / total,
            'by_category': dict(by_category),
            'avg_iterations': sum(e['iterations'] for e in experiments) / total,
            'total_learnings': sum(e['learnings_count'] for e in experiments)
        }

    def _load_state(self):
        """Load experiment history"""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    self.experiments = data.get('experiments', [])
        except Exception as e:
            logger.error(f"Failed to load state: {e}")

    def _save_state(self):
        """Save experiment history"""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, 'w') as f:
                json.dump({
                    'experiments': self.experiments[-1000:],  # Keep last 1000
                    'saved_at': datetime.utcnow().isoformat()
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
