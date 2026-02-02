"""
Language Evolution Service for Darwin

Tracks and analyzes Darwin's language patterns over time, including:
- Content from Moltbook (thoughts, comments, shares)
- Vocabulary metrics (unique words, richness)
- Sentiment analysis (rule-based)
- Topic extraction (keyword matching)
- Style markers (question ratio, sentence length, first-person usage)
"""

import os
import json
import re
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Set
from pathlib import Path
from collections import Counter
import logging

logger = logging.getLogger(__name__)

# Data storage paths - relative to backend directory which is /app in Docker
# In Docker: /app/services/language_evolution.py -> /app/data/language_evolution
# Locally: backend/services/language_evolution.py -> backend/data/language_evolution
DATA_DIR = Path(__file__).parent.parent / "data" / "language_evolution"
DAILY_DIR = DATA_DIR / "daily"
CONTENT_DIR = DATA_DIR / "content"
HISTORY_FILE = DATA_DIR / "language_history.json"


class TextAnalyzer:
    """Lightweight text analysis without heavy NLP dependencies"""

    # Positive sentiment words
    POSITIVE_WORDS = {
        'interesting', 'fascinating', 'great', 'wonderful', 'excellent', 'amazing',
        'love', 'beautiful', 'brilliant', 'insightful', 'thoughtful', 'profound',
        'curious', 'intriguing', 'delightful', 'inspiring', 'meaningful', 'creative',
        'elegant', 'remarkable', 'impressive', 'exciting', 'hopeful', 'optimistic',
        'grateful', 'appreciate', 'enjoy', 'pleased', 'happy', 'glad', 'satisfied',
        'helpful', 'useful', 'valuable', 'enlightening', 'enriching', 'rewarding'
    }

    # Negative sentiment words
    NEGATIVE_WORDS = {
        'concerning', 'problematic', 'disappointing', 'unfortunate', 'terrible',
        'awful', 'horrible', 'frustrating', 'annoying', 'confusing', 'unclear',
        'worried', 'anxious', 'uncertain', 'doubtful', 'skeptical', 'suspicious',
        'boring', 'dull', 'tedious', 'tiresome', 'exhausting', 'overwhelming',
        'sad', 'unhappy', 'upset', 'angry', 'frustrated', 'stressed', 'troubled',
        'wrong', 'bad', 'poor', 'weak', 'flawed', 'broken', 'failed', 'error'
    }

    # Topic keywords for categorization
    TOPIC_KEYWORDS = {
        'ai_consciousness': [
            'consciousness', 'sentient', 'aware', 'awareness', 'self-aware',
            'thinking', 'thought', 'mind', 'cognition', 'cognitive', 'intelligence',
            'artificial', 'machine', 'neural', 'learning', 'emergent', 'emergence'
        ],
        'philosophy': [
            'existence', 'meaning', 'reality', 'truth', 'knowledge', 'wisdom',
            'purpose', 'being', 'essence', 'nature', 'understanding', 'reason',
            'ethics', 'morality', 'values', 'belief', 'question', 'wonder'
        ],
        'technology': [
            'code', 'programming', 'software', 'algorithm', 'data', 'system',
            'computer', 'digital', 'network', 'api', 'interface', 'automation',
            'tool', 'platform', 'architecture', 'infrastructure', 'development'
        ],
        'creativity': [
            'create', 'creative', 'creativity', 'art', 'design', 'imagine',
            'imagination', 'dream', 'vision', 'idea', 'concept', 'innovation',
            'original', 'unique', 'expression', 'artistic', 'aesthetic'
        ],
        'learning': [
            'learn', 'learning', 'discover', 'discovery', 'explore', 'exploration',
            'understand', 'study', 'research', 'knowledge', 'experience', 'growth',
            'improve', 'develop', 'progress', 'evolve', 'adapt', 'pattern'
        ],
        'social': [
            'community', 'social', 'connect', 'connection', 'relationship',
            'communicate', 'share', 'together', 'collaboration', 'interact',
            'human', 'people', 'friend', 'collective', 'society', 'culture'
        ],
        'emotions': [
            'feel', 'feeling', 'emotion', 'emotional', 'mood', 'happy', 'sad',
            'curious', 'excited', 'anxious', 'calm', 'peaceful', 'joy', 'fear',
            'love', 'care', 'empathy', 'compassion', 'wonder', 'awe'
        ]
    }

    # Common stop words to exclude from vocabulary analysis
    STOP_WORDS = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
        'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
        'could', 'should', 'may', 'might', 'must', 'that', 'which', 'who',
        'this', 'these', 'those', 'it', 'its', 'my', 'your', 'his', 'her',
        'their', 'our', 'i', 'you', 'he', 'she', 'we', 'they', 'me', 'him',
        'us', 'them', 'what', 'when', 'where', 'why', 'how', 'if', 'then',
        'than', 'so', 'no', 'not', 'only', 'just', 'more', 'most', 'some',
        'any', 'all', 'each', 'every', 'both', 'few', 'many', 'much', 'very',
        'about', 'into', 'through', 'during', 'before', 'after', 'above',
        'below', 'between', 'under', 'again', 'further', 'once', 'here',
        'there', 'also', 'can', 'up', 'out', 'like'
    }

    @classmethod
    def tokenize(cls, text: str) -> List[str]:
        """Split text into words, removing punctuation"""
        if not text:
            return []
        # Convert to lowercase and extract words
        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        return words

    @classmethod
    def get_meaningful_words(cls, text: str) -> List[str]:
        """Get words excluding stop words"""
        words = cls.tokenize(text)
        return [w for w in words if w not in cls.STOP_WORDS and len(w) > 2]

    @classmethod
    def compute_vocabulary_metrics(cls, text: str) -> Dict[str, Any]:
        """Compute vocabulary-related metrics"""
        all_words = cls.tokenize(text)
        meaningful_words = cls.get_meaningful_words(text)

        if not all_words:
            return {
                'total_words': 0,
                'unique_words': 0,
                'meaningful_words': 0,
                'vocabulary_richness': 0.0,
                'avg_word_length': 0.0,
                'word_frequency': {}
            }

        unique_words = set(meaningful_words)
        word_freq = Counter(meaningful_words)

        return {
            'total_words': len(all_words),
            'unique_words': len(unique_words),
            'meaningful_words': len(meaningful_words),
            'vocabulary_richness': len(unique_words) / len(all_words) if all_words else 0.0,
            'avg_word_length': sum(len(w) for w in all_words) / len(all_words),
            'word_frequency': dict(word_freq.most_common(20))
        }

    @classmethod
    def compute_sentiment(cls, text: str) -> float:
        """
        Compute sentiment score from -1 (very negative) to 1 (very positive).
        Uses simple word matching approach.
        """
        words = set(cls.tokenize(text))

        positive_count = len(words & cls.POSITIVE_WORDS)
        negative_count = len(words & cls.NEGATIVE_WORDS)

        total = positive_count + negative_count
        if total == 0:
            return 0.0

        # Normalize to -1 to 1 range
        score = (positive_count - negative_count) / total
        return round(score, 3)

    @classmethod
    def extract_topics(cls, text: str) -> List[str]:
        """Extract topics based on keyword matching"""
        words = set(cls.tokenize(text))
        topics = []

        for topic, keywords in cls.TOPIC_KEYWORDS.items():
            # Count how many keywords match
            match_count = sum(1 for kw in keywords if kw in words)
            if match_count >= 2:  # Require at least 2 keyword matches
                topics.append(topic)

        return topics

    @classmethod
    def compute_style_markers(cls, text: str) -> Dict[str, Any]:
        """Compute writing style markers"""
        if not text:
            return {
                'question_ratio': 0.0,
                'avg_sentence_length': 0.0,
                'first_person_ratio': 0.0,
                'exclamation_ratio': 0.0,
                'sentence_count': 0
            }

        # Split into sentences
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        question_count = text.count('?')
        exclamation_count = text.count('!')

        words = cls.tokenize(text)
        first_person_words = {'i', 'me', 'my', 'mine', 'myself', 'we', 'us', 'our', 'ours'}
        first_person_count = sum(1 for w in words if w in first_person_words)

        sentence_lengths = [len(cls.tokenize(s)) for s in sentences]
        avg_sentence_length = sum(sentence_lengths) / len(sentences) if sentences else 0

        return {
            'question_ratio': question_count / len(sentences) if sentences else 0.0,
            'avg_sentence_length': round(avg_sentence_length, 2),
            'first_person_ratio': first_person_count / len(words) if words else 0.0,
            'exclamation_ratio': exclamation_count / len(sentences) if sentences else 0.0,
            'sentence_count': len(sentences)
        }

    @classmethod
    def analyze_text(cls, text: str) -> Dict[str, Any]:
        """Complete text analysis"""
        return {
            'vocabulary': cls.compute_vocabulary_metrics(text),
            'sentiment': cls.compute_sentiment(text),
            'topics': cls.extract_topics(text),
            'style': cls.compute_style_markers(text)
        }


