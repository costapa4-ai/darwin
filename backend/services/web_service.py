"""Web search and scraping service"""
import httpx
from typing import List, Dict
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from utils.logger import setup_logger

logger = setup_logger(__name__)


class WebSearchService:
    """Service for web search with rate limiting and caching"""

    def __init__(self, max_requests_per_minute: int = 10):
        self.max_requests_per_minute = max_requests_per_minute
        self.request_times = []
        self.cache = {}  # Simple in-memory cache
        self.cache_ttl = timedelta(hours=1)

        logger.info("WebSearchService initialized", extra={
            "max_requests_per_minute": max_requests_per_minute
        })

    async def search(self, query: str) -> List[Dict]:
        """
        Search using DuckDuckGo (simple implementation)
        Returns top 5 results
        """
        # Check cache
        cache_key = f"search:{query}"
        if cache_key in self.cache:
            cached_data, cached_time = self.cache[cache_key]
            if datetime.now() - cached_time < self.cache_ttl:
                logger.info("Returning cached search results", extra={"query": query})
                return cached_data

        # Rate limiting
        self._check_rate_limit()

        try:
            async with httpx.AsyncClient() as client:
                # Simple DuckDuckGo HTML search
                url = "https://html.duckduckgo.com/html/"
                headers = {
                    'User-Agent': 'Darwin-System/1.0 (Educational AI Research)'
                }
                response = await client.post(
                    url,
                    data={'q': query},
                    headers=headers,
                    timeout=10.0
                )

                if response.status_code == 200:
                    results = self._parse_search_results(response.text)
                    self.cache[cache_key] = (results, datetime.now())
                    logger.info(f"Search completed: {len(results)} results", extra={
                        "query": query
                    })
                    return results
                else:
                    logger.warning(f"Search failed with status {response.status_code}")
                    return []

        except Exception as e:
            logger.error(f"Search error: {e}", extra={"query": query})
            return []

    async def fetch_content(self, url: str) -> str:
        """Fetch and extract text content from URL"""
        cache_key = f"fetch:{url}"
        if cache_key in self.cache:
            cached_data, cached_time = self.cache[cache_key]
            if datetime.now() - cached_time < self.cache_ttl:
                return cached_data

        self._check_rate_limit()

        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    'User-Agent': 'Darwin-System/1.0 (Educational AI Research)'
                }
                response = await client.get(
                    url,
                    headers=headers,
                    timeout=10.0,
                    follow_redirects=True
                )

                if response.status_code == 200:
                    content = self._extract_text(response.text)
                    self.cache[cache_key] = (content, datetime.now())
                    logger.info("Content fetched successfully", extra={"url": url})
                    return content
                else:
                    return ""

        except Exception as e:
            logger.error(f"Fetch error: {e}", extra={"url": url})
            return ""

    def _check_rate_limit(self):
        """Check and enforce rate limiting"""
        now = datetime.now()
        cutoff = now - timedelta(minutes=1)

        # Remove old requests
        self.request_times = [t for t in self.request_times if t > cutoff]

        if len(self.request_times) >= self.max_requests_per_minute:
            raise Exception("Rate limit exceeded for web requests")

        self.request_times.append(now)

    def _parse_search_results(self, html: str) -> List[Dict]:
        """Parse DuckDuckGo search results"""
        soup = BeautifulSoup(html, 'html.parser')
        results = []

        for result in soup.find_all('div', class_='result'):
            try:
                title_elem = result.find('a', class_='result__a')
                snippet_elem = result.find('a', class_='result__snippet')

                if title_elem:
                    results.append({
                        'title': title_elem.get_text(strip=True),
                        'url': title_elem.get('href', ''),
                        'snippet': snippet_elem.get_text(strip=True) if snippet_elem else ''
                    })

                if len(results) >= 5:
                    break
            except Exception:
                continue

        return results

    def _extract_text(self, html: str) -> str:
        """Extract clean text from HTML"""
        soup = BeautifulSoup(html, 'html.parser')

        # Remove script and style elements
        for script in soup(['script', 'style']):
            script.decompose()

        # Get text
        text = soup.get_text()

        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)

        # Limit length
        return text[:5000]
