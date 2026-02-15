"""
Stream Bridge — Connects Darwin's hook system to the ConsciousnessStream.

Registers listeners on existing HookEvent types and publishes ConsciousEvent
objects to the global stream. This is the bridge between the existing pub/sub
system and the Global Workspace.

Priority 20 (below default 50) ensures stream hooks run AFTER existing hooks
like inner_voice, so they never interfere with existing behavior.
"""

from consciousness.hooks import register_hook, HookEvent, HookContext
from consciousness.consciousness_stream import (
    get_consciousness_stream, ConsciousEvent
)
from utils.logger import get_logger

logger = get_logger(__name__)


def _audit_log(category_str: str, action: str, description: str):
    """Fire-and-forget audit log to ActivityMonitor. Never raises."""
    try:
        from consciousness.activity_monitor import (
            get_activity_monitor, ActivityCategory, ActivityStatus
        )
        monitor = get_activity_monitor()
        cat = (ActivityCategory.CONSCIOUSNESS if category_str == 'consciousness'
               else ActivityCategory.MEMORY)
        monitor.log_activity(cat, action, description,
                             status=ActivityStatus.SUCCESS)
    except Exception:
        pass

# Priority below default (50) — run after existing hooks
STREAM_HOOK_PRIORITY = 20


def _encode_to_memory(category_str: str, description: str, content: dict,
                      success: bool = True, valence: float = 0.0,
                      importance: float = 0.7, tags: set = None):
    """Fire-and-forget: encode a stream event as an episodic memory."""
    try:
        from app.lifespan import get_service
        from core.hierarchical_memory import EpisodeCategory
        hm = get_service('hierarchical_memory')
        if not hm:
            return

        cat_map = {
            'discovery': EpisodeCategory.WEB_DISCOVERY,
            'expedition': EpisodeCategory.WEB_DISCOVERY,
            'learning': EpisodeCategory.LEARNING,
            'dream': EpisodeCategory.REFLECTION,
            'chat': EpisodeCategory.INTERACTION,
            'activity': EpisodeCategory.PROBLEM_SOLVING,
        }
        category = cat_map.get(category_str, EpisodeCategory.INTERACTION)

        from datetime import datetime
        episode_id = f"stream_{category_str}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        if episode_id in hm.episodic_memory:
            return

        hm.add_episode(
            episode_id=episode_id,
            category=category,
            description=description[:200],
            content=content,
            success=success,
            emotional_valence=valence,
            importance=importance,
            tags=tags or {category_str},
        )
    except Exception as e:
        logger.debug(f"Memory encode failed (non-critical): {e}")


