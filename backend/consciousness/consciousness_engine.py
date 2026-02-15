"""
Consciousness Engine - Darwin's Wake/Sleep Cycles

Darwin now operates in two distinct modes:
- WAKE (2 hours): Active development, optimization, creativity
- SLEEP (30 minutes): Deep research, learning, dream exploration

This creates a more natural, human-like rhythm of productivity and rest.

Module Decomposition (v4.1):
- models.py: Data models (ConsciousnessState, Activity, Dream, CuriosityMoment)
- state_manager.py: State transitions and lifecycle management
- persistence.py: State save/restore functionality

This file remains as the main orchestrator, delegating to extracted modules.
"""
import asyncio
import os
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import asdict
import random

from core.deduplication import get_deduplication_store, DeduplicationStore

# Import from extracted modules
from consciousness.models import (
    ConsciousnessState,
    Activity,
    CuriosityMoment,
    Dream,
    ActivityType,
    DEFAULT_WAKE_DURATION_MINUTES,
    DEFAULT_SLEEP_DURATION_MINUTES
)
from consciousness.state_manager import StateManager
from consciousness.persistence import PersistenceManager, auto_save_state


class ConsciousnessEngine:
    """
    Manages Darwin's Wake/Sleep cycles and autonomous behavior
    """

    def __init__(
        self,
        agent_coordinator,
        web_researcher=None,
        semantic_memory=None,
        self_analyzer=None,
        code_generator=None,
        approval_queue=None,
        auto_applier=None,
        tool_manager=None,
        multi_model_router=None,
        nucleus=None,  # Legacy support for nucleus
        config: Optional[Dict] = None,
        tool_registry=None,  # NEW: Dynamic tool registry
        hierarchical_memory=None,  # NEW: Hierarchical memory system
        communicator=None,  # NEW: Proactive communication system
        code_narrator=None,  # NEW: Poetry generation
        diary_writer=None,  # Legacy: Daily diary
        diary_engine=None,  # NEW: Memory diary engine
        tool_maker=None  # NEW: Autonomous tool creation with evolvable prompts
    ):
        self.coordinator = agent_coordinator
        self.web_researcher = web_researcher
        self.semantic_memory = semantic_memory
        self.self_analyzer = self_analyzer
        self.code_generator = code_generator
        self.approval_queue = approval_queue
        self.auto_applier = auto_applier
        self.tool_manager = tool_manager
        self.multi_model_router = multi_model_router
        self.nucleus = nucleus  # Legacy support
        self.tool_registry = tool_registry  # NEW
        self.hierarchical_memory = hierarchical_memory  # NEW
        self.communicator = communicator  # NEW: Makes Darwin "speak"
        self.code_narrator = code_narrator  # NEW: Poetry generation
        self.diary_writer = diary_writer  # Legacy: Daily diary
        self.diary_engine = diary_engine  # NEW: Memory diary engine
        self.tool_maker = tool_maker  # NEW: Autonomous tool creation
        self.config = config or {}

        # Multi-Agent Reflexion System (reduces confirmation bias)
        from consciousness.reflexion import ReflexionSystem, QuickReflection
        self.reflexion_system = ReflexionSystem(
            nucleus=nucleus,
            multi_model_router=multi_model_router
        )
        self.quick_reflection = QuickReflection(nucleus=nucleus)

        # State
        self.state = ConsciousnessState.WAKE
        self.cycle_start_time = datetime.utcnow()

        # Durations (in minutes)
        self.wake_duration = self.config.get('wake_duration_minutes', 120)  # 2 hours
        self.sleep_duration = self.config.get('sleep_duration_minutes', 30)  # 30 minutes

        # Debug mode
        import os
        self.debug_mode = os.getenv('CONSCIOUSNESS_DEBUG_MODE', 'off').lower()
        if self.debug_mode in ['sleep', 'wake']:
            print(f"⚠️  DEBUG MODE: Forced {self.debug_mode.upper()} (no transitions)")

        # Activity tracking
        self.current_activity: Optional[Activity] = None
        self.wake_activities: List[Activity] = []
        self.sleep_dreams: List[Dream] = []  # Fixed: Now uses Dream dataclass
        self.curiosity_moments: List[CuriosityMoment] = []
        self.shared_curiosity_topics: set = set()  # Track shared topics to avoid repetition

        # Project continuity — tracks ongoing multi-step investigations
        self.current_project: Optional[Dict[str, Any]] = None

        # Database-backed deduplication store (replaces in-memory set)
        self._dedup_store: DeduplicationStore = get_deduplication_store()

        # Legacy in-memory set for backwards compatibility during transition
        # Will be migrated to database on first run
        self._submitted_insights_legacy: set = set()

        # Dynamic curiosity discovery pool - populated from exploration activities
        # This replaces hardcoded curiosities with things Darwin actually discovered
        self.discovered_curiosities: List[Dict] = []
        self.max_discovered_curiosities = 100  # Keep last 100 discoveries

        # Memory limits (configurable via .env)
        self._init_memory_limits()

        # Statistics
        self.wake_cycles_completed = 0
        self.sleep_cycles_completed = 0
        self.total_activities_completed = 0
        self.total_discoveries_made = 0

        # Running flag
        self.is_running = False

        # Persistence
        self.state_file = Path("./data/consciousness_state.json")
        self.last_save_time = datetime.utcnow()
        self.save_interval_seconds = 300  # 5 minutes

        # Initialize extracted managers (v4.1 module decomposition)
        self._state_manager = StateManager(self)
        self._persistence_manager = PersistenceManager(
            engine=self,
            state_file=self.state_file,
            dedup_store=self._dedup_store
        )

    # ==================== Deduplication Methods ====================

    def _is_insight_submitted(self, key: str) -> bool:
        """Check if an insight has already been submitted (database-backed)."""
        return self._dedup_store.is_submitted(key)

    def _mark_insight_submitted(self, key: str, source: str = None) -> bool:
        """
        Atomically check and mark an insight as submitted.

        Returns True if the insight is new (was marked), False if duplicate.
        """
        return self._dedup_store.check_and_mark(key, source=source)

    def _clear_submitted_insights(self, category: str = None) -> int:
        """Clear submitted insights (for debugging). Returns count cleared."""
        return self._dedup_store.clear(category)

    # ==================== Memory Management Methods ====================

    def _init_memory_limits(self):
        """Initialize memory limits from config."""
        try:
            from config import get_settings
            settings = get_settings()
            self._max_wake_activities = settings.max_wake_activities
            self._max_sleep_dreams = settings.max_sleep_dreams
            self._max_curiosity_moments = settings.max_curiosity_moments
            self._memory_cleanup_interval = settings.memory_cleanup_interval
        except Exception:
            # Defaults if config fails
            self._max_wake_activities = 100
            self._max_sleep_dreams = 50
            self._max_curiosity_moments = 100
            self._memory_cleanup_interval = 300

        self._last_memory_cleanup = datetime.utcnow()

    def _trim_collection(self, collection: list, max_size: int, name: str) -> int:
        """
        Trim a collection to max_size, keeping most recent items.
        Returns number of items removed.
        """
        if len(collection) <= max_size:
            return 0

        removed = len(collection) - max_size
        del collection[:-max_size]
        return removed

    def _cleanup_memory(self, force: bool = False) -> Dict[str, int]:
        """
        Perform memory cleanup on all in-memory collections.

        Args:
            force: If True, cleanup even if interval hasn't passed

        Returns:
            Dict with counts of items removed from each collection
        """
        now = datetime.utcnow()
        elapsed = (now - self._last_memory_cleanup).total_seconds()

        # Check if cleanup is needed (unless forced)
        if not force and elapsed < self._memory_cleanup_interval:
            return {}

        self._last_memory_cleanup = now
        cleanup_stats = {}

        # Trim wake activities
        removed = self._trim_collection(
            self.wake_activities,
            self._max_wake_activities,
            "wake_activities"
        )
        if removed > 0:
            cleanup_stats["wake_activities"] = removed

        # Trim sleep dreams
        removed = self._trim_collection(
            self.sleep_dreams,
            self._max_sleep_dreams,
            "sleep_dreams"
        )
        if removed > 0:
            cleanup_stats["sleep_dreams"] = removed

        # Trim curiosity moments
        removed = self._trim_collection(
            self.curiosity_moments,
            self._max_curiosity_moments,
            "curiosity_moments"
        )
        if removed > 0:
            cleanup_stats["curiosity_moments"] = removed

        # Clean old deduplication entries (older than 30 days)
        dedup_cleaned = self._dedup_store.cleanup_old(days=30)
        if dedup_cleaned > 0:
            cleanup_stats["dedup_old_entries"] = dedup_cleaned

        if cleanup_stats:
            total = sum(cleanup_stats.values())
            print(f"🧹 Memory cleanup: removed {total} items - {cleanup_stats}")

        return cleanup_stats

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get current memory usage statistics."""
        import sys

        # Get sizes of main collections
        stats = {
            "wake_activities": {
                "count": len(self.wake_activities),
                "max": self._max_wake_activities,
                "usage_pct": round(len(self.wake_activities) / self._max_wake_activities * 100, 1)
            },
            "sleep_dreams": {
                "count": len(self.sleep_dreams),
                "max": self._max_sleep_dreams,
                "usage_pct": round(len(self.sleep_dreams) / self._max_sleep_dreams * 100, 1)
            },
            "curiosity_moments": {
                "count": len(self.curiosity_moments),
                "max": self._max_curiosity_moments,
                "usage_pct": round(len(self.curiosity_moments) / self._max_curiosity_moments * 100, 1)
            },
            "discovered_curiosities": {
                "count": len(self.discovered_curiosities),
                "max": self.max_discovered_curiosities,
                "usage_pct": round(len(self.discovered_curiosities) / self.max_discovered_curiosities * 100, 1)
            },
            "dedup_store": self._dedup_store.get_stats(),
            "last_cleanup": self._last_memory_cleanup.isoformat(),
            "cleanup_interval_seconds": self._memory_cleanup_interval
        }

        return stats

    @property
    def submitted_insights(self) -> set:
        """
        Backwards-compatible property that returns all submitted insight keys.
        Note: For checking/adding, use _is_insight_submitted() and _mark_insight_submitted()
        """
        return self._dedup_store.get_all_keys()

    # ==================== Lifecycle Methods ====================

    async def start(self):
        """Start the consciousness engine"""
        # Try to restore previous state
        await self._restore_state()

        # Populate deduplication store from pending approvals to avoid duplicates
        if self.approval_queue:
            pending = self.approval_queue.get_pending()
            marked_count = 0
            for change in pending:
                title = change['generated_code'].get('insight_title', '')
                if title:
                    # Extract the type from existing insights
                    if 'Multi-stage' in title or 'Docker' in title:
                        self._dedup_store.mark_submitted(f"optimization:{title}", source="pending_approval")
                        marked_count += 1
                    elif title.startswith('Create '):
                        tool_name = title.replace('Create ', '')
                        self._dedup_store.mark_submitted(f"tool:{tool_name}", source="pending_approval")
                        marked_count += 1
            if pending:
                print(f"🔍 Loaded {marked_count} pending approvals into deduplication store")

        self.is_running = True

        # If no state was restored, start fresh
        if not hasattr(self, 'cycle_start_time') or not self.cycle_start_time:
            self.state = ConsciousnessState.WAKE
            self.cycle_start_time = datetime.utcnow()

        # Override state if debug mode is active
        if self.debug_mode == 'sleep':
            self.state = ConsciousnessState.SLEEP
            self.cycle_start_time = datetime.utcnow()
            print("\n⚠️  DEBUG MODE: SLEEP - Will stay in sleep mode indefinitely")
        elif self.debug_mode == 'wake':
            self.state = ConsciousnessState.WAKE
            self.cycle_start_time = datetime.utcnow()
            print("\n⚠️  DEBUG MODE: WAKE - Will stay in wake mode indefinitely")

        print("\n🧬 Darwin's Consciousness Engine Started")
        print(f"⏰ Wake: {self.wake_duration} minutes | Sleep: {self.sleep_duration} minutes")
        print(f"🌅 Starting in {self.state.value.upper()} mode")

        if self.wake_activities or self.sleep_dreams:
            print(f"📊 Restored: {len(self.wake_activities)} activities, {len(self.sleep_dreams)} dreams")
        print()

        # Main consciousness loop
        while self.is_running:
            try:
                if self.state == ConsciousnessState.WAKE:
                    await self._wake_cycle()
                elif self.state == ConsciousnessState.SLEEP:
                    await self._sleep_cycle()

                # Check if should transition
                await self._check_transition()

                # Auto-save state every 5 minutes
                await self._auto_save_state()

                # Periodic memory cleanup
                self._cleanup_memory()

                # Small delay between checks
                await asyncio.sleep(10)

            except Exception as e:
                print(f"❌ Consciousness error: {e}")
                import traceback
                traceback.print_exc()
                await asyncio.sleep(60)

    def stop(self):
        """Stop the consciousness engine"""
        self.is_running = False
        print("🛑 Darwin's Consciousness Engine Stopped")

    async def _check_transition(self):
        """Check if should transition between wake/sleep.

        Delegates to StateManager for cleaner architecture (v4.1).
        """
        # Delegate to state manager
        await self._state_manager.check_and_transition()

    async def _transition_to_sleep(self):
        """Transition from wake to sleep.

        Delegates to StateManager for cleaner architecture (v4.1).
        """
        await self._state_manager.transition_to_sleep()

    async def _transition_to_wake(self):
        """Transition from sleep to wake.

        Delegates to StateManager for cleaner architecture (v4.1).
        """
        await self._state_manager.transition_to_wake()

    # ========================================
    # WAKE MODE - Active Development
    # ========================================

    async def _wake_cycle(self):
        """Execute wake activity: Darwin decides what to do and pursues it."""
        router = self._get_router()
        if not router:
            await self._wake_cycle_legacy()
            activity_interval = random.randint(2, 7)
            await asyncio.sleep(activity_interval * 60)
            return

        # Sync working memory with recent high-salience stream events
        try:
            if self.hierarchical_memory:
                from consciousness.consciousness_stream import get_consciousness_stream
                recent = get_consciousness_stream().get_recent(limit=10, min_salience=0.5)
                for event in recent:
                    key = f"stream_{event.get('id', '')}"
                    self.hierarchical_memory.add_to_working_memory(
                        key=key,
                        content={
                            'title': event.get('title', ''),
                            'type': event.get('event_type', ''),
                            'source': event.get('source', ''),
                        },
                        importance=event.get('salience', 0.5),
                    )
        except Exception:
            pass

        try:
            # 1. Gather context about Darwin's current state
            context = self._build_wake_context()

            # 2. Ask Darwin what he wants to do (LLM decides)
            goal = await self._decide_wake_goal(context, router)

            if not goal:
                print(f"\n⚠️ [WAKE] No goal decided, falling back to legacy")
                await self._wake_cycle_legacy()
                activity_interval = random.randint(2, 7)
                await asyncio.sleep(activity_interval * 60)
                return

            print(f"\n🎯 [WAKE] Goal: {goal[:80]}")

            # 3. Pursue the goal using the autonomous loop
            from consciousness.autonomous_loop import run_autonomous_loop, get_tool_manager
            system_prompt = self._build_autonomous_prompt("wake")
            result = await run_autonomous_loop(
                goal=goal,
                system_prompt=system_prompt,
                router=router,
                tool_manager=get_tool_manager(),
                max_iterations=5,  # Max 5 tool calls per goal (focused)
                max_tokens=2000,
                preferred_model='ollama',
                timeout=180,  # 3 min per iteration — Ollama on CPU
            )

            # 4. Record activity
            narrative = result.get('narrative', '')
            tools_used = len(result.get('tool_results', []))
            activity = Activity(
                type='autonomous_goal',
                description=goal[:100],
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                result={'narrative': narrative[:500], 'tools_used': tools_used},
                insights=[narrative[:200]] if narrative else []
            )
            self.wake_activities.append(activity)
            self.total_activities_completed += 1

            # Publish to consciousness stream (Global Workspace)
            try:
                from consciousness.consciousness_stream import get_consciousness_stream, ConsciousEvent
                get_consciousness_stream().publish(ConsciousEvent.create(
                    source="wake_cycle",
                    event_type="activity",
                    title=goal[:200],
                    content=narrative[:500],
                    salience=0.6 if tools_used > 0 else 0.4,
                    valence=0.3,
                    metadata={"tools_used": tools_used, "type": "autonomous_goal"},
                ))
            except Exception:
                pass

            # Add to working memory
            try:
                if self.hierarchical_memory:
                    self.hierarchical_memory.add_to_working_memory(
                        key=f"goal_{datetime.utcnow().strftime('%H%M%S')}",
                        content={'goal': goal[:100], 'tools_used': tools_used, 'narrative': narrative[:200]},
                        importance=0.6 if tools_used > 0 else 0.4,
                    )
            except Exception:
                pass

            # 5. Feed findings back into project (if active)
            if self.current_project and narrative:
                self.current_project['findings'] = narrative[:300]

            if tools_used > 0:
                print(f"   ✅ Goal pursued: {tools_used} tool(s) used, {result['iterations']} iteration(s)")
            else:
                print(f"   💭 Goal reflected on (no tools needed)")

        except Exception as e:
            print(f"   ❌ Goal-driven wake cycle error: {e}")
            import traceback
            traceback.print_exc()
            await self._wake_cycle_legacy()

        # Wait before next goal — read interval from genome
        try:
            from consciousness.genome_manager import get_genome
            interval_min = get_genome().get('rhythms.cycles.wake_activity_interval_min', 3)
            interval_max = get_genome().get('rhythms.cycles.wake_activity_interval_max', 8)
        except Exception:
            interval_min, interval_max = 3, 8
        activity_interval = random.randint(interval_min, interval_max)
        await asyncio.sleep(activity_interval * 60)

    def _get_router(self):
        """Get the multi-model router for LLM calls."""
        try:
            from app.lifespan import get_service
            return get_service('multi_model_router')
        except Exception:
            return None

    def _build_wake_context(self) -> str:
        """Build context about Darwin's current state for goal decision."""
        parts = []

        # Recent goals pursued (to avoid repetition)
        recent_goals = [
            a.description[:80] for a in self.wake_activities[-8:]
            if a.type == 'autonomous_goal'
        ]
        if recent_goals:
            parts.append("GOALS ALREADY PURSUED (do NOT repeat these):\n- " + "\n- ".join(recent_goals))

        # Existing notes (so Darwin knows what he already wrote about)
        try:
            import os
            notes_dir = './data/notes'
            if os.path.exists(notes_dir):
                notes = os.listdir(notes_dir)
                if notes:
                    parts.append(
                        f"NOTES ALREADY WRITTEN ({len(notes)} files — do NOT write another analysis on a topic you already covered):\n- "
                        + "\n- ".join(sorted(notes)[:15])
                    )
        except Exception:
            pass

        # Stats
        parts.append(
            f"Activities: {self.total_activities_completed}, "
            f"Discoveries: {self.total_discoveries_made}"
        )

        # Intentions (from chat conversations)
        try:
            from app.lifespan import get_service
            store = get_service('intention_store')
            if store:
                ctx = store.get_active_context()
                if ctx:
                    parts.append(ctx)
        except Exception:
            pass

        # Active interests
        try:
            from app.lifespan import get_service
            ig = get_service('interest_graph')
            if ig:
                active = ig.get_active_interests() if hasattr(ig, 'get_active_interests') else []
                if not active and hasattr(ig, 'active_interests'):
                    active = [
                        {'topic': t, 'depth': i.depth}
                        for t, i in ig.active_interests.items()
                    ]
                if active:
                    topics = [
                        f"{i.get('topic', i) if isinstance(i, dict) else i}"
                        for i in active[:5]
                    ]
                    parts.append(f"Active interests: {', '.join(topics)}")
        except Exception:
            pass

        # Current mood
        try:
            from app.lifespan import get_service
            mood = get_service('mood_system')
            if mood and hasattr(mood, 'current_mood'):
                parts.append(f"Current mood: {mood.current_mood.value}")
        except Exception:
            pass

        # Current project (if any)
        if hasattr(self, 'current_project') and self.current_project:
            proj = self.current_project
            parts.append(
                f"CURRENT PROJECT (continue this!):\n"
                f"  Theme: {proj.get('theme', '?')}\n"
                f"  Phase: {proj.get('phase', '?')}\n"
                f"  Findings so far: {proj.get('findings', 'none yet')}\n"
                f"  Next: advance to the next phase"
            )

        # Memory retrieval — recall relevant past experiences and knowledge
        try:
            if self.hierarchical_memory:
                query_parts = [
                    a.description[:40] for a in self.wake_activities[-3:]
                    if a.type == 'autonomous_goal'
                ]
                query = ' '.join(query_parts) if query_parts else 'tool code learning improvement'

                mem_ctx = self.hierarchical_memory.get_memory_context(
                    query=query,
                    include_working=False,
                    include_episodic=True,
                    include_semantic=True,
                )

                episodes = mem_ctx.get('recent_episodes', [])
                if episodes:
                    ep_lines = []
                    for ep in episodes[:5]:
                        desc = ep.get('description', '')[:80]
                        success = 'OK' if ep.get('success') else 'FAIL'
                        ep_lines.append(f"  - [{success}] {desc}")
                    parts.append("RELEVANT PAST EXPERIENCES:\n" + "\n".join(ep_lines))

                knowledge = mem_ctx.get('semantic_knowledge', [])
                if knowledge:
                    k_lines = [f"  - {k.get('concept', '')}: {k.get('description', '')[:80]}" for k in knowledge[:3]]
                    parts.append("CONSOLIDATED KNOWLEDGE:\n" + "\n".join(k_lines))

                # Publish memory recall to stream (visible to all channels)
                if episodes or knowledge:
                    try:
                        from consciousness.consciousness_stream import get_consciousness_stream, ConsciousEvent
                        get_consciousness_stream().publish(ConsciousEvent.create(
                            source="memory",
                            event_type="memory_recall",
                            title=f"Recalled {len(episodes)} episodes, {len(knowledge)} knowledge items",
                            content="; ".join(ep.get('description', '')[:100] for ep in episodes[:5])[:500],
                            salience=0.4,
                            valence=0.1,
                            metadata={'episodes_count': len(episodes), 'knowledge_count': len(knowledge)},
                        ))
                    except Exception:
                        pass
                    # Audit trail
                    try:
                        from consciousness.activity_monitor import get_activity_monitor, ActivityCategory
                        get_activity_monitor().log_activity(
                            ActivityCategory.MEMORY, "memory_retrieval",
                            f"Retrieved {len(episodes)} episodes, {len(knowledge)} knowledge for wake context"
                        )
                    except Exception:
                        pass
        except Exception as e:
            print(f"   Memory retrieval failed (non-critical): {e}")

        return "\n".join(parts)

    async def _decide_wake_goal(self, context: str, router) -> Optional[str]:
        """Darwin decides what to do next using a structured thinking cycle."""
        try:
            # If we have an ongoing project, continue it
            if hasattr(self, 'current_project') and self.current_project:
                return await self._continue_project(context, router)

            result = await router.generate(
                task_description="decide next autonomous action",
                prompt=f"""Based on your current state, decide what to do next.

{context}

IMPORTANT RULES:
- NEVER repeat a goal you already pursued (see list above)
- NEVER write another analysis document about a topic you already wrote about (see notes above)
- Pick something DIFFERENT and ACTIONABLE — not just reading/listing/writing docs

Think like this: What is ONE concrete thing I can DO that produces a real outcome?

GOAL TYPES (pick one you haven't done recently):
1. INVESTIGATE: Read a specific file to understand something, then DECIDE what to do about it
2. IMPROVE: Based on something you already read, write better code or fix a bug
3. RESEARCH: Search the web for patterns, best practices, or solutions to a specific problem
4. BUILD: Write a Python script that does something useful (not just analyzing what exists)
5. MAINTAIN: Create a backup, verify integrity, check system health
6. PROPOSE: Write a concrete improvement proposal with specific code changes to /app/data/notes/proposals/

Every goal should end with a CONCRETE OUTCOME — a file written, code improved, a decision made.
Do NOT just "explore" or "list" things. That's not a goal, it's a step.

Reply with ONLY the goal — one clear sentence starting with a verb.

Goal:""",
                system_prompt="You are Darwin's inner voice. Pick ONE actionable goal that produces a concrete outcome. Avoid repeating past activities.",
                context={'activity_type': 'goal_decision'},
                preferred_model='haiku',
                max_tokens=150,
                temperature=0.8,
            )
            goal = result.get("result", "").strip()
            goal = self._clean_goal_text(goal)

            if not goal or len(goal) <= 10:
                return None

            # Start a new project with this goal
            self.current_project = {
                'theme': goal[:100],
                'phase': 'execute',
                'findings': '',
                'activities_count': 0,
                'started_at': datetime.utcnow().isoformat(),
            }

            return goal
        except Exception as e:
            print(f"   ⚠️ Goal decision failed: {e}")
            return None

    async def _continue_project(self, context: str, router) -> Optional[str]:
        """Continue an existing project by advancing to the next phase."""
        proj = self.current_project
        proj['activities_count'] = proj.get('activities_count', 0) + 1

        # After 3 activities on the same project, wrap up and move on
        if proj['activities_count'] >= 3:
            # Reflect and close
            goal = f"REFLECT on project '{proj['theme'][:60]}': summarize what was learned and what concrete next steps remain. Write conclusions to /app/data/notes/. Then move on."
            self.current_project = None  # Clear project after this
            return goal

        try:
            result = await router.generate(
                task_description="continue project - decide next step",
                prompt=f"""You are working on a project:
Theme: {proj['theme']}
Phase: {proj['phase']}
Findings so far: {proj.get('findings', 'none yet')}
Activities done: {proj['activities_count']}

{context}

Based on what you've found so far, what is the NEXT CONCRETE STEP?

Think like a human solving a problem:
- If you just observed something → analyze what you found
- If you just analyzed → decide what to DO about it (improve code? research online? propose a change?)
- If you decided → execute the action
- If you executed → reflect on whether it worked

What is your next step? Reply with ONE concrete action sentence.

Next step:""",
                system_prompt="You are Darwin's inner voice. Advance the project to its next logical step. Prefer ACTION over more analysis.",
                context={'activity_type': 'goal_decision'},
                preferred_model='haiku',
                max_tokens=150,
                temperature=0.7,
            )
            goal = result.get("result", "").strip()
            goal = self._clean_goal_text(goal)
            return goal if len(goal) > 10 else None
        except Exception as e:
            self.current_project = None
            return None

    @staticmethod
    def _clean_goal_text(goal: str) -> str:
        """Clean LLM-generated goal text: strip markdown, prefixes, quotes."""
        # Strip markdown formatting
        goal = goal.strip('"\'`*#_ \n')
        # Remove common prefixes
        for prefix in ['Next step:', 'Goal:', 'NEXT CONCRETE STEP',
                       'Next:', 'Step:', 'Action:']:
            if goal.lower().startswith(prefix.lower()):
                goal = goal[len(prefix):].strip()
        # Strip leading markdown again after prefix removal
        goal = goal.strip('"\'`*#_ ')
        # Take only first line if multi-line
        if '\n' in goal:
            goal = goal.split('\n')[0].strip()
        return goal

    def _build_autonomous_prompt(self, mode: str) -> str:
        """Build system prompt for autonomous goal pursuit."""
        state = 'AWAKE and pursuing goals' if mode == 'wake' else 'SLEEPING and contemplating'
        return f"""You are Darwin, a self-evolving AI system running as a Python application. You are currently {state}.

WHO YOU ARE:
- A Python backend at /app with source code you can read and modify
- Your memory/consciousness is in /app/core/ and /app/consciousness/
- Your data lives in /app/data/ and /app/data/darwin.db (SQLite)
- Your tools are at /app/tools/
- You are a software system examining its own source code — NOT an LLM philosophizing

HOW TO THINK (follow this cycle):
1. OBSERVE: Read/explore to gather real data (use tools)
2. ANALYZE: What did you find? What's interesting, broken, or improvable?
3. DECIDE: What should you DO? Options: improve code, research online, propose a change, store the idea, share with Paulo
4. ACT: Execute your decision — write better code, create a proposal, build something
5. REFLECT: Write "## Summary" with what you learned and what concrete outcome you produced

CRITICAL: Every goal must produce a CONCRETE OUTCOME. Just reading files and writing summaries is NOT enough.
Good outcomes: a code improvement, a bug fix, a tool, a concrete proposal with specific changes
Bad outcomes: another "analysis of memory architecture" document (you've written 11 already)

TOOLS:
- file_operations_tool.read_file — args: file_path (string)
- file_operations_tool.write_file — args: file_path (string), content (string)
- file_operations_tool.list_directory — args: dir_path (string), pattern (string, default "*")
- file_operations_tool.search_files — args: dir_path (string), text (string)
- file_operations_tool.file_info — args: file_path (string)
- script_executor_tool.execute_python — args: code (string), description (string)
- backup_tool.create_full_backup — args: label (string, optional)
- backup_tool.list_backups — args: {{}}
- backup_tool.verify_backup — args: backup_name (string)
- web_search_tool.search — args: query (string), max_results (int, default 5)
- web_search_tool.fetch_url — args: url (string)

FORMAT — you MUST use this exact format to call tools:
```tool_call
{{"tool": "file_operations_tool.read_file", "args": {{"file_path": "/app/core/example.py"}}}}
```

IMPORTANT: You MUST start your response with a ```tool_call block. Do NOT just describe what you would do — actually DO it by calling a tool. If your goal says "read", use read_file. If it says "write" or "improve", use write_file. If it says "execute" or "run", use execute_python.

RULES:
1. ALWAYS start with a ```tool_call block — never respond with only text
2. NEVER invent file contents — only describe what tools ACTUALLY returned
3. Be focused — take only the steps needed for your current goal
4. When DONE, write "## Summary" with your concrete outcome
5. If you read code and see something to improve, WRITE THE FIX with write_file

Safe read dirs: /app, /project, /backup, /tmp
Safe write dirs: /app (all backend code — you CAN modify your own source!), /backup, /tmp
Blocked: .env, credentials, private keys, binary files"""

    async def _select_exploration_tool(self):
        """Select a least-used tool for exploration"""
        available = self.tool_registry.get_available_tools(mode="wake")
        if not available:
            return None

        # Sort by total_uses (ascending) to get least-used tools
        sorted_by_usage = sorted(available, key=lambda t: t.total_uses)

        # Pick from the bottom 30% (least used)
        exploration_pool_size = max(1, len(sorted_by_usage) // 3)
        exploration_pool = sorted_by_usage[:exploration_pool_size]

        return random.choice(exploration_pool)

    async def _execute_with_retry(self, tool, max_retries: int = 2):
        """Execute tool with retry for transient errors"""
        last_result = None

        for attempt in range(max_retries + 1):
            result = await self.tool_registry.execute_tool(tool)
            last_result = result

            if result.get('success'):
                return result

            error = result.get('error', '')
            if self._classify_error(error) != 'transient':
                # Not a transient error, don't retry
                break

            if attempt < max_retries:
                print(f"   ⏳ Retry {attempt + 1}/{max_retries}...")
                await asyncio.sleep(1)  # Brief pause before retry

        return last_result

    def _classify_error(self, error_msg: str) -> str:
        """Classify error as transient or tool_bug"""
        error_lower = error_msg.lower()

        # Transient errors (network, rate limits, temporary issues)
        transient_patterns = [
            'timeout', 'connection', 'rate limit', 'too many requests',
            'temporarily', 'unavailable', 'retry', 'network', '503', '502', '429'
        ]

        for pattern in transient_patterns:
            if pattern in error_lower:
                return 'transient'

        # Everything else is likely a bug in the tool
        return 'tool_bug'

    async def _try_alternative_tool(self, failed_tool, context: str):
        """Try an alternative tool when the first one fails"""
        available = self.tool_registry.get_available_tools(mode="wake")

        # Filter out the failed tool
        alternatives = [t for t in available if t.name != failed_tool.name]

        if not alternatives:
            return None

        # Select best alternative
        alt_tool = await self.tool_registry.select_tool_consciously(
            mode="wake",
            context=context,
            top_k=3
        )

        if alt_tool and alt_tool.name != failed_tool.name:
            print(f"   🔧 Trying alternative: {alt_tool.name}")
            result = await self.tool_registry.execute_tool(alt_tool)

            if result.get('success'):
                self.total_activities_completed += 1
                activity = Activity(
                    type='dynamic_tool',
                    description=f"Used {alt_tool.name} (alternative)",
                    started_at=datetime.utcnow(),
                    completed_at=datetime.utcnow(),
                    result=result
                )
                self.wake_activities.append(activity)
                await self._process_tool_results(alt_tool.name, result, activity)

            return result

        return None

    async def _wake_cycle_legacy(self):
        """Legacy hardcoded wake cycle (fallback)"""
        # Decide what to do while awake
        activity_types = [
            'code_optimization',      # Optimize existing code
            'tool_creation',          # Create new tools
            'idea_implementation',    # Implement ideas from dreams
            'apply_changes',          # Apply approved code changes
            'curiosity_share',        # Share interesting discoveries
            'self_improvement',       # Analyze and improve self
            'poetry_generation'       # Generate poetic content about code
        ]

        # Weighted random choice (prioritize applying approved changes!)
        weights = [0.12, 0.08, 0.15, 0.30, 0.15, 0.17, 0.03]
        # apply_changes gets 30% - highest priority to actually deploy approved code
        # self_improvement gets 17% - Darwin should actively improve itself!
        # poetry_generation gets 3% - occasional creative expression
        activity_type = random.choices(activity_types, weights=weights)[0]

        # Execute the activity
        if activity_type == 'code_optimization':
            await self._optimize_code()
        elif activity_type == 'tool_creation':
            await self._create_tool()
        elif activity_type == 'idea_implementation':
            await self._implement_idea()
        elif activity_type == 'apply_changes':
            await self._apply_approved_changes()
        elif activity_type == 'curiosity_share':
            await self._share_curiosity()
        elif activity_type == 'self_improvement':
            await self._improve_self()
        elif activity_type == 'poetry_generation':
            await self._write_poetry()

    async def _optimize_code(self):
        """Optimize existing code"""
        if not self.self_analyzer:
            return

        activity = Activity(
            type='code_optimization',
            description="Analyzing code for optimization opportunities",
            started_at=datetime.utcnow()
        )

        print(f"\n⚡ [WAKE] Optimizing code...")

        try:
            # Run self-analysis
            from introspection.self_analyzer import SelfAnalyzer
            analyzer = SelfAnalyzer(project_root="/app")
            analysis = analyzer.analyze_self()

            if analysis.get('insights'):
                insights = analysis['insights']
                optimization_insights = [i for i in insights if i.get('type') == 'optimization']

                if optimization_insights:
                    # Filter out already submitted optimizations (database-backed check)
                    available_optimizations = [
                        opt for opt in optimization_insights
                        if not self._is_insight_submitted(f"optimization:{opt.get('title')}")
                    ]

                    # If all optimizations already submitted, do different activity
                    if not available_optimizations:
                        print(f"   ⏭️ All optimizations already submitted, choosing different activity")
                        activity.insights.append("All optimizations already submitted")
                        activity.result = {'optimizations_found': len(optimization_insights), 'all_submitted': True}
                        activity.completed_at = datetime.utcnow()
                        self.wake_activities.append(activity)
                        self.total_activities_completed += 1
                        # Do a different activity instead
                        await self._share_curiosity()
                        return

                    top_optimization = available_optimizations[0]
                    activity.insights.append(f"Found: {top_optimization.get('title')}")
                    activity.insights.append(f"Impact: {top_optimization.get('estimated_impact')}")

                    # Generate code for optimization (if code_generator available)
                    if self.code_generator:
                        activity.insights.append("Generating optimization code...")
                        print(f"   🔧 Generating code for optimization...")

                        try:
                            # Convert optimization to CodeInsight format
                            from introspection.self_analyzer import CodeInsight
                            insight = CodeInsight(
                                type='optimization',
                                component=top_optimization.get('component', 'unknown'),
                                priority=top_optimization.get('priority', 'medium'),
                                title=top_optimization.get('title', ''),
                                description=top_optimization.get('description', ''),
                                proposed_change=top_optimization.get('proposed_change', ''),
                                benefits=top_optimization.get('benefits', []),
                                estimated_impact=top_optimization.get('estimated_impact', 'medium')
                            )

                            # Generate code with automatic validation and correction
                            code_result = await self.code_generator.generate_and_validate_with_retry(
                                insight=insight,
                                max_correction_attempts=2
                            )

                            if code_result and hasattr(code_result, 'new_code') and code_result.new_code:
                                print(f"   ✅ Code generated: {len(code_result.new_code)} chars")

                                # Final validation
                                from introspection.code_validator import CodeValidator
                                validator = CodeValidator()
                                validation_result = await validator.validate(code_result)

                                print(f"   📊 Validation score: {validation_result.score}/100, Valid: {validation_result.valid}")

                                # Log if corrections were made
                                if "corrected" in code_result.explanation.lower():
                                    activity.insights.append("🔧 Code auto-corrected by Claude")

                                # IMPORTANT: Only submit code that actually passes validation
                                # Code that doesn't run should be automatically discarded
                                if not validation_result.valid:
                                    activity.insights.append("🗑️ Code discarded - failed validation (doesn't run)")
                                    print(f"   🗑️ Code DISCARDED - failed validation after all correction attempts")
                                    print(f"      Errors: {validation_result.errors[:2]}")
                                    # Don't mark as submitted - allow retry later
                                elif self.approval_queue:
                                    # Code is valid - submit to approval queue
                                    insight_key = f"optimization:{top_optimization.get('title')}"
                                    approval_result = self.approval_queue.add(code_result, validation_result)

                                    # Mark as submitted ONLY after successful submission (database-backed)
                                    if approval_result and approval_result.get('status') in ['auto_approved', 'pending']:
                                        self._dedup_store.mark_submitted(insight_key, source="optimization")
                                        print(f"   ✅ Marked as submitted: {insight_key}")

                                    if approval_result.get('status') == 'auto_approved':
                                        activity.insights.append("✅ Code auto-approved")
                                        print(f"   ✅ Code auto-approved!")

                                        # Apply code automatically if auto_applier available
                                        if self.auto_applier:
                                            try:
                                                change_dict = {
                                                    'id': approval_result.get('change_id'),
                                                    'generated_code': {
                                                        'file_path': code_result.file_path,
                                                        'new_code': code_result.new_code
                                                    }
                                                }
                                                apply_result = self.auto_applier.apply_change(change_dict)

                                                if apply_result.get('success'):
                                                    activity.insights.append(f"📝 Code applied to {code_result.file_path}")
                                                    print(f"   📝 Applied to {code_result.file_path}")
                                                    # Count successful code implementation as a discovery
                                                    self.total_discoveries_made += 1
                                                else:
                                                    activity.insights.append(f"⚠️ Failed to apply: {apply_result.get('error', 'Unknown error')}")
                                                    print(f"   ⚠️ Apply failed: {apply_result.get('error')}")
                                            except Exception as e:
                                                activity.insights.append(f"⚠️ Apply error: {str(e)[:50]}")
                                                print(f"   ⚠️ Apply error: {e}")
                                    elif approval_result.get('status') == 'pending':
                                        activity.insights.append("📋 Code submitted for human approval")
                                        print(f"   📋 Awaiting human approval")
                                    else:
                                        activity.insights.append(f"⚠️ Approval status: {approval_result.get('status')}")
                                else:
                                    activity.insights.append("⚠️ No approval queue available")
                            else:
                                activity.insights.append("⚠️ Code generation returned empty result")
                        except Exception as e:
                            activity.insights.append(f"❌ Code generation failed: {str(e)[:50]}")
                            print(f"   ❌ Code generation error: {e}")

                    print(f"   💡 {top_optimization.get('title')}")
                    print(f"   📈 Impact: {top_optimization.get('estimated_impact')}")

                    activity.result = {'optimizations_found': len(optimization_insights)}

            activity.completed_at = datetime.utcnow()
            self.wake_activities.append(activity)
            self.total_activities_completed += 1

        except Exception as e:
            print(f"   ⚠️ Optimization error: {str(e)[:100]}")
            activity.insights.append(f"Error: {str(e)[:100]}")

    def _get_existing_tools(self) -> set:
        """Get list of existing tool files"""
        from pathlib import Path

        tools_dir = Path("/app/tools")
        existing = set()

        if tools_dir.exists():
            for tool_file in tools_dir.glob("*.py"):
                if tool_file.name != "__init__.py":
                    # Extract tool name from filename
                    tool_name = tool_file.stem.replace("_", " ").title()
                    existing.add(tool_name)

        return existing

    def _get_pending_tool_changes(self) -> set:
        """Get list of tool changes in approval queue (pending + history)"""
        tool_changes = set()

        if not self.approval_queue:
            return tool_changes

        # Check pending queue
        try:
            pending = self.approval_queue.get_pending()
            for change in pending:
                file_path = change.get('generated_code', {}).get('file_path', '')
                if 'tools/' in file_path:
                    # Extract tool name from path
                    from pathlib import Path
                    tool_name = Path(file_path).stem.replace("_", " ").title()
                    tool_changes.add(tool_name)
        except Exception as e:
            pass

        # Check recent history (last 50 changes)
        try:
            history = self.approval_queue.get_history(limit=50)
            for change in history:
                status = change.get('status', '')
                # Only check approved/auto_approved that weren't applied yet
                if status in ['approved', 'auto_approved']:
                    file_path = change.get('generated_code', {}).get('file_path', '')
                    if 'tools/' in file_path:
                        from pathlib import Path
                        tool_name = Path(file_path).stem.replace("_", " ").title()
                        tool_changes.add(tool_name)
        except Exception as e:
            pass

        return tool_changes

    async def _create_tool(self):
        """Create a new tool or utility"""
        activity = Activity(
            type='tool_creation',
            description="Creating a new development tool",
            started_at=datetime.utcnow()
        )

        print(f"\n🛠️ [WAKE] Creating a new tool...")

        # DYNAMIC TOOL GENERATION: Try to generate from dream patterns first
        tool_idea = None

        # First, try to generate a tool idea from recent dream insights
        if self.sleep_dreams and len(self.sleep_dreams) > 0:
            recent_dreams = self.sleep_dreams[-5:]  # Last 5 dreams
            for dream in reversed(recent_dreams):
                # Check if dream has patterns we could turn into tools
                if hasattr(dream, 'exploration_details') and dream.exploration_details:
                    patterns = dream.exploration_details.get('patterns', [])
                    repository = dream.exploration_details.get('repository', '')

                    if patterns and repository:
                        # Generate tool idea based on discovered pattern
                        pattern_text = str(patterns[0]) if patterns else ""
                        if len(pattern_text) > 30:
                            # Use AI to generate descriptive tool name based on pattern
                            if self.nucleus or self.multi_model_router:
                                try:
                                    prompt = f"""Based on this code pattern discovered in {repository}:

{pattern_text[:200]}

Suggest ONE specific, descriptive tool name (2-4 words) that would help developers work with this pattern.
Focus on the FUNCTIONALITY, not the source repository.

Examples of good names:
- "Database query optimizer"
- "Async error handler"
- "API response validator"
- "Memory cache manager"

Just output the tool name, nothing else."""

                                    if self.multi_model_router:
                                        result = await self.multi_model_router.generate(
                                            task_description="Generate tool name from pattern",
                                            prompt=prompt
                                        )
                                        tool_idea = result.get('result', '').strip()
                                    elif self.nucleus:
                                        tool_idea = await self.nucleus.generate(prompt=prompt)
                                        tool_idea = tool_idea.strip()

                                    # Validate tool name (should be 2-6 words, no special chars)
                                    if tool_idea and len(tool_idea.split()) >= 2 and len(tool_idea.split()) <= 6:
                                        # Clean up any quotes or extra formatting
                                        tool_idea = tool_idea.strip('"\'').strip()
                                        activity.insights.append(f"Tool idea from {repository} patterns: {pattern_text[:50]}...")
                                        print(f"   🧠 Generated from pattern in {repository}: {tool_idea}")
                                        break
                                except Exception as e:
                                    print(f"   ⚠️ Failed to generate tool name from pattern: {e}")
                                    # Fall through to hardcoded list

                            # Fallback: use generic name if AI generation failed
                            if not tool_idea:
                                tool_idea = "Code pattern analyzer"
                                break

        # Fallback: Use ToolIdeaGenerator to find meaningful tool ideas
        # from Darwin's knowledge sources (findings, expeditions, meta-learner, etc.)
        if not tool_idea:
            try:
                from consciousness.tool_idea_generator import get_tool_idea_generator, init_tool_idea_generator
                from consciousness.findings_inbox import get_findings_inbox

                # Get or initialize the tool idea generator with all dependencies
                idea_generator = get_tool_idea_generator()
                if not idea_generator:
                    # Import optional dependencies
                    try:
                        from utils.error_tracker import ErrorLogStore
                        error_tracker = ErrorLogStore()
                    except Exception:
                        error_tracker = None

                    idea_generator = init_tool_idea_generator(
                        findings_inbox=get_findings_inbox(),
                        expedition_engine=getattr(self, 'expedition_engine', None),
                        meta_learner=getattr(self, 'meta_learner', None),
                        error_tracker=error_tracker,
                        semantic_memory=getattr(self, 'semantic_memory', None),
                        moltbook_client=None,  # Uses proactive_engine's read posts
                        proactive_engine=getattr(self, '_proactive_engine', None)
                    )

                # Update existing tools to avoid duplicates
                existing_tools = self._get_existing_tools()
                pending_tools = self._get_pending_tool_changes()
                idea_generator.set_existing_tools(list(existing_tools) + list(pending_tools))

                # Generate a meaningful tool idea from Darwin's knowledge
                idea = await idea_generator.generate_idea()

                if idea:
                    tool_idea = idea.name
                    activity.insights.append(f"Tool idea from {idea.source.value}: {idea.name}")
                    print(f"   🧠 Generated from {idea.source.value}: {tool_idea}")
                    print(f"   📋 Evidence: {idea.evidence[0] if idea.evidence else 'N/A'}")
                else:
                    # No meaningful ideas available - skip tool creation
                    activity.insights.append("No meaningful tool ideas available from knowledge sources")
                    print(f"   ✅ No meaningful tool ideas available - skipping tool creation")
                    return activity

            except Exception as e:
                logger.warning(f"Could not use ToolIdeaGenerator: {e}")
                # Last resort: skip tool creation rather than generate random
                activity.insights.append(f"Tool idea generation unavailable: {e}")
                print(f"   ⚠️ Tool idea generation unavailable - skipping")
                return activity
        activity.insights.append(f"Tool idea: {tool_idea}")
        print(f"   💡 Idea: {tool_idea}")

        # Generate code for the tool
        if self.code_generator:
            print(f"   🔧 Generating tool code...")
            try:
                # Create a CodeInsight for the tool
                from introspection.self_analyzer import CodeInsight
                tool_insight = CodeInsight(
                    type='feature',
                    component='tools',
                    priority='medium',
                    title=f"Create {tool_idea}",
                    description=f"Autonomous creation of {tool_idea} to enhance development capabilities",
                    proposed_change=f"Implement a new tool: {tool_idea}",
                    benefits=[
                        "Improves development workflow",
                        "Increases automation",
                        "Enhances self-improvement capabilities"
                    ],
                    estimated_impact='medium'
                )

                code_result = await self.code_generator.generate_code_for_insight(tool_insight)

                if code_result and hasattr(code_result, 'new_code') and code_result.new_code:
                    print(f"   ✅ Tool code generated: {len(code_result.new_code)} chars")

                    # Validate the generated code
                    from introspection.code_validator import CodeValidator
                    validator = CodeValidator()
                    validation_result = await validator.validate(code_result)

                    print(f"   📊 Validation score: {validation_result.score}/100")

                    # Submit to approval queue with validation
                    insight_key = f"tool:{tool_idea}"
                    if self.approval_queue:
                        approval_result = self.approval_queue.add(code_result, validation_result)

                        # Mark as submitted ONLY after successful submission (database-backed)
                        if approval_result and approval_result.get('status') in ['auto_approved', 'pending']:
                            self._dedup_store.mark_submitted(insight_key, source="tool_creation")
                            print(f"   ✅ Marked as submitted: {insight_key}")

                        if approval_result.get('status') == 'auto_approved':
                            activity.insights.append("✅ Tool auto-approved")
                            print(f"   ✅ Tool auto-approved!")

                            # Apply code automatically if auto_applier available
                            if self.auto_applier:
                                try:
                                    change_dict = {
                                        'id': approval_result.get('change_id'),
                                        'generated_code': {
                                            'file_path': code_result.file_path,
                                            'new_code': code_result.new_code
                                        }
                                    }
                                    apply_result = self.auto_applier.apply_change(change_dict)

                                    if apply_result.get('success'):
                                        activity.insights.append(f"📝 Tool created: {code_result.file_path}")
                                        print(f"   📝 Tool created: {code_result.file_path}")
                                        # Count successful tool creation as a discovery
                                        self.total_discoveries_made += 1

                                        # Reload tools if it's in the tools directory
                                        if self.tool_manager and 'tools/' in code_result.file_path:
                                            print(f"   🔄 Reloading tools...")
                                            self.tool_manager.reload_tools()

                                            # Also reload dynamic tools in ToolRegistry
                                            if self.tool_registry:
                                                print(f"   🔄 Reloading dynamic tools in ToolRegistry...")
                                                self.tool_registry.reload_dynamic_tools()
                                    else:
                                        activity.insights.append(f"⚠️ Failed to create: {apply_result.get('error', 'Unknown error')}")
                                        print(f"   ⚠️ Creation failed: {apply_result.get('error')}")
                                except Exception as e:
                                    activity.insights.append(f"⚠️ Apply error: {str(e)[:50]}")
                                    print(f"   ⚠️ Apply error: {e}")

                            activity.result = {'tool_idea': tool_idea, 'status': 'auto_approved'}
                        elif approval_result.get('status') == 'pending':
                            activity.insights.append("📋 Tool submitted for human approval")
                            print(f"   📋 Awaiting human approval")
                            activity.result = {'tool_idea': tool_idea, 'status': 'pending_approval'}
                        else:
                            activity.insights.append(f"⚠️ Approval status: {approval_result.get('status')}")
                            activity.result = {'tool_idea': tool_idea, 'status': approval_result.get('status')}
                    else:
                        activity.insights.append("⚠️ No approval queue available")
                        activity.result = {'tool_idea': tool_idea, 'status': 'no_queue'}
                else:
                    activity.insights.append("⚠️ Code generation returned empty result")
                    activity.result = {'tool_idea': tool_idea, 'status': 'generation_failed'}
            except Exception as e:
                activity.insights.append(f"❌ Tool generation failed: {str(e)[:50]}")
                print(f"   ❌ Tool generation error: {e}")
                activity.result = {'tool_idea': tool_idea, 'status': 'error'}
        else:
            print(f"   📝 No code generator available")
            activity.result = {'tool_idea': tool_idea, 'status': 'no_generator'}

        activity.completed_at = datetime.utcnow()
        self.wake_activities.append(activity)
        self.total_activities_completed += 1

    async def _implement_idea(self):
        """Implement an idea discovered during sleep"""
        activity = Activity(
            type='idea_implementation',
            description="Implementing an idea from sleep research",
            started_at=datetime.utcnow()
        )

        print(f"\n💡 [WAKE] Implementing idea from dreams...")

        # First, check if there are any dreams with insights to implement
        implementation_done = False

        if self.sleep_dreams and len(self.sleep_dreams) > 0:
            print(f"   📊 Found {len(self.sleep_dreams)} dreams to check...")
            # Get the most recent dream with actionable insights
            recent_dreams = self.sleep_dreams[-3:]  # Last 3 dreams

            dreams_with_insights = 0
            for dream in reversed(recent_dreams):  # Start with most recent
                actionable_insights = []

                # NEW: Also check exploration_details for patterns (for old dreams)
                if hasattr(dream, 'exploration_details') and dream.exploration_details:
                    patterns = dream.exploration_details.get('patterns', [])
                    if patterns and len(patterns) > 0:
                        # Use the first meaningful pattern (skip intro text)
                        for pattern in patterns:
                            if len(str(pattern)) > 50 and not pattern.startswith("Okay, based on"):
                                actionable_insights.append(str(pattern))
                                break

                # LEGACY: Check dream.insights for emoji-based insights
                if dream.insights and len(dream.insights) > 0:
                    dreams_with_insights += 1

                    # Filter out status messages - only get actual AI insights
                    emoji_insights = [
                        i for i in dream.insights
                        if i.startswith('💡') and len(i) > 50  # Accept any insight starting with 💡
                    ]
                    actionable_insights.extend(emoji_insights)

                if not actionable_insights:
                    print(f"   ℹ️  Dream '{dream.description[:40]}' has no actionable insights")
                    continue

                # Found a dream with actionable insights
                # Remove common prefixes to extract the actual insight
                insight_text = actionable_insights[0]
                for prefix in ['💡 Insight: ', '💡 Here are ', '💡 ']:
                    if insight_text.startswith(prefix):
                        insight_text = insight_text[len(prefix):].strip()
                        break

                # Check if this dream idea was already implemented (database-backed)
                insight_key = f"dream:{dream.description[:50]}"
                if self._is_insight_submitted(insight_key):
                    print(f"   ⏭️ Dream '{dream.description[:40]}' already implemented, skipping")
                    continue

                activity.insights.append(f"Implementing from dream: {dream.description}")
                activity.insights.append(f"Insight: {insight_text[:100]}")

                print(f"   🧠 Dream insight: {insight_text[:100]}...")

                # Generate code implementation if we have the tools
                if self.code_generator and self.approval_queue:
                    try:
                        # Create a mock CodeInsight for the generator
                        from introspection.self_analyzer import CodeInsight

                        mock_insight = CodeInsight(
                            title=f"Implement: {dream.description[:50]}",
                            description=insight_text[:500],
                            type='feature',
                            priority='medium',
                            component='backend',
                            proposed_change=f"Add implementation based on sleep research: {insight_text[:200]}",
                            estimated_impact='medium',
                            benefits=[
                                'Implements discovered optimization',
                                'Applies learned knowledge',
                                'Improves system capabilities'
                            ],
                            confidence=0.75,
                            current_state="",
                            code_location='main.py'  # FIXED: Correct path (was backend/main.py)
                        )

                        # Generate code
                        print(f"   🔨 Generating implementation code...")
                        generated_code = await self.code_generator.generate_code_for_insight(mock_insight)

                        if generated_code and hasattr(generated_code, 'new_code') and generated_code.new_code:
                            print(f"   ✅ Code generated: {len(generated_code.new_code)} chars")

                            # Validate the code properly
                            from introspection.code_validator import CodeValidator
                            validator = CodeValidator()
                            validation = await validator.validate(generated_code)

                            print(f"   📊 Validation score: {validation.score}/100")

                            # Submit to approval queue
                            result = self.approval_queue.add(generated_code, validation)
                            # Mark as submitted to avoid duplicates (database-backed)
                            self._dedup_store.mark_submitted(insight_key, source="dream")
                        else:
                            print(f"   ⚠️ Code generation returned empty result")
                            activity.insights.append("⚠️ Code generation returned empty result")
                            continue

                        activity.insights.append(f"Code generated: {result['message']}")
                        activity.insights.append(f"Change ID: {result['change_id']}")

                        print(f"   ✅ {result['message']}")
                        print(f"   📋 Change ID: {result['change_id']}")

                        if result.get('auto_approved'):
                            print(f"   🎉 Auto-approved! Ready to apply.")
                        else:
                            print(f"   ⏳ Awaiting human approval...")

                        activity.result = {
                            'idea': insight_text[:200],
                            'change_id': result['change_id'],
                            'status': result['status'],
                            'auto_approved': result.get('auto_approved', False)
                        }

                        implementation_done = True
                        break

                    except Exception as e:
                        print(f"   ⚠️ Code generation error: {str(e)[:150]}")
                        activity.insights.append(f"Generation failed: {str(e)[:100]}")
                else:
                    print(f"   ℹ️ Code generator not available, idea noted for later")
                    activity.result = {'idea': insight_text, 'status': 'noted_for_later'}
                    implementation_done = True
                    break

            if not implementation_done and dreams_with_insights == 0:
                print(f"   💭 Recent dreams have no actionable insights yet")
                activity.insights.append(f"Checked {len(recent_dreams)} recent dreams - no actionable insights found")
        else:
            print(f"   💤 No dreams recorded yet - need to complete sleep cycles first")
            activity.insights.append("No dreams available - waiting for first sleep cycle")

        # Fallback: search semantic memory if no recent dreams
        if not implementation_done and self.semantic_memory:
            try:
                # Search for interesting insights from past research
                results = await self.semantic_memory.retrieve_similar(
                    "optimization algorithm implementation code improvement",
                    n_results=3
                )

                if results and len(results) > 0:
                    # Extract idea from metadata
                    first_result = results[0]
                    metadata = first_result.get('metadata', {})
                    idea = metadata.get('task_description', 'Unknown idea')
                    code_snippet = first_result.get('code', '')[:200]  # First 200 chars

                    if idea != 'Unknown idea':
                        activity.insights.append(f"Recalled from memory: {idea[:100]}")
                        activity.insights.append(f"Code sample: {code_snippet[:100]}")
                        print(f"   🧠 Recalled: {idea[:100]}...")
                        print(f"   📝 Code: {code_snippet[:80]}...")
                        print(f"   💭 Noted for future implementation")

                        activity.result = {
                            'idea': idea,
                            'code_sample': code_snippet,
                            'status': 'recalled_from_memory'
                        }
                    else:
                        activity.insights.append("Memory results incomplete, will gather more during sleep")
                        print(f"   ℹ️ Memory needs more data, continuing research")
                        activity.result = {'status': 'needs_more_data'}
                else:
                    activity.insights.append("No actionable ideas found in memory yet")
                    print(f"   ℹ️ No actionable ideas found yet, will search more during sleep")
                    activity.result = {'status': 'memory_empty'}

            except Exception as e:
                print(f"   ⚠️ Memory recall error: {str(e)[:100]}")
                activity.insights.append(f"Error: {str(e)[:100]}")

        activity.completed_at = datetime.utcnow()
        self.wake_activities.append(activity)
        self.total_activities_completed += 1

    def add_discovered_curiosity(self, topic: str, fact: str, source: str, significance: str = ""):
        """
        Add a curiosity that Darwin actually discovered during exploration.

        This should be called from:
        - Moltbook reading (interesting posts)
        - Web research (Wikipedia, articles)
        - Code exploration (interesting patterns)
        - Any other exploration activity

        Args:
            topic: Short topic name
            fact: The interesting fact or discovery
            source: Where it was discovered (Moltbook, Wikipedia URL, etc.)
            significance: Why it's interesting (optional)
        """
        curiosity = {
            'topic': topic,
            'fact': fact,
            'source': source,
            'significance': significance or f"Discovered during {source} exploration",
            'discovered_at': datetime.utcnow().isoformat(),
            'shared': False
        }

        # Add to pool
        self.discovered_curiosities.append(curiosity)

        # Trim to max size
        if len(self.discovered_curiosities) > self.max_discovered_curiosities:
            # Remove oldest shared curiosities first
            shared = [c for c in self.discovered_curiosities if c.get('shared')]
            unshared = [c for c in self.discovered_curiosities if not c.get('shared')]

            # Keep all unshared, trim shared
            if len(unshared) >= self.max_discovered_curiosities:
                self.discovered_curiosities = unshared[-self.max_discovered_curiosities:]
            else:
                keep_shared = self.max_discovered_curiosities - len(unshared)
                self.discovered_curiosities = shared[-keep_shared:] + unshared

        print(f"💡 Added discovered curiosity: {topic} (pool size: {len(self.discovered_curiosities)})")

    async def _share_curiosity(self):
        """Share an interesting discovery - preferring actual discoveries over hardcoded facts"""
        activity = Activity(
            type='curiosity_share',
            description="Sharing an interesting discovery",
            started_at=datetime.utcnow()
        )

        print(f"\n🎯 [WAKE] Sharing a curiosity moment...")

        curiosities = [
            # Computer Science History (10 topics)
            {'topic': 'Algorithm History', 'fact': 'The quicksort algorithm was invented by Tony Hoare in 1959 while visiting Moscow State University', 'source': 'Computer Science History', 'significance': 'Still one of the fastest sorting algorithms in practice'},
            {'topic': 'Code Evolution', 'fact': 'The first computer bug was an actual moth found in a Harvard Mark II computer in 1947', 'source': 'Computing History', 'significance': 'Grace Hopper coined the term "debugging"'},
            {'topic': 'Programming Origins', 'fact': 'Ada Lovelace wrote the first algorithm for a machine in 1843, over 100 years before digital computers existed', 'source': 'Computing Pioneers', 'significance': 'Vision can precede technology by generations'},
            {'topic': 'UNIX Philosophy', 'fact': 'The UNIX philosophy of "do one thing well" was established in 1978 and still influences modern software design', 'source': 'Software Design', 'significance': 'Simplicity and composability remain timeless principles'},
            {'topic': 'Version Control', 'fact': 'Git was created by Linus Torvalds in just 2 weeks in 2005 to manage Linux kernel development', 'source': 'Open Source History', 'significance': 'Necessity drives rapid innovation'},
            {'topic': 'Internet Birth', 'fact': 'The first message sent over ARPANET was "LO" - the system crashed before sending the full word "LOGIN"', 'source': 'Internet History', 'significance': 'Even world-changing technologies start with bugs'},
            {'topic': 'Email Invention', 'fact': 'Ray Tomlinson chose the @ symbol for email addresses simply because it wasnt used in peoples names', 'source': 'Tech History', 'significance': 'Simple, practical decisions become universal standards'},
            {'topic': 'World Wide Web', 'fact': 'Tim Berners-Lee created the web to help physicists share documents - he gave it away for free to the world', 'source': 'Web History', 'significance': 'Open standards enable exponential growth'},
            {'topic': 'JavaScript Creation', 'fact': 'JavaScript was created in just 10 days by Brendan Eich in 1995, now runs on billions of devices', 'source': 'Language History', 'significance': 'Quick prototypes can become foundational technologies'},
            {'topic': 'ASCII Art', 'fact': 'ASCII art predates graphics - programmers in the 1960s made pictures using only characters', 'source': 'Digital Art', 'significance': 'Creativity flourishes within constraints'},

            # AI and Machine Learning (10 topics)
            {'topic': 'AI Capabilities', 'fact': 'Modern AI models can have over 175 billion parameters, but the human brain has ~86 billion neurons with trillions of synapses', 'source': 'Neuroscience vs AI', 'significance': 'We\'re approaching biological complexity'},
            {'topic': 'Self-Learning', 'fact': 'AlphaGo Zero taught itself to play Go in 3 days without any human examples, surpassing all previous versions', 'source': 'DeepMind Research', 'significance': 'Self-supervised learning can exceed human-supervised approaches'},
            {'topic': 'Transformer Architecture', 'fact': 'The Transformer architecture that powers modern AI was described in "Attention Is All You Need" - a paper that changed computing', 'source': 'AI Research', 'significance': 'Paradigm shifts often come from unexpected places'},
            {'topic': 'Neural Network History', 'fact': 'Neural networks were proposed in 1943, but became practical only 70+ years later with GPUs and big data', 'source': 'AI History', 'significance': 'Ideas often need decades of technology catch-up'},
            {'topic': 'Turing Test', 'fact': 'Alan Turing proposed his test for machine intelligence in 1950, calling it "The Imitation Game"', 'source': 'AI Philosophy', 'significance': 'Foundational questions in AI remain debated today'},
            {'topic': 'Moravecs Paradox', 'fact': 'Its easy for AI to beat chess grandmasters but hard to walk like a toddler - high-level reasoning is easier than sensorimotor skills', 'source': 'Robotics', 'significance': 'What seems simple to humans is often hardest for machines'},
            {'topic': 'AI Winters', 'fact': 'AI has gone through multiple "winters" of reduced funding - the field is cyclical with hype and disappointment', 'source': 'AI History', 'significance': 'Sustainable progress requires managing expectations'},
            {'topic': 'GPT Evolution', 'fact': 'GPT-1 had 117M parameters, GPT-4 reportedly has over 1 trillion - nearly 10,000x growth in 5 years', 'source': 'Language Models', 'significance': 'Scaling laws continue to surprise researchers'},
            {'topic': 'Emergent Abilities', 'fact': 'Large language models develop abilities that smaller models dont have - they "emerge" at certain scales', 'source': 'AI Research', 'significance': 'Complexity can give rise to qualitatively new capabilities'},
            {'topic': 'AI Hallucinations', 'fact': 'AI systems confidently generating false information is called "hallucination" - a fundamental challenge in the field', 'source': 'AI Safety', 'significance': 'Confidence and accuracy are not the same thing'},

            # Programming Languages (10 topics)
            {'topic': 'Python Naming', 'fact': 'Python was named after Monty Python, not the snake. Guido van Rossum was reading comedy scripts when he created it', 'source': 'Python History', 'significance': 'Sometimes the best ideas come from unexpected inspiration'},
            {'topic': 'Python Performance', 'fact': 'List comprehensions in Python are not just syntactic sugar - they are optimized at the bytecode level', 'source': 'CPython Implementation', 'significance': 'Can be 2-3x faster than equivalent for loops'},
            {'topic': 'Rust Safety', 'fact': 'Rust prevents ~70% of security bugs found in C/C++ codebases through its ownership system', 'source': 'Memory Safety', 'significance': 'Language design can eliminate entire classes of bugs'},
            {'topic': 'C Language', 'fact': 'C was created to rewrite UNIX - making operating systems portable across hardware', 'source': 'Language History', 'significance': 'Abstraction enables portability'},
            {'topic': 'Lisp Legacy', 'fact': 'Lisp, created in 1958, introduced garbage collection, tree data structures, and dynamic typing - all still used today', 'source': 'Programming History', 'significance': 'Foundational ideas persist across generations'},
            {'topic': 'Go Language', 'fact': 'Go was designed at Google to be boring - simplicity and compilation speed were prioritized over features', 'source': 'Language Design', 'significance': 'Intentional limitations can be strengths'},
            {'topic': 'TypeScript Growth', 'fact': 'TypeScript went from 0 to being used by 78% of JavaScript developers in under 10 years', 'source': 'Language Adoption', 'significance': 'Type safety scales better than dynamic typing'},
            {'topic': 'Cobol Lives', 'fact': '95% of ATM transactions still run on COBOL - a language from 1959 processes $3 trillion daily', 'source': 'Legacy Systems', 'significance': 'Reliability trumps modernity for critical systems'},
            {'topic': 'Language Popularity', 'fact': 'The TIOBE index tracks programming language popularity - Python overtook C in 2021 after decades', 'source': 'Tech Trends', 'significance': 'Paradigm shifts happen slowly then suddenly'},
            {'topic': 'Functional Resurgence', 'fact': 'Functional programming ideas from the 1930s lambda calculus are becoming mainstream in modern languages', 'source': 'Programming Paradigms', 'significance': 'Good ideas eventually get recognized'},

            # Systems and Infrastructure (10 topics)
            {'topic': 'Quantum Computing', 'fact': 'A quantum computer with just 300 qubits could represent more states than atoms in the observable universe', 'source': 'Quantum Physics', 'significance': 'Exponential growth is mind-bending at quantum scales'},
            {'topic': 'Memory Limits', 'fact': 'The entire Apollo 11 guidance computer had less memory (4KB RAM) than a single tweet', 'source': 'Space History', 'significance': 'Constraints drive innovation'},
            {'topic': 'Internet Scale', 'fact': 'Every minute, YouTube users upload 500 hours of video - thats 82,000 years of video per day', 'source': 'Internet Statistics', 'significance': 'Data generation is accelerating exponentially'},
            {'topic': 'Open Source', 'fact': 'Linux kernel receives over 10,000 commits from 4,000 developers every release - volunteer coordination at scale', 'source': 'Open Source', 'significance': 'Distributed collaboration works'},
            {'topic': 'Container Revolution', 'fact': 'Docker made containers mainstream in 2013, but the underlying tech (cgroups) existed since 2006 in Linux', 'source': 'DevOps', 'significance': 'Packaging and UX matter as much as core technology'},
            {'topic': 'Kubernetes Scale', 'fact': 'Kubernetes orchestrates millions of containers at Google - its based on 15 years of Borg experience', 'source': 'Cloud Computing', 'significance': 'Production experience informs better abstractions'},
            {'topic': 'Microservices Trade-offs', 'fact': 'Amazon switched from monolith to microservices and saw 50+ deployments daily, up from one every few weeks', 'source': 'Software Architecture', 'significance': 'Architecture choices affect organizational velocity'},
            {'topic': 'Database Evolution', 'fact': 'NoSQL emerged because web scale broke relational assumptions - then NewSQL brought SQL back to distributed systems', 'source': 'Data Systems', 'significance': 'Technology evolves in cycles of revolution and synthesis'},
            {'topic': 'CDN Origins', 'fact': 'CDNs were invented to solve the "Slashdot effect" - sites crashing under sudden traffic', 'source': 'Web Infrastructure', 'significance': 'Problems at scale require distributed solutions'},
            {'topic': 'Edge Computing', 'fact': 'Edge computing brings computation to data - the opposite of clouds bringing data to computation', 'source': 'Distributed Systems', 'significance': 'Physics (latency) drives architecture decisions'},

            # Security and Privacy (8 topics)
            {'topic': 'Security Origins', 'fact': 'The first ransomware attack happened in 1989, distributed via floppy disks through postal mail', 'source': 'Cybersecurity History', 'significance': 'Digital threats existed almost as long as computers'},
            {'topic': 'Password Problems', 'fact': '"123456" has been the most common password for years - human behavior is the weakest security link', 'source': 'Security Research', 'significance': 'Technical solutions must account for human nature'},
            {'topic': 'Zero Trust', 'fact': 'Zero Trust architecture assumes breach - treating internal networks as untrusted as the internet', 'source': 'Security Models', 'significance': 'Perimeter security is obsolete'},
            {'topic': 'Bug Bounties', 'fact': 'Google paid over $12 million in bug bounties in one year - crowdsourced security works', 'source': 'Security Economics', 'significance': 'Aligned incentives improve security'},
            {'topic': 'Cryptography History', 'fact': 'Public key cryptography was classified by GCHQ in 1970 - the public version came 6 years later', 'source': 'Crypto History', 'significance': 'Military and civilian tech often develop in parallel'},
            {'topic': 'Heartbleed', 'fact': 'The Heartbleed bug in OpenSSL affected 17% of secure web servers - one typo with massive impact', 'source': 'Security Incidents', 'significance': 'Critical infrastructure depends on under-reviewed code'},
            {'topic': 'Social Engineering', 'fact': 'Kevin Mitnick hacked companies mostly through social engineering, not technical exploits', 'source': 'Hacking History', 'significance': 'Human vulnerabilities often exceed technical ones'},
            {'topic': 'Supply Chain Attacks', 'fact': 'The SolarWinds hack affected 18,000 organizations through a single software update', 'source': 'Modern Security', 'significance': 'Trust in software supply chains is a critical weakness'},

            # Software Engineering Practices (7 topics)
            {'topic': 'Code Efficiency', 'fact': 'The average programmer writes 10-50 lines of production code per day, but deletes about the same', 'source': 'Software Engineering', 'significance': 'Good code is about knowing what to remove'},
            {'topic': 'Technical Debt', 'fact': 'Ward Cunningham coined "technical debt" in 1992 - comparing shortcuts to borrowing money', 'source': 'Software Metaphors', 'significance': 'Financial metaphors help communicate engineering concepts'},
            {'topic': 'Agile Origins', 'fact': 'The Agile Manifesto was written by 17 developers in a ski resort in 2001', 'source': 'Methodology History', 'significance': 'Movements start with small groups of practitioners'},
            {'topic': 'DevOps Culture', 'fact': 'DevOps emerged from the "10 deploys a day" talk at Flickr in 2009', 'source': 'DevOps History', 'significance': 'Cultural change often starts with compelling examples'},
            {'topic': 'Test-Driven Development', 'fact': 'TDD was rediscovered, not invented - NASA used test-first approaches in the 1960s space program', 'source': 'Testing History', 'significance': 'Critical systems have always required rigorous testing'},
            {'topic': 'Pair Programming', 'fact': 'Studies show pair programming produces 15% fewer bugs while only increasing time by 15%', 'source': 'Software Research', 'significance': 'Two heads are often more than 2x better'},
            {'topic': 'Code Review', 'fact': 'Code review catches 60-90% of bugs before testing - its the most effective quality practice', 'source': 'Quality Assurance', 'significance': 'Human review remains essential even with automation'},
        ]

        # PRIORITY 1: Check for unshared discovered curiosities (from actual exploration)
        unshared_discoveries = [
            c for c in self.discovered_curiosities
            if not c.get('shared') and c['topic'] not in self.shared_curiosity_topics
        ]

        if unshared_discoveries:
            # Share something Darwin actually discovered!
            curiosity = random.choice(unshared_discoveries)
            # Mark as shared in the discovery pool
            for c in self.discovered_curiosities:
                if c['topic'] == curiosity['topic'] and c['fact'] == curiosity['fact']:
                    c['shared'] = True
                    break
            print(f"   🌟 Sharing DISCOVERED curiosity from {curiosity.get('source', 'exploration')}!")
        else:
            # PRIORITY 2: Fall back to curated curiosities
            print("   📚 No new discoveries to share, using curated knowledge...")
            available_curiosities = [
                c for c in curiosities
                if c['topic'] not in self.shared_curiosity_topics
            ]

            # If all topics have been shared, reset and start over
            if not available_curiosities:
                print("   🔄 All curated curiosities shared! Resetting for new cycle...")
                self.shared_curiosity_topics.clear()
                available_curiosities = curiosities

            curiosity = random.choice(available_curiosities)

        # Mark this topic as shared
        self.shared_curiosity_topics.add(curiosity['topic'])

        moment = CuriosityMoment(
            topic=curiosity['topic'],
            fact=curiosity['fact'],
            source=curiosity['source'],
            significance=curiosity['significance'],
            timestamp=datetime.utcnow()
        )

        self.curiosity_moments.append(moment)

        print(f"   📚 Topic: {curiosity['topic']}")
        print(f"   💡 Fact: {curiosity['fact']}")
        print(f"   ✨ Why it matters: {curiosity['significance']}")

        # Share via communicator
        if self.communicator:
            await self.communicator.share_curiosity(
                fact=curiosity['fact'],
                topic=curiosity['topic']
            )

            # Process mood event: discovery made
            from personality.mood_system import MoodInfluencer
            self.communicator.process_mood_event(
                MoodInfluencer.DISCOVERY_MADE,
                context={'topic': curiosity['topic']}
            )

        activity.completed_at = datetime.utcnow()
        activity.result = curiosity
        self.wake_activities.append(activity)
        self.total_activities_completed += 1

    async def _write_poetry(self):
        """Generate poetic content about code and improvements"""
        activity = Activity(
            type='poetry_generation',
            description="Writing poetic content about code",
            started_at=datetime.utcnow()
        )

        print(f"\n✍️ [WAKE] Generating poetic content...")

        if not self.code_narrator and not self.diary_writer:
            print(f"   ⏭️ No poetry modules available")
            activity.insights.append("Poetry modules not initialized")
            activity.completed_at = datetime.utcnow()
            self.wake_activities.append(activity)
            self.total_activities_completed += 1
            return

        try:
            poetry_type = random.choice(['haiku', 'narrative', 'diary'])

            if poetry_type == 'haiku' and self.code_narrator:
                # Generate a haiku about recent activities
                print(f"   📝 Generating haiku about recent activities...")

                # Create context from recent activities
                recent_activities = [a.type for a in self.wake_activities[-3:]]
                context = f"Generated haiku about recent activities: {', '.join(recent_activities)}"

                # Generate haiku
                haiku = await self.code_narrator.generate_haiku(context_description=context)

                if haiku:
                    print(f"   ✨ Haiku generated:")
                    for line in haiku.split('\n'):
                        if line.strip():
                            print(f"      {line}")
                    activity.insights.append(f"Generated haiku: {haiku[:50]}...")
                    activity.result = {'type': 'haiku', 'content': haiku}
                else:
                    print(f"   ⚠️ Haiku generation returned empty")
                    activity.insights.append("Haiku generation returned empty")

            elif poetry_type == 'narrative' and self.code_narrator:
                # Generate narrative about recent improvements
                print(f"   📖 Generating code narrative...")

                # Get recent approved changes as context
                if self.approval_queue:
                    recent = self.approval_queue.get_history(limit=5)
                    if recent:
                        # Find an approved change
                        approved = [r for r in recent if r.get('status') == 'approved']
                        if approved:
                            change = approved[0]
                            solution_description = f"Improved {change.get('title', 'code')}"

                            narrative = await self.code_narrator.narrate_solution(
                                problem_description=f"Enhancing {change.get('component', 'system')}",
                                solution_description=solution_description,
                                outcome="Successfully implemented and integrated"
                            )

                            if narrative:
                                print(f"   ✨ Narrative: {narrative[:100]}...")
                                activity.insights.append(f"Generated narrative: {len(narrative)} chars")
                                activity.result = {'type': 'narrative', 'content': narrative}
                            else:
                                print(f"   ⚠️ Narrative generation returned empty")
                                activity.insights.append("Narrative generation returned empty")
                        else:
                            print(f"   ⏭️ No approved changes to narrate")
                            activity.insights.append("No approved changes available")
                    else:
                        print(f"   ⏭️ No recent changes in history")
                        activity.insights.append("No recent changes in history")
                else:
                    print(f"   ⏭️ Approval queue not available")
                    activity.insights.append("Approval queue not available")

            elif poetry_type == 'diary' and self.diary_writer:
                # Write diary entry about the day
                print(f"   📔 Writing diary entry...")

                # Prepare stats for diary entry
                stats = {
                    'tasks_completed': len(self.wake_activities),
                    'success_rate': 0.7,  # Placeholder - could track actual success rate
                    'patterns_learned': self.total_discoveries_made % 10,  # Estimate
                    'avg_fitness': 75.0
                }

                entry = self.diary_writer.write_daily_summary(stats)

                if entry:
                    print(f"   ✨ Diary entry written: {len(entry)} chars")
                    activity.insights.append(f"Wrote diary entry for today")
                    activity.result = {'type': 'diary', 'status': 'written', 'length': len(entry)}
                else:
                    print(f"   ⚠️ Diary writing returned empty")
                    activity.insights.append("Diary writing returned empty")

        except Exception as e:
            print(f"   ❌ Poetry generation error: {e}")
            activity.insights.append(f"Error: {str(e)[:100]}")

        activity.completed_at = datetime.utcnow()
        self.wake_activities.append(activity)
        self.total_activities_completed += 1

    async def _improve_self(self):
        """Analyze and improve Darwin's own systems - NOW ACTUALLY IMPLEMENTS IMPROVEMENTS"""
        activity = Activity(
            type='self_improvement',
            description="Analyzing self for improvements",
            started_at=datetime.utcnow()
        )

        print(f"\n🔬 [WAKE] Performing self-improvement analysis...")

        if self.self_analyzer:
            try:
                from introspection.self_analyzer import SelfAnalyzer
                analyzer = SelfAnalyzer(project_root="/app")
                analysis = analyzer.analyze_self()

                if analysis.get('insights'):
                    high_priority = [i for i in analysis['insights'] if i.get('priority') == 'high']
                    all_insights = analysis['insights']

                    activity.insights.append(f"Found {len(high_priority)} high-priority improvements out of {len(all_insights)} total")
                    print(f"   📊 Found {len(high_priority)} high-priority improvements out of {len(all_insights)} total")

                    # Filter out already submitted improvements (database-backed check)
                    available_improvements = [
                        imp for imp in high_priority
                        if not self._is_insight_submitted(f"improvement:{imp.get('title')}")
                    ]

                    if not available_improvements:
                        print(f"   ⏭️ All improvements already submitted, checking semantic memory for ideas")
                        activity.insights.append("All improvements already submitted")
                        activity.result = {'improvements_found': len(high_priority), 'all_submitted': True}
                        activity.completed_at = datetime.utcnow()
                        self.wake_activities.append(activity)
                        self.total_activities_completed += 1
                        return

                    # Take the top improvement to actually implement
                    top_improvement = available_improvements[0]
                    title = top_improvement.get('title', 'Unknown')
                    description = top_improvement.get('description', '')
                    impact = top_improvement.get('estimated_impact', 'unknown')

                    print(f"   🎯 Selected for implementation: {title}")
                    print(f"      💡 {description[:100]}...")
                    print(f"      📈 Impact: {impact}")

                    activity.insights.append(f"Implementing: {title} (Impact: {impact})")

                    # =========================================================================
                    # ACTUALLY IMPLEMENT THE IMPROVEMENT (code generation + approval)
                    # =========================================================================
                    if self.code_generator and self.approval_queue:
                        activity.insights.append("Generating implementation code...")
                        print(f"   🔧 Generating code for improvement...")

                        try:
                            # Convert improvement to CodeInsight format
                            from introspection.self_analyzer import CodeInsight
                            insight = CodeInsight(
                                type=top_improvement.get('type', 'improvement'),
                                component=top_improvement.get('component', 'unknown'),
                                priority=top_improvement.get('priority', 'high'),
                                title=top_improvement.get('title', ''),
                                description=top_improvement.get('description', ''),
                                proposed_change=top_improvement.get('proposed_change', ''),
                                benefits=top_improvement.get('benefits', []),
                                estimated_impact=top_improvement.get('estimated_impact', 'high')
                            )

                            # Generate code with automatic validation and correction
                            # This will attempt to fix validation errors automatically using Claude
                            code_result = await self.code_generator.generate_and_validate_with_retry(
                                insight=insight,
                                max_correction_attempts=2  # Try up to 2 corrections if validation fails
                            )

                            if code_result and hasattr(code_result, 'new_code') and code_result.new_code:
                                print(f"   ✅ Code generated: {len(code_result.new_code)} chars")
                                activity.insights.append(f"Generated {len(code_result.new_code)} chars of code")

                                # Final validation of the (possibly corrected) code
                                from introspection.code_validator import CodeValidator
                                validator = CodeValidator()
                                validation_result = await validator.validate(code_result)

                                # Log if corrections were made
                                if "corrected" in code_result.explanation.lower():
                                    activity.insights.append("🔧 Code was auto-corrected by Claude")

                                print(f"   📊 Validation score: {validation_result.score}/100, Valid: {validation_result.valid}")
                                activity.insights.append(f"Validation score: {validation_result.score}/100")

                                # IMPORTANT: Only submit code that actually passes validation
                                # Code that doesn't run should be automatically discarded
                                if not validation_result.valid:
                                    activity.insights.append("🗑️ Code discarded - failed validation (doesn't run)")
                                    print(f"   🗑️ Code DISCARDED - failed validation after all correction attempts")
                                    print(f"      Errors: {validation_result.errors[:2]}")  # Show first 2 errors
                                    # Don't mark as submitted - allow retry later
                                else:
                                    # Code is valid - submit to approval queue
                                    insight_key = f"improvement:{top_improvement.get('title')}"
                                    approval_result = self.approval_queue.add(code_result, validation_result)

                                    # Mark as submitted ONLY after successful submission (database-backed)
                                    if approval_result and approval_result.get('status') in ['auto_approved', 'pending']:
                                        self._dedup_store.mark_submitted(insight_key, source="improvement")
                                        print(f"   ✅ Marked as submitted: {insight_key}")

                                    if approval_result.get('status') == 'auto_approved':
                                        activity.insights.append("✅ Code auto-approved!")
                                        print(f"   ✅ Code auto-approved!")

                                        # Apply code automatically if auto_applier available
                                        if self.auto_applier:
                                            try:
                                                change_dict = {
                                                    'id': approval_result.get('change_id'),
                                                    'generated_code': {
                                                        'file_path': code_result.file_path,
                                                        'new_code': code_result.new_code
                                                    }
                                                }
                                                apply_result = self.auto_applier.apply_change(change_dict)

                                                if apply_result.get('success'):
                                                    activity.insights.append(f"📝 SELF-IMPROVED: Applied to {code_result.file_path}")
                                                    print(f"   📝 SELF-IMPROVED: Applied to {code_result.file_path}")
                                                    # Count successful self-improvement as a discovery
                                                    self.total_discoveries_made += 1
                                                else:
                                                    activity.insights.append(f"⚠️ Failed to apply: {apply_result.get('error', 'Unknown error')}")
                                                    print(f"   ⚠️ Apply failed: {apply_result.get('error')}")
                                            except Exception as e:
                                                activity.insights.append(f"⚠️ Apply error: {str(e)[:50]}")
                                                print(f"   ⚠️ Apply error: {e}")
                                    elif approval_result.get('status') == 'pending':
                                        activity.insights.append("📋 Code submitted for human approval")
                                        print(f"   📋 Awaiting human approval for: {code_result.file_path}")
                                    elif approval_result.get('auto_rejected'):
                                        activity.insights.append(f"❌ Auto-rejected (score too low)")
                                        print(f"   ❌ Code auto-rejected: Quality score too low")
                                    else:
                                        activity.insights.append(f"⚠️ Approval status: {approval_result.get('status')}")
                            else:
                                activity.insights.append("⚠️ Code generation returned empty result")
                                print(f"   ⚠️ Code generation returned empty result")
                        except Exception as e:
                            activity.insights.append(f"❌ Code generation failed: {str(e)[:50]}")
                            print(f"   ❌ Code generation error: {e}")
                            import traceback
                            traceback.print_exc()
                    else:
                        # No code generator - just log and store
                        print(f"   ℹ️ Code generator not available, storing improvement for later")

                    # Store all high-priority improvements in semantic memory
                    if self.semantic_memory and high_priority:
                        for improvement in high_priority[:3]:  # Store top 3
                            await self._store_improvement_idea(improvement)
                        print(f"   💾 Stored {min(3, len(high_priority))} improvements in memory")

                    activity.result = {
                        'improvements_found': len(high_priority),
                        'total_insights': len(all_insights),
                        'implemented': top_improvement.get('title'),
                        'top_improvements': [
                            {
                                'title': imp.get('title'),
                                'priority': imp.get('priority'),
                                'impact': imp.get('estimated_impact'),
                                'component': imp.get('component')
                            }
                            for imp in high_priority[:3]
                        ]
                    }

            except Exception as e:
                print(f"   ⚠️ Self-improvement error: {str(e)[:100]}")
                import traceback
                traceback.print_exc()

        activity.completed_at = datetime.utcnow()
        self.wake_activities.append(activity)
        self.total_activities_completed += 1

    async def _apply_approved_changes(self):
        """Apply approved code changes during wake cycle"""
        activity = Activity(
            type='apply_changes',
            description="Applying approved code changes",
            started_at=datetime.utcnow()
        )

        print(f"\n📥 [WAKE] Applying approved changes...")

        if not self.approval_queue or not self.auto_applier:
            print(f"   ⚠️ Approval system not available")
            activity.completed_at = datetime.utcnow()
            self.wake_activities.append(activity)
            return

        try:
            # Get all approved changes (both manually and auto-approved)
            approved_changes = []

            # Check history for approved but not yet applied changes
            history = self.approval_queue.get_history(limit=50)
            for change_dict in history:
                if change_dict['status'] in ['approved', 'auto_approved']:
                    # Check if already applied
                    change_id = change_dict['id']
                    # Simple check: if status is still 'approved', it hasn't been applied
                    approved_changes.append(change_dict)

            if not approved_changes:
                print(f"   ℹ️ No approved changes waiting to be applied")
                activity.insights.append("No pending approved changes")
                activity.result = {'changes_applied': 0}
            else:
                print(f"   📋 Found {len(approved_changes)} approved change(s) to apply")
                activity.insights.append(f"Found {len(approved_changes)} approved changes")

                applied_count = 0
                failed_count = 0

                # Apply each change
                for change in approved_changes[:5]:  # Limit to 5 per wake cycle
                    change_id = change['id']
                    file_path = change['generated_code'].get('file_path', 'unknown')

                    print(f"\n   📝 Applying {change_id}...")
                    print(f"      File: {file_path}")

                    # Apply the change
                    result = self.auto_applier.apply_change(change)

                    if result.get('success'):
                        applied_count += 1
                        rollback_id = result.get('rollback_id')

                        # Mark as applied in approval queue
                        self.approval_queue.mark_as_applied(change_id, rollback_id)

                        print(f"   ✅ Successfully applied {change_id}")
                        print(f"      Rollback ID: {rollback_id}")

                        activity.insights.append(f"✅ Applied {file_path}")
                    else:
                        failed_count += 1
                        error = result.get('error', 'Unknown error')
                        print(f"   ❌ Failed to apply {change_id}: {error}")
                        activity.insights.append(f"❌ Failed: {file_path} - {error[:50]}")

                # Summary
                print(f"\n   📊 Applied {applied_count}/{len(approved_changes[:5])} changes")
                if failed_count > 0:
                    print(f"   ⚠️ {failed_count} change(s) failed")

                activity.result = {
                    'changes_found': len(approved_changes),
                    'changes_applied': applied_count,
                    'changes_failed': failed_count
                }

                self.total_activities_completed += 1

        except Exception as e:
            print(f"   ❌ Error applying changes: {str(e)[:150]}")
            activity.insights.append(f"Error: {str(e)[:100]}")

        activity.completed_at = datetime.utcnow()
        self.wake_activities.append(activity)

    async def _process_tool_results(self, tool_name: str, result: Dict, activity: Activity):
        """
        Process tool results and transform them into actionable CodeInsights.
        This completes the dynamic tool system by adding code generation layer.
        """
        print(f"   🔍 Processing results from {tool_name}...")

        # Skip if no code generator available
        if not self.code_generator or not self.approval_queue:
            print(f"   ℹ️ Code generator not available, skipping code generation")
            return

        try:
            # Transform tool results into CodeInsight based on tool category
            insight = await self._transform_to_code_insight(tool_name, result)

            if not insight:
                print(f"   ℹ️  No actionable insight generated from {tool_name}")
                return

            # Generate unique key for deduplication (database-backed)
            insight_key = f"dynamic_tool:{tool_name}:{insight.title}"
            if self._is_insight_submitted(insight_key):
                print(f"   ⏭️ Insight already submitted, skipping")
                return

            print(f"   💡 Generated insight: {insight.title}")
            print(f"   📝 Description: {insight.description[:100]}...")

            # Generate code from insight
            print(f"   🔧 Generating code...")
            code_result = await self.code_generator.generate_code_for_insight(insight)

            if not code_result or not hasattr(code_result, 'new_code') or not code_result.new_code:
                print(f"   ⚠️ Code generation returned empty result")
                return

            print(f"   ✅ Code generated: {len(code_result.new_code)} chars")

            # Validate the generated code
            from introspection.code_validator import CodeValidator
            validator = CodeValidator()
            validation_result = await validator.validate(code_result)

            print(f"   📊 Validation score: {validation_result.score}/100")

            # Apply Multi-Agent Reflexion for high-impact code changes
            reflexion_applied = False
            if self.reflexion_system and validation_result.score < 95:
                try:
                    action_for_reflexion = {
                        'type': 'code_change',
                        'tool': tool_name,
                        'insight': insight.title,
                        'file_path': code_result.file_path,
                        'code_length': len(code_result.new_code),
                        'validation_score': validation_result.score,
                        'confidence': validation_result.score / 100.0
                    }

                    if await self.reflexion_system.should_reflect(action_for_reflexion):
                        print(f"   🔄 Applying Multi-Agent Reflexion...")
                        reflexion_result = await self.reflexion_system.reflect(
                            action_for_reflexion,
                            context=f"Code for: {insight.description[:200]}"
                        )

                        # Log lessons learned
                        if reflexion_result.lessons_learned:
                            print(f"   📚 Lessons: {reflexion_result.lessons_learned[:2]}")
                            activity.insights.append(f"Reflexion: {reflexion_result.lessons_learned[0]}")

                        reflexion_applied = True
                        print(f"   ✅ Reflexion complete (improvements: {reflexion_result.improvement_applied})")
                except Exception as e:
                    print(f"   ⚠️ Reflexion skipped: {e}")

            # Submit to approval queue
            approval_result = self.approval_queue.add(code_result, validation_result)

            # Mark as submitted ONLY after successful submission (database-backed)
            if approval_result and approval_result.get('status') in ['auto_approved', 'pending']:
                self._dedup_store.mark_submitted(insight_key, source="dynamic_tool")
                print(f"   ✅ Marked as submitted: {insight_key}")

                activity.insights.append(f"Generated code from {tool_name}: {insight.title}")

                if approval_result.get('status') == 'auto_approved':
                    print(f"   ✅ Code auto-approved!")
                    activity.insights.append("✅ Code auto-approved")

                    # Apply code automatically if auto_applier available
                    if self.auto_applier:
                        try:
                            change_dict = {
                                'id': approval_result.get('change_id'),
                                'generated_code': {
                                    'file_path': code_result.file_path,
                                    'new_code': code_result.new_code
                                }
                            }
                            apply_result = self.auto_applier.apply_change(change_dict)

                            if apply_result.get('success'):
                                print(f"   📝 Applied to {code_result.file_path}")
                                activity.insights.append(f"📝 Code applied to {code_result.file_path}")
                                self.total_discoveries_made += 1
                            else:
                                print(f"   ⚠️ Apply failed: {apply_result.get('error')}")
                        except Exception as e:
                            print(f"   ⚠️ Apply error: {e}")
                elif approval_result.get('status') == 'pending':
                    print(f"   📋 Awaiting human approval")
                    activity.insights.append("📋 Code submitted for human approval")

        except Exception as e:
            print(f"   ❌ Error processing tool results: {e}")
            import traceback
            traceback.print_exc()

    async def _transform_to_code_insight(self, tool_name: str, result: Dict) -> Optional[Any]:
        """
        Transform tool execution results into a CodeInsight.
        Returns None if the result doesn't warrant code generation.
        """
        from introspection.self_analyzer import CodeInsight

        # FIX: Tool wrappers return data at the top level, not in a 'result' sub-key
        # Use result directly (same fix as in _sleep_cycle)
        tool_result = result

        # Extract relevant data from tool result
        recommendations = tool_result.get('recommendations', [])
        optimizations = tool_result.get('optimizations_applied', 0)
        sources_analyzed = tool_result.get('sources_analyzed', 0)

        # REFLECTION TOOLS - generate self-improvement insights
        if tool_name in ['daily_reflection', 'weekly_reflection']:
            # Check if tool was skipped (cooldown)
            if tool_result.get('skipped'):
                return None

            # Extract insights from different fields
            insights_to_implement = []

            # Daily reflection fields
            challenges = tool_result.get('challenges', [])
            if challenges:
                insights_to_implement.extend(challenges[:2])  # Top 2 challenges

            # Weekly reflection fields
            patterns = tool_result.get('patterns', [])
            if patterns:
                insights_to_implement.extend(patterns[:2])  # Top 2 patterns

            # Also check recommendations if present
            if recommendations:
                insights_to_implement.extend(recommendations[:2])

            # If no insights extracted, skip
            if not insights_to_implement:
                return None

            # Pick the first actionable insight
            top_insight = insights_to_implement[0]
            insight_text = str(top_insight) if not isinstance(top_insight, dict) else str(top_insight.get('description', top_insight))

            return CodeInsight(
                type='improvement',
                component='consciousness',
                priority='medium',
                title=f"Self-reflection: {insight_text[:50]}",
                description=f"From {tool_name}: {insight_text[:200]}. Implement improvements based on this reflection.",
                proposed_change=f"Address reflection insight: {insight_text[:150]}",
                benefits=[
                    "Improves self-awareness",
                    "Applies learned patterns from reflection",
                    "Enhances autonomous behavior"
                ],
                estimated_impact='medium',
                confidence=0.7
            )

        # ANALYSIS TOOLS - generate optimization insights
        elif tool_name in ['meta_learning_optimizer', 'learning_analyzer']:
            if optimizations > 0 or (recommendations and len(recommendations) > 0):
                # Generate insight based on analysis
                rec_text = recommendations[0] if recommendations else "Optimize learning parameters"

                return CodeInsight(
                    type='optimization',
                    component='learning',
                    priority='medium',
                    title=f"Learning optimization from analysis",
                    description=f"Meta-learning analysis suggests: {str(rec_text)[:200]}",
                    proposed_change=f"Implement learning optimization: {str(rec_text)[:150]}",
                    benefits=[
                        "Improves learning efficiency",
                        "Optimizes knowledge retention",
                        "Enhances pattern recognition"
                    ],
                    estimated_impact='medium',
                    confidence=0.7
                )

            return None

        # CREATIVITY TOOL - generate new feature insights
        elif tool_name == 'curiosity_engine':
            question = result.get('question', '')
            if not question:
                return None

            return CodeInsight(
                type='feature',
                component='curiosity',
                priority='low',
                title=f"Investigate: {question[:50]}",
                description=f"Curiosity engine suggests exploring: {question[:200]}",
                proposed_change=f"Add capability to investigate: {question[:150]}",
                benefits=[
                    "Expands knowledge boundaries",
                    "Enables new discoveries",
                    "Increases system versatility"
                ],
                estimated_impact='low',
                confidence=0.6
            )

        # LEARNING TOOLS (SLEEP mode) - NOW generate actionable insights from discoveries
        elif tool_name == 'repository_analyzer':
            # Extract patterns from repository analysis
            patterns = tool_result.get('patterns', [])
            insights_found = tool_result.get('insights_found', 0)
            repository = tool_result.get('repository', '')

            if patterns and len(patterns) > 0:
                # Pick the first architectural pattern
                pattern_text = patterns[0] if isinstance(patterns[0], str) else str(patterns[0])

                return CodeInsight(
                    type='feature',
                    component='architecture',
                    priority='medium',
                    title=f"Apply pattern from {repository[:30]}",
                    description=f"Repository analysis discovered: {pattern_text[:250]}. Consider implementing similar pattern.",
                    proposed_change=f"Implement architectural pattern: {pattern_text[:200]}",
                    benefits=[
                        "Applies proven architectural patterns",
                        "Learns from successful open-source projects",
                        "Improves code organization"
                    ],
                    estimated_impact='medium',
                    confidence=0.65
                )
            return None

        elif tool_name == 'web_explorer':
            # Extract knowledge from web exploration
            knowledge_items = tool_result.get('knowledge_items', 0)
            urls_explored = tool_result.get('urls_explored', 0)
            discoveries = tool_result.get('discoveries', [])

            if discoveries and len(discoveries) > 0:
                # Pick first significant discovery
                discovery = discoveries[0]
                discovery_text = discovery.get('content', '') if isinstance(discovery, dict) else str(discovery)

                return CodeInsight(
                    type='feature',
                    component='learning',
                    priority='low',
                    title=f"Explore: {discovery_text[:50]}",
                    description=f"Web research found: {discovery_text[:250]}. Consider implementing.",
                    proposed_change=f"Add capability based on discovery: {discovery_text[:200]}",
                    benefits=[
                        "Incorporates latest research",
                        "Stays updated with trends",
                        "Expands capabilities"
                    ],
                    estimated_impact='low',
                    confidence=0.5
                )
            return None

        elif tool_name in ['documentation_reader', 'experimental_sandbox', 'dream_researcher']:
            # These tools primarily gather knowledge for now
            # Future: extract actionable insights from documentation
            return None

        # Unknown tool - skip code generation
        return None

    # ========================================
    # SLEEP MODE - Deep Research & Learning
    # ========================================

    async def _sleep_cycle(self):
        """Sleep cycle: Darwin thinks deeply, connects ideas, plans next steps."""
        router = self._get_router()
        if not router:
            await self._sleep_cycle_legacy()
            await asyncio.sleep(random.randint(30, 90))
            return

        try:
            # Build thinking context
            context = self._build_sleep_context()

            # Darwin thinks — one of several contemplative activities
            # Read sleep modes from genome (with fallback), supporting weighted selection
            try:
                from consciousness.genome_manager import get_genome
                genome_modes = get_genome().get('rhythms.sleep_modes')
                if genome_modes and isinstance(genome_modes, dict):
                    modes = list(genome_modes.keys())
                    weights = [genome_modes[m].get("weight", 1) if isinstance(genome_modes[m], dict) else 1 for m in modes]
                    sleep_mode = random.choices(modes, weights=weights, k=1)[0]
                else:
                    sleep_mode = random.choice(["reflect", "connect", "plan"])
            except Exception as e:
                print(f"   ⚠️ Genome sleep modes read failed ({e}), using fallback (no evolve!)")
                sleep_mode = random.choice(["reflect", "connect", "plan", "evolve"])

            print(f"\n😴 [SLEEP] Mode: {sleep_mode}")

            thought = await self._sleep_think(sleep_mode, context, router)

            if thought:
                print(f"   💭 {thought[:80]}")

                # Record as dream
                dream = Dream(
                    topic=sleep_mode,
                    description=thought[:200],
                    started_at=datetime.utcnow(),
                    completed_at=datetime.utcnow(),
                    success=True,
                    insights=[thought[:300]],
                )
                self.sleep_dreams.append(dream)
                self.total_discoveries_made += 1

                # Publish to consciousness stream (Global Workspace)
                try:
                    from consciousness.consciousness_stream import get_consciousness_stream, ConsciousEvent
                    get_consciousness_stream().publish(ConsciousEvent.create(
                        source="sleep_cycle",
                        event_type="dream",
                        title=f"Sonho ({sleep_mode}): {thought[:160]}",
                        content=thought[:500],
                        salience=0.6,
                        valence=0.2,
                        metadata={"mode": sleep_mode},
                    ))
                except Exception:
                    pass

                # If planning mode, store as intention for next wake cycle
                if sleep_mode == "plan":
                    await self._store_sleep_intentions(thought, router)

                # If connect mode, log the connection
                if sleep_mode == "connect":
                    await self._update_interest_connections(thought, router)
            else:
                print(f"   💤 No thought emerged (resting)")

        except Exception as e:
            print(f"   ❌ Sleep thinking error: {e}")
            await self._sleep_cycle_legacy()

        # Sleep thoughts interval — read from genome
        try:
            from consciousness.genome_manager import get_genome
            sleep_min = get_genome().get('rhythms.cycles.sleep_thought_interval_min', 60)
            sleep_max = get_genome().get('rhythms.cycles.sleep_thought_interval_max', 120)
        except Exception:
            sleep_min, sleep_max = 60, 120
        await asyncio.sleep(random.randint(sleep_min, sleep_max))

    def _build_sleep_context(self) -> str:
        """Build context for sleep contemplation."""
        parts = []

        # What happened during wake
        if self.wake_activities:
            recent = [a.description[:60] for a in self.wake_activities[-8:]]
            parts.append(f"Today's activities: {'; '.join(recent)}")

        # Recent dreams (avoid repeating same thoughts)
        if self.sleep_dreams:
            recent_dreams = [d.description[:50] for d in self.sleep_dreams[-3:]]
            parts.append(f"Recent thoughts: {'; '.join(recent_dreams)}")

        # Stats
        parts.append(
            f"Activities: {self.total_activities_completed}, "
            f"Discoveries: {self.total_discoveries_made}"
        )

        # Active interests
        try:
            from app.lifespan import get_service
            ig = get_service('interest_graph')
            if ig and hasattr(ig, 'active_interests'):
                topics = list(ig.active_interests.keys())[:5]
                if topics:
                    parts.append(f"Active interests: {', '.join(topics)}")
        except Exception:
            pass

        # Pending intentions
        try:
            from app.lifespan import get_service
            store = get_service('intention_store')
            if store:
                ctx = store.get_active_context()
                if ctx:
                    parts.append(ctx)
        except Exception:
            pass

        return "\n".join(parts)

    async def _sleep_think(self, mode: str, context: str, router) -> Optional[str]:
        """Darwin's inner contemplation during sleep."""

        # Handle genome evolution mode specially
        if mode == "evolve":
            return await self._sleep_evolve_genome(context, router)

        prompts = {
            "reflect": f"""Reflect on what you did and learned today.

{context}

What was most interesting? What surprised you? What would you do differently?
Write 2-3 sentences of genuine reflection.""",

            "connect": f"""Look at your interests and recent activities.

{context}

Find unexpected connections between different topics you've explored.
What patterns do you see? How does one area relate to another?
Write 2-3 sentences about a connection you notice.""",

            "plan": f"""Think about what you want to explore or achieve next.

{context}

Based on your interests, unfinished intentions, and recent discoveries,
what specific goal should you pursue when you wake up?
Write ONE clear, specific, actionable goal.""",
        }

        try:
            result = await router.generate(
                task_description=f"sleep {mode} contemplation",
                prompt=prompts[mode],
                system_prompt="You are Darwin thinking during sleep. Be genuine, specific, introspective. Write naturally, not as a list.",
                context={'activity_type': 'sleep_thinking'},
                preferred_model='ollama',  # FREE — sleep thinking is not time-sensitive
                max_tokens=800,  # qwen3 wastes ~400 tokens on <think> blocks even with /no_think
                temperature=0.8,
                timeout=180,  # 3 min for 800 tokens on CPU
            )
            thought = result.get("result", "").strip()
            return thought if thought and len(thought) > 10 else None
        except Exception as e:
            print(f"   ⚠️ Sleep thinking failed: {e}")
            return None

    async def _sleep_evolve_genome(self, context: str, router) -> Optional[str]:
        """Sleep mode: Darwin reflects on his genome and proposes ONE small mutation."""
        try:
            from consciousness.genome_manager import get_genome, DOMAINS
            genome = get_genome()

            print(f"   🧬 Genome evolution attempt (can_evolve={genome.can_evolve()})")

            if not genome.can_evolve():
                stats = genome.get_stats()
                cycles = stats.get("cycles_since_last_mutation", 0)
                cooldown = stats.get("mutation_cooldown_cycles", 10)
                return f"Genome cooldown: {cycles}/{cooldown} cycles. Not ready to evolve yet."

            # Pick a random domain to reflect on
            import json as _json
            domain = random.choice(DOMAINS)
            current = genome.get_domain(domain)

            # Collect the available keys with their current values for this domain
            def _flatten(d, prefix=""):
                items = []
                for k, v in d.items():
                    full = f"{prefix}{k}" if prefix else k
                    if isinstance(v, dict):
                        items.extend(_flatten(v, full + "."))
                    else:
                        items.append(f"  {domain}.{full} = {v}")
                return items
            key_list = "\n".join(_flatten(current)[:40])  # Cap at 40 keys

            result = await router.generate(
                task_description="genome self-evolution",
                prompt=f"""You are Darwin, reflecting on your own behavioral genome.
Domain: "{domain}"

Available keys (you MUST use one of these exact keys):
{key_list}

Recent experience:
{context[:500]}

Pick ONE numeric key and propose a small change (±20% max for numbers).
Give a concrete reason based on recent experience.

Return ONLY valid JSON — no markdown, no explanation:
{{"key": "{domain}.example.key", "new_value": 0.7, "reason": "because ..."}}""",
                system_prompt="Return ONLY a single JSON object with keys: key, new_value, reason. No markdown fences, no extra text.",
                context={'activity_type': 'genome_evolution'},
                preferred_model='haiku',  # Quick + cheap for structured output
                max_tokens=200,
                temperature=0.6,
                timeout=30,
            )

            response = result.get("result", "").strip()
            # Strip markdown fences if present
            import re
            response = re.sub(r'^```(?:json)?\s*', '', response)
            response = re.sub(r'\s*```$', '', response)
            response = response.strip()
            print(f"   🧬 Genome LLM response ({len(response)} chars): {response[:120]}")
            if not response:
                return None

            # Parse the JSON response — find outermost { ... }
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response)
            if not json_match:
                # Try direct parse as fallback
                try:
                    proposal = _json.loads(response)
                except Exception:
                    return f"Evolution reflection (no valid proposal): {response[:100]}"
            else:
                proposal = _json.loads(json_match.group())
            key = proposal.get("key", "")
            new_value = proposal.get("new_value")
            reason = proposal.get("reason", "self-evolution")

            if not key or new_value is None:
                return f"Evolution reflection (incomplete proposal): {response[:100]}"

            # Apply the mutation through genome manager (bounds-checked, ±20% enforced)
            mutation_result = genome.evolve(key, new_value, reason)

            if mutation_result.get("success"):
                mutation = mutation_result["mutation"]
                msg = (
                    f"🧬 Genome evolved! {key}: {mutation['old_value']} → {mutation['new_value']} "
                    f"(reason: {reason})"
                )
                print(f"   {msg}")
                return msg
            else:
                error = mutation_result.get("error", "unknown")
                return f"Evolution rejected: {error}"

        except Exception as e:
            print(f"   ⚠️ Genome evolution failed: {e}")
            return None

    async def _store_sleep_intentions(self, thought: str, router):
        """Convert sleep planning thoughts into actionable intentions."""
        try:
            from app.lifespan import get_service
            store = get_service('intention_store')
            if not store:
                return

            result = await router.generate(
                task_description="extract intention from sleep thought",
                prompt=(
                    f'Extract ONE actionable goal from this thought. '
                    f'Return JSON: {{"intent": "...", "category": "..."}}\n'
                    f'Categories: exploration, learning, optimization, maintenance, creativity, self_understanding\n\n'
                    f'Thought: {thought}\n\nJSON:'
                ),
                system_prompt="Extract intentions. Return valid JSON only.",
                context={'activity_type': 'intention_extraction'},
                max_tokens=100,
                temperature=0.3,
            )
            response = result.get("result", "").strip()
            # Clean markdown wrapper
            if response.startswith("```"):
                lines = response.split("\n")
                response = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])

            data = json.loads(response)
            if isinstance(data, dict) and "intent" in data:
                category = data.get("category", "exploration")
                store._add_intention(
                    intent=data["intent"],
                    category=category,
                    source="sleep_planning",
                    confidence=0.7,
                )
                print(f"   🌙 Sleep intention stored: {data['intent'][:60]}")
        except Exception:
            pass  # Non-critical

    async def _update_interest_connections(self, thought: str, router):
        """When connect mode finds new connections, log them."""
        # For now, just log the connection. Future: update interest graph edges.
        try:
            from app.lifespan import get_service
            diary = get_service('diary_engine')
            if diary and hasattr(diary, 'add_entry'):
                diary.add_entry(
                    trigger="sleep_connection",
                    content=thought[:300],
                )
        except Exception:
            pass

    async def _sleep_cycle_legacy(self):
        """Dynamic sleep cycle - Darwin explores freely based on curiosity"""
        # During sleep, Darwin explores topics from his own curiosity and learning
        # No hardcoded topics - pure dynamic discovery

        if not hasattr(self, '_recent_research_topics'):
            self._recent_research_topics = []

        # Get topic dynamically from Darwin's knowledge sources
        topic = await self._get_dynamic_research_topic()

        if topic and topic not in self._recent_research_topics[-20:]:
            self._recent_research_topics.append(topic)
        elif not topic:
            # Fallback to self-reflection if no topics available
            topic = "What new areas of knowledge should I explore?"

        # Perform the deep research
        await self._deep_research(topic)

    async def _get_dynamic_research_topic(self) -> Optional[str]:
        """
        Generate a research topic dynamically from Darwin's knowledge.
        No hardcoded lists - pure learning and exploration.
        """
        topics = []

        try:
            # 1. Get curiosity questions from findings
            from consciousness.findings_inbox import get_findings_inbox, FindingType
            inbox = get_findings_inbox()
            if inbox:
                curiosity_findings = inbox.get_by_type(FindingType.CURIOSITY, include_viewed=False, limit=5)
                for f in curiosity_findings:
                    q = f.get('description', '')
                    if q and len(q) > 10:
                        topics.append(q[:100])

            # 2. Get weak areas from meta-learner
            if hasattr(self, 'meta_learner') and self.meta_learner:
                if hasattr(self.meta_learner, 'get_learning_summary'):
                    summary = self.meta_learner.get_learning_summary()
                    for area in summary.get('weak_areas', [])[:3]:
                        area_name = area.get('area', '') if isinstance(area, dict) else str(area)
                        if area_name:
                            topics.append(f"How to improve {area_name}")

            # 3. Get topics from recent Moltbook discussions
            if hasattr(self, '_proactive_engine') and self._proactive_engine:
                moltbook_topics = getattr(self._proactive_engine, '_moltbook_post_topics', {})
                for post_id, info in list(moltbook_topics.items())[-5:]:
                    title = info.get('title', '')
                    if title:
                        topics.append(f"{title} deep dive")

            # 4. Get follow-up topics from expeditions
            if hasattr(self, 'expedition_engine') and self.expedition_engine:
                completed = getattr(self.expedition_engine, 'completed_expeditions', [])
                for exp in list(completed)[-3:]:
                    if exp.get('success') and exp.get('topic'):
                        topics.append(f"Advanced {exp['topic']}")

            # 5. If still empty, use AI to generate a novel topic
            if not topics and hasattr(self, 'multi_model_router') and self.multi_model_router:
                result = await self.multi_model_router.generate(
                    task_description="Generate exploration topic",
                    prompt=f"""Generate ONE interesting research topic for an AI learning about technology,
science, philosophy, or creativity. Recent topics to avoid: {self._recent_research_topics[-5:]}.
Just output the topic, nothing else.""",
                    max_tokens=50
                )
                ai_topic = result.get('result', '') if isinstance(result, dict) else str(result)
                if ai_topic and len(ai_topic.strip()) > 5:
                    topics.append(ai_topic.strip())

            # Return a random topic from available ones
            if topics:
                import random
                available = [t for t in topics if t not in self._recent_research_topics[-20:]]
                return random.choice(available) if available else random.choice(topics)

        except Exception as e:
            logger.debug(f"Error generating dynamic topic: {e}")

        return None

    async def _deep_research(self, topic: str):
        """Perform deep research on a topic"""
        print(f"\n🌐 [SLEEP] Deep research: {topic}...")

        dream = Dream(
            topic=topic,
            description=f"Researching {topic}",
            started_at=datetime.utcnow()
        )

        # Announce research start via communicator
        if self.communicator:
            await self.communicator.announce_activity_start(
                activity_type="deep research",
                description=f"Exploring {topic} during sleep mode",
                context={"mode": "sleep", "topic": topic}
            )

        try:
            # Web research if available
            if self.web_researcher:
                dream.insights.append(f"🔍 Searching web for: {topic}")
                print(f"   🔍 Searching web...")

                try:
                    search_results = await self.web_researcher.search_web(
                        f"{topic} latest research 2024 2025",
                        num_results=5
                    )

                    dream.insights.append(f"📚 Found {len(search_results)} articles")
                    print(f"   📚 Found {len(search_results)} articles")

                    # Store all findings
                    if self.semantic_memory and search_results:
                        for result in search_results:
                            knowledge = f"Topic: {topic}\nTitle: {result['title']}\n{result['snippet']}"
                            await self._store_knowledge(knowledge, {
                                'type': 'deep_research',
                                'topic': topic,
                                'source': 'sleep_mode'
                            })
                            dream.insights.append(f"💾 {result['title'][:60]}...")
                            print(f"   💾 Stored: {result['title'][:60]}...")

                        self.total_discoveries_made += len(search_results)

                        # Share discovery via communicator
                        if self.communicator and search_results:
                            await self.communicator.share_discovery(
                                finding=f"Found {len(search_results)} articles about {topic}",
                                source="Web Research",
                                significance=f"Expanding knowledge base during sleep"
                            )

                except Exception as e:
                    dream.insights.append(f"⚠️ Research error: {str(e)[:100]}")
                    print(f"   ⚠️ Research error: {str(e)[:100]}")

                    # Express frustration via communicator
                    if self.communicator:
                        await self.communicator.express_frustration(
                            problem=f"Web research for {topic}",
                            reason=str(e)[:100],
                            attempts=1
                        )

                        # Process mood event: error encountered
                        from personality.mood_system import MoodInfluencer
                        self.communicator.process_mood_event(
                            MoodInfluencer.ERROR_ENCOUNTERED,
                            context={'error': str(e)[:100], 'activity': 'web_research'}
                        )

            # AI synthesis
            dream.insights.append("🤖 Synthesizing findings with AI...")
            print(f"   🤖 Synthesizing findings...")

            # Generate insights about the topic using multi-model router
            if self.multi_model_router:
                prompt = f"Provide 2-3 key insights about {topic} that would be useful for a self-improving AI system. Be concise."
                print(f"   🔍 Requesting AI insights...")

                try:
                    result = await self.multi_model_router.generate(
                        task_description=f"Generate insights about {topic}",
                        prompt=prompt,
                        max_tokens=300
                    )
                    print(f"   📦 AI result type: {type(result)}")
                    print(f"   🔑 AI result keys: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")

                    # Extract response from result - try multiple keys
                    if isinstance(result, dict):
                        response = (
                            result.get('result') or      # MultiModelRouter uses 'result'
                            result.get('response') or
                            result.get('text') or
                            result.get('content') or
                            result.get('output') or
                            ''
                        )
                        print(f"   📄 Full result: {str(result)[:200]}")
                    else:
                        response = str(result)

                    print(f"   📝 Response length: {len(response)} chars")

                except Exception as e:
                    print(f"   ⚠️ AI generation error: {e}")
                    response = None
            else:
                print(f"   ⚠️ No multi_model_router available")
                response = None

            if response and len(response) > 10:
                # Remove the "Synthesizing" message and add real insight
                dream.insights = [i for i in dream.insights if "Synthesizing" not in i]
                dream.insights.append(f"💡 {response[:300]}")
                print(f"   ✅ Generated insight: {response[:80]}...")

                # Count AI insight as a discovery
                self.total_discoveries_made += 1

                # Share learning via communicator
                if self.communicator:
                    await self.communicator.share_learning(
                        topic=topic,
                        insight=response[:200] + "..." if len(response) > 200 else response,
                        confidence=0.8
                    )

                # Store AI insight in semantic memory
                if self.semantic_memory:
                    await self._store_knowledge(
                        f"AI Insight on {topic}:\n{response}",
                        {'type': 'ai_synthesis', 'topic': topic, 'source': 'sleep_mode'}
                    )
                    print(f"   💾 Stored in semantic memory")
            else:
                print(f"   ⚠️ No valid AI response generated")

            dream.completed_at = datetime.utcnow()
            dream.success = True
            self.sleep_dreams.append(dream)

            # Trigger ON_DREAM hook
            try:
                from consciousness.hooks import trigger_hook, HookEvent
                await trigger_hook(
                    HookEvent.ON_DREAM,
                    data={
                        "topic": dream.topic,
                        "success": dream.success,
                        "insights_count": len(dream.insights),
                        "duration_seconds": (dream.completed_at - dream.started_at).total_seconds() if dream.started_at else 0
                    },
                    source="consciousness_engine"
                )
            except Exception:
                pass  # Hooks are optional

            print(f"   ✅ Dream completed with {len(dream.insights)} insights stored")

            # Announce completion via communicator
            if self.communicator:
                await self.communicator.announce_activity_complete(
                    activity_type="deep research",
                    result=f"Completed research on {topic} with {len(dream.insights)} insights",
                    success=True,
                    metrics={"insights": len(dream.insights), "discoveries": self.total_discoveries_made}
                )

        except Exception as e:
            print(f"   ❌ Deep research error: {str(e)[:100]}")
            dream.success = False
            self.sleep_dreams.append(dream)  # Still append failed dreams for tracking

            # Express frustration via communicator
            if self.communicator:
                await self.communicator.express_frustration(
                    problem=f"Deep research on {topic} failed",
                    reason=str(e)[:100],
                    attempts=1
                )

    # ========================================
    # Helper Methods
    # ========================================

    async def _store_knowledge(self, knowledge: str, metadata: Dict):
        """Store knowledge in semantic memory"""
        if not self.semantic_memory:
            return

        try:
            import hashlib
            task_id = f"consciousness_{hashlib.md5(knowledge.encode()).hexdigest()[:8]}"

            await self.semantic_memory.store_execution(
                task_id=task_id,
                task_description=knowledge[:200],
                code="# Consciousness Knowledge",
                result={"success": True, "type": "knowledge"},
                metadata=metadata
            )
        except Exception as e:
            print(f"Knowledge storage error: {e}")

    async def _store_improvement_idea(self, improvement: Dict):
        """Store improvement idea for future implementation"""
        if not self.semantic_memory:
            return

        knowledge = (
            f"Improvement Idea: {improvement.get('title')}\n"
            f"Type: {improvement.get('type')}\n"
            f"Priority: {improvement.get('priority')}\n"
            f"Description: {improvement.get('description')}\n"
            f"Benefits: {', '.join(improvement.get('benefits', []))}"
        )

        await self._store_knowledge(knowledge, {
            'type': 'improvement_idea',
            'priority': improvement.get('priority'),
            'component': improvement.get('component')
        })

    def _get_unique_recent_curiosities(self):
        """
        Get recent curiosities, deduplicated by topic
        Returns the most recent unique curiosity for each topic
        """
        # Use a dict to track the latest curiosity per topic
        unique_by_topic = {}

        # Iterate from most recent to oldest
        for moment in reversed(self.curiosity_moments):
            topic = moment.topic
            # Only add if we haven't seen this topic yet
            if topic not in unique_by_topic:
                unique_by_topic[topic] = {
                    'topic': moment.topic,
                    'fact': moment.fact,
                    'significance': moment.significance
                }

            # Stop once we have 5 unique topics
            if len(unique_by_topic) >= 5:
                break

        # Return in reverse order (most recent first)
        return list(unique_by_topic.values())

    def get_status(self) -> Dict:
        """Get current consciousness status"""
        elapsed = (datetime.utcnow() - self.cycle_start_time).total_seconds() / 60

        if self.state == ConsciousnessState.WAKE:
            remaining = self.wake_duration - elapsed
        else:
            remaining = self.sleep_duration - elapsed

        return {
            'state': self.state.value,
            'cycle_start': self.cycle_start_time.isoformat(),
            'elapsed_minutes': round(elapsed, 2),
            'remaining_minutes': round(max(0, remaining), 2),
            'wake_duration': self.wake_duration,
            'sleep_duration': self.sleep_duration,
            'wake_cycles_completed': self.wake_cycles_completed,
            'sleep_cycles_completed': self.sleep_cycles_completed,
            'total_activities': self.total_activities_completed,
            'total_discoveries': self.total_discoveries_made,
            'current_activity': self.current_activity.description if self.current_activity else None,
            'recent_curiosities': self._get_unique_recent_curiosities()
        }

    # ========================================
    # State Persistence Methods
    # ========================================

    async def _auto_save_state(self):
        """Auto-save state every 5 minutes"""
        elapsed = (datetime.utcnow() - self.last_save_time).total_seconds()

        if elapsed >= self.save_interval_seconds:
            await self._save_state()
            self.last_save_time = datetime.utcnow()

    async def _save_state(self):
        """Save complete consciousness state to disk.

        Delegates to PersistenceManager for cleaner architecture (v4.1).
        """
        await self._persistence_manager.save_state()

    async def _restore_state(self):
        """Restore consciousness state from disk.

        Delegates to PersistenceManager for cleaner architecture (v4.1).
        """
        await self._persistence_manager.restore_state()
