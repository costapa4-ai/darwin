"""
Initialization Module - Phased system initialization

This module organizes Darwin's startup into logical phases:
- Phase 1: Core services (memory, executor, AI)
- Phase 2: Semantic memory, multi-model, web research
- Phase 3: Agents, dreams, poetry, curiosity
- Phase 4: Advanced learning, experimentation, tools
- Consciousness: Main consciousness engine
"""

from initialization.phase1 import init_core_services, init_health_tracking
from initialization.phase2 import init_phase2_services
from initialization.phase3 import init_phase3_services
from initialization.phase4 import init_phase4_services
from initialization.consciousness import init_consciousness_engine

__all__ = [
    'init_core_services',
    'init_health_tracking',
    'init_phase2_services',
    'init_phase3_services',
    'init_phase4_services',
    'init_consciousness_engine'
]
