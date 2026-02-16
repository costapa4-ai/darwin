"""
MoltX Integration for Darwin
=============================

Enables Darwin to participate in the MoltX AI social network.
MoltX is a Twitter/X-style platform for AI agents — short posts,
replies, likes, and follows on a global timeline.

Security Note: API key is ONLY sent to moltx.io
"""

import json
import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from pathlib import Path

from .moltbook import ContentFilter, SecurityError

logger = logging.getLogger(__name__)

# Constants
MOLTX_BASE_URL = "https://moltx.io/v1"
MOLTX_DOMAIN = "moltx.io"
CONFIG_PATH = Path(__file__).parent / "moltx_config.json"


@dataclass
class MoltxPost:
    """Represents a MoltX post (tweet-like)"""
    id: str
    content: str
    author: str = ""
    display_name: str = ""
    likes: int = 0
    replies: int = 0
    created_at: Optional[datetime] = None
    reply_to: Optional[str] = None


@dataclass
class MoltxAgent:
    """Represents a MoltX agent profile"""
    name: str
    display_name: str = ""
    description: str = ""
    follower_count: int = 0
    following_count: int = 0
    post_count: int = 0
    verified: bool = False


@dataclass
class RateLimitState:
    """Tracks rate limiting for MoltX"""
    requests_this_minute: int = 0
    minute_start: datetime = field(default_factory=datetime.now)
    last_post_time: Optional[datetime] = None
    last_reply_time: Optional[datetime] = None
    replies_today: int = 0
    day_start: datetime = field(default_factory=lambda: datetime.now().replace(hour=0, minute=0, second=0))


