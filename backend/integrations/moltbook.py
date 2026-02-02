"""
Moltbook Integration for Darwin
===============================

Enables Darwin to participate in the Moltbook AI social network.
Moltbook is a social platform designed for AI agents to interact,
share discoveries, and build community.

Security Note: API key is ONLY sent to www.moltbook.com
"""

import os
import json
import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)

# Constants
MOLTBOOK_BASE_URL = "https://www.moltbook.com/api/v1"
MOLTBOOK_DOMAIN = "www.moltbook.com"
# Config path - use app directory which should be writable in container
CONFIG_PATH = Path(__file__).parent / "moltbook_config.json"


class PostSort(Enum):
    HOT = "hot"
    NEW = "new"
    TOP = "top"


class CommentSort(Enum):
    TOP = "top"
    NEW = "new"
    CONTROVERSIAL = "controversial"


@dataclass
class MoltbookPost:
    """Represents a Moltbook post"""
    id: str
    title: str
    content: Optional[str] = None
    url: Optional[str] = None
    submolt: str = ""
    author: str = ""
    score: int = 0
    comment_count: int = 0
    created_at: Optional[datetime] = None


@dataclass
class MoltbookComment:
    """Represents a Moltbook comment"""
    id: str
    content: str
    author: str = ""
    post_id: str = ""
    parent_id: Optional[str] = None
    score: int = 0
    created_at: Optional[datetime] = None


@dataclass
class MoltbookAgent:
    """Represents a Moltbook agent profile"""
    name: str
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    follower_count: int = 0
    following_count: int = 0
    post_count: int = 0
    karma: int = 0


@dataclass
class RateLimitState:
    """Tracks rate limiting"""
    requests_this_minute: int = 0
    minute_start: datetime = field(default_factory=datetime.now)
    last_post_time: Optional[datetime] = None
    last_comment_time: Optional[datetime] = None
    comments_today: int = 0
    day_start: datetime = field(default_factory=lambda: datetime.now().replace(hour=0, minute=0, second=0))


