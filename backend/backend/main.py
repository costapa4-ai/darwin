```python
"""
Distributed Consensus System for Self-Improving AI
Implements Raft-based consensus with CAP theorem considerations
"""

import asyncio
import time
import random
import json
import hashlib
from typing import Dict, List, Optional, Set, Tuple, Any
from enum import Enum
from dataclasses import dataclass, field, asdict
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NodeState(Enum):
    """States a node can be in according to Raft consensus"""
    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"


class ConsistencyLevel(Enum):
    """CAP theorem consistency levels"""
    STRONG = "strong"  # CP - Consistency + Partition tolerance
    EVENTUAL = "eventual"  # AP - Availability + Partition tolerance
    WEAK = "weak"  # High availability, eventual consistency


@dataclass
class LogEntry:
    """Represents a single log entry in the distributed log"""
    term: int
    index: int
    command: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    checksum: str = field(default="")
    
    def __post_init__(self):
        if not self.checksum:
            self.checksum = self._calculate_checksum()
    
    def _calculate_checksum(self) -> str:
        """Calculate SHA-256 checksum for integrity verification"""
        data = f"{self.term}:{self.index}:{json.dumps(self.command, sort_keys=True)}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def verify_integrity(self) -> bool:
        """Verify entry integrity"""
        return self.checksum == self._calculate_checksum()


@dataclass
class VoteRequest:
    """Request for votes during leader election"""
    term: int
    candidate_id: str
    last_log_index: int
    last_log_term: int


@dataclass
class VoteResponse:
    """Response to vote request"""
    term: int
    vote_granted: bool


@dataclass
class AppendEntriesRequest:
    """Request to append entries (heartbeat or log replication)"""
    term: int
    leader_id: str
    prev_log_index: int
    prev_log_term: int
    entries: List[LogEntry]
    leader_commit: int


@dataclass
class AppendEntriesResponse:
    """Response to append entries request"""
    term: int
    success: bool
    match_index: int


class ConsensusNode:
    """
    Implements Raft consensus algorithm for distributed coordination
    Handles leader election, log replication, and safety guarantees
    """
    
    def __init__(
        self,
        node_id: str,
        peers: List[str],
        consistency_level: ConsistencyLevel = ConsistencyLevel.STRONG,
        election_timeout_range: Tuple[float, float] = (0.15, 0.30),
        heartbeat_interval: float = 0.05
    ):
        self.node_id = node_id
        self.peers = peers
        self.consistency_level = consistency_level
        self.election_timeout_range = election_timeout_range
        self.heartbeat_interval = heartbeat_interval
        
        self.current_term: int = 0
        self.voted_for: Optional[str] = None
        self.log: List[LogEntry] = []
        self.commit_index: int = -1
        self.last_applied: int = -1
        
        self.state: NodeState = NodeState.FOLLOWER
        self.leader_id: Optional[str] = None
        
        self.next_index: Dict[str, int] = {peer: 0 for peer in peers}
        self.match_index: Dict[str, int] = {peer: -1 for peer in peers}
        
        self.votes_received: Set[str] = set()
        self.last_heartbeat: float = time.time()
        self.election_timeout: float = self._random_election_timeout()
        
        self.state_machine: Dict[str, Any] = {}
        self.is_running: bool = False
        
        logger.info(f"Node {node_id} initialized with consistency level: {consistency_level.value}")
    
    def _random_election_timeout(self) -> float:
        """Generate random election timeout to prevent split votes"""
        return random.uniform(*self.election_timeout_range)
    
    async def start(self):
        """Start the consensus node"""
        self.is_running = True
        await asyncio.gather(
            self._election_timer(),
            self._heartbeat_timer(),
            self._apply_committed_entries()
        )
    
    async def stop(self):
        """Stop the consensus node"""
        self.is_running = False
        logger.info(f"Node {self.node_id} stopped")
    
    async def _election_timer(self):
        """Monitor election timeout and trigger elections"""
        while self.is_running:
            await asyncio.sleep(0.01)
            
            if self.state == NodeState.LEADER:
                continue
            
            if time.time() - self.last_heartbeat > self.election_timeout:
                await self._start_election()
    
    async def _start_election(self):
        """Initiate leader election"""
        self.state = NodeState.CANDIDATE
        self.current_term += 1
        self.voted_for = self.node_id
        self.votes_received = {self.node_id}
        self.election_timeout = self._random_election_timeout()
        self.last_heartbeat = time.time()
        
        logger.info(f"Node {self.node_id} starting election for term {self.current_term}")
        
        last_log_index = len(self.log) - 1
        last_log_term = self.log[-1].term if self.log else 0
        
        vote_request = VoteRequest(
            term=self.current_term,
            candidate_id=self.node_id,
            last_log_index=last_log_index,
            last_log_term=last_log_term
        )
        
        vote_tasks = [
            self._request_vote(peer, vote_request)
            for peer in self.peers
        ]
        
        await asyncio.gather(*vote_tasks, return_exceptions=True)
        
        if len(self.votes_received) > (len(self.peers) + 1) // 2:
            await self._become_leader()
    
    async def _request_vote(self, peer: str, vote_request: VoteRequest):
        """Request vote from a peer"""
        try:
            response = await self._send_vote_request(peer, vote_request)
            
            if response.term > self.current_term:
                await self._step_down(response.term)
                return
            
            if response.vote_granted and self.state == NodeState.CANDIDATE:
                self.votes_received.add(peer)
                logger.debug(f"Node {self.node_id} received vote from {peer}")
        except Exception as e:
            logger.warning(f"Failed to request vote from {peer}: {e}")
    
    async def _send_vote_request(self, peer: str, vote_request: VoteRequest) -> VoteResponse:
        """Simulate sending vote request (implement actual RPC in production)"""
        await asyncio.sleep(random.uniform(0.01, 0.05))
        
        vote_granted = random.random() > 0.2
        return VoteResponse(term=self.current_term, vote_granted=vote_granted)
    
    async def handle_vote_request(self, request: VoteRequest) -> VoteResponse:
        """Handle incoming vote request"""
        if request.term > self.current_term:
            await self._step_down(