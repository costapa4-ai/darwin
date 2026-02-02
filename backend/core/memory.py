"""Memory system for storing execution history with vector-based similarity search."""
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
from functools import lru_cache
import hashlib
from utils.logger import setup_logger

logger = setup_logger(__name__)


# Query result cache with TTL tracking
class QueryCache:
    """Simple LRU cache with TTL for query results."""

    def __init__(self, max_size: int = 100, ttl_seconds: int = 300):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, tuple] = {}  # key -> (result, timestamp)
        self._access_order: List[str] = []

    def _make_key(self, query: str, limit: int) -> str:
        """Create cache key from query parameters."""
        return hashlib.md5(f"{query}:{limit}".encode()).hexdigest()

    def get(self, query: str, limit: int) -> Optional[List[Dict]]:
        """Get cached result if valid."""
        key = self._make_key(query, limit)
        if key not in self._cache:
            return None

        result, timestamp = self._cache[key]
        if (datetime.now() - timestamp).total_seconds() > self.ttl_seconds:
            # Expired
            del self._cache[key]
            if key in self._access_order:
                self._access_order.remove(key)
            return None

        # Update access order
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)

        return result

    def set(self, query: str, limit: int, result: List[Dict]) -> None:
        """Cache a query result."""
        key = self._make_key(query, limit)

        # Evict oldest if at capacity
        while len(self._cache) >= self.max_size and self._access_order:
            oldest_key = self._access_order.pop(0)
            self._cache.pop(oldest_key, None)

        self._cache[key] = (result, datetime.now())
        self._access_order.append(key)

    def clear(self) -> None:
        """Clear all cached results."""
        self._cache.clear()
        self._access_order.clear()

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "ttl_seconds": self.ttl_seconds
        }


