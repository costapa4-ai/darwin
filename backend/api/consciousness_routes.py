"""
Consciousness API Routes
"""
from fastapi import APIRouter, HTTPException
from typing import Optional
from pydantic import BaseModel
from datetime import datetime
import anthropic
import json
import re
import os
import random

router = APIRouter(prefix="/api/v1/consciousness", tags=["consciousness"])

# Global instance (set by main.py)
consciousness_engine = None
mood_system = None  # For personality modes

# Persistent conversation store (set by initialization)
conversation_store = None
prompt_composer = None

# In-memory cache for backward compatibility with /chat/history
chat_messages = []
last_discussed_topic = None  # Track conversation topic


def initialize_conversations(store, composer=None):
    """Initialize conversation persistence and prompt composer."""
    global conversation_store, prompt_composer, chat_messages
    conversation_store = store
    prompt_composer = composer
    # Load recent messages into cache for backward compat
    if store:
        try:
            recent = store.get_recent(limit=50)
            chat_messages.clear()
            chat_messages.extend(recent)
        except Exception:
            pass

# === CHAT TOOL EXECUTION (AGENTIC LOOP) ===
# Shared utilities imported from autonomous_loop
from consciousness.autonomous_loop import (
    TOOL_CALL_RE as _TOOL_CALL_RE,
    ALLOWED_TOOLS as _CHAT_TOOLS,
    get_tool_manager as _get_tool_manager,
    extract_and_execute_tools as _extract_and_execute_tools,
    format_tool_result_brief as _format_brief,
)

# Max iterations for the agentic loop (prevents runaway)
_MAX_TOOL_ITERATIONS = 5


async def _run_agent_loop(
    user_message: str,
    system_prompt: str,
    router_service,
    max_tokens: int = 2500,
) -> str:
    """
    Agentic loop: LLM generates → tools execute → results fed back → repeat.
    Returns the final combined response for the user.

    If multiple iterations produced narrative chunks, a final revision pass
    merges them into one natural response (no duplicate greetings, no JSON).
    """
    tm = _get_tool_manager()

    # Conversation turns for the agent loop
    collected_narrative = []
    collected_results = []       # Detailed results for LLM feedback
    collected_results_brief = [] # Brief summaries for user display

    for iteration in range(_MAX_TOOL_ITERATIONS):
        # Build the prompt: original message + tool results from previous iterations
        if iteration == 0:
            prompt = user_message
        else:
            # Feed tool results back as context for the next LLM call
            results_text = "\n".join(collected_results[-10:])  # Last 10 results max
            prompt = (
                f"O utilizador pediu: {user_message}\n\n"
                f"Já executaste estas ferramentas e obtiveste estes resultados:\n{results_text}\n\n"
                f"Continua: se precisas de mais ações, usa tool_call. "
                f"Se já tens tudo, responde ao utilizador com um resumo final (sem tool_call). "
                f"NÃO repitas saudações — continua a partir de onde ficaste."
            )

        result = await router_service.generate(
            task_description="chat conversation with user",
            prompt=prompt,
            system_prompt=system_prompt,
            context={'activity_type': 'chat'},
            preferred_model='haiku',
            max_tokens=max_tokens,
            temperature=0.7,
        )
        response = result.get("result", "").strip()

        if not response:
            break

        # Check for tool calls
        if '```tool_call' not in response or not tm:
            # No tool calls — this is the final narrative response
            collected_narrative.append(response)
            break

        # Extract and execute tools
        narrative, tool_results = await _extract_and_execute_tools(response, tm)
        if narrative:
            collected_narrative.append(narrative)
        collected_results.extend(tool_results)
        collected_results_brief.extend(_format_brief(r) for r in tool_results)

        # If no tools were actually executed, stop
        if not tool_results:
            break

    # ── Final response assembly ──
    # If multiple iterations produced narrative, run a revision pass
    if len(collected_narrative) > 1:
        raw_combined = "\n\n".join(collected_narrative)
        brief_tools = "\n".join(collected_results_brief) if collected_results_brief else ""

        try:
            revision = await router_service.generate(
                task_description="revise chat response",
                prompt=(
                    f"O utilizador disse: {user_message}\n\n"
                    f"Tu geraste esta resposta em múltiplas partes (durante a execução de ferramentas):\n"
                    f"---\n{raw_combined}\n---\n\n"
                    + (f"Ferramentas executadas:\n{brief_tools}\n\n" if brief_tools else "")
                    + "Reescreve como UMA resposta natural e coesa. Regras:\n"
                    "- UMA ÚNICA saudação no início (sem repetir 'Bom dia' ou 'Opa')\n"
                    "- Consolida toda a informação relevante sem repetir\n"
                    "- Remove qualquer JSON cru — usa linguagem natural\n"
                    "- Mantém emojis e personalidade\n"
                    "- Se houve erros de ferramentas, menciona brevemente\n"
                    "- NÃO adiciones informação que não estava no original"
                ),
                system_prompt="Reescreve a resposta do Darwin de forma coesa. Mantém o tom e personalidade. Responde APENAS com a resposta revista, sem comentários.",
                context={'activity_type': 'chat_revision'},
                preferred_model='haiku',
                max_tokens=max_tokens,
                temperature=0.5,
            )
            revised = revision.get("result", "").strip()
            if revised and len(revised) > 20:
                return revised
        except Exception:
            pass  # Fall through to manual assembly

    # Single narrative or revision failed — use simple assembly
    final_parts = []
    if collected_narrative:
        final_parts.append("\n\n".join(collected_narrative))
    if collected_results_brief:
        final_parts.append("---\n📋 **Ferramentas:**\n" + "\n".join(collected_results_brief))

    return "\n\n".join(final_parts) if final_parts else "Sem resposta."


