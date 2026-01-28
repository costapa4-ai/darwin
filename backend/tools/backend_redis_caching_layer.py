import redis
import json
from typing import Any, Dict, Optional, List
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class RedisCache:
    """
    A class for managing Redis caching.
    """

    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0, expiry: int = 3600):
        """
        Initializes the RedisCache with connection details.

        Args:
            host (str): The Redis host. Defaults to 'localhost'.
            port (int): The Redis port. Defaults to 6379.
            db (int): The Redis database number. Defaults to 0.
            expiry (int): Default expiry time for cached items in seconds. Defaults to 3600 (1 hour).
        """
        self.host = host
        self.port = port
        self.db = db
        self.expiry = expiry
        self.redis_client: redis.Redis = self._connect_redis()  # Explicitly type hint redis_client

    def _connect_redis(self) -> redis.Redis:
        """
        Establishes a connection to the Redis server.

        Returns:
            redis.Redis: A Redis client instance.
        Raises:
            redis.exceptions.ConnectionError: If a connection to Redis cannot be established.
        """
        try:
            redis_client = redis.Redis(host=self.host, port=self.port, db=self.db, decode_responses=True)
            redis_client.ping()  # Check if the connection is successful
            logging.info("Successfully connected to Redis.")
            return redis_client
        except redis.exceptions.ConnectionError as e:
            logging.error(f"Failed to connect to Redis: {e}")
            raise

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieves data from the cache.

        Args:
            key (str): The key to retrieve.

        Returns:
            Optional[Any]: The cached data, or None if the key is not found.
        """
        try:
            value = self.redis_client.get(key)
            if value:
                try:
                    return json.loads(value)  # Deserialize JSON data
                except json.JSONDecodeError:
                    return value  # Return as string if not JSON
            else:
                return None
        except redis.exceptions.RedisError as e:
            logging.error(f"Error retrieving data from Redis for key {key}: {e}")
            return None

    def set(self, key: str, value: Any, expiry: Optional[int] = None) -> None:
        """
        Stores data in the cache.

        Args:
            key (str): The key to store the data under.
            value (Any): The data to store.
            expiry (Optional[int]): The expiry time in seconds. If None, the default expiry is used.
        """
        try:
            expiry_time = expiry if expiry is not None else self.expiry
            try:
                json_value = json.dumps(value)  # Serialize to JSON
                self.redis_client.set(key, json_value, ex=expiry_time)
            except TypeError:
                self.redis_client.set(key, str(value), ex=expiry_time)  # Store as string if JSON serialization fails
            logging.debug(f"Successfully cached data for key {key} with expiry {expiry_time} seconds.")
        except redis.exceptions.RedisError as e:
            logging.error(f"Error setting data in Redis for key {key}: {e}")

    def delete(self, key: str) -> None:
        """
        Deletes data from the cache.

        Args:
            key (str): The key to delete.
        """
        try:
            self.redis_client.delete(key)
            logging.debug(f"Successfully deleted data for key {key}.")
        except redis.exceptions.RedisError as e:
            logging.error(f"Error deleting data from Redis for key {key}: {e}")

    def clear(self) -> None:
        """
        Clears all data from the cache (use with caution!).
        """
        try:
            self.redis_client.flushdb()
            logging.warning("Successfully cleared all data from Redis.")
        except redis.exceptions.RedisError as e:
            logging.error(f"Error clearing Redis database: {e}")


# Example Usage (Illustrative - adapt to your specific application)

# Initialize Redis cache
redis_host = os.environ.get("REDIS_HOST", "localhost")
redis_port = int(os.environ.get("REDIS_PORT", 6379))
redis_db = int(os.environ.get("REDIS_DB", 0))
cache = RedisCache(host=redis_host, port=redis_port, db=redis_db)


def get_metrics(agent_id: str) -> Dict[str, Any]:
    """
    Fetches metrics for a given agent, using the cache.

    Args:
        agent_id (str): The ID of the agent.

    Returns:
        Dict[str, Any]: The metrics data, or an empty dictionary if not found.
    """
    cache_key = f"metrics:{agent_id}"
    metrics = cache.get(cache_key)
    if metrics:
        logging.info(f"Metrics for agent {agent_id} retrieved from cache.")
        return metrics
    else:
        # Simulate fetching from the database
        metrics = {"cpu_usage": 0.5, "memory_usage": 0.7}  # Replace with actual database retrieval
        cache.set(cache_key, metrics)
        logging.info(f"Metrics for agent {agent_id} fetched from database and cached.")
        return metrics


def get_agent_stats(agent_id: str) -> Dict[str, Any]:
    """
    Fetches agent stats for a given agent, using the cache.

    Args:
        agent_id (str): The ID of the agent.

    Returns:
        Dict[str, Any]: The agent stats data, or an empty dictionary if not found.
    """
    cache_key = f"agent_stats:{agent_id}"
    agent_stats = cache.get(cache_key)
    if agent_stats:
        logging.info(f"Agent stats for agent {agent_id} retrieved from cache.")
        return agent_stats
    else:
        # Simulate fetching from the database
        agent_stats = {"status": "active", "version": "1.0"}  # Replace with actual database retrieval
        cache.set(cache_key, agent_stats)
        logging.info(f"Agent stats for agent {agent_id} fetched from database and cached.")
        return agent_stats


def get_dream_history(user_id: str) -> List[Dict[str, Any]]:
    """
    Fetches dream history for a given user, using the cache.

    Args:
        user_id (str): The ID of the user.

    Returns:
        List[Dict[str, Any]]: The dream history data, or an empty list if not found.
    """
    cache_key = f"dream_history:{user_id}"
    dream_history = cache.get(cache_key)
    if dream_history:
        logging.info(f"Dream history for user {user_id} retrieved from cache.")
        return dream_history
    else:
        # Simulate fetching from the database
        dream_history = [{"dream_id": 1, "content": "Flying"}, {"dream_id": 2, "content": "Meeting aliens"}]  # Replace with actual database retrieval
        cache.set(cache_key, dream_history)
        logging.info(f"Dream history for user {user_id} fetched from database and cached.")
        return dream_history


if __name__ == '__main__':
    # Example usage
    agent_id = "agent123"
    user_id = "user456"

    metrics = get_metrics(agent_id)
    print(f"Metrics: {metrics}")

    agent_stats = get_agent_stats(agent_id)
    print(f"Agent stats: {agent_stats}")

    dream_history = get_dream_history(user_id)
    print(f"Dream history: {dream_history}")

    # Example of deleting a specific key