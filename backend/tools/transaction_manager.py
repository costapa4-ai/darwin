"""
Transaction Manager for Darwin System

This module provides a comprehensive transaction management system that tracks,
logs, and manages operations with rollback capabilities. It enhances development
workflow by providing atomic operations and audit trails.
"""

import json
import logging
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Union


class TransactionStatus(Enum):
    """Status of a transaction."""
    PENDING = "pending"
    ACTIVE = "active"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


class TransactionPriority(Enum):
    """Priority levels for transactions."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class TransactionOperation:
    """Represents a single operation within a transaction."""
    operation_id: str
    operation_type: str
    description: str
    execute_fn: Optional[Callable] = None
    rollback_fn: Optional[Callable] = None
    execute_args: Dict[str, Any] = field(default_factory=dict)
    rollback_args: Dict[str, Any] = field(default_factory=dict)
    executed: bool = False
    execution_result: Any = None
    execution_time: Optional[float] = None
    error: Optional[str] = None


@dataclass
class Transaction:
    """Represents a transaction with multiple operations."""
    transaction_id: str
    name: str
    status: TransactionStatus
    priority: TransactionPriority
    operations: List[TransactionOperation] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert transaction to dictionary for serialization."""
        return {
            "transaction_id": self.transaction_id,
            "name": self.name,
            "status": self.status.value,
            "priority": self.priority.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self.metadata,
            "error_message": self.error_message,
            "operations_count": len(self.operations)
        }


