"""
Distributed Consciousness Initialization

Initializes:
- Instance Registry for peer discovery
- Memory Sync Protocol
- P2P Mesh Network
- Consciousness Fork Manager
"""

from typing import Dict, Any, Optional
import os

from config import get_settings
from utils.logger import setup_logger

logger = setup_logger(__name__)


async def init_distributed_services(settings, phase2: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Initialize distributed consciousness services.

    Args:
        settings: Application settings
        phase2: Phase 2 services (for memory sync)

    Returns:
        Dict with distributed service instances
    """
    services = {
        'instance_registry': None,
        'memory_sync': None,
        'mesh_network': None,
        'fork_manager': None
    }

    # Check if distributed mode is enabled
    enable_distributed = getattr(settings, 'enable_distributed', False) or \
                         os.environ.get('ENABLE_DISTRIBUTED', '').lower() == 'true'

    if not enable_distributed:
        logger.info("Distributed consciousness disabled (set ENABLE_DISTRIBUTED=true to enable)")
        return services

    try:
        # Instance Registry
        from distributed.instance_registry import InstanceRegistry, InstanceCapabilities

        instance_name = getattr(settings, 'instance_name', None) or \
                        os.environ.get('DARWIN_INSTANCE_NAME', 'darwin-primary')

        host = getattr(settings, 'host', '0.0.0.0')
        port = getattr(settings, 'port', 8000)

        registry = InstanceRegistry(
            instance_name=instance_name,
            host=host,
            port=port
        )

        # Create local instance with capabilities
        capabilities = InstanceCapabilities(
            can_dream=True,
            can_learn=True,
            can_execute_code=False,
            can_browse_web=True,
            has_voice=phase2.get('voice_engine') is not None if phase2 else False,
            has_ui_automation=phase2.get('ui_automation_engine') is not None if phase2 else False,
            supported_models=['claude', 'gemini', 'ollama']
        )

        registry.create_local_instance(capabilities)
        await registry.start()

        services['instance_registry'] = registry
        logger.info(f"Instance Registry initialized: {instance_name}")

        # Add seed nodes from environment
        seed_nodes = os.environ.get('DARWIN_SEED_NODES', '')
        if seed_nodes:
            for node in seed_nodes.split(','):
                node = node.strip()
                if node:
                    registry.add_seed_node(node)

    except Exception as e:
        logger.error(f"Failed to initialize Instance Registry: {e}")
        import traceback
        logger.error(traceback.format_exc())

    # Memory Sync Protocol
    if services['instance_registry']:
        try:
            from distributed.memory_sync import MemorySyncProtocol

            sync = MemorySyncProtocol(
                instance_id=services['instance_registry'].instance_id
            )

            # Register memory handlers if semantic memory available
            if phase2 and phase2.get('semantic_memory'):
                semantic_memory = phase2['semantic_memory']

                # Register handlers for different memory types
                from distributed.memory_sync import MemoryType

                # These would need to be implemented based on your memory storage
                # For now, we'll use placeholder handlers
                async def get_all_memories():
                    try:
                        return await semantic_memory.get_all()
                    except:
                        return []

                async def get_memory_by_id(memory_id):
                    try:
                        return await semantic_memory.get(memory_id)
                    except:
                        return None

                async def save_memory(content, memory_id):
                    try:
                        await semantic_memory.store(content, memory_id)
                    except:
                        pass

                sync.register_memory_handler(
                    MemoryType.SEMANTIC,
                    get_all=get_all_memories,
                    get_by_id=get_memory_by_id,
                    save=save_memory
                )

            services['memory_sync'] = sync
            logger.info("Memory Sync Protocol initialized")

        except Exception as e:
            logger.error(f"Failed to initialize Memory Sync: {e}")

    # P2P Mesh Network
    if services['instance_registry']:
        try:
            from distributed.mesh_network import MeshNetwork

            mesh = MeshNetwork(
                instance_id=services['instance_registry'].instance_id,
                instance_name=services['instance_registry'].instance_name,
                port=port + 1  # Use different port for mesh
            )

            await mesh.start()
            services['mesh_network'] = mesh
            logger.info("Mesh Network initialized")

        except Exception as e:
            logger.error(f"Failed to initialize Mesh Network: {e}")

    # Consciousness Fork Manager
    if services['instance_registry']:
        try:
            from distributed.consciousness_fork import ConsciousnessForkManager

            fork_manager = ConsciousnessForkManager(
                instance_id=services['instance_registry'].instance_id
            )

            # Register state providers
            if phase2 and phase2.get('semantic_memory'):
                async def get_memories_state():
                    try:
                        return await phase2['semantic_memory'].get_all()
                    except:
                        return []

                fork_manager.register_state_provider('memories', get_memories_state)

            if phase2 and phase2.get('meta_learner'):
                async def get_learnings_state():
                    try:
                        return phase2['meta_learner'].get_state()
                    except:
                        return {}

                fork_manager.register_state_provider('learnings', get_learnings_state)

            services['fork_manager'] = fork_manager
            logger.info("Consciousness Fork Manager initialized")

        except Exception as e:
            logger.error(f"Failed to initialize Fork Manager: {e}")

    return services


async def stop_distributed_services(services: Dict[str, Any]):
    """Stop all distributed services gracefully"""

    if services.get('mesh_network'):
        await services['mesh_network'].stop()

    if services.get('instance_registry'):
        await services['instance_registry'].stop()

    logger.info("Distributed services stopped")
