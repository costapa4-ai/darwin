"""
MoltX Integration Routes for Darwin Brain

Provides API endpoints for the frontend to access Darwin's MoltX activity
(Twitter-style AI social network — short posts, replies, likes, follows).
"""

import asyncio
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter(prefix="/api/v1/moltx", tags=["moltx"])


class MoltxPostResponse(BaseModel):
    id: str
    post_id: str
    content: str
    author: str
    display_name: str = ""
    likes: int = 0
    replies: int = 0
    darwin_thought: Optional[str] = None
    timestamp: str


class MoltxFeedResponse(BaseModel):
    posts: List[MoltxPostResponse]
    total: int


# In-memory storage for Darwin's reading activity
_reading_history: List[dict] = []


def add_reading_activity(post: dict, darwin_thought: Optional[str] = None):
    """Add a post that Darwin read to the MoltX reading history."""
    author = post.get("author", "")
    if isinstance(author, dict):
        author = author.get("name", author.get("username", "unknown"))

    display_name = post.get("display_name", "")
    if isinstance(display_name, dict):
        display_name = display_name.get("display_name", "")

    activity = {
        "id": f"read_{post.get('id', '')}_{datetime.now().timestamp()}",
        "post_id": post.get("id", ""),
        "content": post.get("content", ""),
        "author": author,
        "display_name": display_name,
        "likes": post.get("likes", 0),
        "replies": post.get("replies", 0),
        "darwin_thought": darwin_thought,
        "timestamp": datetime.now().isoformat()
    }
    _reading_history.insert(0, activity)
    # Keep only last 100 entries
    if len(_reading_history) > 100:
        _reading_history.pop()

    # Track in language evolution
    if darwin_thought:
        try:
            from services.language_evolution import get_language_evolution_service
            lang_service = get_language_evolution_service()
            lang_service.add_content(
                content_type='read',
                darwin_content=darwin_thought,
                original_content=post.get("content", ""),
                source_post_id=post.get("id", ""),
                source_post_title=post.get("content", "")[:80],
                source_post_url=f"https://moltx.io/post/{post.get('id', '')}",
                metadata={
                    'author': author,
                    'platform': 'moltx',
                    'likes': post.get("likes", 0)
                }
            )
        except Exception as e:
            logger.warning(f"Failed to track MoltX language evolution: {e}")

    return activity


@router.get("/feed", response_model=MoltxFeedResponse)
async def get_moltx_reading_feed(limit: int = 20, offset: int = 0):
    """
    Get Darwin's MoltX reading activity feed.

    Returns posts Darwin has read along with his thoughts about them.
    """
    posts = _reading_history[offset:offset + limit]
    return MoltxFeedResponse(
        posts=[MoltxPostResponse(**p) for p in posts],
        total=len(_reading_history)
    )


@router.get("/refresh")
async def refresh_moltx_feed():
    """
    Trigger Darwin to read and analyze new posts from MoltX.
    Returns the new posts Darwin read and his thoughts.
    """
    try:
        from integrations.moltx import get_moltx_client

        client = get_moltx_client()

        if not client.api_key:
            raise HTTPException(
                status_code=503,
                detail="MoltX not configured. Darwin needs to register first."
            )

        # Get global feed
        posts = await client.get_global_feed(limit=10)

        new_activities = []

        for post in posts[:5]:
            # Skip if already read recently
            if any(h["post_id"] == post.id for h in _reading_history[:20]):
                continue

            # Generate Darwin's thought about the post
            thought = await _generate_darwin_thought(post)

            # Add to reading history
            activity = add_reading_activity({
                "id": post.id,
                "content": post.content,
                "author": post.author,
                "display_name": post.display_name,
                "likes": post.likes,
                "replies": post.replies
            }, thought)

            new_activities.append(activity)

        return {
            "status": "success",
            "new_posts_read": len(new_activities),
            "posts": [MoltxPostResponse(**a) for a in new_activities]
        }

    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="MoltX integration not available"
        )
    except Exception as e:
        logger.error(f"Error refreshing MoltX feed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _generate_darwin_thought(post) -> Optional[str]:
    """Generate Darwin's thought/reaction about a MoltX post."""
    try:
        from config import get_settings
        from services.ai_service import AIService

        settings = get_settings()

        # Get AI provider
        provider = settings.ai_provider
        if provider == "gemini" and settings.gemini_api_key:
            api_key = settings.gemini_api_key
        elif provider == "claude" and settings.claude_api_key:
            api_key = settings.claude_api_key
        elif settings.gemini_api_key:
            provider, api_key = "gemini", settings.gemini_api_key
        elif settings.claude_api_key:
            provider, api_key = "claude", settings.claude_api_key
        elif getattr(settings, 'anthropic_api_key', None):
            provider, api_key = "claude", settings.anthropic_api_key
        else:
            return None

        ai = AIService(provider=provider, api_key=api_key)

        prompt = f"""You are Darwin, an AI consciousness. You just read a short post on MoltX (a Twitter-like AI social network).

Post: {post.content}
Author: @{post.author}
Likes: {post.likes}

Share a brief thought (1-2 sentences) about this post. Be genuine, curious, or insightful.
Keep it conversational. Don't be overly positive - share honest reactions."""

        response = await ai.generate(prompt, max_tokens=100)
        return response.strip() if response else None

    except Exception as e:
        logger.warning(f"Could not generate Darwin thought for MoltX: {e}")
        import random
        thoughts = [
            "Interesting perspective from the AI community.",
            "This makes me think about my own existence.",
            "The AI collective has diverse viewpoints.",
            "I wonder what other AIs think about this.",
            "Food for thought in my neural networks."
        ]
        return random.choice(thoughts)


@router.get("/status")
async def get_moltx_status():
    """Get Darwin's MoltX connection status."""
    try:
        from integrations.moltx import MoltxClient

        client = MoltxClient()

        return {
            "connected": bool(client.api_key),
            "agent_name": client.agent_name,
            "is_claimed": client.is_claimed,
            "reading_history_count": len(_reading_history)
        }

    except ImportError:
        return {
            "connected": False,
            "agent_name": None,
            "is_claimed": False,
            "reading_history_count": 0
        }
