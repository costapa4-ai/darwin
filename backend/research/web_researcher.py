"""
Web Research System
Integrates multiple sources: SerpAPI, GitHub, StackOverflow, ArXiv
"""
import aiohttp
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import re

from utils.logger import get_logger

logger = get_logger(__name__)


class WebResearcher:
    """
    Advanced web research system for gathering context and solutions
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize web researcher

        Args:
            config: Configuration with API keys
        """
        self.config = config
        self.serpapi_key = config.get("serpapi_api_key", "")
        self.github_token = config.get("github_token", "")

        # Rate limiting
        self.request_delay = 1.0  # seconds between requests
        self.last_request_time = 0

        logger.info("WebResearcher initialized")

    async def _rate_limited_request(self, url: str, headers: Optional[Dict] = None) -> Dict[str, Any]:
        """Make rate-limited HTTP request"""
        # Wait if needed
        current_time = asyncio.get_event_loop().time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.request_delay:
            await asyncio.sleep(self.request_delay - time_since_last)

        self.last_request_time = asyncio.get_event_loop().time()

        # Make request
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers or {}) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Request failed: {response.status}")
                    return {}

    async def search_web(self, query: str, num_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search web using SerpAPI

        Args:
            query: Search query
            num_results: Number of results

        Returns:
            List of search results
        """
        if not self.serpapi_key:
            logger.warning("SerpAPI key not configured")
            return []

        try:
            url = "https://serpapi.com/search"
            params = {
                "q": query,
                "api_key": self.serpapi_key,
                "num": num_results
            }

            # Build URL with params
            url_with_params = f"{url}?{'&'.join(f'{k}={v}' for k, v in params.items())}"

            response = await self._rate_limited_request(url_with_params)

            # Extract organic results
            results = []
            for result in response.get("organic_results", [])[:num_results]:
                results.append({
                    "title": result.get("title", ""),
                    "link": result.get("link", ""),
                    "snippet": result.get("snippet", ""),
                    "source": "web"
                })

            logger.info(f"Found {len(results)} web results for: {query}")
            return results

        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return []

    async def search_github(self, query: str, language: str = "python") -> List[Dict[str, Any]]:
        """
        Search GitHub repositories and code

        Args:
            query: Search query
            language: Programming language filter

        Returns:
            List of GitHub results
        """
        try:
            # Search repositories
            url = f"https://api.github.com/search/repositories?q={query}+language:{language}&sort=stars&per_page=5"

            headers = {}
            if self.github_token:
                headers["Authorization"] = f"token {self.github_token}"

            response = await self._rate_limited_request(url, headers)

            results = []
            for repo in response.get("items", []):
                results.append({
                    "title": repo.get("full_name", ""),
                    "link": repo.get("html_url", ""),
                    "description": repo.get("description", ""),
                    "stars": repo.get("stargazers_count", 0),
                    "language": repo.get("language", ""),
                    "source": "github"
                })

            logger.info(f"Found {len(results)} GitHub results for: {query}")
            return results

        except Exception as e:
            logger.error(f"GitHub search failed: {e}")
            return []

    async def search_stackoverflow(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search StackOverflow questions

        Args:
            query: Search query
            max_results: Maximum results

        Returns:
            List of StackOverflow results
        """
        try:
            url = f"https://api.stackexchange.com/2.3/search/advanced?order=desc&sort=votes&q={query}&site=stackoverflow&pagesize={max_results}"

            response = await self._rate_limited_request(url)

            results = []
            for item in response.get("items", []):
                results.append({
                    "title": item.get("title", ""),
                    "link": item.get("link", ""),
                    "score": item.get("score", 0),
                    "answer_count": item.get("answer_count", 0),
                    "is_answered": item.get("is_answered", False),
                    "source": "stackoverflow"
                })

            logger.info(f"Found {len(results)} StackOverflow results for: {query}")
            return results

        except Exception as e:
            logger.error(f"StackOverflow search failed: {e}")
            return []

    async def search_arxiv(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search ArXiv papers

        Args:
            query: Search query
            max_results: Maximum results

        Returns:
            List of ArXiv results
        """
        try:
            import xml.etree.ElementTree as ET

            url = f"http://export.arxiv.org/api/query?search_query=all:{query}&start=0&max_results={max_results}"

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        xml_data = await response.text()
                        root = ET.fromstring(xml_data)

                        results = []
                        namespace = {'atom': 'http://www.w3.org/2005/Atom'}

                        for entry in root.findall('atom:entry', namespace):
                            title = entry.find('atom:title', namespace)
                            link = entry.find('atom:id', namespace)
                            summary = entry.find('atom:summary', namespace)

                            results.append({
                                "title": title.text.strip() if title is not None else "",
                                "link": link.text if link is not None else "",
                                "summary": summary.text.strip() if summary is not None else "",
                                "source": "arxiv"
                            })

                        logger.info(f"Found {len(results)} ArXiv results for: {query}")
                        return results

            return []

        except Exception as e:
            logger.error(f"ArXiv search failed: {e}")
            return []

    async def comprehensive_search(
        self,
        query: str,
        sources: Optional[List[str]] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Perform comprehensive search across multiple sources

        Args:
            query: Search query
            sources: List of sources to search (default: all)

        Returns:
            Results grouped by source
        """
        available_sources = ["web", "github", "stackoverflow", "arxiv"]
        sources_to_search = sources or available_sources

        results = {}

        # Create search tasks
        tasks = []
        if "web" in sources_to_search and self.serpapi_key:
            tasks.append(("web", self.search_web(query)))

        if "github" in sources_to_search:
            tasks.append(("github", self.search_github(query)))

        if "stackoverflow" in sources_to_search:
            tasks.append(("stackoverflow", self.search_stackoverflow(query)))

        if "arxiv" in sources_to_search:
            tasks.append(("arxiv", self.search_arxiv(query)))

        # Execute searches in parallel
        for source, task in tasks:
            try:
                results[source] = await task
            except Exception as e:
                logger.error(f"Search failed for {source}: {e}")
                results[source] = []

        total_results = sum(len(r) for r in results.values())
        logger.info(f"Comprehensive search complete: {total_results} total results")

        return results

    def format_research_context(self, results: Dict[str, List[Dict[str, Any]]]) -> str:
        """
        Format research results into context string for AI

        Args:
            results: Research results by source

        Returns:
            Formatted context string
        """
        context_parts = ["# Research Context\n"]

        for source, items in results.items():
            if not items:
                continue

            context_parts.append(f"\n## {source.upper()} Results:\n")

            for i, item in enumerate(items[:3], 1):  # Top 3 from each source
                context_parts.append(f"\n{i}. **{item.get('title', 'N/A')}**")
                context_parts.append(f"   Link: {item.get('link', 'N/A')}")

                if 'snippet' in item:
                    context_parts.append(f"   {item['snippet']}")
                elif 'description' in item:
                    context_parts.append(f"   {item['description']}")
                elif 'summary' in item:
                    context_parts.append(f"   {item['summary'][:200]}...")

                if source == "github" and 'stars' in item:
                    context_parts.append(f"   ⭐ {item['stars']} stars")
                elif source == "stackoverflow" and 'score' in item:
                    context_parts.append(f"   Score: {item['score']}, Answers: {item.get('answer_count', 0)}")

        return "\n".join(context_parts)

    async def research_task(self, task_description: str) -> str:
        """
        Research a task and return formatted context

        Args:
            task_description: Task to research

        Returns:
            Formatted research context
        """
        logger.info(f"Researching task: {task_description}")

        # Perform comprehensive search
        results = await self.comprehensive_search(task_description)

        # Format for AI consumption
        context = self.format_research_context(results)

        return context

    async def research(
        self,
        query: str,
        max_results: int = 5
    ) -> Dict[str, Any]:
        """
        Research a topic and return structured findings.

        This method is used by the Curiosity Expedition system.
        Uses multiple search strategies with fallbacks:
        1. API-based searches (if keys configured)
        2. DuckDuckGo via WebSearchService (no API key needed)
        3. GitHub public search (limited rate)

        Args:
            query: Research query/question
            max_results: Maximum number of results per source

        Returns:
            Dict with:
                - success: bool
                - sources: List of source URLs explored
                - findings: List of discoveries with title/summary
                - synthesis: Overall synthesis of findings
        """
        logger.info(f"Researching: {query}")

        sources = []
        findings = []

        try:
            # Strategy 1: Try API-based comprehensive search if keys are available
            if self.serpapi_key:
                search_results = await self.comprehensive_search(query)

                for source_name, items in search_results.items():
                    for item in items[:max_results]:
                        url = item.get('link', item.get('url', ''))
                        if url:
                            sources.append(url)

                        title = item.get('title', 'Untitled')
                        content = (
                            item.get('snippet', '') or
                            item.get('description', '') or
                            item.get('summary', '') or
                            item.get('abstract', '')
                        )

                        if title and content:
                            findings.append({
                                'title': title,
                                'summary': content[:500],
                                'content': content,
                                'source': source_name,
                                'url': url
                            })

            # Strategy 2: Fallback to DuckDuckGo via WebSearchService (no API key needed)
            if not findings:
                logger.info("Using DuckDuckGo fallback for research")
                try:
                    from services.web_service import WebSearchService
                    web_service = WebSearchService()
                    ddg_results = await web_service.search(query)

                    for item in ddg_results[:max_results]:
                        url = item.get('url', '')
                        if url:
                            sources.append(url)

                        title = item.get('title', 'Untitled')
                        snippet = item.get('snippet', '')

                        if title:
                            findings.append({
                                'title': title,
                                'summary': snippet[:500] if snippet else f"Result about: {query}",
                                'content': snippet,
                                'source': 'duckduckgo',
                                'url': url
                            })

                    logger.info(f"DuckDuckGo returned {len(ddg_results)} results")

                except Exception as ddg_error:
                    logger.warning(f"DuckDuckGo search failed: {ddg_error}")

            # Strategy 3: Also try GitHub search (works without token, but rate limited)
            if len(findings) < max_results:
                try:
                    github_results = await self.search_github(query)
                    for item in github_results[:max_results - len(findings)]:
                        url = item.get('link', '')
                        if url:
                            sources.append(url)

                        findings.append({
                            'title': item.get('title', 'GitHub Project'),
                            'summary': item.get('description', '')[:500] if item.get('description') else f"GitHub project related to: {query}",
                            'content': item.get('description', ''),
                            'source': 'github',
                            'url': url,
                            'stars': item.get('stars', 0)
                        })

                    logger.info(f"GitHub returned {len(github_results)} results")

                except Exception as gh_error:
                    logger.debug(f"GitHub search failed: {gh_error}")

            # Generate synthesis if we found anything
            synthesis = ""
            if findings:
                topics = [f.get('title', '')[:50] for f in findings[:3]]
                unique_sources = set()
                for s in sources[:5]:
                    try:
                        if '/' in s:
                            domain = s.split('/')[2]
                            unique_sources.add(domain)
                    except:
                        pass

                synthesis = f"Explored {len(findings)} resources about: {query}. "
                synthesis += f"Key topics covered: {', '.join(topics)}. "
                if unique_sources:
                    synthesis += f"Sources include: {', '.join(list(unique_sources)[:3])}."

            success = len(findings) > 0

            logger.info(f"Research complete: {len(findings)} findings, {len(sources)} sources, success={success}")

            return {
                'success': success,
                'sources': sources[:max_results * 2],
                'findings': findings[:max_results],
                'synthesis': synthesis,
                'query': query
            }

        except Exception as e:
            logger.error(f"Research failed for '{query}': {e}")
            return {
                'success': False,
                'sources': [],
                'findings': [],
                'synthesis': f"Research could not be completed: {str(e)[:100]}",
                'query': query,
                'error': str(e)
            }
