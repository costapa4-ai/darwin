"""Configuration management for Darwin System"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with Phase 2 enhancements"""

    # AI Configuration
    claude_api_key: str = ""
    anthropic_api_key: str = ""  # Used by proactive engine (set ANTHROPIC_API_KEY in .env)
    gemini_api_key: str = ""
    openai_api_key: str = ""  # Phase 2: Optional OpenAI support
    ai_provider: str = "claude"
    claude_model: str = ""
    gemini_model: str = ""
    openai_model: str = ""  # Phase 2

    # Phase 2: Multi-Model Router
    enable_multi_model: bool = True
    routing_strategy: str = "tiered"  # performance, cost, speed, balanced, tiered

    # Ollama (Local LLM - FREE!)
    ollama_enabled: bool = True
    ollama_url: str = "http://ollama:11434"
    ollama_model: str = "llama3.2"  # or mistral, codellama, etc.

    # Phase 2: Semantic Memory & RAG
    enable_semantic_memory: bool = True
    enable_rag: bool = True
    chroma_persist_directory: str = "./data/chroma"

    # Phase 2: Web Research
    enable_web_research: bool = False  # Disabled by default (requires API keys)
    serpapi_api_key: str = ""
    github_token: str = ""

    # Phase 2: Meta-Learning
    enable_meta_learning: bool = True
    auto_optimize: bool = True
    optimization_interval_hours: int = 24

    # Phase 3: Multi-Agent System
    enable_multi_agent: bool = True
    default_agent_mode: str = "auto"  # auto, best, round_robin, specific name
    enable_collaborative_mode: bool = True
    collaboration_num_agents: int = 3

    # Phase 3: Dream Mode
    enable_dream_mode: bool = True
    dream_idle_threshold_minutes: int = 5
    dream_check_interval_seconds: int = 60
    dream_max_duration_minutes: int = 30

    # Phase 3: Code Poetry
    enable_code_poetry: bool = True
    enable_daily_diary: bool = True
    poetry_style: str = "narrative"  # haiku, narrative, technical

    # Phase 3: Curiosity Engine
    enable_curiosity: bool = True
    curiosity_level: float = 0.7  # 0.0 to 1.0

    # Phase 3: Auto-Benchmarking
    enable_auto_benchmark: bool = False  # Expensive, enable selectively

    # Rate Limits
    max_requests_per_minute: int = 10
    max_requests_per_day: int = 100
    max_api_calls_per_hour: int = 50

    # Security
    execution_timeout: int = 30
    max_memory_mb: int = 256
    allowed_modules: str = "os,sys,json,math,datetime,re,itertools,collections,functools"

    # Features
    enable_web_search: bool = True
    enable_auto_evolution: bool = True
    max_generations: int = 5
    population_size: int = 3

    # Infrastructure
    redis_url: str = "redis://redis:6379"
    database_url: str = "sqlite:///data/darwin.db"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
