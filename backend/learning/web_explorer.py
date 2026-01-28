"""
Web Explorer - Autonomous Web Navigation and Learning

This module enables Darwin to autonomously explore the web,
follow links, extract knowledge, and learn from diverse sources.
"""

import aiohttp
import asyncio
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import re
import hashlib

from utils.logger import get_logger

logger = get_logger(__name__)


class WebExplorer:
    """
    Autonomous web exploration system for diverse learning
    """

    def __init__(self, semantic_memory, multi_model_router, config: Optional[Dict] = None):
        """
        Initialize web explorer

        Args:
            semantic_memory: Semantic memory for storing discoveries
            multi_model_router: AI router for content analysis
            config: Configuration options
        """
        self.memory = semantic_memory
        self.ai_router = multi_model_router
        self.config = config or {}

        # Exploration tracking
        self.visited_urls: Set[str] = set()
        self.discovered_knowledge: List[Dict[str, Any]] = []

        # Configuration
        self.max_depth = self.config.get('max_depth', 2)
        self.max_urls_per_session = self.config.get('max_urls_per_session', 10)
        self.request_timeout = self.config.get('request_timeout', 10)
        self.user_agent = self.config.get('user_agent',
            'Mozilla/5.0 (Darwin AI Bot) Learning/1.0')

        # Interesting domains for learning
        self.priority_domains = [
            'arxiv.org',
            'github.com',
            'stackoverflow.com',
            'medium.com',
            'dev.to',
            'python.org',
            'tensorflow.org',
            'pytorch.org',
            'kubernetes.io',
            'docker.com',
            'aws.amazon.com/blogs',
            'cloud.google.com/blog',
            'microsoft.com/research',
            'openai.com',
            'anthropic.com',
            'huggingface.co'
        ]

        logger.info("WebExplorer initialized")

    async def explore_autonomous(self,
                                 seed_urls: List[str],
                                 topic: str) -> Dict[str, Any]:
        """
        Autonomously explore the web starting from seed URLs

        Args:
            seed_urls: Initial URLs to start exploration
            topic: Topic of interest for focused exploration

        Returns:
            Exploration report with discoveries
        """
        logger.info(f"Starting autonomous exploration on topic: {topic}")

        # Reset visited URLs for this session to allow fresh exploration
        self.visited_urls.clear()

        exploration_report = {
            'topic': topic,
            'started_at': datetime.utcnow().isoformat(),
            'seed_urls': seed_urls,
            'urls_explored': 0,
            'knowledge_extracted': 0,
            'insights_generated': 0,
            'discoveries': []
        }

        urls_to_visit = seed_urls.copy()
        depth = 0

        while urls_to_visit and depth < self.max_depth and len(self.visited_urls) < self.max_urls_per_session:
            current_url = urls_to_visit.pop(0)

            # Skip if already visited
            if current_url in self.visited_urls:
                continue

            try:
                # Explore the URL
                result = await self._explore_url(current_url, topic)

                if result['success']:
                    self.visited_urls.add(current_url)
                    exploration_report['urls_explored'] += 1

                    # Extract and store knowledge
                    if result.get('content'):
                        knowledge = await self._extract_knowledge(
                            result['content'],
                            current_url,
                            topic
                        )

                        if knowledge:
                            exploration_report['knowledge_extracted'] += 1
                            exploration_report['discoveries'].append({
                                'url': current_url,
                                'title': result.get('title'),
                                'key_points': knowledge.get('key_points', [])
                            })

                            # Store in semantic memory
                            await self._store_discovery(knowledge, current_url, topic)

                    # Find interesting links to follow
                    if result.get('links') and depth < self.max_depth - 1:
                        interesting_links = self._filter_interesting_links(
                            result['links'],
                            topic
                        )
                        urls_to_visit.extend(interesting_links[:3])  # Follow top 3

                # Rate limiting
                await asyncio.sleep(2)

            except Exception as e:
                logger.error(f"Error exploring {current_url}: {e}")
                continue

            depth += 1

        # Generate AI insights from all discoveries
        if exploration_report['discoveries']:
            insights = await self._generate_insights(
                exploration_report['discoveries'],
                topic
            )
            exploration_report['insights_generated'] = len(insights)
            exploration_report['insights'] = insights

        exploration_report['completed_at'] = datetime.utcnow().isoformat()
        logger.info(f"Exploration complete: {exploration_report['urls_explored']} URLs, "
                   f"{exploration_report['knowledge_extracted']} knowledge items extracted")

        return exploration_report

    async def _explore_url(self, url: str, topic: str) -> Dict[str, Any]:
        """
        Explore a single URL and extract content

        Args:
            url: URL to explore
            topic: Topic context

        Returns:
            Exploration result
        """
        result = {
            'success': False,
            'url': url,
            'title': None,
            'content': None,
            'links': []
        }

        try:
            headers = {'User-Agent': self.user_agent}

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.request_timeout)
                ) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')

                        # Extract title
                        title_tag = soup.find('title')
                        result['title'] = title_tag.get_text().strip() if title_tag else 'No title'

                        # Extract main content
                        result['content'] = self._extract_main_content(soup)

                        # Extract links
                        result['links'] = self._extract_links(soup, url)

                        result['success'] = True
                        logger.info(f"Successfully explored: {url}")
                    else:
                        logger.warning(f"Failed to fetch {url}: Status {response.status}")

        except asyncio.TimeoutError:
            logger.warning(f"Timeout fetching {url}")
        except Exception as e:
            logger.error(f"Error exploring {url}: {e}")

        return result

    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """
        Extract main textual content from HTML

        Args:
            soup: BeautifulSoup object

        Returns:
            Extracted text content
        """
        # Remove script and style elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header']):
            element.decompose()

        # Try to find main content area
        main_content = (
            soup.find('main') or
            soup.find('article') or
            soup.find('div', class_=re.compile('content|article|post', re.I)) or
            soup.find('body')
        )

        if main_content:
            # Extract paragraphs
            paragraphs = main_content.find_all('p')
            text = ' '.join(p.get_text().strip() for p in paragraphs if p.get_text().strip())

            # Limit length
            return text[:5000] if text else ''

        return ''

    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """
        Extract links from HTML

        Args:
            soup: BeautifulSoup object
            base_url: Base URL for resolving relative links

        Returns:
            List of absolute URLs
        """
        links = []

        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']

            # Convert to absolute URL
            absolute_url = urljoin(base_url, href)

            # Basic validation
            parsed = urlparse(absolute_url)
            if parsed.scheme in ['http', 'https'] and parsed.netloc:
                links.append(absolute_url)

        return links

    def _filter_interesting_links(self, links: List[str], topic: str) -> List[str]:
        """
        Filter links to find interesting ones for exploration

        Args:
            links: List of URLs
            topic: Topic context

        Returns:
            Filtered list of interesting URLs
        """
        interesting = []

        for link in links:
            # Already visited
            if link in self.visited_urls:
                continue

            parsed = urlparse(link)

            # Check if domain is in priority list
            for priority_domain in self.priority_domains:
                if priority_domain in parsed.netloc:
                    interesting.append(link)
                    break
            else:
                # Check if URL contains topic-related keywords
                topic_keywords = topic.lower().split()
                link_lower = link.lower()

                if any(keyword in link_lower for keyword in topic_keywords):
                    interesting.append(link)

        return interesting[:10]  # Limit to top 10

    async def _extract_knowledge(self,
                                 content: str,
                                 url: str,
                                 topic: str) -> Optional[Dict[str, Any]]:
        """
        Extract knowledge from content using AI

        Args:
            content: Text content
            url: Source URL
            topic: Topic context

        Returns:
            Extracted knowledge
        """
        if not content or len(content) < 100:
            return None

        try:
            # Use AI to extract key points
            prompt = f"""Analyze the following content about {topic}.
Extract the 3-5 most important key points or insights that would be valuable for learning.
Be concise and focus on actionable or novel information.

Content:
{content[:2000]}

Provide your response as a list of key points."""

            result = await self.ai_router.generate(
                task_description=f"Extract knowledge from {url}",
                prompt=prompt,
                max_tokens=500
            )

            response_text = result.get('result', '') if isinstance(result, dict) else str(result)

            # Parse key points
            key_points = [
                line.strip('- •*').strip()
                for line in response_text.split('\n')
                if line.strip() and len(line.strip()) > 10
            ]

            return {
                'url': url,
                'topic': topic,
                'key_points': key_points[:5],
                'full_content': content[:1000],
                'timestamp': datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error extracting knowledge: {e}")
            return None

    async def _store_discovery(self, knowledge: Dict[str, Any], url: str, topic: str):
        """
        Store discovered knowledge in semantic memory

        Args:
            knowledge: Knowledge dictionary
            url: Source URL
            topic: Topic context
        """
        if not self.memory:
            return

        try:
            # Create unique task ID
            task_id = f"web_exploration_{hashlib.md5(url.encode()).hexdigest()[:8]}"

            # Format knowledge for storage
            description = f"Web Exploration: {topic}\nSource: {url}\n\n"
            description += "Key Points:\n"
            for i, point in enumerate(knowledge.get('key_points', []), 1):
                description += f"{i}. {point}\n"

            await self.memory.store_execution(
                task_id=task_id,
                task_description=description,
                code=f"# Web exploration discovery\n# URL: {url}",
                result={'success': True, 'type': 'web_exploration'},
                metadata={
                    'type': 'web_exploration',
                    'topic': topic,
                    'source_url': url,
                    'discovered_at': knowledge.get('timestamp'),
                    'learning_source': 'autonomous_web_exploration'
                }
            )

            logger.info(f"Stored web discovery from {url}")

        except Exception as e:
            logger.error(f"Error storing discovery: {e}")

    async def _generate_insights(self,
                                discoveries: List[Dict[str, Any]],
                                topic: str) -> List[str]:
        """
        Generate high-level insights from all discoveries

        Args:
            discoveries: List of discoveries
            topic: Topic context

        Returns:
            List of insights
        """
        try:
            # Compile all key points
            all_points = []
            for discovery in discoveries:
                all_points.extend(discovery.get('key_points', []))

            if not all_points:
                return []

            # Use AI to synthesize insights
            prompt = f"""Based on these learning discoveries about {topic}, generate 3 high-level insights or patterns.
Focus on connections, trends, or actionable conclusions.

Discoveries:
{chr(10).join(f"- {point}" for point in all_points[:20])}

Provide 3 synthesized insights:"""

            result = await self.ai_router.generate(
                task_description=f"Synthesize insights about {topic}",
                prompt=prompt,
                max_tokens=400
            )

            response_text = result.get('result', '') if isinstance(result, dict) else str(result)

            # Parse insights
            insights = [
                line.strip('- •*123.').strip()
                for line in response_text.split('\n')
                if line.strip() and len(line.strip()) > 20
            ]

            return insights[:3]

        except Exception as e:
            logger.error(f"Error generating insights: {e}")
            return []

    async def explore_trending_topics(self) -> Dict[str, Any]:
        """
        Explore trending topics in tech/AI

        Returns:
            Exploration report
        """
        trending_sources = [
            'https://news.ycombinator.com/',
            'https://github.com/trending',
            'https://www.reddit.com/r/MachineLearning/',
            'https://arxiv.org/list/cs.AI/recent'
        ]

        return await self.explore_autonomous(
            seed_urls=trending_sources,
            topic='trending technology and AI'
        )

    def get_exploration_stats(self) -> Dict[str, Any]:
        """
        Get exploration statistics

        Returns:
            Statistics dictionary
        """
        return {
            'urls_visited': len(self.visited_urls),
            'knowledge_items': len(self.discovered_knowledge),
            'visited_urls': list(self.visited_urls)[-10:]  # Last 10
        }
