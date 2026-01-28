"""
Code Repository Analyzer - Learn from Public Code

Analyzes popular GitHub repositories and other code sources
to learn patterns, best practices, and innovative solutions.
"""

import aiohttp
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import hashlib
import base64
import re

from utils.logger import get_logger

logger = get_logger(__name__)


class CodeRepositoryAnalyzer:
    """
    Analyzes code repositories to extract learning insights
    """

    def __init__(self, semantic_memory, multi_model_router, config: Optional[Dict] = None):
        """
        Initialize repository analyzer

        Args:
            semantic_memory: Semantic memory for storage
            multi_model_router: AI router for analysis
            config: Configuration with API keys
        """
        self.memory = semantic_memory
        self.ai_router = multi_model_router
        self.config = config or {}

        self.github_token = self.config.get('github_token', '')

        # Popular repositories by category
        self.notable_repos = {
            'ml_frameworks': [
                'tensorflow/tensorflow',
                'pytorch/pytorch',
                'huggingface/transformers'
            ],
            'web_frameworks': [
                'tiangolo/fastapi',
                'pallets/flask',
                'django/django',
                'facebook/react',
                'vuejs/vue'
            ],
            'devops': [
                'kubernetes/kubernetes',
                'docker/compose',
                'hashicorp/terraform'
            ],
            'databases': [
                'redis/redis',
                'postgres/postgres',
                'mongodb/mongo'
            ],
            'ai_agents': [
                'anthropics/anthropic-sdk-python',
                'openai/openai-python',
                'langchain-ai/langchain'
            ],
            'tools': [
                'microsoft/vscode',
                'neovim/neovim',
                'git/git'
            ]
        }

        self.analyzed_repos = []

        logger.info("CodeRepositoryAnalyzer initialized")

    async def analyze_random_repository(self) -> Dict[str, Any]:
        """
        Analyze a random popular repository

        Returns:
            Analysis report
        """
        import random

        # Select random category and repo
        category = random.choice(list(self.notable_repos.keys()))
        repos_in_category = self.notable_repos[category]
        repo = random.choice(repos_in_category)

        logger.info(f"Analyzing repository: {repo}")

        return await self.analyze_repository(repo, category)

    async def analyze_repository(self, repo_full_name: str, category: str = 'general') -> Dict[str, Any]:
        """
        Analyze a specific repository

        Args:
            repo_full_name: Repository full name (owner/repo)
            category: Repository category

        Returns:
            Analysis report
        """
        report = {
            'repository': repo_full_name,
            'category': category,
            'started_at': datetime.utcnow().isoformat(),
            'success': False,
            'insights': [],
            'patterns_discovered': 0
        }

        try:
            # Fetch repository info
            repo_info = await self._fetch_repo_info(repo_full_name)

            if not repo_info:
                report['error'] = 'Failed to fetch repository info'
                return report

            report['stars'] = repo_info.get('stargazers_count', 0)
            report['language'] = repo_info.get('language', 'Unknown')
            report['description'] = repo_info.get('description', '')

            # Analyze repository structure
            structure = await self._analyze_repo_structure(repo_full_name)
            report['structure_insights'] = structure.get('insights', [])

            # Analyze key files
            key_files = await self._analyze_key_files(repo_full_name)
            report['code_insights'] = key_files.get('insights', [])

            # Combine all insights
            all_insights = (
                structure.get('insights', []) +
                key_files.get('insights', [])
            )

            if all_insights:
                # Generate high-level patterns
                patterns = await self._identify_patterns(
                    all_insights,
                    repo_full_name,
                    category
                )

                report['patterns_discovered'] = len(patterns)
                report['patterns'] = patterns
                report['insights'] = all_insights

                # Store in memory
                await self._store_repo_analysis(
                    repo_full_name,
                    category,
                    all_insights,
                    patterns,
                    repo_info
                )

            report['success'] = True
            self.analyzed_repos.append({
                'repo': repo_full_name,
                'category': category,
                'timestamp': datetime.utcnow().isoformat()
            })

        except Exception as e:
            logger.error(f"Error analyzing repository {repo_full_name}: {e}")
            report['error'] = str(e)

        report['completed_at'] = datetime.utcnow().isoformat()
        return report

    async def _fetch_repo_info(self, repo_full_name: str) -> Optional[Dict[str, Any]]:
        """
        Fetch repository information from GitHub API

        Args:
            repo_full_name: Repository full name

        Returns:
            Repository info or None
        """
        try:
            url = f"https://api.github.com/repos/{repo_full_name}"
            headers = {'Accept': 'application/vnd.github.v3+json'}

            if self.github_token:
                headers['Authorization'] = f'token {self.github_token}'

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.warning(f"Failed to fetch repo info: {response.status}")
                        return None

        except Exception as e:
            logger.error(f"Error fetching repo info: {e}")
            return None

    async def _analyze_repo_structure(self, repo_full_name: str) -> Dict[str, Any]:
        """
        Analyze repository structure

        Args:
            repo_full_name: Repository full name

        Returns:
            Structure analysis
        """
        result = {'insights': []}

        try:
            # Fetch root directory contents
            url = f"https://api.github.com/repos/{repo_full_name}/contents"
            headers = {'Accept': 'application/vnd.github.v3+json'}

            if self.github_token:
                headers['Authorization'] = f'token {self.github_token}'

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        contents = await response.json()

                        # Analyze structure
                        directories = [item['name'] for item in contents if item['type'] == 'dir']
                        files = [item['name'] for item in contents if item['type'] == 'file']

                        # Identify patterns
                        if 'tests' in directories or 'test' in directories:
                            result['insights'].append("Repository includes comprehensive test suite")

                        if 'docs' in directories or 'documentation' in directories:
                            result['insights'].append("Well-documented with dedicated docs directory")

                        if 'docker-compose.yml' in files or 'Dockerfile' in files:
                            result['insights'].append("Uses containerization for deployment")

                        if '.github' in directories:
                            result['insights'].append("Implements CI/CD with GitHub Actions")

                        if 'README.md' in files:
                            result['insights'].append("Includes comprehensive README for onboarding")

                        # Check for common patterns
                        if 'src' in directories or 'lib' in directories:
                            result['insights'].append("Clean source code organization")

                        if 'examples' in directories:
                            result['insights'].append("Provides example code for learning")

                        logger.info(f"Analyzed structure: {len(result['insights'])} insights")

        except Exception as e:
            logger.error(f"Error analyzing repo structure: {e}")

        return result

    async def _analyze_key_files(self, repo_full_name: str) -> Dict[str, Any]:
        """
        Analyze key files in repository

        Args:
            repo_full_name: Repository full name

        Returns:
            File analysis
        """
        result = {'insights': []}

        try:
            # Key files to analyze
            key_files = ['README.md', 'CONTRIBUTING.md', 'setup.py', 'pyproject.toml', 'package.json']

            for filename in key_files:
                try:
                    content = await self._fetch_file_content(repo_full_name, filename)

                    if content:
                        # Analyze content
                        insights = await self._analyze_file_content(content, filename)
                        result['insights'].extend(insights)

                        # Rate limiting
                        await asyncio.sleep(1)

                except Exception as e:
                    logger.debug(f"Could not analyze {filename}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error analyzing key files: {e}")

        return result

    async def _fetch_file_content(self, repo_full_name: str, filename: str) -> Optional[str]:
        """
        Fetch file content from repository

        Args:
            repo_full_name: Repository full name
            filename: File to fetch

        Returns:
            File content or None
        """
        try:
            url = f"https://api.github.com/repos/{repo_full_name}/contents/{filename}"
            headers = {'Accept': 'application/vnd.github.v3+json'}

            if self.github_token:
                headers['Authorization'] = f'token {self.github_token}'

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()

                        # Decode base64 content
                        if data.get('encoding') == 'base64':
                            content_bytes = base64.b64decode(data['content'])
                            return content_bytes.decode('utf-8', errors='ignore')

                    return None

        except Exception as e:
            logger.debug(f"Error fetching file {filename}: {e}")
            return None

    async def _analyze_file_content(self, content: str, filename: str) -> List[str]:
        """
        Analyze file content for insights

        Args:
            content: File content
            filename: Filename

        Returns:
            List of insights
        """
        insights = []

        try:
            # Use AI to analyze
            prompt = f"""Analyze this {filename} file and extract 2-3 key technical insights or best practices.
Focus on:
- Code organization patterns
- Testing strategies
- Documentation practices
- Dependency management
- Architecture decisions

File content:
{content[:1500]}

Provide 2-3 specific insights:"""

            result = await self.ai_router.generate(
                task_description=f"Analyze {filename}",
                prompt=prompt,
                max_tokens=300
            )

            response_text = result.get('result', '') if isinstance(result, dict) else str(result)

            # Parse insights
            for line in response_text.split('\n'):
                line = line.strip('- •*123.').strip()
                if line and len(line) > 15:
                    insights.append(line)

            return insights[:3]

        except Exception as e:
            logger.error(f"Error analyzing file content: {e}")
            return []

    async def _identify_patterns(self,
                                insights: List[str],
                                repo_name: str,
                                category: str) -> List[str]:
        """
        Identify high-level patterns from insights

        Args:
            insights: Collected insights
            repo_name: Repository name
            category: Repository category

        Returns:
            List of patterns
        """
        try:
            prompt = f"""Based on analysis of {repo_name} ({category}), identify 2-3 high-level
patterns or architectural decisions that make this repository successful.

Insights:
{chr(10).join(f"- {insight}" for insight in insights[:10])}

Provide 2-3 architectural patterns or design decisions:"""

            result = await self.ai_router.generate(
                task_description=f"Identify patterns in {repo_name}",
                prompt=prompt,
                max_tokens=400
            )

            response_text = result.get('result', '') if isinstance(result, dict) else str(result)

            # Parse patterns
            patterns = []
            for line in response_text.split('\n'):
                line = line.strip('- •*123.').strip()
                if line and len(line) > 20:
                    patterns.append(line)

            return patterns[:3]

        except Exception as e:
            logger.error(f"Error identifying patterns: {e}")
            return []

    async def _store_repo_analysis(self,
                                  repo_name: str,
                                  category: str,
                                  insights: List[str],
                                  patterns: List[str],
                                  repo_info: Dict):
        """
        Store repository analysis in semantic memory

        Args:
            repo_name: Repository name
            category: Category
            insights: Extracted insights
            patterns: Identified patterns
            repo_info: Repository information
        """
        if not self.memory:
            return

        try:
            task_id = f"repo_analysis_{hashlib.md5(repo_name.encode()).hexdigest()[:8]}"

            description = f"Code Repository Analysis: {repo_name}\n"
            description += f"Category: {category}\n"
            description += f"Stars: {repo_info.get('stargazers_count', 0)}\n"
            description += f"Language: {repo_info.get('language', 'Unknown')}\n\n"

            description += "Key Insights:\n"
            for i, insight in enumerate(insights[:5], 1):
                description += f"{i}. {insight}\n"

            description += "\nArchitectural Patterns:\n"
            for i, pattern in enumerate(patterns, 1):
                description += f"{i}. {pattern}\n"

            await self.memory.store_execution(
                task_id=task_id,
                task_description=description,
                code=f"# Analysis of {repo_name}\n# {repo_info.get('description', '')}",
                result={'success': True, 'type': 'repository_analysis'},
                metadata={
                    'type': 'repository_analysis',
                    'repository': repo_name,
                    'category': category,
                    'stars': repo_info.get('stargazers_count', 0),
                    'language': repo_info.get('language', 'Unknown'),
                    'insights_count': len(insights),
                    'patterns_count': len(patterns),
                    'learning_source': 'code_repository_analysis'
                }
            )

            logger.info(f"Stored analysis of {repo_name}")

        except Exception as e:
            logger.error(f"Error storing repo analysis: {e}")

    async def analyze_trending_repositories(self, language: str = 'python') -> Dict[str, Any]:
        """
        Analyze trending repositories on GitHub

        Args:
            language: Programming language filter

        Returns:
            Analysis report
        """
        logger.info(f"Analyzing trending {language} repositories")

        report = {
            'language': language,
            'started_at': datetime.utcnow().isoformat(),
            'repositories_analyzed': 0,
            'total_insights': 0,
            'insights': []
        }

        try:
            # Search for trending repos
            url = f"https://api.github.com/search/repositories"
            params = {
                'q': f'language:{language} stars:>1000',
                'sort': 'stars',
                'order': 'desc',
                'per_page': 5
            }

            headers = {'Accept': 'application/vnd.github.v3+json'}
            if self.github_token:
                headers['Authorization'] = f'token {self.github_token}'

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()

                        for repo in data.get('items', [])[:3]:  # Analyze top 3
                            repo_name = repo['full_name']

                            analysis = await self.analyze_repository(repo_name, 'trending')

                            if analysis.get('success'):
                                report['repositories_analyzed'] += 1
                                insights = analysis.get('insights', [])
                                report['total_insights'] += len(insights)
                                report['insights'].extend(insights[:3])  # Top 3 from each

                            # Rate limiting
                            await asyncio.sleep(3)

        except Exception as e:
            logger.error(f"Error analyzing trending repos: {e}")
            report['error'] = str(e)

        report['completed_at'] = datetime.utcnow().isoformat()
        report['success'] = report['repositories_analyzed'] > 0

        return report

    def get_analysis_stats(self) -> Dict[str, Any]:
        """
        Get repository analysis statistics

        Returns:
            Statistics dictionary
        """
        category_counts = {}
        for analysis in self.analyzed_repos:
            category = analysis['category']
            category_counts[category] = category_counts.get(category, 0) + 1

        return {
            'total_repos_analyzed': len(self.analyzed_repos),
            'categories_covered': list(category_counts.keys()),
            'repos_per_category': category_counts,
            'recent_analyses': self.analyzed_repos[-5:]  # Last 5
        }
