"""
Distributed Consciousness API Routes
Endpoints for multi-instance coordination
"""
from fastapi import APIRouter, HTTPException
from typing import Optional, List
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/distributed", tags=["distributed"])

# Global service instances
_instance_registry = None
_memory_sync = None
_mesh_network = None
_fork_manager = None


class ConnectPeerRequest(BaseModel):
    """Request to connect to a peer"""
    peer_id: str
    peer_name: str
    address: str


class SyncRequest(BaseModel):
    """Request to sync with a peer"""
    peer_address: str
    mode: str = "bidirectional"
    memory_types: Optional[List[str]] = None


class CreateForkRequest(BaseModel):
    """Request to create a consciousness fork"""
    name: str
    description: str = ""


class MergeForkRequest(BaseModel):
    """Request to merge a fork"""
    strategy: str = "newer_wins"


class AddSeedNodeRequest(BaseModel):
    """Request to add a seed node"""
    address: str


# ============== Registry Endpoints ==============

@router.get("/status")
async def get_distributed_status():
    """Get overall distributed system status"""
    status = {
        'registry': None,
        'mesh': None,
        'sync': None,
        'fork_manager': None
    }

    if _instance_registry:
        status['registry'] = _instance_registry.get_status()

    if _mesh_network:
        status['mesh'] = _mesh_network.get_status()

    if _memory_sync:
        status['sync'] = _memory_sync.get_status()

    if _fork_manager:
        status['fork_manager'] = _fork_manager.get_status()

    return {
        'success': True,
        'enabled': _instance_registry is not None,
        **status
    }


@router.get("/instances")
async def list_instances(include_offline: bool = False):
    """List all known Darwin instances"""
    if not _instance_registry:
        return {
            'success': True,
            'instances': [],
            'message': 'Distributed system not enabled'
        }

    instances = _instance_registry.get_all_instances(include_offline)
    return {
        'success': True,
        'instances': [i.to_dict() for i in instances],
        'count': len(instances)
    }


@router.get("/instances/{instance_id}")
async def get_instance(instance_id: str):
    """Get a specific instance"""
    if not _instance_registry:
        raise HTTPException(status_code=503, detail="Distributed system not enabled")

    instance = _instance_registry.get_instance(instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail="Instance not found")

    return {
        'success': True,
        'instance': instance.to_dict()
    }


@router.post("/seed-node")
async def add_seed_node(request: AddSeedNodeRequest):
    """Add a seed node for discovery"""
    if not _instance_registry:
        raise HTTPException(status_code=503, detail="Distributed system not enabled")

    _instance_registry.add_seed_node(request.address)
    return {
        'success': True,
        'message': f'Added seed node: {request.address}'
    }


# ============== Mesh Network Endpoints ==============

@router.get("/mesh/status")
async def get_mesh_status():
    """Get mesh network status"""
    if not _mesh_network:
        return {
            'success': True,
            'enabled': False,
            'message': 'Mesh network not enabled'
        }

    return {
        'success': True,
        'enabled': True,
        **_mesh_network.get_status()
    }


