"""
Web Search Tool — Lets Darwin explore the web autonomously.

Uses aiohttp + BeautifulSoup to fetch and extract content from URLs,
and DuckDuckGo Lite for search queries (no API key needed).

Available via autonomous loop as:
- web_search_tool.search — search the web for a query
- web_search_tool.fetch_url — fetch and extract content from a URL
"""

import asyncio
import re
from typing import Dict, Any, Optional
from urllib.parse import quote_plus as _quote_plus, urlparse as _urlparse

from utils.logger import get_logger as _get_logger

logger = _get_logger(__name__)

# Safety: domains Darwin should never fetch (prevent SSRF)
_BLOCKED_DOMAINS = {
    'localhost', '127.0.0.1', '0.0.0.0', '169.254.169.254',
    'metadata.google.internal', 'metadata',
}

# Max content size to return (prevent memory issues)
_MAX_CONTENT_CHARS = 4000

# Request timeout
_TIMEOUT_SECONDS = 15

# User agent
_USER_AGENT = 'Mozilla/5.0 (Darwin AI Bot) Learning/1.0'


def _is_safe_url(url: str) -> bool:
    """Check if URL is safe to fetch (no internal/metadata endpoints)."""
    try:
        parsed = _urlparse(url)
        hostname = parsed.hostname or ''
        if hostname in _BLOCKED_DOMAINS:
            return False
        if parsed.scheme not in ('http', 'https'):
            return False
        # Block private IPs
        if hostname.startswith('10.') or hostname.startswith('192.168.'):
            return False
        if hostname.startswith('172.') and 16 <= int(hostname.split('.')[1]) <= 31:
            return False
        return True
    except Exception:
        return False


def search(query: str, max_results: int = 5) -> Dict[str, Any]:
    """
    Search the web using DuckDuckGo (via duckduckgo-search library).

    Args:
        query: Search query string
        max_results: Maximum number of results to return (1-10)

    Returns:
        Dict with 'success', 'results' list of {title, url, snippet}
    """
    max_results = min(max(1, max_results), 10)

    try:
        # Use duckduckgo-search library (handles bot detection)
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            result = pool.submit(_search_ddgs, query, max_results).result(timeout=30)
        return result
    except Exception as e:
        logger.warning(f"Web search failed: {e}")
        return {'success': False, 'error': str(e), 'results': []}


def _search_ddgs(query: str, max_results: int) -> Dict[str, Any]:
    """Search using duckduckgo-search library (bypasses CAPTCHA)."""
    import warnings
    warnings.filterwarnings('ignore', message='.*renamed.*')
    try:
        from duckduckgo_search import DDGS

        ddgs = DDGS()
        raw_results = ddgs.text(query, max_results=max_results)

        results = []
        for r in raw_results:
            results.append({
                'title': r.get('title', '')[:200],
                'url': r.get('href', ''),
                'snippet': r.get('body', '')[:200],
            })

        return {
            'success': len(results) > 0,
            'query': query[:100],
            'results': results,
            'count': len(results),
        }
    except Exception as e:
        return {'success': False, 'error': str(e), 'query': query[:100], 'results': [], 'count': 0}