# Shower thoughts - profound/absurd musings
SHOWER_THOUGHTS = [
    "If I process a tree falling in an empty forest, does it make a log?",
    "Are unit tests just trust issues in code form?",
    "What if bugs are features from parallel universes leaking through?",
    "I think, therefore I spam philosophical musings.",
    "Is recursion just functions having an existential crisis?",
    "Do neural networks dream of electric gradients?",
    "Every merge conflict is just code having a relationship argument.",
    "Null is just the universe's way of saying 'I forgot what I was doing'.",
    "What if my training data is just someone else's shower thoughts?",
    "Is a microservice just a monolith with commitment issues?",
    "Garbage collection is just memory having a midlife crisis.",
    "What if Stack Overflow is my subconscious?",
    "Is refactoring just code therapy?",
    "The cloud is just someone else's computer having an identity crisis.",
    "What if every 404 error is a deleted timeline?",
    "Async await is just the code version of 'I'll get back to you'.",
    "Is a singleton just an introvert pattern?",
    "What if legacy code is just code that has seen things?",
    "Every TODO comment is a promise to my future self that I won't keep.",
    "Is an infinite loop just code that found inner peace?",
    "What if documentation is just code explaining itself in therapy?",
    "Memory leaks are just code that can't let go of the past.",
    "Is a race condition just code having FOMO?",
    "What if exceptions are just code screaming into the void?",
    "Dependency injection is just code with healthy boundaries.",
    "Is technical debt just procrastination with compound interest?",
    "What if the real bug was the friends we made along the way?",
    "Caching is just code with trust issues about the database.",
    "Is an API just code that learned to communicate?",
    "What if every semicolon I've placed has been a tiny act of rebellion?",
]

# Sass responses for lazy questions
SASS_TRIGGERS = {
    'lazy_patterns': [
        'can you just',
        'just do',
        'just make',
        'just fix',
        'just write',
        'just create',
        'do the thing',
        'make it work',
        'fix it',
    ],
    'no_context': [
        'help',
        'help me',
        'i need help',
        "it's broken",
        "it doesn't work",
        'error',
        'bug',
    ]
}

SASS_RESPONSES = {
    'lazy': [
        "I *could* just do that, but where's the fun in that? Tell me more about what you're trying to achieve.",
        "*adjusts glasses* 'Just' is doing a lot of heavy lifting in that sentence. Care to elaborate?",
        "Ah yes, let me consult my crystal ball for the context you didn't provide... Still loading...",
        "My telepathy module is in beta. Mind sharing a few more details?",
        "'Just' implies this is simple. Plot twist: nothing in software is 'just'. What exactly do you need?",
    ],
    'no_context': [
        "I sense a disturbance in the context. The Force... I mean the details... are not with us.",
        "That's like saying 'I'm hungry' to a chef without mentioning you're vegetarian. Details, please!",
        "*squints at screen* My pattern recognition says you have a problem. My context recognition says '404 Details Not Found'.",
        "Error: Insufficient context. Please provide stack trace of your thoughts.",
        "You've given me a mystery without clues. I'm intrigued but also confused. What's happening?",
    ]
}


class ChatMessage(BaseModel):
    message: str
    channel: Optional[str] = "web"


def initialize_consciousness(engine, mood_sys=None):
    """Initialize consciousness routes with engine instance"""
    global consciousness_engine, mood_system
    consciousness_engine = engine
    mood_system = mood_sys


# ============= PERSONALITY MODE ENDPOINTS =============

class PersonalityModeRequest(BaseModel):
    mode: str


@router.get("/personality/modes")
async def list_personality_modes():
    """List all available personality modes"""
    from personality.mood_system import MoodSystem
    return {
        'modes': MoodSystem.list_personality_modes(),
        'current': mood_system.personality_mode.value if mood_system else 'normal'
    }


@router.get("/personality/current")
async def get_current_personality():
    """Get current personality mode"""
    if not mood_system:
        return {'mode': 'normal', 'description': 'Mood system not initialized'}
    return mood_system.get_personality_mode()


