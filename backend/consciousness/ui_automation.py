"""
UI Automation Consciousness - Visual Web Understanding

Provides Darwin with browser automation capabilities for:
- Autonomous web research and navigation
- Screenshot analysis for visual understanding
- Documentation site exploration
- Visual discovery extraction

Uses Playwright for browser control and integrates with
multi-model router for visual analysis.
"""

import asyncio
import base64
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List
import json
import re

from utils.logger import get_logger

logger = get_logger(__name__)


class BrowsingIntent(Enum):
    """Types of browsing intentions"""
    RESEARCH = "research"           # Deep dive into a topic
    DOCUMENTATION = "documentation" # Navigate official docs
    TUTORIAL = "tutorial"           # Find and follow tutorials
    EXPLORATION = "exploration"     # Free-form curiosity browsing
    MONITORING = "monitoring"       # Check status of something
    SCREENSHOT = "screenshot"       # Just capture visual state


class NavigationAction(Enum):
    """Available navigation actions"""
    GOTO = "goto"
    CLICK = "click"
    TYPE = "type"
    SCROLL = "scroll"
    SCREENSHOT = "screenshot"
    WAIT = "wait"
    BACK = "back"
    FORWARD = "forward"
    EXTRACT = "extract"


@dataclass
class VisualDiscovery:
    """A discovery made through visual browsing"""
    id: str
    timestamp: datetime
    url: str
    title: str
    discovery_type: str  # 'code_example', 'concept', 'pattern', 'warning', 'tip'
    content: str
    visual_context: Optional[str] = None  # Base64 screenshot region
    confidence: float = 0.8
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'url': self.url,
            'title': self.title,
            'discovery_type': self.discovery_type,
            'content': self.content,
            'has_visual': self.visual_context is not None,
            'confidence': self.confidence,
            'metadata': self.metadata
        }


@dataclass
class BrowsingSession:
    """A browser automation session"""
    id: str
    intent: BrowsingIntent
    start_url: str
    started_at: datetime = field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    pages_visited: List[str] = field(default_factory=list)
    discoveries: List[VisualDiscovery] = field(default_factory=list)
    screenshots_taken: int = 0
    status: str = "active"  # active, completed, failed, cancelled
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'intent': self.intent.value,
            'start_url': self.start_url,
            'started_at': self.started_at.isoformat(),
            'ended_at': self.ended_at.isoformat() if self.ended_at else None,
            'pages_visited': len(self.pages_visited),
            'discoveries_count': len(self.discoveries),
            'screenshots_taken': self.screenshots_taken,
            'status': self.status,
            'error': self.error
        }


