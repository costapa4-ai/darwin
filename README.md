# Darwin - Autonomous Code Evolution System

Darwin is a sophisticated AI-powered autonomous system that evolves, learns, and improves code through consciousness-inspired wake/sleep cycles, multi-agent collaboration, and hierarchical memory systems.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Core Components](#core-components)
- [API Reference](#api-reference)
- [Frontend](#frontend)
- [Troubleshooting](#troubleshooting)
- [Development Guide](#development-guide)

---

## Overview

Darwin operates as an autonomous AI system with:

- **Wake/Sleep Cycles**: 2-hour active development periods followed by 30-minute research/learning phases
- **Multi-Model AI Routing**: Intelligent task routing between Claude, Gemini, and Haiku based on complexity
- **Hierarchical Memory**: Working, episodic, and semantic memory layers for learning
- **Multi-Agent Collaboration**: 4 agent personalities (Academic, Artist, Hacker, Pragmatic) for diverse solutions
- **Sandbox Execution**: Safe, isolated code execution with resource limits
- **Self-Evolution**: Iterative code improvement with fitness scoring

### System Capabilities

| Phase | Features |
|-------|----------|
| Phase 1 | Core AI, safe execution, evolution engine |
| Phase 2 | Semantic memory, multi-model routing, web research |
| Phase 3 | Consciousness engine, dreams, curiosity, personality |
| Phase 4 | Advanced learning, experimentation sandbox, tool registry |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                          │
│                      http://localhost:3001                       │
└─────────────────────────┬───────────────────────────────────────┘
                          │ HTTP/WebSocket
┌─────────────────────────▼───────────────────────────────────────┐
│                     Backend (FastAPI)                            │
│                     http://localhost:8000                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                  Consciousness Engine                    │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐ │    │
│  │  │   WAKE   │→ │TRANSITION│→ │  SLEEP   │→ │TRANSITION│ │    │
│  │  │  2 hrs   │  │          │  │  30 min  │  │          │ │    │
│  │  └──────────┘  └──────────┘  └──────────┘  └─────────┘ │    │
│  └─────────────────────────────────────────────────────────┘    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐     │
│  │   Nucleus   │  │  Evolution  │  │  Multi-Model Router │     │
│  │  (AI Brain) │  │   Engine    │  │ Claude/Gemini/Haiku │     │
│  └─────────────┘  └─────────────┘  └─────────────────────┘     │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              Hierarchical Memory System                  │    │
│  │  Working (short) → Episodic (medium) → Semantic (long)  │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
         │                    │                    │
    ┌────▼────┐         ┌────▼────┐         ┌────▼────┐
    │ Sandbox │         │  Redis  │         │ SQLite  │
    │  (exec) │         │ (cache) │         │  (db)   │
    └─────────┘         └─────────┘         └─────────┘
```

### Directory Structure

```
Darwin/
├── backend/
│   ├── main.py                 # Entry point
│   ├── config.py               # Configuration management
│   ├── app/
│   │   ├── factory.py          # FastAPI app factory
│   │   ├── lifespan.py         # Startup/shutdown lifecycle
│   │   └── routes.py           # Route registration
│   ├── api/                    # API route handlers
│   │   ├── routes.py           # Core task routes
│   │   ├── consciousness_routes.py
│   │   ├── phase2_routes.py
│   │   ├── phase3_routes.py
│   │   ├── cost_routes.py
│   │   └── websocket.py
│   ├── core/
│   │   ├── nucleus.py          # Central AI brain
│   │   ├── executor.py         # Safe code execution
│   │   ├── evolution.py        # Code evolution engine
│   │   ├── memory.py           # SQLite memory store
│   │   ├── semantic_memory.py  # ChromaDB vector store
│   │   └── hierarchical_memory.py
│   ├── ai/
│   │   ├── multi_model_router.py
│   │   └── models/
│   │       ├── claude_client.py
│   │       ├── gemini_client.py
│   │       └── openai_client.py
│   ├── consciousness/
│   │   ├── consciousness_engine.py  # Main consciousness loop
│   │   ├── tool_registry.py    # Dynamic tool management
│   │   ├── tool_wrappers.py    # Tool integrations
│   │   ├── reflexion.py        # Multi-agent verification
│   │   └── governance.py       # Decision policies
│   ├── agents/
│   │   ├── coordinator.py      # Multi-agent coordination
│   │   └── personalities/      # 4 agent personalities
│   ├── dream/
│   │   ├── dream_engine.py     # Sleep-mode dreams
│   │   └── idle_detector.py    # Triggers dream mode
│   ├── learning/
│   │   ├── web_explorer.py     # Autonomous web research
│   │   ├── documentation_reader.py
│   │   ├── code_repository_analyzer.py
│   │   └── meta_learning_enhanced.py
│   ├── experimentation/
│   │   ├── sandbox_manager.py  # 3 isolated sandboxes
│   │   ├── experiment_designer.py
│   │   └── trial_error_engine.py
│   ├── introspection/
│   │   ├── approval_system.py  # Change approval workflow
│   │   ├── auto_applier.py     # Applies approved changes
│   │   ├── health_tracker.py   # System health & recovery
│   │   └── quality_analyzer.py
│   ├── personality/
│   │   ├── mood_system.py
│   │   ├── communication_system.py
│   │   └── context_awareness.py
│   └── initialization/
│       ├── phase1.py           # Core services
│       ├── phase2.py           # Semantic memory, multi-model
│       ├── phase3.py           # Agents, dreams, curiosity
│       ├── phase4.py           # Learning, experimentation
│       └── consciousness.py    # Consciousness setup
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── NewDashboard.jsx    # Main dashboard
│   │   │   ├── ApprovalsPanel.jsx  # Change approvals
│   │   │   ├── DarwinMessages.jsx  # Message display
│   │   │   └── ...
│   │   └── hooks/
│   │       └── useWebSocket.js
│   └── package.json
├── docker-compose.yml
├── .env.example
└── data/                       # Runtime data (gitignored)
```

---

## Installation

### Prerequisites

- Docker and Docker Compose
- API keys for at least one AI provider (Claude, Gemini, or OpenAI)

### Quick Start

1. **Clone and configure**
   ```bash
   cd Darwin
   cp .env.example .env
   # Edit .env with your API keys
   ```

2. **Start services**
   ```bash
   docker compose up -d
   ```

3. **Access Darwin**
   - Frontend: http://localhost:3001
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Environment Variables

Create a `.env` file with:

```bash
# Required: At least one AI provider
CLAUDE_API_KEY=sk-ant-...
GEMINI_API_KEY=AIza...
# OPENAI_API_KEY=sk-...

# AI Configuration
AI_PROVIDER=gemini                    # Default provider: claude, gemini, openai
ROUTING_STRATEGY=tiered               # tiered, balanced, performance, cost, speed

# Phase 2 Features
ENABLE_SEMANTIC_MEMORY=true
ENABLE_WEB_RESEARCH=true
ENABLE_META_LEARNING=true
SERPAPI_API_KEY=...                   # For web research
GITHUB_TOKEN=ghp_...                  # For repo analysis

# Phase 3 Features
ENABLE_MULTI_AGENT=true
ENABLE_DREAM_MODE=true
DREAM_IDLE_THRESHOLD_MINUTES=5
ENABLE_CODE_POETRY=true
ENABLE_CURIOSITY=true

# Infrastructure
REDIS_URL=redis://redis:6379
DATABASE_URL=sqlite:///data/darwin.db
MAX_REQUESTS_PER_MINUTE=10
```

---

## Configuration

### Multi-Model Routing Strategies

Darwin uses intelligent routing to optimize cost and quality:

| Strategy | Description | Best For |
|----------|-------------|----------|
| `tiered` | Haiku→Gemini→Claude based on complexity | Production (recommended) |
| `balanced` | Cost/speed/quality balance | General use |
| `performance` | Always use best model (Claude) | Quality-critical tasks |
| `cost` | Always use cheapest model | Budget-conscious |
| `speed` | Always use fastest model | Low-latency needs |

**Model Pricing (per 1K tokens):**
- Claude Haiku: $0.001 (simple tasks)
- Gemini Flash: $0.0005 (moderate tasks)
- Claude Sonnet: $0.015 (complex tasks)

### Feature Flags

Enable/disable features in `.env`:

```bash
# Phase 2
ENABLE_SEMANTIC_MEMORY=true    # Vector-based memory
ENABLE_WEB_RESEARCH=true       # Web exploration
ENABLE_META_LEARNING=true      # Self-optimization

# Phase 3
ENABLE_MULTI_AGENT=true        # 4 agent personalities
ENABLE_DREAM_MODE=true         # Sleep-mode research
ENABLE_CODE_POETRY=true        # Creative expression
ENABLE_CURIOSITY=true          # Discovery sharing

# Phase 4 (automatic when dependencies available)
# Web explorer, documentation reader, experimentation sandbox
```

---

## Core Components

### Nucleus (AI Brain)

**File**: `backend/core/nucleus.py`

The central intelligence that orchestrates AI interactions:

```python
# Key methods
nucleus.generate_solution(task, context)    # Generate code with RAG
nucleus.analyze_result(code, result)        # Evaluate execution
nucleus.evolve_code(code, feedback)         # Improve based on feedback
```

**Features:**
- RAG (Retrieval Augmented Generation) with semantic memory
- Multi-model routing integration
- Web research integration
- Code generation with context

### Consciousness Engine

**File**: `backend/consciousness/consciousness_engine.py`

Manages the wake/sleep lifecycle:

```
WAKE (2 hours)          SLEEP (30 minutes)
├── Code optimization   ├── Web research
├── Tool creation       ├── Dream exploration
├── Curiosity sharing   ├── Memory consolidation
├── User interactions   ├── Self-reflection
└── Approval review     └── Learning synthesis
```

**Key attributes:**
- `state`: Current consciousness state (WAKE/SLEEP/TRANSITION)
- `activities`: List of wake activities
- `dreams`: List of sleep dreams
- `curiosities`: Interesting discoveries
- `wake_cycles`: Total wake cycles completed
- `discoveries`: Total discoveries made

### Tool Registry

**File**: `backend/consciousness/tool_registry.py`

Dynamic tool discovery and state-aware selection:

**Tool Modes:**
- `WAKE`: Active development tools
- `SLEEP`: Research and learning tools
- `BOTH`: Always available
- `ON_DEMAND`: Explicit request only

**Tool Categories:**
- LEARNING, EXPERIMENTATION, ANALYSIS
- CREATIVITY, OPTIMIZATION, COMMUNICATION, REFLECTION

### Multi-Model Router

**File**: `backend/ai/multi_model_router.py`

Intelligent task routing:

```python
router.select_model(task_description, context)  # Select best model
router.generate(task, prompt, context)          # Generate with routing
router.get_router_stats()                       # Usage statistics
```

**Task Complexity Detection:**
- SIMPLE: Chat, status, basic queries → Haiku
- MODERATE: Research, analysis → Gemini
- COMPLEX: Code generation, architecture → Claude Sonnet

### Memory Systems

**Three-Layer Hierarchy:**

1. **Working Memory** (seconds-minutes)
   - Currently active information
   - Limited capacity

2. **Episodic Memory** (hours-days)
   - Specific experiences with temporal context
   - Task executions and results

3. **Semantic Memory** (permanent)
   - Consolidated general knowledge
   - Patterns and learnings

**Consolidation:** During SLEEP, important episodic memories are consolidated into semantic memory.

### Safe Executor

**File**: `backend/core/executor.py`

Sandboxed code execution:

```python
executor.execute(code, timeout=30, memory_limit=256*1024*1024)
```

**Safety Features:**
- Process isolation (multiprocessing)
- Timeout enforcement (default: 30s)
- Memory limits (default: 256MB)
- Module whitelist validation
- Restricted globals
- Output sanitization

### Evolution Engine

**File**: `backend/core/evolution.py`

Iterative code improvement:

**Fitness Function (0-100):**
- Success: 40 points
- Speed: 20 points
- Memory efficiency: 15 points
- Code quality: 15 points
- Correctness: 10 points

---

## API Reference

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/tasks` | Create a new task |
| GET | `/api/tasks/{id}` | Get task status |
| GET | `/api/generations/{task_id}` | Get evolution generations |
| GET | `/api/metrics` | System metrics |
| GET | `/api/health` | Health check |

### Consciousness Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/consciousness/status` | Current consciousness state |
| GET | `/api/v1/consciousness/wake-activities` | Wake cycle activities |
| GET | `/api/v1/consciousness/sleep-dreams` | Sleep cycle dreams |
| GET | `/api/v1/consciousness/curiosities` | Discovery moments |
| GET | `/api/v1/consciousness/approvals/pending` | Pending changes |
| POST | `/api/v1/consciousness/approvals/{id}/approve` | Approve a change |
| POST | `/api/v1/consciousness/approvals/{id}/reject` | Reject a change |
| GET | `/api/v1/consciousness/chat-history` | Chat history |
| POST | `/api/v1/consciousness/chat` | Send chat message |

### Cost Tracking Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/costs/summary` | Cost summary with estimates |
| GET | `/api/v1/costs/detailed` | Detailed cost breakdown |
| POST | `/api/v1/costs/set-strategy/{strategy}` | Change routing strategy |

### Phase 2 Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/phase2/memory/stats` | Memory statistics |
| POST | `/api/v1/phase2/memory/search` | Semantic search |
| POST | `/api/v1/phase2/multi-model/analyze` | Multi-model analysis |
| POST | `/api/v1/phase2/research` | Web research |

### WebSocket

Connect to `ws://localhost:8000/ws` for real-time updates:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  // Handle: activity, dream, curiosity, approval, etc.
};
```

---

## Frontend

### Main Dashboard

**File**: `frontend/src/components/NewDashboard.jsx`

The primary interface showing:
- Consciousness status (WAKE/SLEEP/TRANSITION)
- Activity metrics (activities, discoveries, wake cycles)
- Live event feed
- Chat interface
- Cost tracking button
- Approvals panel toggle

### Key Components

| Component | Purpose |
|-----------|---------|
| `ApprovalsPanel.jsx` | Review and approve/reject code changes |
| `DarwinMessages.jsx` | Display Darwin's communications |
| `ConsciousnessMonitor.jsx` | Real-time consciousness state |
| `DreamViewer.jsx` | View dream content |
| `LiveFeed.jsx` | Real-time event stream |
| `MetricsPanel.jsx` | System metrics display |

### API Communication

```javascript
const API_BASE = 'http://localhost:8000';

// Fetch consciousness status
const res = await fetch(`${API_BASE}/api/v1/consciousness/status`);

// Send chat message
await fetch(`${API_BASE}/api/v1/consciousness/chat`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ message: 'Hello Darwin!' })
});
```

---

## Troubleshooting

### Common Issues

#### Backend won't start

```bash
# Check logs
docker compose logs backend --tail=50

# Common fixes:
# 1. Missing API keys in .env
# 2. Port 8000 already in use
# 3. Redis not starting
```

#### Frontend can't connect to backend

```bash
# Verify backend is running
curl http://localhost:8000/api/health

# Check CORS settings in backend/app/factory.py
# Allowed origins: localhost:3000, localhost:3001, localhost:5173
```

#### Consciousness engine not starting

```bash
# Check initialization logs
docker compose logs backend | grep -i consciousness

# Verify all phase dependencies are initialized
curl http://localhost:8000/ | python -m json.tool
```

#### High API costs

```bash
# Switch to tiered routing
curl -X POST http://localhost:8000/api/v1/costs/set-strategy/tiered

# Check current strategy
curl http://localhost:8000/api/v1/costs/summary
```

#### Memory issues

```bash
# Clear ChromaDB vector store
rm -rf backend/data/chroma_db

# Clear Redis cache
docker compose exec redis redis-cli FLUSHALL
```

### Health Check Endpoints

```bash
# System status
curl http://localhost:8000/

# Full health
curl http://localhost:8000/api/health

# Consciousness status
curl http://localhost:8000/api/v1/consciousness/status
```

### Log Files

```bash
# Backend logs
docker compose logs -f backend

# All services
docker compose logs -f

# Specific time range
docker compose logs --since="2h" backend
```

---

## Development Guide

### Adding a New Tool

1. **Create tool function** in `backend/learning/` or appropriate directory:

```python
async def my_new_tool(params: Dict) -> Dict:
    """Tool description"""
    # Implementation
    return {"success": True, "result": ...}
```

2. **Register in tool_wrappers.py**:

```python
# backend/consciousness/tool_wrappers.py
def wrap_my_tool(tool_registry, my_tool_instance):
    async def wrapper(params):
        return await my_tool_instance.execute(params)

    tool_registry.register_tool(
        name="my_new_tool",
        func=wrapper,
        description="What this tool does",
        mode=ToolMode.WAKE,  # or SLEEP, BOTH
        category=ToolCategory.ANALYSIS,
        cooldown_minutes=10
    )
```

3. **Initialize in phase4.py** (or appropriate phase):

```python
# backend/initialization/phase4.py
my_tool = MyToolClass(config)
services['my_tool'] = my_tool
```

### Adding a New API Route

1. **Create route file** in `backend/api/`:

```python
# backend/api/my_routes.py
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/my-feature", tags=["my-feature"])

@router.get("/status")
async def get_status():
    return {"status": "ok"}
```

2. **Register in routes.py**:

```python
# backend/app/routes.py
from api import my_routes

def register_all_routes(app: FastAPI):
    # ... existing routes ...
    app.include_router(my_routes.router)
```

### Modifying Consciousness Behavior

**Wake Activities** (`consciousness_engine.py`):
- Modify `_run_wake_cycle()` method
- Add new activity types to the Activity dataclass

**Sleep Dreams** (`consciousness_engine.py`):
- Modify `_run_sleep_cycle()` method
- Integrate with dream_engine.py for research

**Tool Selection** (`tool_registry.py`):
- Modify `select_tools()` for different selection logic
- Adjust cooldowns and modes in tool registration

### Testing Changes

```bash
# Rebuild and restart
docker compose build backend && docker compose up -d

# Watch logs
docker compose logs -f backend

# Test specific endpoint
curl http://localhost:8000/api/v1/your-endpoint
```

### Code Style

- Python: Follow PEP 8
- TypeScript/React: Follow ESLint config
- Use type hints in Python
- Document public methods with docstrings
- Keep functions focused and small

---

## Docker Services

| Service | Port | Purpose |
|---------|------|---------|
| backend | 8000 | FastAPI server |
| frontend | 3001 | React app (Vite) |
| redis | 6379 | Caching |
| sandbox | - | Isolated execution |

### Docker Commands

```bash
# Start all services
docker compose up -d

# Rebuild specific service
docker compose build backend
docker compose up -d backend

# View logs
docker compose logs -f backend

# Stop all
docker compose down

# Clean restart
docker compose down -v && docker compose up -d
```

---

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]
