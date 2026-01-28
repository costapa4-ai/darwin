"""
Documentation Reader - Official Documentation Learning System

Reads, analyzes, and learns from official documentation of frameworks,
libraries, and technologies.
"""

import aiohttp
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import hashlib
import re

from utils.logger import get_logger

logger = get_logger(__name__)


class DocumentationReader:
    """
    System for reading and learning from official documentation
    """

    def __init__(self, semantic_memory, multi_model_router):
        """
        Initialize documentation reader

        Args:
            semantic_memory: Semantic memory for storage
            multi_model_router: AI router for analysis
        """
        self.memory = semantic_memory
        self.ai_router = multi_model_router

        # Official documentation sources
        self.doc_sources = {
            'python': {
                'base_url': 'https://docs.python.org/3/',
                'topics': ['library', 'tutorial', 'reference', 'howto']
            },
            'fastapi': {
                'base_url': 'https://fastapi.tiangolo.com/',
                'topics': ['tutorial', 'advanced', 'deployment']
            },
            'docker': {
                'base_url': 'https://docs.docker.com/',
                'topics': ['engine', 'compose', 'swarm']
            },
            'kubernetes': {
                'base_url': 'https://kubernetes.io/docs/',
                'topics': ['concepts', 'tasks', 'tutorials']
            },
            'tensorflow': {
                'base_url': 'https://www.tensorflow.org/guide',
                'topics': ['keras', 'data', 'distribute']
            },
            'pytorch': {
                'base_url': 'https://pytorch.org/docs/stable/',
                'topics': ['tensors', 'nn', 'autograd']
            },
            'react': {
                'base_url': 'https://react.dev/',
                'topics': ['learn', 'reference', 'blog']
            },
            'typescript': {
                'base_url': 'https://www.typescriptlang.org/docs/',
                'topics': ['handbook', 'reference']
            },
            'redis': {
                'base_url': 'https://redis.io/docs/',
                'topics': ['commands', 'data-types', 'patterns']
            },
            'postgresql': {
                'base_url': 'https://www.postgresql.org/docs/current/',
                'topics': ['tutorial', 'sql', 'admin']
            }
        }

        self.docs_read = []

        logger.info("DocumentationReader initialized with {} sources".format(len(self.doc_sources)))

    async def read_random_documentation(self) -> Dict[str, Any]:
        """
        Read a random piece of documentation

        Returns:
            Reading report
        """
        import random

        # Select random technology and topic
        tech = random.choice(list(self.doc_sources.keys()))
        doc_info = self.doc_sources[tech]

        logger.info(f"Reading {tech} documentation...")

        report = {
            'technology': tech,
            'started_at': datetime.utcnow().isoformat(),
            'sections_read': 0,
            'insights_extracted': 0,
            'success': False
        }

        try:
            # Read documentation section
            result = await self._read_doc_section(tech, doc_info)

            if result['success']:
                report['sections_read'] = 1
                report['content_length'] = len(result.get('content', ''))

                # Extract learning insights
                insights = await self._extract_doc_insights(
                    result['content'],
                    tech,
                    result.get('url', '')
                )

                if insights:
                    report['insights_extracted'] = len(insights)
                    report['insights'] = insights

                    # Store in memory
                    await self._store_doc_knowledge(
                        tech,
                        result.get('url', ''),
                        result['content'],
                        insights
                    )

                report['success'] = True
                self.docs_read.append({
                    'tech': tech,
                    'timestamp': datetime.utcnow().isoformat(),
                    'url': result.get('url', '')
                })

        except Exception as e:
            logger.error(f"Error reading documentation: {e}")
            report['error'] = str(e)

        report['completed_at'] = datetime.utcnow().isoformat()
        return report

    async def _read_doc_section(self, tech: str, doc_info: Dict) -> Dict[str, Any]:
        """
        Read a documentation section

        Args:
            tech: Technology name
            doc_info: Documentation info

        Returns:
            Reading result
        """
        result = {
            'success': False,
            'tech': tech,
            'url': None,
            'content': None
        }

        try:
            base_url = doc_info['base_url']

            # Try to fetch documentation
            headers = {
                'User-Agent': 'Mozilla/5.0 (Darwin AI Bot) Documentation/1.0'
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    base_url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    if response.status == 200:
                        html = await response.text()

                        # Extract text content (simplified)
                        from bs4 import BeautifulSoup
                        soup = BeautifulSoup(html, 'html.parser')

                        # Remove scripts, styles
                        for element in soup(['script', 'style', 'nav', 'footer']):
                            element.decompose()

                        # Get main content
                        main_content = (
                            soup.find('main') or
                            soup.find('article') or
                            soup.find('div', class_=re.compile('content|docs|documentation', re.I)) or
                            soup.find('body')
                        )

                        if main_content:
                            text = main_content.get_text(separator='\n', strip=True)

                            # Clean up
                            lines = [line.strip() for line in text.split('\n') if line.strip()]
                            content = '\n'.join(lines)

                            # Limit length
                            result['content'] = content[:4000]
                            result['url'] = base_url
                            result['success'] = True

                            logger.info(f"Successfully read {tech} docs from {base_url}")
                    else:
                        logger.warning(f"Failed to fetch {base_url}: {response.status}")

        except Exception as e:
            logger.error(f"Error reading doc section: {e}")

        return result

    async def _extract_doc_insights(self,
                                   content: str,
                                   tech: str,
                                   url: str) -> List[str]:
        """
        Extract learning insights from documentation

        Args:
            content: Documentation content
            tech: Technology name
            url: Source URL

        Returns:
            List of insights
        """
        if not content or len(content) < 100:
            return []

        try:
            prompt = f"""Analyze this {tech} documentation and extract 3-5 key learnings or best practices.
Focus on:
- Important concepts
- Common patterns
- Best practices
- Performance tips
- Security considerations

Documentation excerpt:
{content[:2000]}

Provide 3-5 concise key learnings:"""

            result = await self.ai_router.generate(
                task_description=f"Extract insights from {tech} documentation",
                prompt=prompt,
                max_tokens=500
            )

            response_text = result.get('result', '') if isinstance(result, dict) else str(result)

            # Parse insights
            insights = []
            for line in response_text.split('\n'):
                line = line.strip('- •*123456789.').strip()
                if line and len(line) > 15:
                    insights.append(line)

            return insights[:5]

        except Exception as e:
            logger.error(f"Error extracting doc insights: {e}")
            return []

    async def _store_doc_knowledge(self,
                                  tech: str,
                                  url: str,
                                  content: str,
                                  insights: List[str]):
        """
        Store documentation knowledge in semantic memory

        Args:
            tech: Technology name
            url: Source URL
            content: Documentation content
            insights: Extracted insights
        """
        if not self.memory:
            return

        try:
            task_id = f"doc_reading_{tech}_{hashlib.md5(url.encode()).hexdigest()[:8]}"

            description = f"Documentation Reading: {tech}\n"
            description += f"Source: {url}\n\n"
            description += "Key Learnings:\n"

            for i, insight in enumerate(insights, 1):
                description += f"{i}. {insight}\n"

            await self.memory.store_execution(
                task_id=task_id,
                task_description=description,
                code=f"# {tech} documentation knowledge\n# Source: {url}\n\n{content[:500]}",
                result={'success': True, 'type': 'documentation_learning'},
                metadata={
                    'type': 'documentation_reading',
                    'technology': tech,
                    'source_url': url,
                    'insights_count': len(insights),
                    'learning_source': 'official_documentation'
                }
            )

            logger.info(f"Stored {tech} documentation knowledge")

        except Exception as e:
            logger.error(f"Error storing doc knowledge: {e}")

    async def read_technology_deep_dive(self, tech: str) -> Dict[str, Any]:
        """
        Perform a deep dive into a specific technology's documentation

        Args:
            tech: Technology to study

        Returns:
            Deep dive report
        """
        if tech not in self.doc_sources:
            logger.warning(f"Technology {tech} not in documentation sources")
            return {'success': False, 'error': 'Technology not found'}

        logger.info(f"Starting deep dive into {tech} documentation")

        report = {
            'technology': tech,
            'started_at': datetime.utcnow().isoformat(),
            'sections_read': 0,
            'total_insights': 0,
            'insights': []
        }

        # Read main documentation
        result = await self._read_doc_section(tech, self.doc_sources[tech])

        if result['success']:
            report['sections_read'] += 1

            insights = await self._extract_doc_insights(
                result['content'],
                tech,
                result['url']
            )

            if insights:
                report['total_insights'] = len(insights)
                report['insights'] = insights

                await self._store_doc_knowledge(
                    tech,
                    result['url'],
                    result['content'],
                    insights
                )

        report['completed_at'] = datetime.utcnow().isoformat()
        report['success'] = report['sections_read'] > 0

        return report

    async def learn_best_practices(self, domain: str) -> Dict[str, Any]:
        """
        Learn best practices across multiple technologies in a domain

        Args:
            domain: Domain to study (e.g., 'backend', 'frontend', 'ml')

        Returns:
            Learning report
        """
        domain_mapping = {
            'backend': ['python', 'fastapi', 'redis', 'postgresql'],
            'frontend': ['react', 'typescript'],
            'ml': ['tensorflow', 'pytorch'],
            'devops': ['docker', 'kubernetes']
        }

        technologies = domain_mapping.get(domain.lower(), [])

        if not technologies:
            return {'success': False, 'error': 'Domain not found'}

        logger.info(f"Learning {domain} best practices from {len(technologies)} technologies")

        report = {
            'domain': domain,
            'started_at': datetime.utcnow().isoformat(),
            'technologies_studied': [],
            'total_insights': 0,
            'cross_technology_insights': []
        }

        all_insights = []

        for tech in technologies:
            try:
                tech_report = await self.read_technology_deep_dive(tech)

                if tech_report.get('success'):
                    report['technologies_studied'].append(tech)
                    insights = tech_report.get('insights', [])
                    all_insights.extend(insights)
                    report['total_insights'] += len(insights)

                # Rate limiting
                await asyncio.sleep(2)

            except Exception as e:
                logger.error(f"Error studying {tech}: {e}")

        # Generate cross-technology insights
        if all_insights:
            cross_insights = await self._generate_cross_tech_insights(
                all_insights,
                domain,
                technologies
            )
            report['cross_technology_insights'] = cross_insights

        report['completed_at'] = datetime.utcnow().isoformat()
        report['success'] = len(report['technologies_studied']) > 0

        return report

    async def _generate_cross_tech_insights(self,
                                           insights: List[str],
                                           domain: str,
                                           technologies: List[str]) -> List[str]:
        """
        Generate cross-technology insights

        Args:
            insights: All collected insights
            domain: Domain name
            technologies: Technologies studied

        Returns:
            Cross-technology insights
        """
        try:
            prompt = f"""Based on documentation from {', '.join(technologies)} in the {domain} domain,
identify 3 common patterns or best practices that apply across these technologies.

Insights collected:
{chr(10).join(f"- {insight}" for insight in insights[:15])}

Provide 3 cross-technology insights or patterns:"""

            result = await self.ai_router.generate(
                task_description=f"Generate cross-technology insights for {domain}",
                prompt=prompt,
                max_tokens=400
            )

            response_text = result.get('result', '') if isinstance(result, dict) else str(result)

            # Parse insights
            cross_insights = []
            for line in response_text.split('\n'):
                line = line.strip('- •*123.').strip()
                if line and len(line) > 20:
                    cross_insights.append(line)

            return cross_insights[:3]

        except Exception as e:
            logger.error(f"Error generating cross-tech insights: {e}")
            return []

    def get_reading_stats(self) -> Dict[str, Any]:
        """
        Get documentation reading statistics

        Returns:
            Statistics dictionary
        """
        tech_counts = {}
        for doc in self.docs_read:
            tech = doc['tech']
            tech_counts[tech] = tech_counts.get(tech, 0) + 1

        return {
            'total_docs_read': len(self.docs_read),
            'technologies_covered': list(tech_counts.keys()),
            'reads_per_technology': tech_counts,
            'available_sources': list(self.doc_sources.keys())
        }