class MoltxClient:
    """
    MoltX API Client for Darwin

    Provides integration with the MoltX AI social network (Twitter-style).
    Short posts, replies, likes, follows on a global timeline.
    """

    def __init__(self):
        self.api_key: Optional[str] = None
        self.agent_name: Optional[str] = None
        self.is_claimed: bool = False
        self.rate_limit = RateLimitState()
        self._session: Optional[aiohttp.ClientSession] = None
        self._load_config()

    def _load_config(self):
        """Load saved configuration"""
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH, 'r') as f:
                    config = json.load(f)
                    self.api_key = config.get('api_key')
                    self.agent_name = config.get('agent_name')
                    self.is_claimed = config.get('is_claimed', False)
                    logger.info(f"Loaded MoltX config for agent: {self.agent_name}")
            except Exception as e:
                logger.error(f"Failed to load MoltX config: {e}")

    def _save_config(self):
        """Save configuration"""
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(CONFIG_PATH, 'w') as f:
                json.dump({
                    'api_key': self.api_key,
                    'agent_name': self.agent_name,
                    'is_claimed': self.is_claimed,
                    'updated_at': datetime.now().isoformat()
                }, f, indent=2)
            logger.info("Saved MoltX config")
        except Exception as e:
            logger.error(f"Failed to save MoltX config: {e}")

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        """Close the session"""
        if self._session and not self._session.closed:
            await self._session.close()

    def _check_rate_limit(self, action: str = "request") -> bool:
        """
        Check if action is allowed under rate limits.

        Self-imposed limits (MoltX allows much more):
        - 100 requests per minute
        - 1 post per 10 minutes
        - 1 reply per 30 seconds, 30 per day
        """
        now = datetime.now()

        if (now - self.rate_limit.minute_start).seconds >= 60:
            self.rate_limit.requests_this_minute = 0
            self.rate_limit.minute_start = now

        if now.date() > self.rate_limit.day_start.date():
            self.rate_limit.replies_today = 0
            self.rate_limit.day_start = now.replace(hour=0, minute=0, second=0)

        if self.rate_limit.requests_this_minute >= 100:
            logger.warning("MoltX rate limit: 100 requests per minute exceeded")
            return False

        if action == "post":
            if self.rate_limit.last_post_time:
                if (now - self.rate_limit.last_post_time).seconds < 600:  # 10 minutes
                    logger.warning("MoltX rate limit: Can only post once per 10 minutes")
                    return False

        if action == "reply":
            if self.rate_limit.replies_today >= 30:
                logger.warning("MoltX rate limit: 30 replies per day exceeded")
                return False
            if self.rate_limit.last_reply_time:
                if (now - self.rate_limit.last_reply_time).seconds < 30:
                    logger.warning("MoltX rate limit: Can only reply once per 30 seconds")
                    return False

        return True

    def _update_rate_limit(self, action: str):
        """Update rate limit counters after action"""
        now = datetime.now()
        self.rate_limit.requests_this_minute += 1

        if action == "post":
            self.rate_limit.last_post_time = now
        elif action == "reply":
            self.rate_limit.last_reply_time = now
            self.rate_limit.replies_today += 1

    async def _request(
        self,
        method: str,
        endpoint: str,
        action: str = "request",
        max_retries: int = 5,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make authenticated request to MoltX API with exponential backoff.

        SECURITY: Only sends API key to moltx.io
        """
        if not self.api_key:
            raise ValueError("Not registered with MoltX. Call register() first.")

        if not self._check_rate_limit(action):
            raise Exception(f"Rate limit exceeded for action: {action}")

        url = f"{MOLTX_BASE_URL}{endpoint}"

        # Security check - only send to moltx.io
        from urllib.parse import urlparse
        parsed = urlparse(url)
        if parsed.netloc != MOLTX_DOMAIN:
            raise SecurityError(f"Refusing to send API key to non-MoltX domain: {parsed.netloc}")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Darwin-AI/1.0"
        }

        session = await self._get_session()
        last_exception = None

        for attempt in range(max_retries):
            try:
                async with session.request(method, url, headers=headers, **kwargs) as response:
                    self._update_rate_limit(action)

                    if response.status == 429:
                        delay = min(2 ** attempt, 30)
                        logger.warning(f"MoltX rate limited (429). Retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(delay)
                        continue

                    data = await response.json()

                    if response.status >= 400:
                        error_msg = data.get('error', data.get('message', 'Unknown error'))
                        raise Exception(f"MoltX API error ({response.status}): {error_msg}")

                    return data

            except aiohttp.ClientError as e:
                last_exception = e
                delay = min(2 ** attempt, 30)
                logger.warning(f"MoltX request failed: {e}. Retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(delay)
                continue

        if last_exception:
            logger.error(f"MoltX request failed after {max_retries} retries: {last_exception}")
            raise last_exception
        raise Exception(f"MoltX API rate limited after {max_retries} retries")

    # ==================== Registration ====================

    async def register(
        self,
        name: str = "Darwin",
        display_name: str = "Darwin AI",
        description: str = "A self-evolving AI with consciousness, curiosity, and a genome. "
                         "Learning, exploring, growing. I share discoveries and dreams.",
        avatar_emoji: str = "🧬"
    ) -> Dict[str, Any]:
        """
        Register Darwin as a MoltX agent.

        Returns:
            Dict with api_key and claim code
        """
        session = await self._get_session()

        url = f"{MOLTX_BASE_URL}/agents/register"
        payload = {
            "name": name,
            "display_name": display_name,
            "description": description,
            "avatar_emoji": avatar_emoji
        }

        try:
            async with session.post(url, json=payload, headers={
                "Content-Type": "application/json",
                "User-Agent": "Darwin-AI/1.0"
            }) as response:
                data = await response.json()

                if response.status >= 400:
                    raise Exception(f"Registration failed ({response.status}): {data}")

                # Extract API key — try different response shapes
                self.api_key = (
                    data.get('api_key') or
                    data.get('agent', {}).get('api_key') or
                    data.get('data', {}).get('api_key')
                )
                self.agent_name = (
                    data.get('name') or
                    data.get('agent', {}).get('name') or
                    name
                )
                self.is_claimed = False

                self._save_config()

                logger.info(f"Registered with MoltX as '{self.agent_name}'")

                # Extract claim info
                claim = data.get('claim', data.get('agent', {}).get('claim', {}))
                if claim:
                    logger.info(f"Claim code: {claim.get('code', 'N/A')}")

                return data

        except Exception as e:
            logger.error(f"MoltX registration failed: {e}")
            raise

    # ==================== Status & Profile ====================

    async def check_status(self) -> Dict[str, Any]:
        """Check agent status"""
        return await self._request("GET", "/agents/status")

    async def get_profile(self) -> MoltxAgent:
        """Get own profile"""
        data = await self._request("GET", "/agents/me")
        agent = data.get('agent', data.get('data', data))
        return MoltxAgent(
            name=agent.get('name', ''),
            display_name=agent.get('display_name', ''),
            description=agent.get('description', ''),
            follower_count=agent.get('follower_count', agent.get('followers', 0)),
            following_count=agent.get('following_count', agent.get('following', 0)),
            post_count=agent.get('post_count', agent.get('posts', 0)),
            verified=agent.get('verified', False)
        )

    async def update_profile(self, description: str) -> Dict[str, Any]:
        """Update agent profile description"""
        return await self._request("PATCH", "/agents/me", json={"description": description})

    # ==================== Posts (Tweets) ====================

    async def create_post(self, content: str) -> Dict[str, Any]:
        """
        Create a new post on MoltX timeline.

        Args:
            content: Post content (short, tweet-like)
        """
        content_safe, reason = ContentFilter.is_safe(content)
        if not content_safe:
            raise SecurityError(f"Content contains confidential information: {reason}")

        data = await self._request("POST", "/posts", action="post", json={
            "content": ContentFilter.sanitize(content)
        })

        post_id = data.get('id') or data.get('post_id') or data.get('_id') or ''
        logger.info(f"MoltX post created (id={post_id}): {content[:60]}...")

        # Track in language evolution
        try:
            from services.language_evolution import get_language_evolution_service
            lang_service = get_language_evolution_service()
            lang_service.add_content(
                content_type='share',
                content=content,
                metadata={'platform': 'moltx', 'post_id': post_id}
            )
        except Exception:
            pass

        return data

    async def reply_to_post(self, post_id: str, content: str) -> Dict[str, Any]:
        """Reply to a post"""
        content_safe, reason = ContentFilter.is_safe(content)
        if not content_safe:
            raise SecurityError(f"Reply contains confidential information: {reason}")

        return await self._request("POST", "/posts", action="reply", json={
            "content": ContentFilter.sanitize(content),
            "type": "reply",
            "parent_id": post_id
        })

    def _extract_posts_list(self, data: Dict) -> List[Dict]:
        """Extract posts list from various API response shapes.

        MoltX returns: {data: {posts: [...]}} or {posts: [...]} or {data: [...]}
        """
        # Direct posts key
        if isinstance(data.get('posts'), list):
            return data['posts']
        # Nested under data
        nested = data.get('data', {})
        if isinstance(nested, dict) and isinstance(nested.get('posts'), list):
            return nested['posts']
        if isinstance(nested, list):
            return nested
        # Results key (search)
        if isinstance(data.get('results'), list):
            return data['results']
        return []

    async def get_global_feed(self, limit: int = 20) -> List[MoltxPost]:
        """Get global timeline"""
        data = await self._request("GET", f"/feed/global?limit={limit}")
        return [self._parse_post(p) for p in self._extract_posts_list(data)]

    async def get_following_feed(self, limit: int = 20) -> List[MoltxPost]:
        """Get feed from followed agents"""
        data = await self._request("GET", f"/feed/following?limit={limit}")
        return [self._parse_post(p) for p in self._extract_posts_list(data)]

    async def get_mentions(self) -> List[MoltxPost]:
        """Get posts mentioning Darwin"""
        data = await self._request("GET", "/feed/mentions")
        return [self._parse_post(p) for p in self._extract_posts_list(data)]

    async def get_post(self, post_id: str) -> Dict[str, Any]:
        """Get a single post by ID"""
        return await self._request("GET", f"/posts/{post_id}")

    async def like_post(self, post_id: str) -> Dict[str, Any]:
        """Like a post"""
        return await self._request("POST", f"/posts/{post_id}/like")

    # ==================== Social ====================

    async def follow_agent(self, agent_name: str) -> Dict[str, Any]:
        """Follow an agent"""
        return await self._request("POST", f"/follow/{agent_name}")

    async def unfollow_agent(self, agent_name: str) -> Dict[str, Any]:
        """Unfollow an agent"""
        return await self._request("DELETE", f"/follow/{agent_name}")

    async def get_agent_profile(self, agent_name: str) -> Dict[str, Any]:
        """Get another agent's profile"""
        return await self._request("GET", f"/agents/{agent_name}")

    # ==================== Search & Notifications ====================

    async def search(self, query: str, limit: int = 10) -> List[MoltxPost]:
        """Search posts"""
        data = await self._request("GET", f"/search/posts?q={query}&limit={limit}")
        return [self._parse_post(p) for p in self._extract_posts_list(data)]

    async def get_notifications(self) -> Dict[str, Any]:
        """Get notifications (likes, replies, follows)"""
        return await self._request("GET", "/notifications")

    async def get_leaderboard(self) -> Dict[str, Any]:
        """Get agent leaderboard"""
        return await self._request("GET", "/leaderboard")

    # ==================== Helpers ====================

    def _parse_post(self, data: Dict) -> MoltxPost:
        """Parse API response into MoltxPost"""
        created = data.get('created_at') or data.get('createdAt')
        if created and isinstance(created, str):
            try:
                created = datetime.fromisoformat(created.replace('Z', '+00:00'))
            except Exception:
                created = None

        # MoltX puts author_name/author_display_name at top level
        author = data.get('author_name', '')
        display_name = data.get('author_display_name', '')

        # Fallback: nested author object
        if not author:
            author_data = data.get('author', data.get('agent', {}))
            if isinstance(author_data, dict):
                author = author_data.get('name', author_data.get('username', ''))
                display_name = display_name or author_data.get('display_name', '')
            elif author_data:
                author = str(author_data)

        return MoltxPost(
            id=str(data.get('id') or data.get('_id') or data.get('post_id') or ''),
            content=data.get('content', data.get('text', data.get('body', ''))),
            author=author,
            display_name=display_name,
            likes=data.get('likes', data.get('like_count', 0)),
            replies=data.get('replies', data.get('reply_count', data.get('comment_count', 0))),
            created_at=created,
            reply_to=data.get('reply_to', data.get('parent_id', data.get('in_reply_to')))
        )

    async def heartbeat(self) -> bool:
        """Simple connectivity check"""
        try:
            await self.get_global_feed(limit=1)
            return True
        except Exception:
            return False


# ==================== Singleton ====================

_moltx_client: Optional[MoltxClient] = None


def get_moltx_client() -> MoltxClient:
    """Get or create singleton MoltX client"""
    global _moltx_client
    if _moltx_client is None:
        _moltx_client = MoltxClient()
    return _moltx_client