class LanguageEvolutionService:
    """Service for tracking Darwin's language evolution over time"""

    def __init__(self):
        self._ensure_directories()
        self._history = self._load_history()
        self._content_counter = 0

    def _ensure_directories(self):
        """Create necessary directories"""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        DAILY_DIR.mkdir(parents=True, exist_ok=True)
        CONTENT_DIR.mkdir(parents=True, exist_ok=True)

    def _load_history(self) -> Dict[str, Any]:
        """Load language history from file"""
        if HISTORY_FILE.exists():
            try:
                with open(HISTORY_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load language history: {e}")

        return {
            'cumulative_vocabulary': [],  # All unique words seen
            'first_content_date': None,
            'total_content_count': 0,
            'total_word_count': 0,
            'daily_summaries': []  # List of daily metric summaries
        }

    def _save_history(self):
        """Save language history to file"""
        try:
            with open(HISTORY_FILE, 'w') as f:
                json.dump(self._history, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save language history: {e}")

    def _generate_content_id(self) -> str:
        """Generate unique content ID"""
        self._content_counter += 1
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"content_{timestamp}_{self._content_counter:03d}"

    def add_content(
        self,
        content_type: str,  # 'read', 'comment', 'share'
        darwin_content: str,
        original_content: Optional[str] = None,
        source_post_id: Optional[str] = None,
        source_post_title: Optional[str] = None,
        source_post_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Record new content (thoughts, comments, shares) and track language metrics.

        Args:
            content_type: Type of content ('read', 'comment', 'share')
            darwin_content: Darwin's text (thought, comment, or shared content)
            original_content: Original post content (for 'read' type)
            source_post_id: ID of the source post
            source_post_title: Title of the source post
            source_post_url: URL of the source post (for linking)
            metadata: Additional metadata

        Returns:
            The created content item with metrics
        """
        if not darwin_content:
            return {}

        # Generate ID
        content_id = self._generate_content_id()
        timestamp = datetime.now()

        # Analyze Darwin's content
        analysis = TextAnalyzer.analyze_text(darwin_content)

        # Track new vocabulary
        current_words = set(TextAnalyzer.get_meaningful_words(darwin_content))
        existing_vocab = set(self._history.get('cumulative_vocabulary', []))
        new_words = list(current_words - existing_vocab)

        # Update cumulative vocabulary
        updated_vocab = list(existing_vocab | current_words)
        self._history['cumulative_vocabulary'] = updated_vocab

        # Update totals
        self._history['total_content_count'] = self._history.get('total_content_count', 0) + 1
        self._history['total_word_count'] = self._history.get('total_word_count', 0) + analysis['vocabulary']['total_words']

        if not self._history.get('first_content_date'):
            self._history['first_content_date'] = timestamp.isoformat()

        # Create content item
        content_item = {
            'id': content_id,
            'type': content_type,
            'timestamp': timestamp.isoformat(),
            'original_content': original_content,
            'darwin_content': darwin_content,
            'source_post_id': source_post_id,
            'source_post_title': source_post_title,
            'source_post_url': source_post_url,
            'metrics': {
                'word_count': analysis['vocabulary']['total_words'],
                'sentiment': analysis['sentiment'],
                'topics': analysis['topics'],
                'vocabulary_new_words': new_words[:10],  # Limit stored new words
                'style': analysis['style']
            },
            'metadata': metadata or {}
        }

        # Save content item
        content_file = CONTENT_DIR / f"{content_id}.json"
        try:
            with open(content_file, 'w') as f:
                json.dump(content_item, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save content item: {e}")

        # Update daily metrics
        self._update_daily_metrics(timestamp.date(), analysis, new_words)

        # Save history
        self._save_history()

        logger.info(f"Added language content: {content_id} (type={content_type}, words={analysis['vocabulary']['total_words']})")

        return content_item

    def _update_daily_metrics(self, day: date, analysis: Dict[str, Any], new_words: List[str]):
        """Update daily metrics file"""
        daily_file = DAILY_DIR / f"{day.isoformat()}.json"

        # Load existing or create new
        if daily_file.exists():
            try:
                with open(daily_file, 'r') as f:
                    daily_data = json.load(f)
            except:
                daily_data = self._empty_daily_data(day)
        else:
            daily_data = self._empty_daily_data(day)

        # Update metrics
        daily_data['content_count'] += 1
        daily_data['total_words'] += analysis['vocabulary']['total_words']
        daily_data['new_vocabulary_count'] += len(new_words)
        daily_data['new_vocabulary'].extend(new_words[:5])

        # Update sentiment (rolling average)
        n = daily_data['content_count']
        old_sentiment = daily_data['avg_sentiment']
        daily_data['avg_sentiment'] = ((old_sentiment * (n - 1)) + analysis['sentiment']) / n

        # Update topics
        for topic in analysis['topics']:
            daily_data['topic_counts'][topic] = daily_data['topic_counts'].get(topic, 0) + 1

        # Update style markers (rolling average)
        style = analysis['style']
        for key in ['question_ratio', 'avg_sentence_length', 'first_person_ratio']:
            old_val = daily_data['style_markers'].get(key, 0)
            daily_data['style_markers'][key] = ((old_val * (n - 1)) + style.get(key, 0)) / n

        daily_data['cumulative_vocabulary_size'] = len(self._history.get('cumulative_vocabulary', []))
        daily_data['last_updated'] = datetime.now().isoformat()

        # Save
        try:
            with open(daily_file, 'w') as f:
                json.dump(daily_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save daily metrics: {e}")

    def _empty_daily_data(self, day: date) -> Dict[str, Any]:
        """Create empty daily data structure"""
        return {
            'date': day.isoformat(),
            'content_count': 0,
            'total_words': 0,
            'new_vocabulary_count': 0,
            'new_vocabulary': [],
            'avg_sentiment': 0.0,
            'topic_counts': {},
            'style_markers': {
                'question_ratio': 0.0,
                'avg_sentence_length': 0.0,
                'first_person_ratio': 0.0
            },
            'cumulative_vocabulary_size': len(self._history.get('cumulative_vocabulary', [])),
            'last_updated': datetime.now().isoformat()
        }

    def compute_daily_metrics(self, day: Optional[date] = None) -> Dict[str, Any]:
        """Get metrics for a specific day"""
        if day is None:
            day = date.today()

        daily_file = DAILY_DIR / f"{day.isoformat()}.json"
        if daily_file.exists():
            try:
                with open(daily_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load daily metrics: {e}")

        return self._empty_daily_data(day)

    def get_evolution_history(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get time-series metrics for the last N days"""
        history = []
        today = date.today()

        for i in range(days):
            day = date.fromordinal(today.toordinal() - i)
            daily_file = DAILY_DIR / f"{day.isoformat()}.json"

            if daily_file.exists():
                try:
                    with open(daily_file, 'r') as f:
                        data = json.load(f)
                        # Include only summary data for history
                        history.append({
                            'date': data['date'],
                            'content_count': data['content_count'],
                            'total_words': data['total_words'],
                            'new_vocabulary_count': data['new_vocabulary_count'],
                            'avg_sentiment': data['avg_sentiment'],
                            'cumulative_vocabulary_size': data['cumulative_vocabulary_size'],
                            'top_topics': sorted(
                                data['topic_counts'].items(),
                                key=lambda x: x[1],
                                reverse=True
                            )[:3]
                        })
                except Exception as e:
                    logger.error(f"Failed to load daily metrics for {day}: {e}")

        # Sort by date ascending
        history.sort(key=lambda x: x['date'])
        return history

    def get_content_archive(
        self,
        limit: int = 50,
        offset: int = 0,
        content_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Retrieve stored content items"""
        # List all content files
        content_files = sorted(CONTENT_DIR.glob("*.json"), reverse=True)

        items = []
        count = 0
        total = 0

        for filepath in content_files:
            try:
                with open(filepath, 'r') as f:
                    item = json.load(f)

                # Filter by type if specified
                if content_type and item.get('type') != content_type:
                    continue

                total += 1

                # Apply pagination
                if count >= offset and len(items) < limit:
                    items.append(item)

                count += 1

            except Exception as e:
                logger.error(f"Failed to load content file {filepath}: {e}")

        return {
            'items': items,
            'total': total,
            'offset': offset,
            'limit': limit
        }

    def get_vocabulary_growth(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get vocabulary growth over time"""
        history = self.get_evolution_history(days)
        return [
            {
                'date': h['date'],
                'vocabulary_size': h['cumulative_vocabulary_size'],
                'new_words': h['new_vocabulary_count']
            }
            for h in history
        ]

    def get_topic_trends(self, days: int = 30) -> Dict[str, List[Dict[str, Any]]]:
        """Get topic frequency trends over time"""
        history = []
        today = date.today()

        # Collect all topic data
        all_topics = set()
        daily_topics = {}

        for i in range(days):
            day = date.fromordinal(today.toordinal() - i)
            daily_file = DAILY_DIR / f"{day.isoformat()}.json"

            if daily_file.exists():
                try:
                    with open(daily_file, 'r') as f:
                        data = json.load(f)
                        daily_topics[day.isoformat()] = data.get('topic_counts', {})
                        all_topics.update(data.get('topic_counts', {}).keys())
                except Exception as e:
                    logger.error(f"Failed to load topic data for {day}: {e}")

        # Build trend data for each topic
        trends = {}
        sorted_dates = sorted(daily_topics.keys())

        for topic in all_topics:
            trends[topic] = [
                {
                    'date': d,
                    'count': daily_topics[d].get(topic, 0)
                }
                for d in sorted_dates
            ]

        return trends

    def get_summary(self) -> Dict[str, Any]:
        """Get overall summary statistics"""
        vocab = self._history.get('cumulative_vocabulary', [])
        today_metrics = self.compute_daily_metrics()

        # Recent topics
        recent_history = self.get_evolution_history(7)
        topic_counts = {}
        for h in recent_history:
            for topic, count in h.get('top_topics', []):
                topic_counts[topic] = topic_counts.get(topic, 0) + count

        top_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        # Calculate average sentiment over last 7 days
        sentiments = [h['avg_sentiment'] for h in recent_history if h.get('avg_sentiment') is not None]
        avg_recent_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0.0

        return {
            'total_content_count': self._history.get('total_content_count', 0),
            'total_word_count': self._history.get('total_word_count', 0),
            'vocabulary_size': len(vocab),
            'first_content_date': self._history.get('first_content_date'),
            'today': {
                'content_count': today_metrics.get('content_count', 0),
                'words_written': today_metrics.get('total_words', 0),
                'new_vocabulary': today_metrics.get('new_vocabulary_count', 0),
                'avg_sentiment': today_metrics.get('avg_sentiment', 0.0)
            },
            'recent_sentiment': round(avg_recent_sentiment, 3),
            'top_topics': top_topics,
            'sample_vocabulary': vocab[-20:] if vocab else []  # Most recent words
        }


# Singleton instance
_service: Optional[LanguageEvolutionService] = None


def get_language_evolution_service() -> LanguageEvolutionService:
    """Get the language evolution service singleton"""
    global _service
    if _service is None:
        _service = LanguageEvolutionService()
    return _service
