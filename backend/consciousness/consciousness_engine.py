"""
Consciousness Engine - Darwin's Wake/Sleep Cycles

Darwin now operates in two distinct modes:
- WAKE (2 hours): Active development, optimization, creativity
- SLEEP (30 minutes): Deep research, learning, dream exploration

This creates a more natural, human-like rhythm of productivity and rest.
"""
import asyncio
import os
import json
from pathlib import Path
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
import random

from core.deduplication import get_deduplication_store, DeduplicationStore


class ConsciousnessState(Enum):
    """Darwin's consciousness states"""
    WAKE = "wake"
    SLEEP = "sleep"
    TRANSITION = "transition"


@dataclass
class Activity:
    """An activity Darwin performs while awake"""
    type: str  # 'code_optimization', 'tool_creation', 'idea_implementation', 'curiosity_share'
    description: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[Dict] = None
    insights: List[str] = field(default_factory=list)


@dataclass
class CuriosityMoment:
    """A curiosity moment Darwin shares while awake"""
    topic: str
    fact: str
    source: str
    significance: str
    timestamp: datetime


@dataclass
class Dream:
    """A research dream Darwin has during sleep"""
    topic: str
    description: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    success: bool = False
    insights: List[str] = field(default_factory=list)
    exploration_details: Optional[Dict[str, Any]] = None  # NEW: URLs, repos, files explored


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
        diary_engine=None  # NEW: Memory diary engine
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

        # Database-backed deduplication store (replaces in-memory set)
        self._dedup_store: DeduplicationStore = get_deduplication_store()

        # Legacy in-memory set for backwards compatibility during transition
        # Will be migrated to database on first run
        self._submitted_insights_legacy: set = set()

        # Dynamic curiosity discovery pool - populated from exploration activities
        # This replaces hardcoded curiosities with things Darwin actually discovered
        self.discovered_curiosities: List[Dict] = []
        self.max_discovered_curiosities = 100  # Keep last 100 discoveries

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
        """Check if should transition between wake/sleep"""
        # Skip transitions if in debug mode
        if self.debug_mode in ['sleep', 'wake']:
            return  # No transitions in debug mode

        elapsed = (datetime.utcnow() - self.cycle_start_time).total_seconds() / 60

        if self.state == ConsciousnessState.WAKE and elapsed >= self.wake_duration:
            await self._transition_to_sleep()
        elif self.state == ConsciousnessState.SLEEP and elapsed >= self.sleep_duration:
            await self._transition_to_wake()

    async def _transition_to_sleep(self):
        """Transition from wake to sleep"""
        print(f"\n😴 Darwin is getting tired... transitioning to SLEEP")
        print(f"📊 Wake cycle summary: {len(self.wake_activities)} activities completed")

        # Trigger before_sleep hooks
        try:
            from consciousness.hooks import trigger_hook, HookEvent
            await trigger_hook(HookEvent.BEFORE_SLEEP, {
                'activities_count': len(self.wake_activities),
                'wake_cycles_completed': self.wake_cycles_completed
            }, source='consciousness_engine')
        except Exception as e:
            print(f"⚠️ Hook trigger failed: {e}")

        # Write diary entry before sleeping
        if self.diary_engine:
            try:
                diary_path = await self.diary_engine.write_daily_entry(trigger="wake_to_sleep")
                print(f"📔 Diary entry written: {diary_path}")
            except Exception as e:
                print(f"⚠️ Failed to write diary: {e}")

        # Announce transition via communicator
        if self.communicator:
            await self.communicator.share_reflection(
                thought=f"Completed {len(self.wake_activities)} activities during wake cycle. Time to rest and learn deeply.",
                depth="medium"
            )

            # Process mood event: sleep cycle starting
            from personality.mood_system import MoodInfluencer
            self.communicator.process_mood_event(MoodInfluencer.SLEEP_CYCLE_START)

        self.state = ConsciousnessState.SLEEP
        self.cycle_start_time = datetime.utcnow()
        self.wake_cycles_completed += 1

        # Broadcast to channels
        if hasattr(self, 'channel_gateway') and self.channel_gateway:
            try:
                await self.channel_gateway.broadcast_status(
                    f"Darwin is entering SLEEP mode. Completed {len(self.wake_activities)} activities during wake cycle.",
                    "sleep"
                )
            except Exception as e:
                print(f"⚠️ Channel broadcast failed: {e}")

        # Celebrate milestones
        if self.communicator and self.wake_cycles_completed % 10 == 0:
            await self.communicator.celebrate_achievement(
                achievement=f"Completed {self.wake_cycles_completed} wake cycles!",
                milestone=f"{self.wake_cycles_completed} wake cycles"
            )

        # Share summary of wake period
        if self.wake_activities:
            print("✨ During this wake period, I:")
            for activity in self.wake_activities[-5:]:  # Last 5
                print(f"   • {activity.description}")

        # Keep last 50 activities for frontend access (don't clear completely)
        if len(self.wake_activities) > 50:
            self.wake_activities = self.wake_activities[-50:]

        # Trigger after_sleep hooks
        try:
            from consciousness.hooks import trigger_hook, HookEvent
            await trigger_hook(HookEvent.AFTER_SLEEP, {
                'wake_cycles_completed': self.wake_cycles_completed
            }, source='consciousness_engine')
        except Exception as e:
            print(f"⚠️ Hook trigger failed: {e}")

    async def _transition_to_wake(self):
        """Transition from sleep to wake"""
        print(f"\n🌅 Darwin is waking up... transitioning to WAKE")
        print(f"📊 Sleep cycle summary: {len(self.sleep_dreams)} dreams explored")

        # Trigger before_wake hooks
        try:
            from consciousness.hooks import trigger_hook, HookEvent
            await trigger_hook(HookEvent.BEFORE_WAKE, {
                'dreams_count': len(self.sleep_dreams),
                'sleep_cycles_completed': self.sleep_cycles_completed
            }, source='consciousness_engine')
        except Exception as e:
            print(f"⚠️ Hook trigger failed: {e}")

        # Announce transition and discoveries via communicator
        if self.communicator:
            discoveries_count = sum(len(d.insights) for d in self.sleep_dreams if hasattr(d, 'insights') and d.insights)
            await self.communicator.share_reflection(
                thought=f"Waking up refreshed! Explored {len(self.sleep_dreams)} topics and made {discoveries_count} discoveries during sleep.",
                depth="medium"
            )

            # Process mood event: wake cycle starting
            from personality.mood_system import MoodInfluencer
            self.communicator.process_mood_event(
                MoodInfluencer.WAKE_CYCLE_START,
                context={'discoveries': discoveries_count}
            )

        self.state = ConsciousnessState.WAKE
        self.cycle_start_time = datetime.utcnow()
        self.sleep_cycles_completed += 1

        # Broadcast wake and dreams to channels
        if hasattr(self, 'channel_gateway') and self.channel_gateway:
            try:
                # Create dream summary
                discoveries_count = sum(len(d.insights) for d in self.sleep_dreams if hasattr(d, 'insights') and d.insights)
                dream_summary = f"Explored {len(self.sleep_dreams)} topics and made {discoveries_count} discoveries."

                # Get dream highlights
                highlights = []
                for dream in self.sleep_dreams[-3:]:
                    if hasattr(dream, 'insights') and dream.insights:
                        highlights.extend(dream.insights[:1])

                await self.channel_gateway.broadcast_dream(dream_summary, highlights)
            except Exception as e:
                print(f"⚠️ Dream broadcast failed: {e}")

        # Celebrate milestones
        if self.communicator and self.sleep_cycles_completed % 10 == 0:
            await self.communicator.celebrate_achievement(
                achievement=f"Completed {self.sleep_cycles_completed} sleep cycles!",
                milestone=f"{self.sleep_cycles_completed} sleep cycles"
            )

        # Share discoveries from sleep
        if self.sleep_dreams:
            print("💡 During sleep, I discovered:")
            for dream in self.sleep_dreams[-3:]:  # Last 3
                # FIX: Dream is dataclass, not dict - use attributes not .get()
                insights_count = len(dream.insights) if hasattr(dream, 'insights') and dream.insights else 0
                description = dream.description if hasattr(dream, 'description') else 'Unknown'
                print(f"   • {description} ({insights_count} insights)")

        # Keep last 50 dreams for frontend access (don't clear completely)
        if len(self.sleep_dreams) > 50:
            self.sleep_dreams = self.sleep_dreams[-50:]

        # Trigger after_wake hooks
        try:
            from consciousness.hooks import trigger_hook, HookEvent
            await trigger_hook(HookEvent.AFTER_WAKE, {
                'sleep_cycles_completed': self.sleep_cycles_completed,
                'dreams_count': len(self.sleep_dreams)
            }, source='consciousness_engine')
        except Exception as e:
            print(f"⚠️ Hook trigger failed: {e}")

    # ========================================
    # WAKE MODE - Active Development
    # ========================================

    async def _wake_cycle(self):
        """Execute wake activities with tool rotation strategy"""
        # Use dynamic tool registry if available
        if self.tool_registry:
            try:
                # Determine if we should explore (30% chance to use least-used tools)
                exploration_mode = random.random() < 0.30

                # Build context about current state
                context = (
                    f"Darwin is AWAKE and wants to be productive. "
                    f"Completed {self.total_activities_completed} activities, "
                    f"made {self.total_discoveries_made} discoveries. "
                    f"Recent activities: {', '.join([a.type for a in self.wake_activities[-3:]])}. "
                    f"Choose a tool to help Darwin learn, create, or improve."
                )

                if exploration_mode:
                    print(f"\n🔍 [WAKE] Exploration mode - trying less-used tools...")
                    tool = await self._select_exploration_tool()
                else:
                    print(f"\n🧠 [WAKE] Selecting tool consciously...")
                    # Use top_k=5 for more tool diversity
                    tool = await self.tool_registry.select_tool_consciously(
                        mode="wake",
                        context=context,
                        top_k=5
                    )

                if not tool:
                    print(f"   ⚠️ No suitable tool available")
                    await self._wake_cycle_legacy()
                    return

                # Execute tool with retry on transient errors
                result = await self._execute_with_retry(tool, max_retries=2)

                if result.get('success'):
                    tool_name = result.get('tool_used', tool.name)
                    print(f"   ✅ Tool executed: {tool_name}")
                    self.total_activities_completed += 1

                    # Track as activity
                    activity = Activity(
                        type='dynamic_tool',
                        description=f"Used {tool_name}",
                        started_at=datetime.utcnow(),
                        completed_at=datetime.utcnow(),
                        result=result
                    )
                    self.wake_activities.append(activity)

                    # Process tool results and generate code if needed
                    await self._process_tool_results(tool_name, result, activity)
                else:
                    error_msg = result.get('error', 'Unknown error')
                    error_type = self._classify_error(error_msg)
                    print(f"   ⚠️ Tool execution failed ({error_type}): {error_msg}")

                    if error_type == 'transient':
                        # Try a different tool before falling back to legacy
                        print(f"   🔄 Transient error, trying different tool...")
                        alt_result = await self._try_alternative_tool(tool, context)
                        if alt_result and alt_result.get('success'):
                            return  # Alternative tool succeeded

                    # Use legacy as last resort
                    print(f"   🔄 Falling back to legacy activities")
                    await self._wake_cycle_legacy()

            except Exception as e:
                print(f"   ❌ Dynamic tool selection error: {e}")
                # Fallback to legacy hardcoded system
                await self._wake_cycle_legacy()
        else:
            # No tool registry - use legacy hardcoded system
            await self._wake_cycle_legacy()

        # Wait before next activity (activities are spaced out) - 2x faster now!
        activity_interval = random.randint(2, 7)  # 2-7 minutes (was 5-15)
        await asyncio.sleep(activity_interval * 60)

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
        weights = [0.15, 0.08, 0.15, 0.30, 0.17, 0.10, 0.05]
        # apply_changes gets 30% - highest priority to actually deploy approved code
        # poetry_generation gets 5% - occasional creative expression
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

                            # Generate code using the code generator
                            code_result = await self.code_generator.generate_code_for_insight(insight)

                            if code_result and hasattr(code_result, 'new_code') and code_result.new_code:
                                print(f"   ✅ Code generated: {len(code_result.new_code)} chars")

                                # Validate the generated code
                                from introspection.code_validator import CodeValidator
                                validator = CodeValidator()
                                validation_result = await validator.validate(code_result)

                                print(f"   📊 Validation score: {validation_result.score}/100")

                                # Submit to approval queue with validation
                                insight_key = f"optimization:{top_optimization.get('title')}"
                                if self.approval_queue:
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

        # Fallback to hardcoded + expanded list
        if not tool_idea:
            tool_ideas = [
                "Code complexity analyzer",
                "Automated test generator",
                "Performance profiler",
                "Documentation generator",
                "Dependency analyzer",
                "Security vulnerability scanner",
                "API rate limiter",
                "Data validator",
                "Cache manager",
                # NEW: Expanded list
                "Memory leak detector",
                "API response time optimizer",
                "Database query analyzer",
                "Frontend bundle size optimizer",
                "Environment configuration validator",
                "Log aggregation tool",
                "Health check dashboard",
                "Metrics collector",
                "Error tracking system",
                "Load testing framework"
            ]

            # Filter out already submitted, existing, and pending tools
            existing_tools = self._get_existing_tools()
            pending_tools = self._get_pending_tool_changes()

            available_tools = [
                tool for tool in tool_ideas
                if (not self._is_insight_submitted(f"tool:{tool}") and
                    tool not in existing_tools and
                    tool not in pending_tools)
            ]

            # Log what we're skipping
            if len(tool_ideas) > len(available_tools):
                skipped = len(tool_ideas) - len(available_tools)
                print(f"   🔍 Filtered out {skipped} existing/pending tools")

            # If all tools submitted, generate a unique one
            if not available_tools:
                # Generate unique tool based on timestamp
                concepts = ["optimizer", "analyzer", "validator", "monitor", "tracker", "profiler"]
                targets = ["API", "database", "memory", "network", "security", "performance"]
                import time
                tool_idea = f"{random.choice(targets)} {random.choice(concepts)} {int(time.time()) % 1000}"
                activity.insights.append(f"Generated unique tool: {tool_idea}")
                print(f"   🎲 Generated unique tool: {tool_idea}")
            else:
                tool_idea = random.choice(available_tools)
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
        """Analyze and improve Darwin's own systems"""
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

                    # Add details of top 3 improvements to insights
                    for i, improvement in enumerate(high_priority[:3], 1):
                        title = improvement.get('title', 'Unknown')
                        description = improvement.get('description', '')
                        impact = improvement.get('estimated_impact', 'unknown')

                        activity.insights.append(f"{i}. {title} (Impact: {impact})")
                        activity.insights.append(f"   → {description[:150]}")

                        print(f"   {i}. 🎯 {title}")
                        print(f"      💡 {description[:100]}...")
                        print(f"      📈 Impact: {impact}")

                    # Store all high-priority improvements in semantic memory
                    if self.semantic_memory and high_priority:
                        for improvement in high_priority[:3]:  # Store top 3
                            await self._store_improvement_idea(improvement)
                        print(f"   💾 Stored {min(3, len(high_priority))} improvements in memory")

                    activity.result = {
                        'improvements_found': len(high_priority),
                        'total_insights': len(all_insights),
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
        """Execute sleep activities (deep research)"""
        # Use dynamic tool registry if available
        if self.tool_registry:
            try:
                # Build context about current state
                context = (
                    f"Darwin is SLEEPING and wants to learn deeply. "
                    f"Completed {self.sleep_cycles_completed} sleep cycles, "
                    f"made {self.total_discoveries_made} discoveries. "
                    f"Recent dreams: {', '.join([d.topic[:30] for d in self.sleep_dreams[-3:]])}. "
                    f"Choose a learning tool to explore new knowledge during sleep."
                )

                print(f"\n😴 [SLEEP] Selecting learning tool consciously...")

                # Let tool registry select and execute the best tool for sleep mode
                result = await self.tool_registry.select_and_execute(
                    mode="sleep",
                    context=context,
                    top_k=3  # Consider top 3 tools
                )

                if result.get('success'):
                    tool_name = result.get('tool_used')
                    print(f"   ✅ Tool executed: {tool_name}")
                    self.total_discoveries_made += 1

                    # Extract meaningful insights from tool result
                    # FIX: The tool wrappers return data at the top level, not in a 'result' sub-key
                    tool_result = result  # Use result directly, not result.get('result')
                    insights = []
                    exploration_details = {}  # NEW: Track what was explored

                    # Extract key information based on what the tool returned
                    if isinstance(tool_result, dict):
                        # Repository analyzer results
                        if tool_result.get('repository'):
                            repo = tool_result['repository']
                            insights.append(f"📦 Analyzed: {repo}")
                            exploration_details['type'] = 'repository'
                            exploration_details['repository'] = repo
                            exploration_details['url'] = tool_result.get('url', f"https://github.com/{repo}")
                        if tool_result.get('insights_found'):
                            count = tool_result['insights_found']
                            insights.append(f"💡 Found {count} insights")
                            exploration_details['insights_count'] = count
                        if tool_result.get('patterns'):
                            patterns = tool_result['patterns']
                            if isinstance(patterns, list) and patterns:
                                insights.append(f"🔍 Patterns: {', '.join(patterns[:3])}")
                                exploration_details['patterns'] = patterns[:5]
                        if tool_result.get('patterns_discovered'):
                            exploration_details['patterns_count'] = tool_result['patterns_discovered']

                        # Web explorer results
                        if tool_result.get('url'):
                            url = tool_result['url']
                            insights.append(f"🌐 Explored: {url}")
                            exploration_details['type'] = 'web'
                            exploration_details['url'] = url
                        if tool_result.get('urls_visited'):
                            urls = tool_result['urls_visited']
                            exploration_details['urls_visited'] = urls
                            insights.append(f"🌐 Visited {len(urls)} pages")
                        if tool_result.get('content_length'):
                            insights.append(f"📄 {tool_result['content_length']} chars analyzed")
                            exploration_details['content_length'] = tool_result['content_length']
                        if tool_result.get('knowledge_items'):
                            count = tool_result['knowledge_items']
                            insights.append(f"💡 Extracted {count} knowledge items")
                            exploration_details['knowledge_items'] = count

                        # Documentation reader results
                        if tool_result.get('file'):
                            file = tool_result['file']
                            insights.append(f"📚 Read: {file}")
                            exploration_details['type'] = 'documentation'
                            exploration_details['file'] = file
                        if tool_result.get('source'):
                            exploration_details['source'] = tool_result['source']
                        if tool_result.get('sections'):
                            insights.append(f"📑 {tool_result['sections']} sections processed")
                            exploration_details['sections_count'] = tool_result['sections']

                        # Experimental sandbox results
                        if tool_result.get('experiment'):
                            exp = tool_result['experiment']
                            insights.append(f"🧪 Experiment: {exp}")
                            exploration_details['type'] = 'experiment'
                            exploration_details['experiment'] = exp
                        if tool_result.get('outcome'):
                            outcome = tool_result['outcome']
                            insights.append(f"✅ Outcome: {outcome}")
                            exploration_details['outcome'] = outcome
                        if tool_result.get('success_rate'):
                            exploration_details['success_rate'] = tool_result['success_rate']

                    # If no specific insights extracted, add generic summary
                    if not insights:
                        insights.append(f"✅ {tool_name} completed successfully")
                        if isinstance(tool_result, dict) and tool_result:
                            # Add top 2 keys from result
                            keys = list(tool_result.keys())[:2]
                            for key in keys:
                                value = tool_result[key]
                                insights.append(f"• {key}: {str(value)[:80]}")
                                exploration_details[key] = value

                    # Track as dream with exploration details
                    dream = Dream(
                        topic=tool_name,
                        description=f"Used {tool_name} during sleep",
                        started_at=datetime.utcnow(),
                        completed_at=datetime.utcnow(),
                        success=True,
                        insights=insights,
                        exploration_details=exploration_details if exploration_details else None
                    )
                    self.sleep_dreams.append(dream)

                    # NEW: Process SLEEP tool results to generate actionable CodeInsights
                    # This transforms patterns from repository_analyzer and web_explorer into implementation ideas
                    print(f"   🔍 Processing sleep results for wake implementation...")

                    # Create a temporary activity to track code generation from sleep tools
                    temp_activity = Activity(
                        type='dream_processing',
                        description=f"Processing {tool_name} results",
                        started_at=datetime.utcnow(),
                        completed_at=datetime.utcnow()
                    )

                    # Process results (will generate CodeInsights if patterns found)
                    await self._process_tool_results(tool_name, result, temp_activity)
                else:
                    print(f"   ⚠️ Tool execution failed: {result.get('error')}")

            except Exception as e:
                print(f"   ❌ Dynamic tool selection error: {e}")
                # Fallback to legacy hardcoded system
                await self._sleep_cycle_legacy()
        else:
            # No tool registry - use legacy hardcoded system
            await self._sleep_cycle_legacy()

        # Sleep activities happen VERY frequently - Darwin needs to dream and research!
        sleep_interval = random.randint(30, 90)  # 30-90 seconds (was 1-3 minutes)
        await asyncio.sleep(sleep_interval)

    async def _sleep_cycle_legacy(self):
        """Legacy hardcoded sleep cycle (fallback)"""
        # During sleep, Darwin can freely explore the internet
        # without constraints, learning everything possible

        # Expanded research topics for more diversity and innovation
        research_topics = [
            # Core CS & Algorithms
            'quantum computing algorithms',
            'graph neural networks',
            'reinforcement learning from human feedback',
            'transformer architectures evolution',
            'self-supervised learning techniques',
            'federated learning systems',
            'neuromorphic computing',
            'probabilistic programming',

            # System Architecture
            'event-driven architecture patterns',
            'CQRS and event sourcing',
            'microservices orchestration',
            'serverless architecture tradeoffs',
            'distributed consensus algorithms',
            'chaos engineering practices',
            'zero-trust security architecture',

            # Performance & Optimization
            'memory-efficient data structures',
            'GPU acceleration techniques',
            'async I/O optimization',
            'cache coherence strategies',
            'database query optimization',
            'compiler optimization techniques',
            'JIT compilation strategies',

            # Emerging Tech
            'WebAssembly use cases',
            'edge computing paradigms',
            'blockchain beyond cryptocurrency',
            'homomorphic encryption',
            'differential privacy techniques',
            'synthetic data generation',
            'AI interpretability methods',

            # Software Engineering
            'property-based testing',
            'mutation testing strategies',
            'continuous profiling',
            'feature flag architecture',
            'API versioning strategies',
            'dependency injection patterns',
            'hexagonal architecture',

            # AI/ML Specific
            'few-shot learning techniques',
            'neural architecture search',
            'model distillation methods',
            'adversarial training',
            'continual learning strategies',
            'multimodal AI systems',
            'prompt engineering techniques',

            # Innovation & Research
            'biomimetic algorithms',
            'swarm intelligence',
            'evolutionary computation',
            'symbolic AI revival',
            'neurosymbolic AI',
            'automated theorem proving',
            'program synthesis',
            'meta-learning frameworks'
        ]

        # Avoid recently researched topics
        if not hasattr(self, '_recent_research_topics'):
            self._recent_research_topics = []

        # Filter out recent topics
        available_topics = [t for t in research_topics if t not in self._recent_research_topics[-20:]]

        if not available_topics:
            # All topics recently used, reset
            self._recent_research_topics = []
            available_topics = research_topics

        topic = random.choice(available_topics)
        self._recent_research_topics.append(topic)

        await self._deep_research(topic)

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
        """Save complete consciousness state to disk"""
        try:
            # Ensure data directory exists
            self.state_file.parent.mkdir(parents=True, exist_ok=True)

            state = {
                # Current state
                'state': self.state.value,
                'cycle_start_time': self.cycle_start_time.isoformat(),

                # Statistics
                'wake_cycles_completed': self.wake_cycles_completed,
                'sleep_cycles_completed': self.sleep_cycles_completed,
                'total_activities_completed': self.total_activities_completed,
                'total_discoveries_made': self.total_discoveries_made,

                # Activities (last 50 to prevent file bloat)
                'wake_activities': [
                    {
                        'type': a.type,
                        'description': a.description,
                        'started_at': a.started_at.isoformat(),
                        'completed_at': a.completed_at.isoformat() if a.completed_at else None,
                        'result': a.result,
                        'insights': a.insights
                    }
                    for a in self.wake_activities[-50:]
                ],

                # Dreams (last 30)
                'sleep_dreams': [
                    {
                        'topic': d.topic,
                        'description': d.description,
                        'started_at': d.started_at.isoformat(),
                        'completed_at': d.completed_at.isoformat() if d.completed_at else None,
                        'success': d.success,
                        'insights': d.insights,
                        'exploration_details': d.exploration_details  # NEW: Save exploration details
                    }
                    for d in self.sleep_dreams[-30:]
                ],

                # Curiosities (last 20)
                'curiosity_moments': [
                    {
                        'topic': c.topic,
                        'fact': c.fact,
                        'source': c.source,
                        'significance': c.significance,
                        'timestamp': c.timestamp.isoformat()
                    }
                    for c in self.curiosity_moments[-20:]
                ],

                # Deduplication tracking (submitted_insights now stored in database)
                # Keep for backwards compatibility during migration, but will be removed
                'submitted_insights': [],  # No longer saved here - database-backed
                'shared_curiosity_topics': list(self.shared_curiosity_topics),
                'dedup_stats': self._dedup_store.get_stats(),  # For debugging

                # Metadata
                'saved_at': datetime.utcnow().isoformat(),
                'version': '4.0'
            }

            # Write to file with atomic operation
            temp_file = self.state_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)

            # Atomic rename
            temp_file.replace(self.state_file)

            print(f"💾 State saved: {len(self.wake_activities)} activities, {len(self.sleep_dreams)} dreams, {len(self.curiosity_moments)} curiosities")

        except Exception as e:
            print(f"❌ Failed to save state: {e}")

    async def _restore_state(self):
        """Restore consciousness state from disk"""
        try:
            if not self.state_file.exists():
                print("ℹ️  No previous state found, starting fresh")
                return

            with open(self.state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)

            # Restore state
            self.state = ConsciousnessState(state['state'])
            self.cycle_start_time = datetime.fromisoformat(state['cycle_start_time'])

            # Restore statistics
            self.wake_cycles_completed = state.get('wake_cycles_completed', 0)
            self.sleep_cycles_completed = state.get('sleep_cycles_completed', 0)
            self.total_activities_completed = state.get('total_activities_completed', 0)
            self.total_discoveries_made = state.get('total_discoveries_made', 0)

            # Restore activities
            self.wake_activities = [
                Activity(
                    type=a['type'],
                    description=a['description'],
                    started_at=datetime.fromisoformat(a['started_at']),
                    completed_at=datetime.fromisoformat(a['completed_at']) if a.get('completed_at') else None,
                    result=a.get('result'),
                    insights=a.get('insights', [])
                )
                for a in state.get('wake_activities', [])
            ]

            # Restore dreams
            self.sleep_dreams = [
                Dream(
                    topic=d['topic'],
                    description=d['description'],
                    started_at=datetime.fromisoformat(d['started_at']),
                    completed_at=datetime.fromisoformat(d['completed_at']) if d.get('completed_at') else None,
                    success=d.get('success', False),
                    insights=d.get('insights', []),
                    exploration_details=d.get('exploration_details')  # NEW: Restore exploration details
                )
                for d in state.get('sleep_dreams', [])
            ]

            # Restore curiosities
            self.curiosity_moments = [
                CuriosityMoment(
                    topic=c['topic'],
                    fact=c['fact'],
                    source=c['source'],
                    significance=c['significance'],
                    timestamp=datetime.fromisoformat(c['timestamp'])
                )
                for c in state.get('curiosity_moments', [])
            ]

            # Restore deduplication tracking
            # Migrate legacy submitted_insights from JSON to database (one-time migration)
            legacy_insights = state.get('submitted_insights', [])
            if legacy_insights:
                migrated = self._dedup_store.migrate_from_set(set(legacy_insights), source="json_migration")
                print(f"📦 Migrated {migrated} insights from JSON to database")

            self.shared_curiosity_topics = set(state.get('shared_curiosity_topics', []))

            # Get current dedup stats from database
            dedup_stats = self._dedup_store.get_stats()
            print(f"📚 Deduplication database: {dedup_stats['total_entries']} insights, {len(self.shared_curiosity_topics)} curiosity topics")

            # Check if cycle should have already transitioned
            elapsed = (datetime.utcnow() - self.cycle_start_time).total_seconds() / 60

            # If restored time is way beyond cycle duration, reset to fresh cycle
            if self.state == ConsciousnessState.WAKE and elapsed > self.wake_duration:
                # Should have transitioned to sleep already
                excess = elapsed - self.wake_duration
                if excess < self.sleep_duration:
                    # In middle of sleep cycle
                    self.state = ConsciousnessState.SLEEP
                    self.cycle_start_time = datetime.utcnow() - timedelta(minutes=excess)
                    print(f"⏩ Adjusted to SLEEP mode (excess: {excess:.1f} min)")
                else:
                    # Multiple cycles passed, start fresh WAKE
                    self.state = ConsciousnessState.WAKE
                    self.cycle_start_time = datetime.utcnow()
                    print(f"⏩ Multiple cycles passed, starting fresh WAKE")

            elif self.state == ConsciousnessState.SLEEP and elapsed > self.sleep_duration:
                # Should have transitioned to wake already
                self.state = ConsciousnessState.WAKE
                self.cycle_start_time = datetime.utcnow()
                print(f"⏩ Adjusted to WAKE mode (cycle complete)")

            elapsed = (datetime.utcnow() - self.cycle_start_time).total_seconds() / 60
            print(f"✅ State restored from {state['saved_at']}")
            print(f"   State: {self.state.value.upper()} (elapsed: {elapsed:.1f} min)")
            print(f"   Activities: {len(self.wake_activities)} | Dreams: {len(self.sleep_dreams)} | Curiosities: {len(self.curiosity_moments)}")

        except Exception as e:
            print(f"⚠️  Failed to restore state: {e}")
            print("   Starting fresh...")
            # Reset to defaults if restoration fails
            self.wake_activities = []
            self.sleep_dreams = []
            self.curiosity_moments = []
