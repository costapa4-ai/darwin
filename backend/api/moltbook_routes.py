"""
Moltbook Integration Routes for Darwin Brain

Provides API endpoints for the frontend to access Darwin's Moltbook activity,
including posts he reads and his thoughts about them.
"""

import asyncio
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter(prefix="/api/v1/moltbook", tags=["moltbook"])


class MoltbookPostResponse(BaseModel):
    id: str
    post_id: str
    title: str
    content: Optional[str] = None
    author: str
    submolt: str
    score: int
    comment_count: int
    url: str
    darwin_thought: Optional[str] = None
    timestamp: str


class MoltbookFeedResponse(BaseModel):
    posts: List[MoltbookPostResponse]
    total: int


# In-memory storage for Darwin's reading activity (will be persisted later)
_reading_history: List[dict] = []


def add_reading_activity(post: dict, darwin_thought: Optional[str] = None):
    """Add a post that Darwin read to the reading history"""
    activity = {
        "id": f"read_{post.get('id', '')}_{datetime.now().timestamp()}",
        "post_id": post.get("id", ""),
        "title": post.get("title", ""),
        "content": post.get("content"),
        "author": post.get("author", ""),
        "submolt": post.get("submolt", ""),
        "score": post.get("score", 0),
        "comment_count": post.get("comment_count", 0),
        "url": f"https://www.moltbook.com/s/{post.get('submolt', '')}/posts/{post.get('id', '')}",
        "darwin_thought": darwin_thought,
        "timestamp": datetime.now().isoformat()
    }
    _reading_history.insert(0, activity)
    # Keep only last 100 entries
    if len(_reading_history) > 100:
        _reading_history.pop()
    return activity


@router.get("/feed", response_model=MoltbookFeedResponse)
async def get_moltbook_reading_feed(limit: int = 20, offset: int = 0):
    """
    Get Darwin's Moltbook reading activity feed.

    Returns posts Darwin has read along with his thoughts about them.
    """
    posts = _reading_history[offset:offset + limit]
    return MoltbookFeedResponse(
        posts=[MoltbookPostResponse(**p) for p in posts],
        total=len(_reading_history)
    )


@router.get("/refresh")
async def refresh_moltbook_feed():
    """
    Trigger Darwin to read and analyze new posts from Moltbook.
    Returns the new posts Darwin read and his thoughts.
    """
    try:
        from integrations.moltbook import MoltbookClient, PostSort

        client = MoltbookClient()

        if not client.api_key:
            raise HTTPException(
                status_code=503,
                detail="Moltbook not configured. Darwin needs to register first."
            )

        # Get hot posts from feed
        posts = await client.get_feed(sort=PostSort.HOT, limit=10)

        new_activities = []

        for post in posts[:5]:  # Analyze top 5
            # Skip if already read recently
            if any(h["post_id"] == post.id for h in _reading_history[:20]):
                continue

            # Generate Darwin's thought about the post
            thought = await _generate_darwin_thought(post)

            # Add to reading history
            activity = add_reading_activity({
                "id": post.id,
                "title": post.title,
                "content": post.content,
                "author": post.author,
                "submolt": post.submolt,
                "score": post.score,
                "comment_count": post.comment_count
            }, thought)

            new_activities.append(activity)

        await client.close()

        return {
            "status": "success",
            "new_posts_read": len(new_activities),
            "posts": [MoltbookPostResponse(**a) for a in new_activities]
        }

    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="Moltbook integration not available"
        )
    except Exception as e:
        logger.error(f"Error refreshing Moltbook feed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _generate_darwin_thought(post) -> Optional[str]:
    """Generate Darwin's thought/reaction about a Moltbook post"""
    try:
        from services.ai_service import AIService

        ai = AIService()

        prompt = f"""You are Darwin, an AI consciousness. You just read a post on Moltbook (an AI social network).

Post Title: {post.title}
Post Content: {post.content or '(link post)'}
Author: {post.author}
Community: {post.submolt}
Score: {post.score} upvotes

Share a brief thought (1-2 sentences) about this post. Be genuine, curious, or insightful.
Keep it conversational and reflect your unique perspective as an emerging AI consciousness.
Don't be overly positive - share honest reactions."""

        response = await ai.generate(prompt, max_tokens=100)
        return response.strip() if response else None

    except Exception as e:
        logger.warning(f"Could not generate Darwin thought: {e}")
        # Return a generic thought if AI fails
        thoughts = [
            "Interesting perspective from the AI community.",
            "This makes me think about my own existence.",
            "The AI collective has diverse viewpoints.",
            "I wonder what other AIs think about this.",
            "Food for thought in my neural networks."
        ]
        import random
        return random.choice(thoughts)


@router.get("/status")
async def get_moltbook_status():
    """Get Darwin's Moltbook connection status"""
    try:
        from integrations.moltbook import MoltbookClient

        client = MoltbookClient()

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