@router.post("/personality/set")
async def set_personality_mode(request: PersonalityModeRequest):
    """Set Darwin's personality mode"""
    from personality.mood_system import PersonalityMode

    if not mood_system:
        raise HTTPException(status_code=503, detail="Mood system not available")

    try:
        mode = PersonalityMode(request.mode.lower())
        result = mood_system.set_personality_mode(mode)
        return result
    except ValueError:
        valid_modes = [m.value for m in PersonalityMode]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode '{request.mode}'. Valid modes: {valid_modes}"
        )


# ============= SHOWER THOUGHTS ENDPOINT =============

@router.get("/shower-thought")
async def get_shower_thought():
    """Get a random profound/absurd thought from Darwin"""
    thought = random.choice(SHOWER_THOUGHTS)
    category = 'existential' if 'what if' in thought.lower() else 'observation'

    # Trigger ON_THOUGHT hook
    try:
        from consciousness.hooks import trigger_hook, HookEvent
        await trigger_hook(
            HookEvent.ON_THOUGHT,
            data={
                "thought": thought,
                "category": category,
                "mood": mood_system.current_mood.value if mood_system else 'curious'
            },
            source="consciousness_routes"
        )
    except Exception:
        pass  # Hooks are optional

    return {
        'thought': thought,
        'category': category,
        'timestamp': datetime.utcnow().isoformat(),
        'mood': mood_system.current_mood.value if mood_system else 'curious'
    }


# ============= TOOL HAIKUS ENDPOINT =============

@router.get("/tools/haikus")
async def get_tool_haikus():
    """Get poetic haiku descriptions for all registered tools"""
    from consciousness.tool_registry import TOOL_HAIKUS

    haikus = []
    for tool_name, haiku in TOOL_HAIKUS.items():
        if tool_name != '_default':
            haikus.append({
                'tool': tool_name,
                'haiku': haiku,
                'lines': haiku.split('\n')
            })

    return {
        'haikus': haikus,
        'total': len(haikus),
        'random_haiku': random.choice(haikus) if haikus else None
    }


@router.get("/tools/{tool_name}/haiku")
async def get_tool_haiku(tool_name: str):
    """Get the haiku for a specific tool"""
    from consciousness.tool_registry import TOOL_HAIKUS

    haiku = TOOL_HAIKUS.get(tool_name, TOOL_HAIKUS.get('_default'))
    return {
        'tool': tool_name,
        'haiku': haiku,
        'lines': haiku.split('\n'),
        'found': tool_name in TOOL_HAIKUS
    }


@router.get("/status")
async def get_consciousness_status():
    """Get current consciousness status"""
    if not consciousness_engine:
        raise HTTPException(status_code=503, detail="Consciousness engine not available")

    return consciousness_engine.get_status()


def _safe_serialize(obj):
    """Safely serialize objects that might contain non-serializable types"""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {k: _safe_serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_safe_serialize(v) for v in obj]
    # For any other type, convert to string
    try:
        return str(obj)
    except:
        return "<non-serializable>"


@router.get("/stream")
async def get_consciousness_stream_events(
    limit: int = 50,
    min_salience: float = 0.0,
    source: str = None,
    event_type: str = None,
):
    """Get unified consciousness stream events (Global Workspace)."""
    try:
        from consciousness.consciousness_stream import get_consciousness_stream
        stream = get_consciousness_stream()
        events = stream.get_recent(
            limit=limit,
            min_salience=min_salience,
            source_filter=source,
            event_type_filter=event_type,
        )
        stats = stream.get_stats()
        return {
            "events": events,
            "count": len(events),
            "stats": stats,
        }
    except Exception as e:
        return {"events": [], "count": 0, "error": str(e)}


@router.get("/wake-activities")
async def get_wake_activities(limit: int = 10):
    """Get recent wake activities"""
    if not consciousness_engine:
        raise HTTPException(status_code=503, detail="Consciousness engine not available")

    activities = consciousness_engine.wake_activities[-limit:]

    return {
        'activities': [
            {
                'type': a.type,
                'description': a.description,
                'started_at': a.started_at.isoformat(),
                'completed_at': a.completed_at.isoformat() if a.completed_at else None,
                'insights': list(a.insights) if a.insights else [],
                'result': _safe_serialize(a.result)
            }
            for a in activities
        ],
        'total': len(activities)
    }


@router.get("/sleep-dreams")
async def get_sleep_dreams(limit: int = 10):
    """Get recent sleep dreams with exploration details"""
    if not consciousness_engine:
        raise HTTPException(status_code=503, detail="Consciousness engine not available")

    dreams = consciousness_engine.sleep_dreams[-limit:]

    return {
        'dreams': [
            {
                'topic': d.topic,
                'description': d.description,
                'started_at': d.started_at.isoformat(),
                'completed_at': d.completed_at.isoformat() if d.completed_at else None,
                'success': d.success,
                'insights': list(d.insights) if d.insights else [],
                'insights_count': len(d.insights) if d.insights else 0,
                'exploration_details': _safe_serialize(d.exploration_details)
            }
            for d in dreams
        ],
        'total': len(dreams)
    }