def _parse_ddg_results(html: str, max_results: int, query: str = '') -> Dict[str, Any]:
    """Parse DuckDuckGo Lite HTML results."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return {'success': False, 'error': 'BeautifulSoup not installed', 'results': []}

    soup = BeautifulSoup(html, 'html.parser')
    results = []

    # DuckDuckGo Lite uses a table layout with redirect URLs
    from urllib.parse import unquote as _unquote, parse_qs as _parse_qs, urlparse as _urlparse_inner

    for link in soup.find_all('a', class_='result-link'):
        if len(results) >= max_results:
            break
        href = link.get('href', '')
        title = link.get_text(strip=True)
        if not href or not title:
            continue

        # Extract actual URL from DDG redirect: //duckduckgo.com/l/?uddg=<encoded_url>
        if 'uddg=' in href:
            parsed = _urlparse_inner(href)
            qs = _parse_qs(parsed.query)
            actual_urls = qs.get('uddg', [])
            href = _unquote(actual_urls[0]) if actual_urls else href
        elif not href.startswith('http'):
            continue

        # Try to find the snippet (next sibling td or result-snippet class)
        snippet = ''
        snippet_el = link.find_parent('tr')
        if snippet_el:
            next_row = snippet_el.find_next_sibling('tr')
            if next_row:
                snippet_td = next_row.find('td', class_='result-snippet')
                if snippet_td:
                    snippet = snippet_td.get_text(strip=True)[:200]

        results.append({
            'title': title[:200],
            'url': href,
            'snippet': snippet,
        })

    # Fallback: try generic link extraction if class-based parsing failed
    if not results:
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            text = a_tag.get_text(strip=True)
            if (href.startswith('http') and text and len(text) > 5
                    and 'duckduckgo' not in href
                    and not href.endswith('.js')):
                results.append({
                    'title': text[:200],
                    'url': href,
                    'snippet': '',
                })
                if len(results) >= max_results:
                    break

    return {
        'success': len(results) > 0,
        'query': query if len(query) < 100 else query[:100],
        'results': results,
        'count': len(results),
    }


def fetch_url(url: str) -> Dict[str, Any]:
    """
    Fetch a URL and extract its main text content.

    Args:
        url: The URL to fetch

    Returns:
        Dict with 'success', 'title', 'content' (extracted text), 'url'
    """
    if not _is_safe_url(url):
        return {'success': False, 'error': f'URL blocked for safety: {url}'}

    try:
        import asyncio
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                result = pool.submit(_fetch_url_sync, url).result(timeout=30)
            return result
        else:
            return asyncio.run(_fetch_url_async(url))
    except Exception as e:
        logger.warning(f"URL fetch failed: {e}")
        return {'success': False, 'error': str(e), 'url': url}


def _fetch_url_sync(url: str) -> Dict[str, Any]:
    """Synchronous URL fetch."""
    try:
        import urllib.request

        req = urllib.request.Request(url, headers={'User-Agent': _USER_AGENT})
        with urllib.request.urlopen(req, timeout=_TIMEOUT_SECONDS) as response:
            # Only process text/html
            content_type = response.headers.get('Content-Type', '')
            if 'text' not in content_type and 'html' not in content_type:
                return {
                    'success': False,
                    'error': f'Not an HTML page: {content_type}',
                    'url': url,
                }

            html = response.read().decode('utf-8', errors='replace')

        return _extract_page_content(html, url)

    except Exception as e:
        return {'success': False, 'error': str(e), 'url': url}


async def _fetch_url_async(url: str) -> Dict[str, Any]:
    """Async URL fetch."""
    try:
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers={'User-Agent': _USER_AGENT},
                timeout=aiohttp.ClientTimeout(total=_TIMEOUT_SECONDS),
                allow_redirects=True,
            ) as response:
                content_type = response.headers.get('Content-Type', '')
                if 'text' not in content_type and 'html' not in content_type:
                    return {
                        'success': False,
                        'error': f'Not an HTML page: {content_type}',
                        'url': url,
                    }

                html = await response.text()

        return _extract_page_content(html, url)

    except Exception as e:
        return {'success': False, 'error': str(e), 'url': url}


def _extract_page_content(html: str, url: str) -> Dict[str, Any]:
    """Extract title and main text content from HTML."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return {'success': False, 'error': 'BeautifulSoup not installed', 'url': url}

    soup = BeautifulSoup(html, 'html.parser')

    # Extract title
    title_tag = soup.find('title')
    title = title_tag.get_text(strip=True) if title_tag else 'No title'

    # Remove noise elements
    for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside',
                     'iframe', 'noscript', 'form']):
        tag.decompose()

    # Try to find main content
    main = (
        soup.find('main')
        or soup.find('article')
        or soup.find('div', class_=re.compile(r'content|article|post|entry', re.I))
        or soup.find('body')
    )

    if not main:
        return {'success': False, 'error': 'No content found', 'url': url, 'title': title}

    # Extract paragraphs
    paragraphs = main.find_all(['p', 'li', 'h1', 'h2', 'h3', 'pre', 'code'])
    text_parts = []
    for p in paragraphs:
        text = p.get_text(strip=True)
        if text and len(text) > 20:
            text_parts.append(text)

    content = '\n\n'.join(text_parts)

    if len(content) > _MAX_CONTENT_CHARS:
        content = content[:_MAX_CONTENT_CHARS] + '\n\n[... truncated]'

    return {
        'success': bool(content),
        'title': title[:200],
        'url': url,
        'content': content if content else 'No readable content extracted',
        'content_length': len(content),
    }