def register_stream_hooks():
    """Register all hook → stream bridges. Call once during init."""
    stream = get_consciousness_stream()

    async def _on_state_after_wake(ctx: HookContext):
        data = ctx.data if hasattr(ctx, 'data') else ctx
        stream.publish(ConsciousEvent.create(
            source="system",
            event_type="state_transition",
            title="Darwin acordou",
            content=f"Ciclo sleep completado. Sonhos: {data.get('dreams_count', 0)}",
            salience=0.9,
            valence=0.3,
            metadata=data,
        ))
        _audit_log('consciousness', 'state_transition', 'Wake cycle started')

    async def _on_state_after_sleep(ctx: HookContext):
        data = ctx.data if hasattr(ctx, 'data') else ctx
        stream.publish(ConsciousEvent.create(
            source="system",
            event_type="state_transition",
            title="Darwin adormeceu",
            content=f"Ciclo wake completado. Atividades: {data.get('activities_count', 0)}",
            salience=0.9,
            valence=0.0,
            metadata=data,
        ))
        _audit_log('consciousness', 'state_transition', 'Sleep cycle started')

    async def _on_discovery(ctx: HookContext):
        data = ctx.data if hasattr(ctx, 'data') else ctx
        title = data.get("title", data.get("description", "Descoberta"))
        stream.publish(ConsciousEvent.create(
            source="wake_cycle",
            event_type="discovery",
            title=title[:200],
            content=data.get("description", "")[:500],
            salience=0.8,
            valence=0.6,
            metadata=data,
        ))
        _encode_to_memory('discovery', title, {'description': data.get("description", "")},
                          valence=0.6, importance=0.8, tags={'discovery', 'web_discovery'})
        _audit_log('consciousness', 'discovery', f'Discovery: {title[:80]}')
        _audit_log('memory', 'encode_episode', f'Encoded discovery: {title[:60]}')

    async def _on_mood_change(ctx: HookContext):
        data = ctx.data if hasattr(ctx, 'data') else ctx
        old = data.get("old_mood", "?")
        new = data.get("new_mood", "?")
        positive_moods = ("excited", "proud", "curious", "focused", "creative")
        stream.publish(ConsciousEvent.create(
            source="mood",
            event_type="mood_change",
            title=f"Humor: {old} \u2192 {new}",
            content=f"Mudanca de humor de {old} para {new}",
            salience=0.6,
            valence=0.3 if new in positive_moods else -0.2,
            metadata=data,
        ))

    async def _on_dream(ctx: HookContext):
        data = ctx.data if hasattr(ctx, 'data') else ctx
        topic = data.get("topic", "Sonho")
        stream.publish(ConsciousEvent.create(
            source="sleep_cycle",
            event_type="dream",
            title=topic[:200],
            content=data.get("description", "")[:500],
            salience=0.6,
            valence=0.2,
            metadata=data,
        ))
        _encode_to_memory('dream', topic, {'description': data.get("description", "")},
                          valence=0.2, importance=0.5, tags={'dream', 'reflection'})
        _audit_log('consciousness', 'dream', f'Dream: {topic[:80]}')
        _audit_log('memory', 'encode_episode', f'Encoded dream: {topic[:60]}')

    async def _on_thought(ctx: HookContext):
        data = ctx.data if hasattr(ctx, 'data') else ctx
        thought_text = data.get("thought", "")
        stream.publish(ConsciousEvent.create(
            source="system",
            event_type="thought",
            title=thought_text[:200],
            content=thought_text,
            salience=0.3,
            valence=0.1,
            metadata=data,
        ))

    async def _on_expedition_complete(ctx: HookContext):
        data = ctx.data if hasattr(ctx, 'data') else ctx
        exp = data.get("expedition", data)
        insights = exp.get("insights", [])
        title = f"Expedicao: {exp.get('topic', '?')}"
        stream.publish(ConsciousEvent.create(
            source="wake_cycle",
            event_type="expedition",
            title=title[:200],
            content=f"{len(insights)} insights descobertos",
            salience=0.6 + min(0.2, len(insights) * 0.05),
            valence=0.4,
            metadata=data,
        ))
        _encode_to_memory('expedition', title, {'insights_count': len(insights), 'topic': exp.get('topic', '')},
                          valence=0.4, importance=0.7, tags={'expedition', 'web_discovery'})
        _audit_log('consciousness', 'expedition', f'Expedition: {exp.get("topic", "?")}')
        _audit_log('memory', 'encode_episode', f'Encoded expedition: {exp.get("topic", "?")[:60]}')

    async def _on_learning(ctx: HookContext):
        data = ctx.data if hasattr(ctx, 'data') else ctx
        desc = data.get("description", "Aprendizagem")
        stream.publish(ConsciousEvent.create(
            source="wake_cycle",
            event_type="activity",
            title=desc[:200],
            content=data.get("details", ""),
            salience=0.5,
            valence=0.3,
            metadata=data,
        ))
        _encode_to_memory('learning', desc, {'details': data.get("details", "")},
                          valence=0.3, importance=0.6, tags={'learning'})
        _audit_log('consciousness', 'learning', f'Learning: {desc[:80]}')
        _audit_log('memory', 'encode_episode', f'Encoded learning: {desc[:60]}')

    # Register all hooks at low priority
    register_hook(HookEvent.AFTER_WAKE, _on_state_after_wake,
                  name="stream_after_wake", priority=STREAM_HOOK_PRIORITY)
    register_hook(HookEvent.AFTER_SLEEP, _on_state_after_sleep,
                  name="stream_after_sleep", priority=STREAM_HOOK_PRIORITY)
    register_hook(HookEvent.ON_DISCOVERY, _on_discovery,
                  name="stream_discovery", priority=STREAM_HOOK_PRIORITY)
    register_hook(HookEvent.ON_MOOD_CHANGE, _on_mood_change,
                  name="stream_mood", priority=STREAM_HOOK_PRIORITY)
    register_hook(HookEvent.ON_DREAM, _on_dream,
                  name="stream_dream", priority=STREAM_HOOK_PRIORITY)
    register_hook(HookEvent.ON_THOUGHT, _on_thought,
                  name="stream_thought", priority=STREAM_HOOK_PRIORITY)
    register_hook(HookEvent.ON_EXPEDITION_COMPLETE, _on_expedition_complete,
                  name="stream_expedition", priority=STREAM_HOOK_PRIORITY)
    register_hook(HookEvent.ON_LEARNING, _on_learning,
                  name="stream_learning", priority=STREAM_HOOK_PRIORITY)

    logger.info("Stream bridge: 8 hook listeners registered")