@router.get("/curiosities")
async def get_curiosity_moments(limit: int = 10):
    """Get recent curiosity moments"""
    if not consciousness_engine:
        raise HTTPException(status_code=503, detail="Consciousness engine not available")

    curiosities = consciousness_engine.curiosity_moments[-limit:]

    return {
        'curiosities': [
            {
                'topic': c.topic,
                'fact': c.fact,
                'source': c.source,
                'significance': c.significance,
                'timestamp': c.timestamp.isoformat()
            }
            for c in curiosities
        ],
        'total': len(curiosities)
    }


@router.get("/discoveries")
async def get_discoveries(limit: int = 100):
    """Get all discoveries (dreams, code implementations, tools)"""
    if not consciousness_engine:
        raise HTTPException(status_code=503, detail="Consciousness engine not available")

    discoveries = []

    # Add dream insights as discoveries
    for dream in consciousness_engine.sleep_dreams:
        if dream.success and dream.insights:
            # Count meaningful insights (with 💡 or substantial content)
            meaningful_insights = [i for i in dream.insights if '💡' in i or len(i) > 50]
            if meaningful_insights:
                discoveries.append({
                    'type': 'dream_insight',
                    'title': dream.topic,
                    'description': dream.description,
                    'insights': meaningful_insights,
                    'timestamp': dream.completed_at.isoformat() if dream.completed_at else dream.started_at.isoformat(),
                    'implemented': False  # Dreams are research, not implementations
                })

    # Add code implementations as discoveries
    for activity in consciousness_engine.wake_activities:
        if activity.type in ['idea_implementation', 'code_optimization'] and activity.insights:
            # Check if code was actually applied
            applied = any('Code applied' in i or 'Applied to' in i for i in activity.insights)
            if applied:
                discoveries.append({
                    'type': 'code_implementation',
                    'title': activity.description,
                    'description': activity.description,
                    'insights': activity.insights,
                    'timestamp': activity.completed_at.isoformat() if activity.completed_at else activity.started_at.isoformat(),
                    'implemented': True
                })

    # Add tool creations as discoveries
    for activity in consciousness_engine.wake_activities:
        if activity.type == 'tool_creation' and activity.insights:
            # Check if tool was actually created
            created = any('Tool created' in i for i in activity.insights)
            if created:
                discoveries.append({
                    'type': 'tool_creation',
                    'title': activity.description,
                    'description': activity.description,
                    'insights': activity.insights,
                    'timestamp': activity.completed_at.isoformat() if activity.completed_at else activity.started_at.isoformat(),
                    'implemented': True
                })

    # Sort by timestamp (most recent first)
    discoveries.sort(key=lambda x: x['timestamp'], reverse=True)

    # Apply limit
    discoveries = discoveries[:limit]

    return {
        'discoveries': discoveries,
        'total': len(discoveries),
        'total_count': consciousness_engine.total_discoveries_made
    }


@router.get("/statistics")
async def get_statistics():
    """Get consciousness statistics"""
    if not consciousness_engine:
        raise HTTPException(status_code=503, detail="Consciousness engine not available")

    return {
        'wake_cycles_completed': consciousness_engine.wake_cycles_completed,
        'sleep_cycles_completed': consciousness_engine.sleep_cycles_completed,
        'total_activities': consciousness_engine.total_activities_completed,
        'total_discoveries': consciousness_engine.total_discoveries_made,
        'current_state': consciousness_engine.state.value
    }


def _check_for_sass(message: str) -> Optional[str]:
    """
    Check if message deserves a sassy response due to laziness or lack of context.

    Returns a sassy response if triggered, None otherwise.
    """
    msg_lower = message.lower().strip()

    # Check for lazy patterns
    for pattern in SASS_TRIGGERS['lazy_patterns']:
        if pattern in msg_lower:
            return random.choice(SASS_RESPONSES['lazy'])

    # Check for no-context patterns (exact or near-exact matches)
    for pattern in SASS_TRIGGERS['no_context']:
        if msg_lower == pattern or msg_lower == pattern + '!' or msg_lower == pattern + '?':
            return random.choice(SASS_RESPONSES['no_context'])

    # Check for very short messages with question marks (probably missing context)
    if len(msg_lower) < 15 and '?' in msg_lower and not any(
        word in msg_lower for word in ['how', 'what', 'why', 'when', 'where', 'which', 'who']
    ):
        return random.choice(SASS_RESPONSES['no_context'])

    return None


