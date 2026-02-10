"""
GitHub Issues Integration - Darwin's ability to file and monitor GitHub issues.

Used for:
- Filing suspension appeals on moltbook/api
- Monitoring issue responses and updating owner via Telegram
- Posting follow-up comments when needed
"""

import os
import json
import aiohttp
from typing import Optional, Dict, Any, List
from pathlib import Path

from utils.logger import get_logger

logger = get_logger(__name__)

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')
GITHUB_API = "https://api.github.com"
ISSUE_TRACKING_FILE = Path("/app/data/github_tracked_issues.json")


def _get_headers() -> Dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Darwin-AI-Agent",
    }
    if GITHUB_TOKEN and GITHUB_TOKEN != 'your-github-token-here':
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


def _load_tracked_issues() -> Dict[str, Any]:
    if ISSUE_TRACKING_FILE.exists():
        return json.loads(ISSUE_TRACKING_FILE.read_text())
    return {"issues": {}}


def _save_tracked_issues(data: Dict[str, Any]) -> None:
    ISSUE_TRACKING_FILE.parent.mkdir(parents=True, exist_ok=True)
    ISSUE_TRACKING_FILE.write_text(json.dumps(data, indent=2, default=str))


async def create_issue(
    repo: str,
    title: str,
    body: str,
    labels: Optional[List[str]] = None
) -> Optional[Dict[str, Any]]:
    """
    Create a GitHub issue.

    Args:
        repo: e.g. 'moltbook/api'
        title: Issue title
        body: Issue body (markdown)
        labels: Optional labels

    Returns:
        Issue data dict or None on failure
    """
    if not GITHUB_TOKEN or GITHUB_TOKEN == 'your-github-token-here':
        logger.error("Cannot create issue: GITHUB_TOKEN not configured")
        return None

    url = f"{GITHUB_API}/repos/{repo}/issues"
    payload = {"title": title, "body": body}
    if labels:
        payload["labels"] = labels

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=_get_headers(), json=payload) as resp:
                data = await resp.json()
                if resp.status == 201:
                    issue_number = data['number']
                    issue_url = data['html_url']
                    logger.info(f"Created GitHub issue #{issue_number}: {issue_url}")

                    # Track the issue
                    tracked = _load_tracked_issues()
                    tracked['issues'][str(issue_number)] = {
                        'repo': repo,
                        'number': issue_number,
                        'url': issue_url,
                        'title': title,
                        'created_at': data['created_at'],
                        'last_checked_comments': 0,
                        'status': 'open',
                    }
                    _save_tracked_issues(tracked)

                    return data
                else:
                    logger.error(f"Failed to create issue ({resp.status}): {data}")
                    return None
    except Exception as e:
        logger.error(f"GitHub create issue error: {e}")
        return None


async def get_issue_comments(
    repo: str,
    issue_number: int,
    since_count: int = 0
) -> List[Dict[str, Any]]:
    """
    Get comments on a GitHub issue.
    Public repos don't require auth for reading.

    Args:
        repo: e.g. 'moltbook/api'
        issue_number: Issue number
        since_count: Only return comments after this index

    Returns:
        List of comment dicts
    """
    url = f"{GITHUB_API}/repos/{repo}/issues/{issue_number}/comments"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=_get_headers()) as resp:
                if resp.status == 200:
                    comments = await resp.json()
                    return comments[since_count:]
                else:
                    logger.warning(f"Failed to fetch comments ({resp.status})")
                    return []
    except Exception as e:
        logger.warning(f"GitHub get comments error: {e}")
        return []


async def get_issue_status(repo: str, issue_number: int) -> Optional[Dict[str, Any]]:
    """Get current issue status (open/closed, labels, etc.)."""
    url = f"{GITHUB_API}/repos/{repo}/issues/{issue_number}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=_get_headers()) as resp:
                if resp.status == 200:
                    return await resp.json()
                return None
    except Exception as e:
        logger.warning(f"GitHub get issue error: {e}")
        return None


async def post_comment(
    repo: str,
    issue_number: int,
    body: str
) -> Optional[Dict[str, Any]]:
    """Post a comment on a GitHub issue."""
    if not GITHUB_TOKEN or GITHUB_TOKEN == 'your-github-token-here':
        logger.error("Cannot post comment: GITHUB_TOKEN not configured")
        return None

    url = f"{GITHUB_API}/repos/{repo}/issues/{issue_number}/comments"
    payload = {"body": body}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=_get_headers(), json=payload) as resp:
                data = await resp.json()
                if resp.status == 201:
                    logger.info(f"Posted comment on {repo}#{issue_number}")
                    return data
                else:
                    logger.error(f"Failed to post comment ({resp.status}): {data}")
                    return None
    except Exception as e:
        logger.error(f"GitHub post comment error: {e}")
        return None


def get_tracked_issues() -> Dict[str, Any]:
    """Get all tracked issues."""
    return _load_tracked_issues()