class TransactionManager:
    """
    Manages transactions with support for atomic operations, rollback,
    and comprehensive logging.
    """
    
    def __init__(
        self,
        log_dir: Optional[Union[str, Path]] = None,
        enable_persistence: bool = True,
        max_concurrent_transactions: int = 10,
        top_k: int = None,
        **kwargs
    ):
        """
        Initialize the Transaction Manager.
        
        Args:
            log_dir: Directory for transaction logs
            enable_persistence: Whether to persist transactions to disk
            max_concurrent_transactions: Maximum number of concurrent transactions
            top_k: For compatibility with tool registry
            **kwargs: Additional compatibility parameters
        """
        self.log_dir = Path(log_dir) if log_dir else Path("transaction_logs")
        self.enable_persistence = enable_persistence
        self.max_concurrent_transactions = max_concurrent_transactions
        
        if self.enable_persistence:
            try:
                self.log_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logging.error(f"Failed to create log directory: {e}")
                self.enable_persistence = False
        
        self.transactions: Dict[str, Transaction] = {}
        self.active_transactions: Set[str] = set()
        self.lock = threading.RLock()
        
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def create_transaction(
        self,
        name: str,
        priority: Union[TransactionPriority, str] = TransactionPriority.MEDIUM,
        metadata: Optional[Dict[str, Any]] = None,
        top_k: int = None,
        **kwargs
    ) -> str:
        """
        Create a new transaction.
        
        Args:
            name: Name of the transaction
            priority: Priority level
            metadata: Additional metadata
            top_k: For compatibility with tool registry
            **kwargs: Additional compatibility parameters
            
        Returns:
            Transaction ID
        """
        try:
            if isinstance(priority, str):
                try:
                    priority = TransactionPriority[priority.upper()]
                except KeyError:
                    priority = TransactionPriority.MEDIUM
            
            with self.lock:
                if len(self.active_transactions) >= self.max_concurrent_transactions:
                    raise RuntimeError(
                        f"Maximum concurrent transactions ({self.max_concurrent_transactions}) reached"
                    )
                
                transaction_id = str(uuid.uuid4())
                transaction = Transaction(
                    transaction_id=transaction_id,
                    name=name,
                    status=TransactionStatus.PENDING,
                    priority=priority,
                    metadata=metadata or {}
                )
                
                self.transactions[transaction_id] = transaction
                self.logger.info(f"Created transaction {transaction_id}: {name}")
                
                if self.enable_persistence:
                    self._persist_transaction(transaction)
                
                return transaction_id
        except Exception as e:
            self.logger.error(f"Failed to create transaction: {e}")
            raise
    
    def add_operation(
        self,
        transaction_id: str,
        operation_type: str,
        description: str,
        execute_fn: Optional[Callable] = None,
        rollback_fn: Optional[Callable] = None,
        execute_args: Optional[Dict[str, Any]] = None,
        rollback_args: Optional[Dict[str, Any]] = None,
        top_k: int = None,
        **kwargs
    ) -> str:
        """
        Add an operation to a transaction.
        
        Args:
            transaction_id: ID of the transaction
            operation_type: Type of operation
            description: Description of the operation
            execute_fn: Function to execute the operation
            rollback_fn: Function to rollback the operation
            execute_args: Arguments for execute function
            rollback_args: Arguments for rollback function
            top_k: For compatibility with tool registry
            **kwargs: Additional compatibility parameters
            
        Returns:
            Operation ID
        """
        try:
            with self.lock:
                if transaction_id not in self.transactions:
                    raise ValueError(f"Transaction {transaction_id} not found")
                
                transaction = self.transactions[transaction_id]
                
                if transaction.status not in [TransactionStatus.PENDING, TransactionStatus.ACTIVE]:
                    raise ValueError(
                        f"Cannot add operation to transaction in {transaction.status.value} state"
                    )
                
                operation_id = str(uuid.uuid4())
                operation = TransactionOperation(
                    operation_id=operation_id,
                    operation_type=operation_type,
                    description=description,
                    execute_fn=execute_fn,
                    rollback_fn=rollback_fn,
                    execute_args=execute_args or {},
                    rollback_args=rollback_args or {}
                )

                transaction.operations.append(operation)
                self.logger.info(
                    f"Added operation {operation_id} ({operation_type}) to transaction {transaction_id}"
                )

                if self.enable_persistence:
                    self._persist_transaction(transaction)

                return operation_id
        except Exception as e:
            self.logger.error(f"Failed to add operation: {e}")
            raise

    def execute_transaction(
        self,
        transaction_id: str,
        top_k: int = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute all operations in a transaction sequentially.

        Args:
            transaction_id: ID of the transaction to execute
            top_k: For compatibility with tool registry
            **kwargs: Additional compatibility parameters

        Returns:
            Dictionary with execution results
        """
        try:
            with self.lock:
                if transaction_id not in self.transactions:
                    raise ValueError(f"Transaction {transaction_id} not found")

                transaction = self.transactions[transaction_id]

                if transaction.status != TransactionStatus.PENDING:
                    raise ValueError(
                        f"Transaction must be PENDING to execute, got {transaction.status.value}"
                    )

                transaction.status = TransactionStatus.ACTIVE
                transaction.started_at = datetime.now()
                self.active_transactions.add(transaction_id)

            executed_ops = []

            for operation in transaction.operations:
                if operation.execute_fn is None:
                    operation.executed = True
                    executed_ops.append(operation)
                    continue

                try:
                    start_time = time.time()
                    result = operation.execute_fn(**operation.execute_args)
                    operation.execution_time = time.time() - start_time
                    operation.execution_result = result
                    operation.executed = True
                    executed_ops.append(operation)

                    self.logger.info(
                        f"Executed operation {operation.operation_id} "
                        f"({operation.operation_type}) in {operation.execution_time:.3f}s"
                    )
                except Exception as e:
                    operation.error = str(e)
                    self.logger.error(
                        f"Operation {operation.operation_id} failed: {e}"
                    )

                    # Rollback all previously executed operations
                    self._rollback_operations(executed_ops)

                    with self.lock:
                        transaction.status = TransactionStatus.FAILED
                        transaction.error_message = str(e)
                        transaction.completed_at = datetime.now()
                        self.active_transactions.discard(transaction_id)

                    if self.enable_persistence:
                        self._persist_transaction(transaction)

                    return {
                        "status": "failed",
                        "transaction_id": transaction_id,
                        "error": str(e),
                        "executed_operations": len(executed_ops),
                        "total_operations": len(transaction.operations)
                    }

            # All operations succeeded — commit
            with self.lock:
                transaction.status = TransactionStatus.COMMITTED
                transaction.completed_at = datetime.now()
                self.active_transactions.discard(transaction_id)

            if self.enable_persistence:
                self._persist_transaction(transaction)

            total_time = sum(
                op.execution_time for op in transaction.operations
                if op.execution_time is not None
            )

            self.logger.info(
                f"Transaction {transaction_id} committed successfully "
                f"({len(transaction.operations)} operations in {total_time:.3f}s)"
            )

            return {
                "status": "committed",
                "transaction_id": transaction_id,
                "operations_executed": len(transaction.operations),
                "total_time": total_time
            }

        except Exception as e:
            self.logger.error(f"Failed to execute transaction: {e}")
            raise

    def rollback_transaction(
        self,
        transaction_id: str,
        top_k: int = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Rollback a transaction by undoing all executed operations.

        Args:
            transaction_id: ID of the transaction to rollback
            top_k: For compatibility with tool registry
            **kwargs: Additional compatibility parameters

        Returns:
            Dictionary with rollback results
        """
        try:
            with self.lock:
                if transaction_id not in self.transactions:
                    raise ValueError(f"Transaction {transaction_id} not found")

                transaction = self.transactions[transaction_id]

            executed_ops = [op for op in transaction.operations if op.executed]
            rollback_results = self._rollback_operations(executed_ops)

            with self.lock:
                transaction.status = TransactionStatus.ROLLED_BACK
                transaction.completed_at = datetime.now()
                self.active_transactions.discard(transaction_id)

            if self.enable_persistence:
                self._persist_transaction(transaction)

            self.logger.info(
                f"Transaction {transaction_id} rolled back "
                f"({len(executed_ops)} operations reversed)"
            )

            return {
                "status": "rolled_back",
                "transaction_id": transaction_id,
                "operations_rolled_back": len(executed_ops),
                "rollback_results": rollback_results
            }

        except Exception as e:
            self.logger.error(f"Failed to rollback transaction: {e}")
            raise

    def _rollback_operations(self, operations: List[TransactionOperation]) -> List[Dict]:
        """Rollback a list of operations in reverse order."""
        results = []
        for operation in reversed(operations):
            if operation.rollback_fn is None:
                results.append({
                    "operation_id": operation.operation_id,
                    "status": "skipped",
                    "reason": "no rollback function"
                })
                continue

            try:
                operation.rollback_fn(**operation.rollback_args)
                results.append({
                    "operation_id": operation.operation_id,
                    "status": "rolled_back"
                })
                self.logger.info(f"Rolled back operation {operation.operation_id}")
            except Exception as e:
                results.append({
                    "operation_id": operation.operation_id,
                    "status": "rollback_failed",
                    "error": str(e)
                })
                self.logger.error(
                    f"Failed to rollback operation {operation.operation_id}: {e}"
                )

        return results

    def get_transaction_status(
        self,
        transaction_id: str,
        top_k: int = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get the current status of a transaction.

        Args:
            transaction_id: ID of the transaction
            top_k: For compatibility with tool registry
            **kwargs: Additional compatibility parameters

        Returns:
            Dictionary with transaction status information
        """
        with self.lock:
            if transaction_id not in self.transactions:
                return {"status": "error", "error": "Transaction not found"}

            transaction = self.transactions[transaction_id]
            result = transaction.to_dict()
            result["operations"] = [
                {
                    "operation_id": op.operation_id,
                    "type": op.operation_type,
                    "description": op.description,
                    "executed": op.executed,
                    "execution_time": op.execution_time,
                    "error": op.error
                }
                for op in transaction.operations
            ]
            return result

    def list_transactions(
        self,
        status_filter: Optional[str] = None,
        top_k: int = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        List all transactions, optionally filtered by status.

        Args:
            status_filter: Optional status to filter by
            top_k: For compatibility with tool registry
            **kwargs: Additional compatibility parameters

        Returns:
            List of transaction dictionaries
        """
        with self.lock:
            transactions = list(self.transactions.values())

        if status_filter:
            try:
                filter_status = TransactionStatus(status_filter)
                transactions = [t for t in transactions if t.status == filter_status]
            except ValueError:
                pass

        return [t.to_dict() for t in transactions]

    @contextmanager
    def transaction(
        self,
        name: str,
        priority: Union[TransactionPriority, str] = TransactionPriority.MEDIUM,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Context manager for transaction handling.

        Usage:
            with manager.transaction("my_operation") as txn_id:
                manager.add_operation(txn_id, "step1", "First step", fn1)
                manager.execute_transaction(txn_id)
        """
        txn_id = self.create_transaction(name, priority, metadata)
        try:
            yield txn_id
        except Exception as e:
            self.logger.error(f"Transaction {txn_id} context error: {e}")
            if txn_id in self.active_transactions:
                self.rollback_transaction(txn_id)
            raise

    def _persist_transaction(self, transaction: Transaction) -> None:
        """Persist transaction state to disk."""
        if not self.enable_persistence:
            return

        try:
            filepath = self.log_dir / f"{transaction.transaction_id}.json"
            with open(filepath, 'w') as f:
                json.dump(transaction.to_dict(), f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to persist transaction: {e}")