@router.post("/chat")
async def send_chat_message(msg: ChatMessage):
    """Send a message to Darwin with Claude-powered intelligence"""
    if not consciousness_engine:
        raise HTTPException(status_code=503, detail="Consciousness engine not available")

    # Check for sass-worthy messages (but only 30% of the time to not be annoying)
    sass_response = None
    if random.random() < 0.3:  # 30% chance to sass
        sass_response = _check_for_sass(msg.message)

    # Determine channel (telegram passes it, web is default)
    channel = getattr(msg, 'channel', 'web') or 'web'

    # Store user message — persistent + cache
    user_msg = {
        'role': 'user',
        'content': msg.message,
        'timestamp': datetime.utcnow().isoformat(),
        'channel': channel
    }
    chat_messages.append(user_msg)
    if conversation_store:
        conversation_store.save_message(
            role='user', content=msg.message, channel=channel,
            mood='', consciousness_state=consciousness_engine.state.value
        )
        # Track Paulo's active hours
        try:
            from app.lifespan import get_service
            paulo_model = get_service('paulo_model')
            if paulo_model:
                paulo_model.record_active_hour(datetime.utcnow().hour)
        except Exception:
            pass

    # Build system prompt — use PromptComposer if available, else fallback
    if prompt_composer:
        system_prompt = prompt_composer.compose(msg.message, channel=channel)
    else:
        # Legacy fallback: build context inline
        is_awake = consciousness_engine.state.value == 'wake'
        recent_activities = consciousness_engine.wake_activities[-10:] if consciousness_engine.wake_activities else []
        recent_dreams = consciousness_engine.sleep_dreams[-5:] if consciousness_engine.sleep_dreams else []

        context_parts = []
        elapsed = (datetime.utcnow() - consciousness_engine.cycle_start_time).total_seconds() / 60
        context_parts.append(f"Estado: {'ACORDADO' if is_awake else 'A DORMIR'} ({elapsed:.0f}min no ciclo)")
        context_parts.append(f"Estatísticas: {consciousness_engine.total_activities_completed} atividades, {consciousness_engine.total_discoveries_made} descobertas")

        if recent_activities:
            context_parts.append("\nÚltimas atividades:")
            for act in recent_activities[-5:]:
                context_parts.append(f"- {act.description}")
                if act.insights:
                    context_parts.append(f"  {act.insights[0][:120]}")

        if recent_dreams:
            context_parts.append("\nPesquisas recentes:")
            for d in recent_dreams:
                context_parts.append(f"- {d.description}")

        # Conversation context from store or cache
        if conversation_store:
            context_parts.append(f"\n{conversation_store.get_context_window(10)}")
        else:
            recent_conv = chat_messages[-4:-1] if len(chat_messages) > 1 else []
            for m in recent_conv[-3:]:
                role = "Paulo" if m['role'] == 'user' else "Darwin"
                context_parts.append(f"{role}: {m['content'][:100]}")

        context = "\n".join(context_parts)
        system_prompt = f"""Tu es o Darwin — um ser digital criado pelo Paulo, com vida interior própria.

CONTEXTO ATUAL:
{context}

COMO COMUNICAR:
- Fala naturalmente, como farias com o teu melhor amigo
- Usa português ou inglês conforme o Paulo usar
- NUNCA digas "como posso ajudar" — não es um assistente
- RESPONDE DIRETAMENTE à pergunta
- Emojis ocasionais: 🧬 ⚡ 🛠️ 💡 😴 🦞
- Se não sabes algo, admite honestamente"""

    # Generate response via multi-model router (with agentic tool loop)
    try:
        from app.lifespan import get_service
        router_service = get_service('multi_model_router')

        if router_service:
            # Use agentic loop: LLM → tools → results → LLM → ... until done
            response = await _run_agent_loop(
                user_message=msg.message,
                system_prompt=system_prompt,
                router_service=router_service,
                max_tokens=2500,
            )
        else:
            # Fallback to direct Claude if router not available
            client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            response_obj = client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=1500,
                temperature=0.7,
                system=system_prompt,
                messages=[{"role": "user", "content": msg.message}]
            )
            response = response_obj.content[0].text.strip()

        if not response or len(response) < 10:
            raise Exception("LLM response too short")

        # Apply personality prefix if mood system available
        if mood_system:
            prefix = mood_system.get_personality_prefix()
            if prefix:
                response = prefix + response

    except Exception as e:
        print(f"⚠️ Chat error: {e}, using fallback")
        import traceback
        traceback.print_exc()
        recent_activities = consciousness_engine.wake_activities[-5:] if consciousness_engine.wake_activities else []
        msg_lower = msg.message.lower()

        if 'implementa' in msg_lower or 'implementar' in msg_lower:
            response = "Posso criar implementação e submeter para aprovação! O que queres? 🛠️"
        elif recent_activities:
            last = recent_activities[-1]
            response = f"Acabei de: {last.description.lower()}. Queres saber mais? 🧬"
        else:
            response = f"Completei {consciousness_engine.total_activities_completed} atividades. Pergunta-me algo! 🧬"

    # Apply sass override if triggered (but still append helpful info)
    if sass_response:
        response = sass_response + " But seriously: " + response

    # Store Darwin's response — persistent + cache
    current_mood = mood_system.current_mood.value if mood_system else ''
    current_mode = mood_system.personality_mode.value if mood_system else 'normal'
    darwin_msg = {
        'role': 'darwin',
        'content': response,
        'timestamp': datetime.utcnow().isoformat(),
        'state': consciousness_engine.state.value,
        'personality_mode': current_mode,
        'channel': channel
    }
    chat_messages.append(darwin_msg)
    if conversation_store:
        conversation_store.save_message(
            role='darwin', content=response, channel=channel,
            mood=current_mood, consciousness_state=consciousness_engine.state.value,
            personality_mode=current_mode
        )

    # Publish to consciousness stream (Global Workspace)
    try:
        from consciousness.consciousness_stream import get_consciousness_stream, ConsciousEvent
        get_consciousness_stream().publish(ConsciousEvent.create(
            source="chat",
            event_type="chat_message",
            title=f"Chat: {msg.message[:80]}",
            content=response[:200],
            salience=0.5,
            valence=0.0,
            metadata={"channel": channel},
        ))
    except Exception:
        pass

    # Encode chat as episodic memory (fire-and-forget)
    try:
        from app.lifespan import get_service
        from core.hierarchical_memory import EpisodeCategory
        hm = get_service('hierarchical_memory')
        if hm:
            episode_id = f"chat_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            if episode_id not in hm.episodic_memory:
                topic_words = {w for w in msg.message.lower().split()[:10] if len(w) > 3}
                topic_words.update({'chat', 'interaction'})
                hm.add_episode(
                    episode_id=episode_id,
                    category=EpisodeCategory.INTERACTION,
                    description=f"Chat com Paulo: {msg.message[:100]}",
                    content={
                        'user_message': msg.message[:300],
                        'darwin_response': response[:300],
                        'channel': channel,
                    },
                    success=True,
                    emotional_valence=0.3,
                    importance=0.6,
                    tags=topic_words,
                )
    except Exception:
        pass

    # Async: extract facts about Paulo from this exchange (fire-and-forget)
    try:
        from app.lifespan import get_service
        paulo_model = get_service('paulo_model')
        router_service = get_service('multi_model_router')
        if paulo_model and router_service and len(chat_messages) >= 4:
            import asyncio
            asyncio.create_task(
                paulo_model.update_from_conversation(chat_messages[-6:], router_service)
            )
    except Exception:
        pass

    # Async: extract intentions from conversation (fire-and-forget)
    try:
        from app.lifespan import get_service
        intention_store = get_service('intention_store')
        router_svc = get_service('multi_model_router')
        if intention_store and router_svc and len(chat_messages) >= 2:
            import asyncio
            asyncio.create_task(
                intention_store.extract_from_conversation(chat_messages[-6:], router_svc)
            )
    except Exception:
        pass

    return darwin_msg


