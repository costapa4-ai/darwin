"""Memory system for storing execution history"""
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from utils.logger import setup_logger

logger = setup_logger(__name__)


class MemoryStore:
    """Stores and retrieves execution history"""

    def __init__(self, db_path: str = "/app/data/darwin.db"):
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database with schema"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS executions (
                id TEXT PRIMARY KEY,
                task_description TEXT NOT NULL,
                task_type TEXT NOT NULL,
                code TEXT NOT NULL,
                success BOOLEAN NOT NULL,
                execution_time REAL,
                memory_used INTEGER,
                fitness_score REAL,
                generation_number INTEGER,
                output TEXT,
                error TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_task_type
            ON executions(task_type)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_fitness
            ON executions(fitness_score DESC)
        """)

        conn.commit()
        conn.close()
        logger.info("Database initialized", extra={"db_path": self.db_path})

    def save_execution(self, execution_data: Dict) -> str:
        """Save execution result to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO executions (
                id, task_description, task_type, code, success,
                execution_time, memory_used, fitness_score,
                generation_number, output, error, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            execution_data['id'],
            execution_data['task_description'],
            execution_data['task_type'],
            execution_data['code'],
            execution_data['success'],
            execution_data.get('execution_time'),
            execution_data.get('memory_used'),
            execution_data.get('fitness_score'),
            execution_data.get('generation_number', 0),
            execution_data.get('output', ''),
            execution_data.get('error', ''),
            json.dumps(execution_data.get('metadata', {}))
        ))

        conn.commit()
        conn.close()

        logger.info("Execution saved", extra={
            "execution_id": execution_data['id'],
            "success": execution_data['success']
        })

        return execution_data['id']

    def get_similar_tasks(self, task_description: str, limit: int = 5) -> List[Dict]:
        """Find similar tasks based on keywords (simple implementation)"""
        keywords = set(task_description.lower().split())

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM executions
            WHERE success = 1
            ORDER BY fitness_score DESC, created_at DESC
            LIMIT 20
        """)

        results = []
        for row in cursor.fetchall():
            row_keywords = set(row['task_description'].lower().split())
            overlap = len(keywords & row_keywords)

            if overlap > 0:
                results.append({
                    'id': row['id'],
                    'task_description': row['task_description'],
                    'code': row['code'],
                    'fitness_score': row['fitness_score'],
                    'similarity': overlap / len(keywords)
                })

        conn.close()

        # Sort by similarity and return top results
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results[:limit]

    def get_best_solutions(self, task_type: str, limit: int = 10) -> List[Dict]:
        """Get best historical solutions for a task type"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM executions
            WHERE task_type = ? AND success = 1
            ORDER BY fitness_score DESC
            LIMIT ?
        """, (task_type, limit))

        results = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return results

    def get_execution(self, execution_id: str) -> Optional[Dict]:
        """Get specific execution by ID"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM executions WHERE id = ?", (execution_id,))
        row = cursor.fetchone()
        conn.close()

        return dict(row) if row else None

    def get_stats(self) -> Dict:
        """Get overall system statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                COUNT(*) as total_executions,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_executions,
                AVG(CASE WHEN success = 1 THEN execution_time ELSE NULL END) as avg_execution_time,
                AVG(CASE WHEN success = 1 THEN fitness_score ELSE NULL END) as avg_fitness_score
            FROM executions
        """)

        row = cursor.fetchone()
        conn.close()

        return {
            'total_executions': row[0] or 0,
            'successful_executions': row[1] or 0,
            'success_rate': (row[1] / row[0] * 100) if row[0] > 0 else 0,
            'avg_execution_time': row[2] or 0,
            'avg_fitness_score': row[3] or 0
        }