class MemoryStore:
    """
    Stores and retrieves execution history with optimized similarity search.

    Features:
    - SQLite for persistent storage
    - Vector-based similarity via SemanticMemory integration
    - Query result caching with TTL
    - Keyword-based fallback when semantic search unavailable
    """

    def __init__(self, db_path: str = "/app/data/darwin.db", use_semantic: bool = True):
        self.db_path = db_path
        self.use_semantic = use_semantic
        self._semantic_memory = None
        self._query_cache = QueryCache(max_size=100, ttl_seconds=300)
        self._init_database()
        self._init_semantic_memory()

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

        # Additional indices for optimized queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_success_fitness
            ON executions(success, fitness_score DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_created_at
            ON executions(created_at DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_task_type_success
            ON executions(task_type, success)
        """)

        conn.commit()
        conn.close()
        logger.info("Database initialized", extra={"db_path": self.db_path})

    def _init_semantic_memory(self) -> None:
        """Initialize semantic memory for vector-based search."""
        if not self.use_semantic:
            logger.info("Semantic memory disabled, using keyword-based search")
            return

        try:
            from core.semantic_memory import SemanticMemory
            self._semantic_memory = SemanticMemory()
            logger.info("SemanticMemory integrated for vector-based similarity search")
        except ImportError as e:
            logger.warning(f"SemanticMemory not available: {e}. Using keyword-based fallback.")
            self._semantic_memory = None
        except Exception as e:
            logger.warning(f"Failed to initialize SemanticMemory: {e}. Using keyword-based fallback.")
            self._semantic_memory = None

    def save_execution(self, execution_data: Dict) -> str:
        """Save execution result to database and semantic memory."""
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

        # Also store in semantic memory for vector-based retrieval
        if self._semantic_memory and execution_data.get('success'):
            try:
                import asyncio
                # Run async store in a new event loop if needed
                try:
                    loop = asyncio.get_running_loop()
                    # Already in async context
                    asyncio.create_task(self._store_in_semantic_memory(execution_data))
                except RuntimeError:
                    # No running loop, create one
                    asyncio.run(self._store_in_semantic_memory(execution_data))
            except Exception as e:
                logger.warning(f"Failed to store in semantic memory: {e}")

        # Invalidate query cache since we have new data
        self._query_cache.clear()

        logger.info("Execution saved", extra={
            "execution_id": execution_data['id'],
            "success": execution_data['success'],
            "semantic_stored": self._semantic_memory is not None and execution_data.get('success')
        })

        return execution_data['id']

    async def _store_in_semantic_memory(self, execution_data: Dict) -> None:
        """Store execution in semantic memory asynchronously."""
        await self._semantic_memory.store_execution(
            task_id=execution_data['id'],
            task_description=execution_data['task_description'],
            code=execution_data['code'],
            result={
                "success": execution_data['success'],
                "execution_time": execution_data.get('execution_time', 0)
            },
            metadata={
                "task_type": execution_data['task_type'],
                "fitness_score": execution_data.get('fitness_score', 0)
            }
        )

    def get_similar_tasks(self, task_description: str, limit: int = 5) -> List[Dict]:
        """
        Find similar tasks using vector-based similarity search.

        Uses SemanticMemory for embedding-based similarity when available,
        with keyword-based fallback. Results are cached for performance.

        Args:
            task_description: Description of the task to find similar ones for
            limit: Maximum number of results to return

        Returns:
            List of similar tasks with code, fitness_score, and similarity
        """
        # Check cache first
        cached = self._query_cache.get(task_description, limit)
        if cached is not None:
            logger.debug(f"Cache hit for similarity query (limit={limit})")
            return cached

        # Try vector-based search first
        if self._semantic_memory:
            results = self._get_similar_semantic(task_description, limit)
            if results:
                self._query_cache.set(task_description, limit, results)
                return results

        # Fallback to keyword-based search
        results = self._get_similar_keywords(task_description, limit)
        self._query_cache.set(task_description, limit, results)
        return results

    def _get_similar_semantic(self, task_description: str, limit: int) -> List[Dict]:
        """Vector-based similarity search using SemanticMemory."""
        try:
            import asyncio

            async def _retrieve():
                return await self._semantic_memory.retrieve_similar(
                    query=task_description,
                    n_results=limit,
                    filter_success=True
                )

            # Run async retrieval
            try:
                loop = asyncio.get_running_loop()
                # Can't await in sync function with running loop
                # Use run_coroutine_threadsafe instead
                import concurrent.futures
                future = asyncio.run_coroutine_threadsafe(_retrieve(), loop)
                similar = future.result(timeout=10)
            except RuntimeError:
                # No running loop
                similar = asyncio.run(_retrieve())

            if not similar:
                return []

            # Convert to expected format
            results = []
            for item in similar:
                # Distance is typically euclidean, convert to similarity (0-1 scale)
                distance = item.get('distance', 0)
                # ChromaDB returns L2 distance, convert to similarity
                # Smaller distance = more similar, normalize to 0-1
                similarity = 1.0 / (1.0 + distance) if distance is not None else 0.5

                results.append({
                    'id': item['id'],
                    'task_description': item['metadata'].get('task_description', ''),
                    'code': item['code'],
                    'fitness_score': item['metadata'].get('fitness_score', 0),
                    'similarity': similarity,
                    'search_type': 'semantic'
                })

            logger.debug(f"Semantic search returned {len(results)} results")
            return results

        except Exception as e:
            logger.warning(f"Semantic search failed: {e}. Falling back to keywords.")
            return []

    def _get_similar_keywords(self, task_description: str, limit: int) -> List[Dict]:
        """Keyword-based similarity search (fallback method)."""
        keywords = set(task_description.lower().split())

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Use optimized index
        cursor.execute("""
            SELECT * FROM executions
            WHERE success = 1
            ORDER BY fitness_score DESC, created_at DESC
            LIMIT 50
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
                    'similarity': overlap / len(keywords) if keywords else 0,
                    'search_type': 'keyword'
                })

        conn.close()

        # Sort by similarity and return top results
        results.sort(key=lambda x: x['similarity'], reverse=True)
        logger.debug(f"Keyword search returned {len(results[:limit])} results")
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
        """Get overall system statistics including semantic memory and cache."""
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

        stats = {
            'total_executions': row[0] or 0,
            'successful_executions': row[1] or 0,
            'success_rate': (row[1] / row[0] * 100) if row[0] > 0 else 0,
            'avg_execution_time': row[2] or 0,
            'avg_fitness_score': row[3] or 0,
            'query_cache': self._query_cache.stats(),
            'semantic_memory_enabled': self._semantic_memory is not None
        }

        # Add semantic memory stats if available
        if self._semantic_memory:
            try:
                stats['semantic_memory'] = self._semantic_memory.get_stats()
            except Exception as e:
                stats['semantic_memory'] = {'error': str(e)}

        return stats

    def clear_cache(self) -> None:
        """Clear the query result cache."""
        self._query_cache.clear()
        logger.info("Query cache cleared")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get query cache statistics."""
        return self._query_cache.stats()