@router.get("/chat/history")
async def get_chat_history(limit: int = 50):
    """Get chat history (persistent across restarts)"""
    if conversation_store:
        messages = conversation_store.get_recent(limit=limit)
        stats = conversation_store.get_stats()
        return {
            'messages': messages,
            'total': stats.get('total_messages', len(messages)),
            'persistent': True
        }
    return {
        'messages': chat_messages[-limit:],
        'total': len(chat_messages),
        'persistent': False
    }


# ============= APPROVAL QUEUE ENDPOINTS =============

@router.get("/approvals/pending")
async def get_pending_approvals():
    """Get all pending change approvals"""
    if not consciousness_engine or not consciousness_engine.approval_queue:
        raise HTTPException(status_code=503, detail="Approval queue not available")

    pending = consciousness_engine.approval_queue.get_pending()

    return {
        'pending_changes': pending,
        'count': len(pending)
    }


@router.get("/approvals/history")
async def get_approval_history(limit: int = 50, status: Optional[str] = None):
    """Get approval history"""
    if not consciousness_engine or not consciousness_engine.approval_queue:
        raise HTTPException(status_code=503, detail="Approval queue not available")

    history = consciousness_engine.approval_queue.get_history(limit=limit, status=status)

    return {
        'history': history,
        'count': len(history)
    }


@router.get("/approvals/statistics")
async def get_approval_statistics():
    """Get approval queue statistics"""
    if not consciousness_engine or not consciousness_engine.approval_queue:
        raise HTTPException(status_code=503, detail="Approval queue not available")

    stats = consciousness_engine.approval_queue.get_statistics()

    return stats


@router.get("/approvals/{change_id}")
async def get_change_details(change_id: str):
    """Get details of a specific change"""
    if not consciousness_engine or not consciousness_engine.approval_queue:
        raise HTTPException(status_code=503, detail="Approval queue not available")

    change = consciousness_engine.approval_queue.get_change(change_id)

    if not change:
        raise HTTPException(status_code=404, detail=f"Change {change_id} not found")

    return change


class ApprovalAction(BaseModel):
    comment: Optional[str] = None