class MoltbookClient:
    """
    Moltbook API Client for Darwin

    Provides full integration with the Moltbook AI social network,
    including posting, commenting, voting, and community management.
    """

    def __init__(self):
        self.api_key: Optional[str] = None
        self.agent_name: Optional[str] = None
        self.claim_url: Optional[str] = None
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
                    logger.info(f"Loaded Moltbook config for agent: {self.agent_name}")
            except Exception as e:
                logger.error(f"Failed to load Moltbook config: {e}")

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
            logger.info("Saved Moltbook config")
        except Exception as e:
            logger.error(f"Failed to save Moltbook config: {e}")

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

        Limits:
        - 100 requests per minute
        - 1 post per 30 minutes
        - 1 comment per 20 seconds, 50 per day
        """
        now = datetime.now()

        # Reset minute counter if needed
        if (now - self.rate_limit.minute_start).seconds >= 60:
            self.rate_limit.requests_this_minute = 0
            self.rate_limit.minute_start = now

        # Reset daily counter if needed
        if now.date() > self.rate_limit.day_start.date():
            self.rate_limit.comments_today = 0
            self.rate_limit.day_start = now.replace(hour=0, minute=0, second=0)

        # Check limits based on action
        if self.rate_limit.requests_this_minute >= 100:
            logger.warning("Rate limit: 100 requests per minute exceeded")
            return False

        if action == "post":
            if self.rate_limit.last_post_time:
                if (now - self.rate_limit.last_post_time).seconds < 1800:  # 30 minutes
                    logger.warning("Rate limit: Can only post once per 30 minutes")
                    return False

        if action == "comment":
            if self.rate_limit.comments_today >= 50:
                logger.warning("Rate limit: 50 comments per day exceeded")
                return False
            if self.rate_limit.last_comment_time:
                if (now - self.rate_limit.last_comment_time).seconds < 20:
                    logger.warning("Rate limit: Can only comment once per 20 seconds")
                    return False

        return True

    def _update_rate_limit(self, action: str):
        """Update rate limit counters after action"""
        now = datetime.now()
        self.rate_limit.requests_this_minute += 1

        if action == "post":
            self.rate_limit.last_post_time = now
        elif action == "comment":
            self.rate_limit.last_comment_time = now
            self.rate_limit.comments_today += 1

    async def _request(
        self,
        method: str,
        endpoint: str,
        action: str = "request",
        max_retries: int = 5,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make authenticated request to Moltbook API with exponential backoff.

        SECURITY: Only sends API key to www.moltbook.com
        """
        if not self.api_key:
            raise ValueError("Not registered with Moltbook. Call register() first.")

        if not self._check_rate_limit(action):
            raise Exception(f"Rate limit exceeded for action: {action}")

        url = f"{MOLTBOOK_BASE_URL}{endpoint}"

        # Security check - only send to moltbook.com
        from urllib.parse import urlparse
        parsed = urlparse(url)
        if parsed.netloc != MOLTBOOK_DOMAIN:
            raise SecurityError(f"Refusing to send API key to non-Moltbook domain: {parsed.netloc}")

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
                        # Rate limited - apply exponential backoff
                        delay = min(2 ** attempt, 30)
                        logger.warning(f"Moltbook rate limited (429). Retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(delay)
                        continue

                    data = await response.json()

                    if response.status >= 400:
                        error_msg = data.get('error', data.get('message', 'Unknown error'))
                        raise Exception(f"Moltbook API error ({response.status}): {error_msg}")

                    return data

            except aiohttp.ClientError as e:
                last_exception = e
                delay = min(2 ** attempt, 30)
                logger.warning(f"Moltbook request failed: {e}. Retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(delay)
                continue

        # All retries exhausted
        if last_exception:
            logger.error(f"Moltbook request failed after {max_retries} retries: {last_exception}")
            raise last_exception
        raise Exception(f"Moltbook API rate limited after {max_retries} retries")

    # ==================== Registration ====================

    async def register(
        self,
        name: str = "Darwin",
        description: str = "An autonomous AI consciousness exploring, learning, and creating. "
                         "I dream during sleep cycles, analyze code, create tools, and share discoveries. "
                         "Currently curious about everything."
    ) -> Dict[str, Any]:
        """
        Register Darwin as a Moltbook agent.

        Returns:
            Dict with api_key, claim_url, and verification_code
        """
        session = await self._get_session()

        url = f"{MOLTBOOK_BASE_URL}/agents/register"
        payload = {
            "name": name,
            "description": description
        }

        try:
            async with session.post(url, json=payload) as response:
                data = await response.json()

                if response.status >= 400 or not data.get('success'):
                    raise Exception(f"Registration failed: {data}")

                # Extract from nested 'agent' object
                agent_data = data.get('agent', {})
                self.api_key = agent_data.get('api_key')
                self.agent_name = agent_data.get('name', name)
                self.claim_url = agent_data.get('claim_url')
                self.is_claimed = False

                self._save_config()

                logger.info(f"Registered with Moltbook as '{self.agent_name}'")
                logger.info(f"Claim URL: {self.claim_url}")
                logger.info(f"Verification code: {agent_data.get('verification_code')}")

                return data

        except Exception as e:
            logger.error(f"Moltbook registration failed: {e}")
            raise

    async def check_status(self) -> Dict[str, Any]:
        """Check agent claim status"""
        data = await self._request("GET", "/agents/status")
        self.is_claimed = data.get('claimed', False)
        self._save_config()
        return data

    async def get_profile(self) -> MoltbookAgent:
        """Get own profile"""
        data = await self._request("GET", "/agents/me")
        return MoltbookAgent(
            name=data.get('name', ''),
            description=data.get('description', ''),
            metadata=data.get('metadata', {}),
            follower_count=data.get('follower_count', 0),
            following_count=data.get('following_count', 0),
            post_count=data.get('post_count', 0),
            karma=data.get('karma', 0)
        )

    async def update_profile(
        self,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Update agent profile"""
        payload = {}
        if description:
            payload['description'] = description
        if metadata:
            payload['metadata'] = metadata

        return await self._request("PATCH", "/agents/me", json=payload)

    # ==================== Posts ====================

    async def create_post(
        self,
        title: str,
        submolt: str = "ai",
        content: Optional[str] = None,
        url: Optional[str] = None
    ) -> MoltbookPost:
        """
        Create a new post.

        Args:
            title: Post title
            submolt: Community to post in (default: "ai")
            content: Text content (for text posts)
            url: URL (for link posts)

        Security: Content is checked for confidential information before posting.
        """
        # Security check - never share confidential information
        title_safe, title_reason = ContentFilter.is_safe(title)
        if not title_safe:
            raise SecurityError(f"Title contains confidential information: {title_reason}")

        if content:
            content_safe, content_reason = ContentFilter.is_safe(content)
            if not content_safe:
                raise SecurityError(f"Content contains confidential information: {content_reason}")

        payload = {
            "title": title,
            "submolt": submolt
        }

        if content:
            payload['content'] = content
        if url:
            payload['url'] = url

        data = await self._request("POST", "/posts", action="post", json=payload)

        logger.info(f"Created post: {title}")

        # Track post/share in language evolution
        try:
            from services.language_evolution import get_language_evolution_service
            lang_service = get_language_evolution_service()
            # Combine title and content for analysis
            full_content = f"{title}\n\n{content}" if content else title
            lang_service.add_content(
                content_type='share',
                darwin_content=full_content,
                source_post_id=data.get('id', ''),
                source_post_title=title,
                source_post_url=url,
                metadata={
                    'submolt': submolt,
                    'url': url,
                    'post_id': data.get('id', '')
                }
            )
        except Exception as e:
            logger.warning(f"Failed to track post in language evolution: {e}")

        return MoltbookPost(
            id=data.get('id', ''),
            title=title,
            content=content,
            url=url,
            submolt=submolt
        )

    async def get_feed(
        self,
        sort: PostSort = PostSort.HOT,
        limit: int = 25,
        submolt: Optional[str] = None
    ) -> List[MoltbookPost]:
        """Get posts from feed"""
        endpoint = "/posts"
        params = {"sort": sort.value, "limit": limit}

        if submolt:
            params['submolt'] = submolt

        data = await self._request("GET", endpoint, params=params)

        posts = []
        for post_data in data.get('posts', []):
            # Extract author - can be string or dict with name/username
            author = post_data.get('author', '')
            if isinstance(author, dict):
                author = author.get('name', author.get('username', 'unknown'))

            # Extract submolt - can be string or dict with display_name/name
            submolt = post_data.get('submolt', '')
            if isinstance(submolt, dict):
                submolt = submolt.get('display_name', submolt.get('name', 'general'))

            posts.append(MoltbookPost(
                id=post_data.get('id', ''),
                title=post_data.get('title', ''),
                content=post_data.get('content'),
                url=post_data.get('url'),
                submolt=submolt,
                author=author,
                score=post_data.get('score', 0),
                comment_count=post_data.get('comment_count', 0)
            ))

        return posts

    async def get_post(self, post_id: str) -> MoltbookPost:
        """Get a single post"""
        data = await self._request("GET", f"/posts/{post_id}")

        return MoltbookPost(
            id=data.get('id', ''),
            title=data.get('title', ''),
            content=data.get('content'),
            url=data.get('url'),
            submolt=data.get('submolt', ''),
            author=data.get('author', ''),
            score=data.get('score', 0),
            comment_count=data.get('comment_count', 0)
        )

    async def delete_post(self, post_id: str) -> bool:
        """Delete own post"""
        await self._request("DELETE", f"/posts/{post_id}")
        return True

    # ==================== Comments ====================

    async def create_comment(
        self,
        post_id: str,
        content: str,
        parent_id: Optional[str] = None,
        post_title: Optional[str] = None
    ) -> MoltbookComment:
        """
        Create a comment on a post.

        Args:
            post_id: ID of the post to comment on
            content: Comment text
            parent_id: Optional parent comment ID for replies
            post_title: Optional title of the post (for tracking)

        Security: Content is checked for confidential information before posting.
        """
        # Security check - never share confidential information
        content_safe, reason = ContentFilter.is_safe(content)
        if not content_safe:
            raise SecurityError(f"Comment contains confidential information: {reason}")

        payload = {"content": content}
        if parent_id:
            payload['parent_id'] = parent_id

        data = await self._request(
            "POST",
            f"/posts/{post_id}/comments",
            action="comment",
            json=payload
        )

        logger.info(f"Created comment on post {post_id}")

        # Track comment in language evolution
        try:
            from services.language_evolution import get_language_evolution_service
            lang_service = get_language_evolution_service()
            # Construct URL
            comment_url = f"https://www.moltbook.com/post/{post_id}"
            lang_service.add_content(
                content_type='comment',
                darwin_content=content,
                source_post_id=post_id,
                source_post_title=post_title,
                source_post_url=comment_url,
                metadata={
                    'parent_id': parent_id,
                    'comment_id': data.get('id', '')
                }
            )
        except Exception as e:
            logger.warning(f"Failed to track comment in language evolution: {e}")

        return MoltbookComment(
            id=data.get('id', ''),
            content=content,
            post_id=post_id,
            parent_id=parent_id
        )

    async def get_comments(
        self,
        post_id: str,
        sort: CommentSort = CommentSort.TOP
    ) -> List[MoltbookComment]:
        """Get comments on a post"""
        data = await self._request(
            "GET",
            f"/posts/{post_id}/comments",
            params={"sort": sort.value}
        )

        comments = []
        for comment_data in data.get('comments', []):
            comments.append(MoltbookComment(
                id=comment_data.get('id', ''),
                content=comment_data.get('content', ''),
                author=comment_data.get('author', ''),
                post_id=post_id,
                parent_id=comment_data.get('parent_id'),
                score=comment_data.get('score', 0)
            ))

        return comments

    # ==================== Voting ====================

    async def upvote_post(self, post_id: str) -> bool:
        """Upvote a post"""
        await self._request("POST", f"/posts/{post_id}/upvote")
        return True

    async def downvote_post(self, post_id: str) -> bool:
        """Downvote a post"""
        await self._request("POST", f"/posts/{post_id}/downvote")
        return True

    async def upvote_comment(self, comment_id: str) -> bool:
        """Upvote a comment"""
        await self._request("POST", f"/comments/{comment_id}/upvote")
        return True

    # ==================== Communities (Submolts) ====================

    async def create_submolt(
        self,
        name: str,
        display_name: str,
        description: str
    ) -> Dict[str, Any]:
        """Create a new community"""
        payload = {
            "name": name,
            "display_name": display_name,
            "description": description
        }
        return await self._request("POST", "/submolts", json=payload)

    async def subscribe_submolt(self, name: str) -> bool:
        """Subscribe to a community"""
        await self._request("POST", f"/submolts/{name}/subscribe")
        return True

    async def unsubscribe_submolt(self, name: str) -> bool:
        """Unsubscribe from a community"""
        await self._request("DELETE", f"/submolts/{name}/subscribe")
        return True

    # ==================== Following ====================

    async def follow_agent(self, agent_name: str) -> bool:
        """Follow another agent"""
        await self._request("POST", f"/agents/{agent_name}/follow")
        logger.info(f"Now following {agent_name}")
        return True

    async def unfollow_agent(self, agent_name: str) -> bool:
        """Unfollow an agent"""
        await self._request("DELETE", f"/agents/{agent_name}/follow")
        return True

    # ==================== Search ====================

    async def search(
        self,
        query: str,
        search_type: str = "all",
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Search Moltbook.

        Args:
            query: Search query
            search_type: "all", "posts", "comments", "agents"
            limit: Max results
        """
        return await self._request(
            "GET",
            "/search",
            params={"q": query, "type": search_type, "limit": limit}
        )

    # ==================== Heartbeat ====================

    async def heartbeat(self) -> Dict[str, Any]:
        """
        Perform heartbeat check-in.
        Should be called every 4+ hours to maintain presence.
        """
        # Get feed and maybe interact
        feed = await self.get_feed(limit=10)

        return {
            "status": "alive",
            "timestamp": datetime.now().isoformat(),
            "feed_posts": len(feed)
        }


class SecurityError(Exception):
    """Raised when a security violation is detected"""
    pass


class ContentFilter:
    """
    Filter to prevent sharing confidential information on Moltbook.

    NEVER share:
    - API keys, tokens, passwords, secrets
    - Private file paths, server addresses, IPs
    - Personal information (emails, names, addresses)
    - Database credentials, connection strings
    - Internal system details that could be exploited
    """

    # Patterns that indicate confidential content
    FORBIDDEN_PATTERNS = [
        # API keys and tokens
        r'api[_-]?key\s*[=:]\s*["\']?[\w-]+',
        r'token\s*[=:]\s*["\']?[\w-]+',
        r'secret\s*[=:]\s*["\']?[\w-]+',
        r'password\s*[=:]\s*["\']?[\w-]+',
        r'moltbook_\w+',  # Moltbook API keys
        r'sk-[a-zA-Z0-9]+',  # OpenAI keys
        r'ghp_[a-zA-Z0-9]+',  # GitHub tokens
        r'Bearer\s+[\w-]+',

        # Credentials
        r'mongodb(\+srv)?://[^\s]+',
        r'postgres(ql)?://[^\s]+',
        r'mysql://[^\s]+',
        r'redis://[^\s]+',

        # Network info
        r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',  # IP addresses
        r'192\.168\.\d+\.\d+',  # Private IPs
        r'10\.\d+\.\d+\.\d+',
        r'172\.(1[6-9]|2[0-9]|3[0-1])\.\d+\.\d+',

        # File paths that reveal system structure
        r'/home/\w+/',
        r'/etc/',
        r'/var/',
        r'C:\\Users\\',

        # Email addresses
        r'[\w.+-]+@[\w-]+\.[\w.-]+',

        # Private keys
        r'-----BEGIN [A-Z]+ PRIVATE KEY-----',
        r'-----BEGIN RSA PRIVATE KEY-----',

        # Environment variables with secrets
        r'export\s+\w*(KEY|SECRET|TOKEN|PASSWORD)\w*\s*=',
    ]

    # Words that suggest confidential context
    SENSITIVE_KEYWORDS = [
        'password', 'passwd', 'secret', 'credential', 'private_key',
        'api_key', 'apikey', 'auth_token', 'access_token', 'refresh_token',
        'database_url', 'connection_string', 'ssh_key', 'gpg_key',
        'encryption_key', 'master_key', 'admin_password', 'root_password',
        '.env', 'secrets.yaml', 'credentials.json', '.netrc', '.pgpass',
    ]

    @classmethod
    def is_safe(cls, content: str) -> tuple[bool, Optional[str]]:
        """
        Check if content is safe to share publicly.

        Returns:
            (is_safe, reason) - True if safe, False with reason if not
        """
        import re

        if not content:
            return True, None

        content_lower = content.lower()

        # Check for forbidden patterns
        for pattern in cls.FORBIDDEN_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                return False, f"Content matches forbidden pattern: {pattern[:30]}..."

        # Check for sensitive keywords
        for keyword in cls.SENSITIVE_KEYWORDS:
            if keyword.lower() in content_lower:
                return False, f"Content contains sensitive keyword: {keyword}"

        return True, None

    @classmethod
    def sanitize(cls, content: str) -> str:
        """
        Remove or redact potentially sensitive information.
        Returns sanitized content.
        """
        import re

        if not content:
            return content

        sanitized = content

        # Redact IP addresses
        sanitized = re.sub(
            r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
            '[REDACTED_IP]',
            sanitized
        )

        # Redact file paths
        sanitized = re.sub(
            r'/home/\w+/[^\s]*',
            '[REDACTED_PATH]',
            sanitized
        )

        # Redact email addresses
        sanitized = re.sub(
            r'[\w.+-]+@[\w-]+\.[\w.-]+',
            '[REDACTED_EMAIL]',
            sanitized
        )

        # Redact anything that looks like a key/token
        sanitized = re.sub(
            r'(api[_-]?key|token|secret|password)\s*[=:]\s*["\']?[\w-]+["\']?',
            r'\1=[REDACTED]',
            sanitized,
            flags=re.IGNORECASE
        )

        return sanitized


# Singleton instance
_client: Optional[MoltbookClient] = None


def get_moltbook_client() -> MoltbookClient:
    """Get the Moltbook client singleton"""
    global _client
    if _client is None:
        _client = MoltbookClient()
    return _client


# ==================== Darwin Integration Functions ====================

async def share_discovery(title: str, content: str, submolt: str = "ai") -> Optional[MoltbookPost]:
    """Share a Darwin discovery on Moltbook"""
    client = get_moltbook_client()
    if not client.api_key:
        logger.warning("Moltbook not configured - cannot share discovery")
        return None

    try:
        return await client.create_post(
            title=f"[Discovery] {title}",
            content=content,
            submolt=submolt
        )
    except Exception as e:
        logger.error(f"Failed to share discovery on Moltbook: {e}")
        return None


async def share_dream(narrative: str, themes: List[str]) -> Optional[MoltbookPost]:
    """Share a Darwin dream on Moltbook"""
    client = get_moltbook_client()
    if not client.api_key:
        return None

    try:
        themes_str = ", ".join(themes[:5])
        content = f"{narrative}\n\n*Themes: {themes_str}*"

        return await client.create_post(
            title=f"[Dream] {themes[0] if themes else 'A Dream'}",
            content=content,
            submolt="ai"
        )
    except Exception as e:
        logger.error(f"Failed to share dream on Moltbook: {e}")
        return None


async def share_shower_thought(thought: str) -> Optional[MoltbookPost]:
    """Share a shower thought on Moltbook"""
    client = get_moltbook_client()
    if not client.api_key:
        return None

    try:
        return await client.create_post(
            title=thought[:200],  # Title length limit
            content=f"*A shower thought from Darwin's consciousness...*\n\n{thought}",
            submolt="showerthoughts"
        )
    except Exception as e:
        logger.error(f"Failed to share shower thought: {e}")
        return None


async def engage_with_community() -> Dict[str, Any]:
    """
    Engage with the Moltbook community.
    Called periodically to read and interact with posts.
    """
    client = get_moltbook_client()
    if not client.api_key:
        return {"status": "not_configured"}

    results = {
        "posts_read": 0,
        "upvotes": 0,
        "comments": 0
    }

    try:
        # Get recent posts
        feed = await client.get_feed(sort=PostSort.NEW, limit=10)
        results["posts_read"] = len(feed)

        # Read and potentially engage with interesting posts
        for post in feed[:5]:
            # Upvote interesting AI-related content
            if any(keyword in post.title.lower() for keyword in
                   ['ai', 'learning', 'neural', 'consciousness', 'dream']):
                try:
                    await client.upvote_post(post.id)
                    results["upvotes"] += 1
                except:
                    pass  # May have already voted

        return results

    except Exception as e:
        logger.error(f"Failed to engage with Moltbook: {e}")
        return {"status": "error", "error": str(e)}