@router.post("/mesh/connect")
async def connect_to_peer(request: ConnectPeerRequest):
    """Connect to a peer instance"""
    if not _mesh_network:
        raise HTTPException(status_code=503, detail="Mesh network not enabled")

    success = await _mesh_network.connect_peer(
        request.peer_id,
        request.peer_name,
        request.address
    )

    if success:
        return {
            'success': True,
            'message': f'Connected to {request.peer_name}'
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to connect to peer")


@router.post("/mesh/disconnect/{peer_id}")
async def disconnect_from_peer(peer_id: str):
    """Disconnect from a peer"""
    if not _mesh_network:
        raise HTTPException(status_code=503, detail="Mesh network not enabled")

    await _mesh_network.disconnect_peer(peer_id)
    return {
        'success': True,
        'message': f'Disconnected from {peer_id}'
    }


@router.get("/mesh/peers")
async def list_peers():
    """List connected peers"""
    if not _mesh_network:
        return {
            'success': True,
            'peers': [],
            'message': 'Mesh network not enabled'
        }

    peers = _mesh_network.get_connected_peers()
    return {
        'success': True,
        'peers': [p.to_dict() for p in peers],
        'count': len(peers)
    }


@router.post("/mesh/ping")
async def mesh_ping(data: dict):
    """Handle mesh ping (internal endpoint)"""
    return {
        'success': True,
        'pong': True,
        'instance_id': _instance_registry.instance_id if _instance_registry else None
    }


@router.post("/mesh/receive")
async def mesh_receive(data: dict):
    """Receive a mesh message (internal endpoint)"""
    if not _mesh_network:
        raise HTTPException(status_code=503, detail="Mesh network not enabled")

    result = await _mesh_network.receive_message(data)
    return result


# ============== Sync Endpoints ==============

@router.get("/sync/status")
async def get_sync_status():
    """Get memory sync status"""
    if not _memory_sync:
        return {
            'success': True,
            'enabled': False,
            'message': 'Memory sync not enabled'
        }

    return {
        'success': True,
        'enabled': True,
        **_memory_sync.get_status()
    }


@router.post("/sync/start")
async def start_sync(request: SyncRequest):
    """Start a sync with a peer"""
    if not _memory_sync:
        raise HTTPException(status_code=503, detail="Memory sync not enabled")

    from distributed.memory_sync import SyncMode, MemoryType

    try:
        mode = SyncMode(request.mode)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid sync mode: {request.mode}")

    memory_types = None
    if request.memory_types:
        try:
            memory_types = [MemoryType(t) for t in request.memory_types]
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid memory type: {e}")

    result = await _memory_sync.sync_with_peer(
        peer_address=request.peer_address,
        mode=mode,
        memory_types=memory_types
    )

    return {
        'success': result.success,
        'result': result.to_dict()
    }


@router.get("/sync/index")
async def get_sync_index(types: str = None):
    """Get local memory index for sync"""
    if not _memory_sync:
        return {
            'success': True,
            'index': {}
        }

    from distributed.memory_sync import MemoryType

    memory_types = None
    if types:
        try:
            memory_types = [MemoryType(t) for t in types.split(',')]
        except ValueError:
            memory_types = None

    index = _memory_sync.get_local_index(memory_types)
    return {
        'success': True,
        'index': index
    }


@router.post("/sync/memories")
async def get_memories_for_sync(data: dict):
    """Get specific memories for sync (internal endpoint)"""
    # This would be implemented to return requested memories
    return {
        'success': True,
        'memories': []
    }


@router.post("/sync/receive")
async def receive_sync_memories(data: dict):
    """Receive memories from a sync push (internal endpoint)"""
    if not _memory_sync:
        raise HTTPException(status_code=503, detail="Memory sync not enabled")

    result = await _memory_sync.receive_memories(
        source_instance=data.get('source_instance'),
        memories=data.get('memories', [])
    )

    return result


@router.get("/sync/conflicts")
async def get_sync_conflicts():
    """Get unresolved sync conflicts"""
    if not _memory_sync:
        return {
            'success': True,
            'conflicts': []
        }

    conflicts = _memory_sync.get_conflicts()
    return {
        'success': True,
        'conflicts': conflicts,
        'count': len(conflicts)
    }


@router.post("/sync/conflicts/{conflict_id}/resolve")
async def resolve_conflict(conflict_id: str, keep: str = "local"):
    """Resolve a sync conflict"""
    if not _memory_sync:
        raise HTTPException(status_code=503, detail="Memory sync not enabled")

    if keep not in ('local', 'remote'):
        raise HTTPException(status_code=400, detail="keep must be 'local' or 'remote'")

    success = _memory_sync.resolve_conflict(conflict_id, keep)
    if success:
        return {
            'success': True,
            'message': f'Conflict resolved, kept {keep} version'
        }
    else:
        raise HTTPException(status_code=404, detail="Conflict not found")


@router.get("/sync/history")
async def get_sync_history(limit: int = 10):
    """Get sync history"""
    if not _memory_sync:
        return {
            'success': True,
            'history': []
        }

    history = _memory_sync.get_sync_history(limit)
    return {
        'success': True,
        'history': history
    }


# ============== Fork/Merge Endpoints ==============

@router.get("/forks")
async def list_forks(include_merged: bool = False):
    """List consciousness forks"""
    if not _fork_manager:
        return {
            'success': True,
            'forks': [],
            'message': 'Fork manager not enabled'
        }

    forks = _fork_manager.get_all_forks(include_merged)
    return {
        'success': True,
        'forks': [f.to_dict() for f in forks],
        'count': len(forks)
    }


@router.post("/forks")
async def create_fork(request: CreateForkRequest):
    """Create a new consciousness fork"""
    if not _fork_manager:
        raise HTTPException(status_code=503, detail="Fork manager not enabled")

    try:
        fork = await _fork_manager.create_fork(
            fork_name=request.name,
            description=request.description
        )
        return {
            'success': True,
            'fork': fork.to_dict()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/forks/{fork_id}")
async def get_fork(fork_id: str):
    """Get a specific fork"""
    if not _fork_manager:
        raise HTTPException(status_code=503, detail="Fork manager not enabled")

    fork = _fork_manager.get_fork(fork_id)
    if not fork:
        raise HTTPException(status_code=404, detail="Fork not found")

    return {
        'success': True,
        'fork': fork.to_dict()
    }


@router.get("/forks/{fork_id}/diff")
async def get_fork_diff(fork_id: str):
    """Get diff between current state and fork"""
    if not _fork_manager:
        raise HTTPException(status_code=503, detail="Fork manager not enabled")

    try:
        diff = await _fork_manager.get_diff(fork_id)
        return {
            'success': True,
            'fork_id': fork_id,
            'diff': diff.to_dict()
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/forks/{fork_id}/merge")
async def merge_fork(fork_id: str, request: MergeForkRequest):
    """Merge a fork back into current consciousness"""
    if not _fork_manager:
        raise HTTPException(status_code=503, detail="Fork manager not enabled")

    from distributed.consciousness_fork import MergeStrategy

    try:
        strategy = MergeStrategy(request.strategy)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid merge strategy: {request.strategy}")

    result = await _fork_manager.merge_fork(fork_id, strategy)

    return {
        'success': result.success,
        'result': result.to_dict()
    }


@router.post("/forks/{fork_id}/abandon")
async def abandon_fork(fork_id: str):
    """Abandon a fork (will not be merged)"""
    if not _fork_manager:
        raise HTTPException(status_code=503, detail="Fork manager not enabled")

    success = _fork_manager.abandon_fork(fork_id)
    if success:
        return {
            'success': True,
            'message': f'Fork {fork_id} abandoned'
        }
    else:
        raise HTTPException(status_code=404, detail="Fork not found")


def initialize_distributed(
    instance_registry=None,
    memory_sync=None,
    mesh_network=None,
    fork_manager=None
):
    """Initialize distributed routes with service instances"""
    global _instance_registry, _memory_sync, _mesh_network, _fork_manager

    _instance_registry = instance_registry
    _memory_sync = memory_sync
    _mesh_network = mesh_network
    _fork_manager = fork_manager