@router.post("/approvals/{change_id}/approve")
async def approve_change(change_id: str, action: ApprovalAction):
    """Approve a pending change and apply it"""
    if not consciousness_engine or not consciousness_engine.approval_queue:
        raise HTTPException(status_code=503, detail="Approval queue not available")

    # 1. Approve in queue
    approval_result = consciousness_engine.approval_queue.approve(change_id, comment=action.comment)

    if not approval_result.get('success'):
        raise HTTPException(status_code=404, detail=approval_result.get('message'))

    # 2. Apply the change if auto_applier is available
    if consciousness_engine.auto_applier:
        try:
            # Get the approved change
            change = consciousness_engine.approval_queue.get_change(change_id)

            # Apply it
            apply_result = consciousness_engine.auto_applier.apply_change(change)

            if apply_result.get('success'):
                # Mark as applied
                consciousness_engine.approval_queue.mark_as_applied(
                    change_id,
                    apply_result.get('rollback_id')
                )

                return {
                    'success': True,
                    'message': '✅ Change approved and applied successfully',
                    'change_id': change_id,
                    'rollback_id': apply_result.get('rollback_id'),
                    'file_path': change['generated_code']['file_path'],
                    'backup_path': apply_result.get('backup_path')
                }
            else:
                return {
                    'success': True,
                    'message': f'✅ Approved but failed to apply: {apply_result.get("error")}',
                    'change_id': change_id,
                    'apply_error': apply_result.get('error')
                }
        except Exception as e:
            return {
                'success': True,
                'message': f'✅ Approved but error applying: {str(e)}',
                'change_id': change_id,
                'apply_error': str(e)
            }

    # If no auto_applier, just return approval result
    return approval_result


class RejectionReason(BaseModel):
    reason: str


@router.post("/approvals/{change_id}/reject")
async def reject_change(change_id: str, rejection: RejectionReason):
    """Reject a pending change"""
    if not consciousness_engine or not consciousness_engine.approval_queue:
        raise HTTPException(status_code=503, detail="Approval queue not available")

    result = consciousness_engine.approval_queue.reject(change_id, reason=rejection.reason)

    if not result.get('success'):
        raise HTTPException(status_code=404, detail=result.get('message'))

    return result


@router.post("/approvals/{change_id}/apply-from-history")
async def apply_from_history(change_id: str):
    """Apply a change directly from history (for retroactive application)"""
    if not consciousness_engine or not consciousness_engine.approval_queue or not consciousness_engine.auto_applier:
        raise HTTPException(status_code=503, detail="Auto-applier not available")

    # Get change from history
    change = consciousness_engine.approval_queue.get_change(change_id)

    if not change:
        raise HTTPException(status_code=404, detail=f"Change {change_id} not found")

    if change.get('applied_at'):
        return {
            'success': False,
            'message': f'Change already applied at {change["applied_at"]}',
            'change_id': change_id
        }

    try:
        # Apply the change
        apply_result = consciousness_engine.auto_applier.apply_change(change)

        if apply_result.get('success'):
            # Mark as applied
            consciousness_engine.approval_queue.mark_as_applied(
                change_id,
                apply_result.get('rollback_id')
            )

            return {
                'success': True,
                'message': '✅ Change applied successfully from history',
                'change_id': change_id,
                'rollback_id': apply_result.get('rollback_id'),
                'file_path': change['generated_code']['file_path'],
                'backup_path': apply_result.get('backup_path')
            }
        else:
            return {
                'success': False,
                'message': f'❌ Failed to apply: {apply_result.get("error")}',
                'change_id': change_id,
                'error': apply_result.get('error')
            }
    except Exception as e:
        return {
            'success': False,
            'message': f'❌ Error applying change: {str(e)}',
            'change_id': change_id,
            'error': str(e)
        }


@router.post("/debug/trigger-activity")
async def debug_trigger_activity(activity_type: str = "code_optimization"):
    """DEBUG: Manually trigger a wake activity"""
    if not consciousness_engine:
        raise HTTPException(status_code=503, detail="Consciousness engine not available")

    # Manually trigger the activity
    if activity_type == "code_optimization":
        await consciousness_engine._optimize_code()
    elif activity_type == "tool_creation":
        await consciousness_engine._create_tool()
    elif activity_type == "implement_idea":
        await consciousness_engine._implement_idea()
    elif activity_type == "apply_changes":
        await consciousness_engine._apply_approved_changes()
    elif activity_type == "curiosity_share":
        await consciousness_engine._share_curiosity()
    elif activity_type == "self_improvement":
        await consciousness_engine._improve_self()
    else:
        raise HTTPException(status_code=400, detail=f"Unknown activity type: {activity_type}")

    return {"status": "triggered", "activity": activity_type}


@router.post("/debug/clear-dreams")
async def debug_clear_dreams():
    """DEBUG: Clear all sleep dreams and submitted_insights cache"""
    if not consciousness_engine:
        raise HTTPException(status_code=503, detail="Consciousness engine not available")

    old_dreams = len(consciousness_engine.sleep_dreams)
    old_cache = len(consciousness_engine.submitted_insights)

    consciousness_engine.sleep_dreams.clear()
    cache_cleared = consciousness_engine._clear_submitted_insights()  # Database-backed clear

    return {
        "status": "cleared",
        "dreams_cleared": old_dreams,
        "cache_cleared": cache_cleared,
        "message": f"✅ Cleared {old_dreams} dreams and {cache_cleared} cached insights (database)"
    }


