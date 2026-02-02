"""
Language Evolution API Routes

Provides REST endpoints for accessing Darwin's language evolution data,
including metrics history, content archive, vocabulary growth, and topic trends.
"""

from datetime import date
from typing import Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import List, Dict, Any

from services.language_evolution import get_language_evolution_service, TextAnalyzer
from utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter(prefix="/api/v1/language-evolution", tags=["language-evolution"])


# Response Models

class DailyMetricsResponse(BaseModel):
    date: str
    content_count: int
    total_words: int
    new_vocabulary_count: int
    avg_sentiment: float
    topic_counts: Dict[str, int]
    style_markers: Dict[str, float]
    cumulative_vocabulary_size: int


class ContentItemResponse(BaseModel):
    id: str
    type: str
    timestamp: str
    darwin_content: str
    original_content: Optional[str] = None
    source_post_id: Optional[str] = None
    source_post_title: Optional[str] = None
    metrics: Dict[str, Any]


class ContentArchiveResponse(BaseModel):
    items: List[ContentItemResponse]
    total: int
    offset: int
    limit: int


class SummaryResponse(BaseModel):
    total_content_count: int
    total_word_count: int
    vocabulary_size: int
    first_content_date: Optional[str] = None
    today: Dict[str, Any]
    recent_sentiment: float
    top_topics: List[tuple]
    sample_vocabulary: List[str]


class VocabularyGrowthItem(BaseModel):
    date: str
    vocabulary_size: int
    new_words: int


class HistoryItem(BaseModel):
    date: str
    content_count: int
    total_words: int
    new_vocabulary_count: int
    avg_sentiment: float
    cumulative_vocabulary_size: int
    top_topics: List[tuple]


# Endpoints

@router.get("/summary")
async def get_summary() -> Dict[str, Any]:
    """
    Get dashboard summary of Darwin's language evolution.

    Returns overall statistics including:
    - Total content count and word count
    - Vocabulary size
    - Today's metrics
    - Recent sentiment trend
    - Top topics
    """
    service = get_language_evolution_service()
    return service.get_summary()


@router.get("/metrics/history")
async def get_metrics_history(
    days: int = Query(default=30, ge=1, le=365, description="Number of days of history")
) -> List[Dict[str, Any]]:
    """
    Get time-series metrics for language evolution.

    Returns daily metrics for the specified number of days, including:
    - Content count and word count per day
    - New vocabulary added
    - Average sentiment
    - Cumulative vocabulary size
    - Top topics for each day
    """
    service = get_language_evolution_service()
    return service.get_evolution_history(days)


@router.get("/metrics/today")
async def get_today_metrics() -> Dict[str, Any]:
    """
    Get today's language metrics.

    Returns detailed metrics for the current day including:
    - Content count and total words
    - New vocabulary
    - Average sentiment
    - Topic distribution
    - Style markers
    """
    service = get_language_evolution_service()
    return service.compute_daily_metrics()


@router.get("/content")
async def get_content_archive(
    limit: int = Query(default=50, ge=1, le=200, description="Maximum items to return"),
    offset: int = Query(default=0, ge=0, description="Number of items to skip"),
    type: Optional[str] = Query(default=None, description="Filter by content type (read, comment, share)")
) -> Dict[str, Any]:
    """
    Get Darwin's content archive (thoughts, comments, shares).

    Returns paginated list of content items with their metrics.
    Supports filtering by content type.
    """
    service = get_language_evolution_service()
    return service.get_content_archive(limit=limit, offset=offset, content_type=type)


@router.get("/vocabulary/growth")
async def get_vocabulary_growth(
    days: int = Query(default=30, ge=1, le=365, description="Number of days of history")
) -> List[Dict[str, Any]]:
    """
    Get vocabulary growth over time.

    Returns time-series data showing:
    - Cumulative vocabulary size per day
    - New words added per day
    """
    service = get_language_evolution_service()
    return service.get_vocabulary_growth(days)


@router.get("/topics/trends")
async def get_topic_trends(
    days: int = Query(default=30, ge=1, le=365, description="Number of days of history")
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Get topic frequency trends over time.

    Returns a dictionary where each key is a topic name and the value
    is a time-series of daily counts for that topic.
    """
    service = get_language_evolution_service()
    return service.get_topic_trends(days)


@router.post("/analyze")
async def analyze_text(text: str = Query(..., description="Text to analyze")) -> Dict[str, Any]:
    """
    Analyze a text sample using Darwin's language analysis.

    Useful for testing the analysis without recording content.
    Returns vocabulary metrics, sentiment, topics, and style markers.
    """
    return TextAnalyzer.analyze_text(text)


@router.get("/vocabulary/recent")
async def get_recent_vocabulary(
    limit: int = Query(default=50, ge=1, le=200, description="Number of words to return")
) -> Dict[str, Any]:
    """
    Get recently added vocabulary words.

    Returns the most recently added unique words to Darwin's vocabulary.
    """
    service = get_language_evolution_service()
    vocab = service._history.get('cumulative_vocabulary', [])

    return {
        'total_vocabulary_size': len(vocab),
        'recent_words': vocab[-limit:] if vocab else []
    }
