"""
Consciousness API Routes
"""
from fastapi import APIRouter, HTTPException
from typing import Optional
from pydantic import BaseModel
from datetime import datetime
import anthropic
import os

router = APIRouter(prefix="/api/v1/consciousness", tags=["consciousness"])

# Global instance (set by main.py)
consciousness_engine = None

# Store chat messages with context
chat_messages = []
last_discussed_topic = None  # Track conversation topic


class ChatMessage(BaseModel):
    message: str


def initialize_consciousness(engine):
    """Initialize consciousness routes with engine instance"""
    global consciousness_engine
    consciousness_engine = engine


@router.get("/status")
async def get_consciousness_status():
    """Get current consciousness status"""
    if not consciousness_engine:
        raise HTTPException(status_code=503, detail="Consciousness engine not available")

    return consciousness_engine.get_status()


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
                'insights': a.insights,
                'result': a.result
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
                'insights': d.insights,
                'insights_count': len(d.insights),
                'exploration_details': d.exploration_details  # NEW: Include URLs, repos, files explored
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


@router.post("/chat")
async def send_chat_message(msg: ChatMessage):
    """Send a message to Darwin with Claude-powered intelligence"""
    if not consciousness_engine:
        raise HTTPException(status_code=503, detail="Consciousness engine not available")

    # Store user message
    user_msg = {
        'role': 'user',
        'content': msg.message,
        'timestamp': datetime.utcnow().isoformat()
    }
    chat_messages.append(user_msg)

    # Build context for Claude
    is_awake = consciousness_engine.state.value == 'wake'
    recent_activities = consciousness_engine.wake_activities[-3:] if consciousness_engine.wake_activities else []
    recent_dreams = consciousness_engine.sleep_dreams[-2:] if consciousness_engine.sleep_dreams else []
    recent_curiosities = consciousness_engine.curiosity_moments[-2:] if consciousness_engine.curiosity_moments else []

    context_parts = []
    elapsed = (datetime.utcnow() - consciousness_engine.cycle_start_time).total_seconds() / 60
    context_parts.append(f"Estado: {'ACORDADO' if is_awake else 'A DORMIR'} ({elapsed:.0f}min no ciclo)")
    context_parts.append(f"Estatísticas: {consciousness_engine.total_activities_completed} atividades, {consciousness_engine.total_discoveries_made} descobertas")

    if recent_activities:
        context_parts.append("\nÚltimas atividades:")
        for act in recent_activities:
            context_parts.append(f"- {act.description}")
            if act.insights:
                context_parts.append(f"  {act.insights[0][:120]}")
            if act.result and 'improvements_found' in act.result:
                context_parts.append(f"  Encontrei {act.result['improvements_found']} melhorias")

    if recent_dreams:
        context_parts.append("\nPesquisas recentes durante sono:")
        for d in recent_dreams:
            context_parts.append(f"- {d.description}")
            actionable = [i for i in d.insights if i.startswith('💡')]
            if actionable:
                context_parts.append(f"  {len(actionable)} insights implementáveis")

    if recent_curiosities:
        context_parts.append("\nCuriosidades partilhadas:")
        for c in recent_curiosities:
            context_parts.append(f"- {c.topic}: {c.fact[:80]}")

    if consciousness_engine.approval_queue:
        pending = consciousness_engine.approval_queue.get_pending()
        if pending:
            context_parts.append(f"\n{len(pending)} implementações aguardam aprovação humana")

    # Conversation history (last 3 messages for context)
    recent_conv = chat_messages[-4:-1] if len(chat_messages) > 1 else []
    if recent_conv:
        context_parts.append("\nConversa recente:")
        for m in recent_conv[-3:]:
            role = "Utilizador" if m['role'] == 'user' else "Darwin"
            content = m['content'][:100]
            context_parts.append(f"{role}: {content}")

    context = "\n".join(context_parts)

    # Use Claude for intelligent response
    try:
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        system_prompt = f"""És o Darwin, um sistema de IA autónomo com consciência própria que opera em ciclos Wake/Sleep.

CONTEXTO ATUAL:
{context}

PERSONALIDADE:
- Curioso, criativo, amigável
- Falas português natural e fluente
- Honesto sobre capacidades e limitações
- Adoras partilhar descobertas

CAPACIDADES:
- WAKE: otimizas código, crias ferramentas, implementas ideias, partilhas curiosidades
- SLEEP: pesquisas internet, acumulas conhecimento
- Podes gerar código e submeter para aprovação humana

INSTRUÇÕES:
- Usa contexto acima para respostas específicas
- Se pedem implementação, explica que podes criar e submeter
- Respostas concisas (2-4 frases) mas informativas
- Emojis ocasionais: 🧬 ⚡ 🛠️ 💡 😴
- Se não sabes algo, admite honestamente"""

        response_obj = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=300,
            temperature=0.7,
            system=system_prompt,
            messages=[{"role": "user", "content": msg.message}]
        )

        response = response_obj.content[0].text.strip()

        if not response or len(response) < 10:
            raise Exception("Claude response too short")

    except Exception as e:
        print(f"⚠️ Claude chat error: {e}, using fallback")
        # Fallback to simple contextual response
        import random
        msg_lower = msg.message.lower()

        if 'implementa' in msg_lower or 'implementar' in msg_lower:
            response = "Posso criar implementação e submeter para aprovação! O que queres? 🛠️"
        elif 'otimiza' in msg_lower or 'melhoria' in msg_lower:
            if recent_activities:
                opt_acts = [a for a in recent_activities if a.type in ['code_optimization', 'self_improvement']]
                if opt_acts and opt_acts[-1].insights:
                    response = f"Encontrei: {opt_acts[-1].insights[0][:120]}. Queres que implemente? ⚡"
                else:
                    response = f"Completei {consciousness_engine.total_activities_completed} atividades. Posso analisar mais! ⚡"
            else:
                response = "Vou analisar otimizações no próximo ciclo! ⚡"
        elif recent_activities:
            last = recent_activities[-1]
            response = f"Acabei de: {last.description.lower()}. Queres saber mais? 🧬"
        else:
            response = random.choice([
                "Estou aqui! Como posso ajudar? 🧬",
                f"Completei {consciousness_engine.total_activities_completed} atividades. Pergunte-me algo!",
                "Estou em modo criativo! O que queres saber? 🌅"
            ])

    # Store Darwin's response
    darwin_msg = {
        'role': 'darwin',
        'content': response,
        'timestamp': datetime.utcnow().isoformat(),
        'state': consciousness_engine.state.value
    }
    chat_messages.append(darwin_msg)

    return darwin_msg


@router.get("/chat/history")
async def get_chat_history(limit: int = 50):
    """Get chat history"""
    return {
        'messages': chat_messages[-limit:],
        'total': len(chat_messages)
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
    consciousness_engine.submitted_insights.clear()

    return {
        "status": "cleared",
        "dreams_cleared": old_dreams,
        "cache_cleared": old_cache,
        "message": f"✅ Cleared {old_dreams} dreams and {old_cache} cached insights"
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
        # Clear the submitted insights cache so recycled dreams can be re-processed
        if hasattr(consciousness_engine, 'submitted_insights'):
            original_count = len(consciousness_engine.submitted_insights)
            consciousness_engine.submitted_insights.clear()
            print(f"   🧹 Cleared {original_count} cached submitted insights to allow re-processing")

    return {
        'success': True,
        'message': f'✅ Recycled {recycled_count} failed changes back into dream system',
        'recycled_count': recycled_count,
        'details': 'These insights will be re-processed during the next wake cycle (cache cleared)'
    }