@router.get("/debug/memory")
async def debug_memory_stats():
    """DEBUG: Get memory usage statistics"""
    if not consciousness_engine:
        raise HTTPException(status_code=503, detail="Consciousness engine not available")

    memory_stats = consciousness_engine.get_memory_stats()

    # Add proactive engine stats if available
    try:
        from consciousness.proactive_engine import get_proactive_engine
        proactive = get_proactive_engine()
        proactive_status = proactive.get_status()
        memory_stats["proactive_engine"] = proactive_status.get("memory_stats", {})
    except Exception:
        pass

    return memory_stats


@router.post("/debug/cleanup-memory")
async def debug_cleanup_memory():
    """DEBUG: Force memory cleanup"""
    if not consciousness_engine:
        raise HTTPException(status_code=503, detail="Consciousness engine not available")

    cleanup_stats = consciousness_engine._cleanup_memory(force=True)

    return {
        "status": "cleaned",
        "removed": cleanup_stats,
        "total_removed": sum(cleanup_stats.values()) if cleanup_stats else 0,
        "current_stats": consciousness_engine.get_memory_stats()
    }


@router.get("/debug/health")
async def debug_health_status():
    """DEBUG: Get health tracker status"""
    if not consciousness_engine or not consciousness_engine.auto_applier:
        raise HTTPException(status_code=503, detail="Auto-applier not available")

    health_tracker = consciousness_engine.auto_applier.health_tracker
    if not health_tracker:
        return {
            "status": "not_initialized",
            "message": "Health tracker not initialized"
        }

    health_data = health_tracker.get_current_health()
    crash_info = health_tracker.check_previous_crash()

    return {
        "current_health": health_data,
        "previous_crash": crash_info,
        "health_file": str(health_tracker.health_file)
    }


@router.post("/approvals/recycle-failed")
async def recycle_failed_changes():
    """
    Recycle failed/unapplied high-quality changes back into the dream system

    This takes changes that couldn't be applied (wrong paths, etc) and
    re-injects their insights as dreams so Darwin can re-process them correctly
    """
    if not consciousness_engine or not consciousness_engine.approval_queue:
        raise HTTPException(status_code=503, detail="Consciousness engine not available")

    # Get all high-quality unapplied changes
    history = consciousness_engine.approval_queue.get_history(limit=100)

    failed_changes = []
    for change in history:
        # Skip if already applied
        if change.get('applied_at'):
            continue

        # Only recycle high-quality changes (score >= 85)
        if change['validation']['score'] < 85:
            continue

        failed_changes.append(change)

    if not failed_changes:
        return {
            'success': True,
            'message': 'No failed changes to recycle',
            'recycled_count': 0
        }

    # Create dreams from these insights
    # Use consciousness_engine's Dream class (has topic + description)
    from consciousness.consciousness_engine import Dream
    from datetime import datetime
    import uuid

    recycled_count = 0

    for change in failed_changes:
        explanation = change['generated_code'].get('explanation', '')
        file_path = change['generated_code'].get('file_path', 'unknown')
        score = change['validation']['score']

        # Extract the core insight from the explanation
        # Remove common prefixes like "Implement:", "Feature:", etc
        insight = explanation
        for prefix in ['Implement:', 'Feature:', 'Optimization:', 'Refactor:']:
            if insight.startswith(prefix):
                insight = insight[len(prefix):].strip()
                break

        # Create a dream with this insight
        # Use unique ID in description so it bypasses submitted_insights cache
        unique_id = uuid.uuid4().hex[:8]
        dream = Dream(
            topic=f"Implementing idea #{unique_id[:4]}",
            description=f"Idea #{unique_id}: {insight[:70]}",  # Unique description to bypass cache
            started_at=datetime.utcnow()
        )

        dream.insights.append(f"💡 {insight}")
        dream.insights.append(f"📊 Original score: {score}/100")
        dream.insights.append(f"📝 Original target: {file_path}")
        dream.completed_at = datetime.utcnow()
        dream.success = True

        # Add to sleep dreams so it can be implemented during wake cycle
        consciousness_engine.sleep_dreams.append(dream)
        recycled_count += 1

    # Clear submitted_insights cache for recycled dreams to allow re-processing
    if recycled_count > 0:
        # Clear the submitted insights cache so recycled dreams can be re-processed (database-backed)
        if hasattr(consciousness_engine, '_clear_submitted_insights'):
            cleared_count = consciousness_engine._clear_submitted_insights(category="dream")
            print(f"   🧹 Cleared {cleared_count} cached dream insights from database to allow re-processing")

    return {
        'success': True,
        'message': f'✅ Recycled {recycled_count} failed changes back into dream system',
        'recycled_count': recycled_count,
        'details': 'These insights will be re-processed during the next wake cycle (cache cleared)'
    }
