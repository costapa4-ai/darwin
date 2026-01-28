"""
Semantic Memory System with ChromaDB and RAG
Provides vector-based memory storage and retrieval for intelligent task execution
"""
import asyncio
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional
import json
from datetime import datetime
import numpy as np
from sklearn.cluster import DBSCAN

from utils.logger import get_logger

logger = get_logger(__name__)


class SemanticMemory:
    """
    Semantic memory system using ChromaDB for vector storage
    Enables RAG (Retrieval Augmented Generation) for intelligent code evolution
    """

    def __init__(self, persist_directory: str = "./data/chroma"):
        """
        Initialize semantic memory with ChromaDB and embedding model

        Args:
            persist_directory: Directory to persist vector database
        """
        self.persist_directory = persist_directory

        # Initialize ChromaDB client
        self.client = chromadb.Client(Settings(
            persist_directory=persist_directory,
            anonymized_telemetry=False
        ))

        # Initialize embedding model
        logger.info("Loading sentence-transformers model...")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

        # Create or get collections
        self.executions_collection = self.client.get_or_create_collection(
            name="executions",
            metadata={"description": "Task execution history"}
        )

        self.patterns_collection = self.client.get_or_create_collection(
            name="patterns",
            metadata={"description": "Reusable code patterns"}
        )

        logger.info("SemanticMemory initialized successfully")

    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding vector for text"""
        embedding = self.embedding_model.encode(text)
        return embedding.tolist()

    async def store_execution(
        self,
        task_id: str,
        task_description: str,
        code: str,
        result: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Store task execution in semantic memory

        Args:
            task_id: Unique task identifier
            task_description: Natural language task description
            code: Generated code
            result: Execution result
            metadata: Additional metadata
        """
        try:
            # Combine task and code for embedding
            combined_text = f"{task_description}\n\n{code}"

            # Generate embedding
            embedding = self._generate_embedding(combined_text)

            # Prepare metadata
            meta = {
                "task_description": task_description,
                "timestamp": datetime.now().isoformat(),
                "success": result.get("success", False),
                "execution_time": result.get("execution_time", 0),
                **(metadata or {})
            }

            # Store in ChromaDB
            self.executions_collection.add(
                ids=[task_id],
                embeddings=[embedding],
                documents=[code],
                metadatas=[meta]
            )

            logger.info(f"Stored execution {task_id} in semantic memory")

        except Exception as e:
            logger.error(f"Failed to store execution: {e}")

    async def retrieve_similar(
        self,
        query: str,
        n_results: int = 5,
        filter_success: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Retrieve similar past executions using semantic search

        Args:
            query: Task description to search for
            n_results: Number of results to return
            filter_success: Only return successful executions

        Returns:
            List of similar executions with code and metadata
        """
        try:
            # Generate query embedding
            query_embedding = self._generate_embedding(query)

            # Build filter
            where_filter = {"success": True} if filter_success else None

            # Query ChromaDB
            results = self.executions_collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where_filter
            )

            # Format results
            similar_executions = []
            for i in range(len(results["ids"][0])):
                similar_executions.append({
                    "id": results["ids"][0][i],
                    "code": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i] if "distances" in results else None
                })

            logger.info(f"Retrieved {len(similar_executions)} similar executions")
            return similar_executions

        except Exception as e:
            logger.error(f"Failed to retrieve similar executions: {e}")
            return []

    async def find_reusable_patterns(self, min_cluster_size: int = 3) -> List[Dict[str, Any]]:
        """
        Identify reusable code patterns using clustering

        Args:
            min_cluster_size: Minimum executions to form a pattern

        Returns:
            List of identified patterns with example code
        """
        try:
            # Get all executions
            all_executions = self.executions_collection.get(
                where={"success": True},
                include=["embeddings", "documents", "metadatas"]
            )

            if len(all_executions["ids"]) < min_cluster_size:
                logger.info("Not enough executions to identify patterns")
                return []

            # Perform clustering on embeddings
            embeddings = np.array(all_executions["embeddings"])
            clustering = DBSCAN(eps=0.3, min_samples=min_cluster_size).fit(embeddings)

            # Extract patterns
            patterns = []
            for cluster_id in set(clustering.labels_):
                if cluster_id == -1:  # Noise
                    continue

                # Get executions in this cluster
                cluster_indices = np.where(clustering.labels_ == cluster_id)[0]
                cluster_docs = [all_executions["documents"][i] for i in cluster_indices]
                cluster_metas = [all_executions["metadatas"][i] for i in cluster_indices]

                # Create pattern
                pattern = {
                    "pattern_id": f"pattern_{cluster_id}",
                    "occurrences": len(cluster_indices),
                    "example_code": cluster_docs[0],
                    "task_types": [meta.get("task_description", "")[:50] for meta in cluster_metas[:3]]
                }
                patterns.append(pattern)

                # Store pattern in patterns collection
                pattern_embedding = embeddings[cluster_indices[0]].tolist()
                self.patterns_collection.add(
                    ids=[pattern["pattern_id"]],
                    embeddings=[pattern_embedding],
                    documents=[pattern["example_code"]],
                    metadatas=[{
                        "occurrences": pattern["occurrences"],
                        "discovered_at": datetime.now().isoformat()
                    }]
                )

            logger.info(f"Identified {len(patterns)} reusable patterns")
            return patterns

        except Exception as e:
            logger.error(f"Failed to find patterns: {e}")
            return []

    async def get_rag_context(self, task_description: str, max_examples: int = 3) -> str:
        """
        Get RAG context for task generation

        Args:
            task_description: Current task description
            max_examples: Maximum number of examples to include

        Returns:
            Formatted context string with relevant examples
        """
        try:
            # Retrieve similar executions
            similar = await self.retrieve_similar(task_description, n_results=max_examples)

            if not similar:
                return ""

            # Format context
            context_parts = ["Here are similar tasks I've solved before:\n"]
            for i, execution in enumerate(similar, 1):
                context_parts.append(f"\nExample {i}:")
                context_parts.append(f"Task: {execution['metadata'].get('task_description', 'N/A')}")
                context_parts.append(f"Code:\n{execution['code']}")
                context_parts.append(f"Success: {execution['metadata'].get('success', False)}")

            return "\n".join(context_parts)

        except Exception as e:
            logger.error(f"Failed to get RAG context: {e}")
            return ""

    def get_stats(self) -> Dict[str, Any]:
        """Get semantic memory statistics"""
        try:
            executions = self.executions_collection.get()
            patterns = self.patterns_collection.get()

            return {
                "total_executions": len(executions["ids"]),
                "total_patterns": len(patterns["ids"]),
                "collection_names": ["executions", "patterns"]
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {}
