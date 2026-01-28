"""Metrics collection and reporting service"""
from typing import Dict
from datetime import datetime
from core.memory import MemoryStore
from utils.logger import setup_logger

logger = setup_logger(__name__)


class MetricsService:
    """Collects and provides system metrics"""

    def __init__(self, memory: MemoryStore):
        self.memory = memory
        self.start_time = datetime.now()

    def get_system_metrics(self) -> Dict:
        """Get comprehensive system metrics"""
        db_stats = self.memory.get_stats()
        uptime = (datetime.now() - self.start_time).total_seconds()

        metrics = {
            'system': {
                'uptime_seconds': uptime,
                'uptime_formatted': self._format_uptime(uptime),
                'start_time': self.start_time.isoformat()
            },
            'executions': {
                'total': db_stats['total_executions'],
                'successful': db_stats['successful_executions'],
                'failed': db_stats['total_executions'] - db_stats['successful_executions'],
                'success_rate': round(db_stats['success_rate'], 2)
            },
            'performance': {
                'avg_execution_time': round(db_stats['avg_execution_time'], 4),
                'avg_fitness_score': round(db_stats['avg_fitness_score'], 2)
            }
        }

        logger.info("Metrics collected", extra=metrics)
        return metrics

    def get_task_metrics(self, task_id: str) -> Dict:
        """Get metrics for a specific task"""
        # This would query executions for a specific task
        # Simplified for MVP
        return {
            'task_id': task_id,
            'status': 'completed',
            'generations': 0
        }

    def _format_uptime(self, seconds: float) -> str:
        """Format uptime in human-readable format"""
        hours, remainder = divmod(int(seconds), 3600)
        minutes, seconds = divmod(remainder, 60)

        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
