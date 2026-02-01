"""
Distributed Consciousness - Multi-instance Darwin coordination

Enables multiple Darwin instances to:
- Discover each other on the network
- Share memories and learnings
- Coordinate activities
- Fork and merge consciousness states
"""

from .instance_registry import InstanceRegistry, DarwinInstance, InstanceStatus
from .memory_sync import MemorySyncProtocol, SyncMode
from .mesh_network import MeshNetwork, PeerConnection

__all__ = [
    'InstanceRegistry',
    'DarwinInstance',
    'InstanceStatus',
    'MemorySyncProtocol',
    'SyncMode',
    'MeshNetwork',
    'PeerConnection'
]