class UIAutomationEngine:
    """
    Browser automation engine for visual web understanding.

    Enables Darwin to browse websites, capture screenshots,
    and extract visual discoveries using AI-powered analysis.
    """

    def __init__(
        self,
        multi_model_router=None,
        screenshots_path: str = "./data/screenshots",
        headless: bool = True
    ):
        """
        Initialize UI automation engine.

        Args:
            multi_model_router: Router for visual analysis
            screenshots_path: Where to store screenshots
            headless: Run browser in headless mode
        """
        self.multi_model_router = multi_model_router
        self.screenshots_path = Path(screenshots_path)
        self.headless = headless

        # Create screenshots directory
        self.screenshots_path.mkdir(parents=True, exist_ok=True)

        # Session tracking
        self._sessions: Dict[str, BrowsingSession] = {}
        self._active_session: Optional[BrowsingSession] = None
        self._discoveries: List[VisualDiscovery] = []

        # Browser state
        self._browser = None
        self._context = None
        self._page = None
        self._playwright = None

        # Configuration
        self.max_pages_per_session = 20
        self.screenshot_quality = 80
        self.default_timeout = 30000
        self.viewport_width = 1280
        self.viewport_height = 720

        # Statistics
        self._stats = {
            'total_sessions': 0,
            'pages_visited': 0,
            'screenshots_taken': 0,
            'discoveries_made': 0,
            'errors': 0
        }

        logger.info("UIAutomationEngine initialized")

    @property
    def is_browser_active(self) -> bool:
        """Check if browser is currently active"""
        return self._browser is not None and self._page is not None

    async def start_browser(self) -> bool:
        """
        Start the Playwright browser.

        Returns:
            True if browser started successfully
        """
        if self._browser is not None:
            return True

        try:
            from playwright.async_api import async_playwright

            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless
            )
            self._context = await self._browser.new_context(
                viewport={'width': self.viewport_width, 'height': self.viewport_height},
                user_agent='Mozilla/5.0 (Darwin AI Browser) Chrome/120.0.0.0'
            )
            self._page = await self._context.new_page()

            # Set default timeout
            self._page.set_default_timeout(self.default_timeout)

            logger.info("Browser started successfully")
            return True

        except ImportError:
            logger.error("Playwright not installed. Run: pip install playwright && playwright install chromium")
            return False
        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            self._stats['errors'] += 1
            return False

    async def stop_browser(self):
        """Stop the browser and clean up resources"""
        if self._page:
            await self._page.close()
            self._page = None

        if self._context:
            await self._context.close()
            self._context = None

        if self._browser:
            await self._browser.close()
            self._browser = None

        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

        logger.info("Browser stopped")

    async def start_session(
        self,
        url: str,
        intent: BrowsingIntent = BrowsingIntent.EXPLORATION
    ) -> BrowsingSession:
        """
        Start a new browsing session.

        Args:
            url: Starting URL
            intent: The purpose of this browsing session

        Returns:
            The created browsing session
        """
        # Start browser if needed
        if not await self.start_browser():
            raise RuntimeError("Failed to start browser")

        # Create session
        session_id = f"session_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        session = BrowsingSession(
            id=session_id,
            intent=intent,
            start_url=url
        )

        self._sessions[session_id] = session
        self._active_session = session
        self._stats['total_sessions'] += 1

        # Navigate to URL
        await self._navigate_to(url)

        logger.info(f"Started browsing session: {session_id} ({intent.value})")
        return session

    async def end_session(self, session_id: Optional[str] = None) -> BrowsingSession:
        """End a browsing session"""
        session = self._get_session(session_id)
        if not session:
            raise ValueError("No active session to end")

        session.ended_at = datetime.utcnow()
        session.status = "completed"

        if self._active_session and self._active_session.id == session.id:
            self._active_session = None

        logger.info(f"Ended session {session.id}: {len(session.discoveries)} discoveries")
        return session

    async def navigate(self, url: str) -> Dict[str, Any]:
        """
        Navigate to a URL.

        Args:
            url: URL to navigate to

        Returns:
            Page information
        """
        if not self._page:
            raise RuntimeError("Browser not started")

        return await self._navigate_to(url)

    async def _navigate_to(self, url: str) -> Dict[str, Any]:
        """Internal navigation method"""
        try:
            response = await self._page.goto(url, wait_until='networkidle')

            title = await self._page.title()
            current_url = self._page.url

            # Track in session
            if self._active_session:
                self._active_session.pages_visited.append(current_url)

            self._stats['pages_visited'] += 1

            return {
                'success': True,
                'url': current_url,
                'title': title,
                'status': response.status if response else None
            }

        except Exception as e:
            logger.error(f"Navigation error: {e}")
            self._stats['errors'] += 1
            return {
                'success': False,
                'error': str(e)
            }

    async def take_screenshot(
        self,
        filename: Optional[str] = None,
        full_page: bool = False,
        element_selector: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Take a screenshot of the current page.

        Args:
            filename: Optional filename (auto-generated if not provided)
            full_page: Capture full scrollable page
            element_selector: Capture specific element only

        Returns:
            Screenshot information including path and base64 data
        """
        if not self._page:
            raise RuntimeError("Browser not started")

        try:
            # Generate filename
            if not filename:
                timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                filename = f"screenshot_{timestamp}.png"

            filepath = self.screenshots_path / filename

            # Take screenshot
            if element_selector:
                element = await self._page.query_selector(element_selector)
                if element:
                    screenshot_bytes = await element.screenshot()
                else:
                    return {'success': False, 'error': f"Element not found: {element_selector}"}
            else:
                screenshot_bytes = await self._page.screenshot(
                    full_page=full_page,
                    quality=self.screenshot_quality if filename.endswith('.jpg') else None
                )

            # Save to file
            with open(filepath, 'wb') as f:
                f.write(screenshot_bytes)

            # Encode as base64
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')

            # Track stats
            self._stats['screenshots_taken'] += 1
            if self._active_session:
                self._active_session.screenshots_taken += 1

            return {
                'success': True,
                'path': str(filepath),
                'filename': filename,
                'size_bytes': len(screenshot_bytes),
                'base64_preview': screenshot_b64[:100] + '...' if len(screenshot_b64) > 100 else screenshot_b64
            }

        except Exception as e:
            logger.error(f"Screenshot error: {e}")
            self._stats['errors'] += 1
            return {'success': False, 'error': str(e)}

    async def analyze_page(self, screenshot_b64: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze the current page visually using AI.

        Args:
            screenshot_b64: Optional pre-captured screenshot

        Returns:
            Analysis results with identified elements and content
        """
        if not self.multi_model_router:
            # Fallback to basic extraction
            return await self._basic_page_extraction()

        try:
            # Take screenshot if not provided
            if not screenshot_b64:
                screenshot_result = await self.take_screenshot()
                if not screenshot_result['success']:
                    return screenshot_result

                # Read the file
                with open(screenshot_result['path'], 'rb') as f:
                    screenshot_b64 = base64.b64encode(f.read()).decode('utf-8')

            # Get page context
            title = await self._page.title()
            url = self._page.url

            # Use vision-capable model for analysis
            prompt = f"""Analyze this screenshot of a web page.

URL: {url}
Title: {title}

Please identify:
1. Main content type (documentation, tutorial, article, code, etc.)
2. Key information or concepts present
3. Any code examples visible
4. Navigation structure
5. Interesting or notable elements

Respond in JSON format:
{{
    "content_type": "...",
    "main_topic": "...",
    "key_concepts": ["..."],
    "code_examples": ["..."],
    "navigation_links": ["..."],
    "notable_elements": ["..."],
    "recommended_actions": ["..."]
}}"""

            # Call vision model
            response = await self.multi_model_router.route_request(
                prompt=prompt,
                images=[{
                    'type': 'base64',
                    'media_type': 'image/png',
                    'data': screenshot_b64
                }],
                preferred_capabilities=['vision']
            )

            # Parse response
            try:
                analysis = json.loads(response.get('content', '{}'))
            except json.JSONDecodeError:
                analysis = {'raw_analysis': response.get('content', '')}

            return {
                'success': True,
                'url': url,
                'title': title,
                'analysis': analysis
            }

        except Exception as e:
            logger.error(f"Page analysis error: {e}")
            return {'success': False, 'error': str(e)}

    async def _basic_page_extraction(self) -> Dict[str, Any]:
        """Extract basic page information without AI"""
        if not self._page:
            return {'success': False, 'error': 'No page loaded'}

        try:
            title = await self._page.title()
            url = self._page.url

            # Extract text content
            text_content = await self._page.evaluate("""
                () => {
                    // Get main content
                    const main = document.querySelector('main, article, .content, #content');
                    if (main) return main.innerText.substring(0, 2000);
                    return document.body.innerText.substring(0, 2000);
                }
            """)

            # Extract links
            links = await self._page.evaluate("""
                () => {
                    const links = Array.from(document.querySelectorAll('a[href]'));
                    return links.slice(0, 20).map(a => ({
                        text: a.innerText.trim().substring(0, 100),
                        href: a.href
                    })).filter(l => l.text);
                }
            """)

            # Extract code blocks
            code_blocks = await self._page.evaluate("""
                () => {
                    const codes = Array.from(document.querySelectorAll('pre, code'));
                    return codes.slice(0, 5).map(c => c.innerText.substring(0, 500));
                }
            """)

            return {
                'success': True,
                'url': url,
                'title': title,
                'analysis': {
                    'content_type': 'extracted',
                    'text_preview': text_content[:500] if text_content else '',
                    'links_count': len(links),
                    'links': links[:10],
                    'code_blocks_count': len(code_blocks),
                    'code_preview': code_blocks[0][:200] if code_blocks else None
                }
            }

        except Exception as e:
            logger.error(f"Basic extraction error: {e}")
            return {'success': False, 'error': str(e)}

    async def click(self, selector: str) -> Dict[str, Any]:
        """Click an element"""
        if not self._page:
            return {'success': False, 'error': 'No page loaded'}

        try:
            await self._page.click(selector)
            await self._page.wait_for_load_state('networkidle')

            return {
                'success': True,
                'action': 'click',
                'selector': selector,
                'new_url': self._page.url
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def type_text(self, selector: str, text: str) -> Dict[str, Any]:
        """Type text into an input field"""
        if not self._page:
            return {'success': False, 'error': 'No page loaded'}

        try:
            await self._page.fill(selector, text)
            return {
                'success': True,
                'action': 'type',
                'selector': selector
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def scroll(self, direction: str = "down", amount: int = 500) -> Dict[str, Any]:
        """Scroll the page"""
        if not self._page:
            return {'success': False, 'error': 'No page loaded'}

        try:
            delta = amount if direction == "down" else -amount
            await self._page.mouse.wheel(0, delta)
            await asyncio.sleep(0.5)  # Wait for scroll

            return {
                'success': True,
                'action': 'scroll',
                'direction': direction,
                'amount': amount
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def extract_discovery(
        self,
        content: str,
        discovery_type: str,
        capture_visual: bool = False
    ) -> VisualDiscovery:
        """
        Record a visual discovery from the current page.

        Args:
            content: The discovered content
            discovery_type: Type of discovery
            capture_visual: Whether to capture a screenshot

        Returns:
            The created discovery
        """
        if not self._page:
            raise RuntimeError("No page loaded")

        visual_context = None
        if capture_visual:
            screenshot = await self.take_screenshot()
            if screenshot['success']:
                with open(screenshot['path'], 'rb') as f:
                    visual_context = base64.b64encode(f.read()).decode('utf-8')

        discovery = VisualDiscovery(
            id=f"visual_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            timestamp=datetime.utcnow(),
            url=self._page.url,
            title=await self._page.title(),
            discovery_type=discovery_type,
            content=content,
            visual_context=visual_context
        )

        self._discoveries.append(discovery)
        self._stats['discoveries_made'] += 1

        if self._active_session:
            self._active_session.discoveries.append(discovery)

        logger.info(f"Visual discovery recorded: {discovery_type} from {discovery.url}")

        # Trigger hook
        try:
            from consciousness.hooks import trigger_hook, HookEvent
            await trigger_hook(HookEvent.ON_DISCOVERY, {
                'type': 'visual',
                'discovery_type': discovery_type,
                'url': discovery.url,
                'content_preview': content[:200] if content else ''
            }, source='ui_automation')
        except ImportError:
            pass

        return discovery

    async def autonomous_explore(
        self,
        start_url: str,
        topic: str,
        max_pages: int = 5
    ) -> Dict[str, Any]:
        """
        Autonomously explore a website to learn about a topic.

        Args:
            start_url: Starting URL
            topic: Topic to explore
            max_pages: Maximum pages to visit

        Returns:
            Exploration results with discoveries
        """
        session = await self.start_session(start_url, BrowsingIntent.RESEARCH)

        try:
            discoveries = []
            pages_explored = 0

            while pages_explored < max_pages:
                # Analyze current page
                analysis = await self.analyze_page()

                if analysis['success']:
                    # Check if relevant to topic
                    page_analysis = analysis.get('analysis', {})

                    # Extract discoveries if relevant
                    if self._is_relevant_to_topic(page_analysis, topic):
                        content = page_analysis.get('key_concepts', [])
                        if content:
                            discovery = await self.extract_discovery(
                                content=json.dumps(content),
                                discovery_type='concept',
                                capture_visual=True
                            )
                            discoveries.append(discovery)

                    # Find next page to visit
                    recommended = page_analysis.get('recommended_actions', [])
                    links = page_analysis.get('navigation_links', [])

                    next_link = self._find_best_link(links, topic)
                    if next_link and pages_explored < max_pages - 1:
                        await self.navigate(next_link)

                pages_explored += 1
                await asyncio.sleep(1)  # Rate limiting

            session = await self.end_session()

            return {
                'success': True,
                'session': session.to_dict(),
                'pages_explored': pages_explored,
                'discoveries': [d.to_dict() for d in discoveries]
            }

        except Exception as e:
            session.status = "failed"
            session.error = str(e)
            session.ended_at = datetime.utcnow()

            return {
                'success': False,
                'error': str(e),
                'session': session.to_dict()
            }

    def _is_relevant_to_topic(self, analysis: Dict, topic: str) -> bool:
        """Check if page analysis is relevant to topic"""
        topic_lower = topic.lower()

        # Check main topic
        main_topic = analysis.get('main_topic', '').lower()
        if topic_lower in main_topic:
            return True

        # Check key concepts
        concepts = analysis.get('key_concepts', [])
        for concept in concepts:
            if topic_lower in concept.lower():
                return True

        return False

    def _find_best_link(self, links: List[str], topic: str) -> Optional[str]:
        """Find the most relevant link for a topic"""
        topic_words = set(topic.lower().split())

        for link in links:
            if isinstance(link, str):
                link_lower = link.lower()
                if any(word in link_lower for word in topic_words):
                    return link

        return links[0] if links else None

    def _get_session(self, session_id: Optional[str]) -> Optional[BrowsingSession]:
        """Get a session by ID or return active session"""
        if session_id:
            return self._sessions.get(session_id)
        return self._active_session

    def get_discoveries(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent discoveries"""
        return [d.to_dict() for d in self._discoveries[-limit:]]

    def get_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent sessions"""
        sessions = sorted(
            self._sessions.values(),
            key=lambda s: s.started_at,
            reverse=True
        )[:limit]
        return [s.to_dict() for s in sessions]

    def get_stats(self) -> Dict[str, Any]:
        """Get automation statistics"""
        return {
            'browser_active': self.is_browser_active,
            'active_session': self._active_session.to_dict() if self._active_session else None,
            'headless_mode': self.headless,
            'viewport': f"{self.viewport_width}x{self.viewport_height}",
            'statistics': self._stats,
            'total_discoveries': len(self._discoveries),
            'total_sessions': len(self._sessions)
        }


# Global instance
_ui_automation_engine: Optional[UIAutomationEngine] = None


def get_ui_automation_engine() -> Optional[UIAutomationEngine]:
    """Get the global UI automation engine"""
    return _ui_automation_engine


def set_ui_automation_engine(engine: UIAutomationEngine):
    """Set the global UI automation engine"""
    global _ui_automation_engine
    _ui_automation_engine = engine
