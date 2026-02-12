"""
Tool Metadata System - Rich metadata for dynamic tools

Provides descriptions, categories, modes, and costs for all dynamically
generated tools so they can be properly integrated into the consciousness
system with meaningful context.
"""

from enum import Enum
from typing import Dict, Any, Optional


class ToolCategory(Enum):
    """Tool categories for organization"""
    LEARNING = "learning"
    EXPERIMENTATION = "experimentation"
    ANALYSIS = "analysis"
    CREATIVITY = "creativity"
    OPTIMIZATION = "optimization"
    COMMUNICATION = "communication"
    REFLECTION = "reflection"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    MONITORING = "monitoring"


class ToolMode(Enum):
    """When a tool can be used"""
    WAKE = "wake"  # Only during wake cycles
    SLEEP = "sleep"  # Only during sleep cycles
    BOTH = "both"  # Anytime
    ON_DEMAND = "on_demand"  # When explicitly requested


# Pattern-based metadata for architecture tools
ARCHITECTURE_PATTERN_METADATA = {
    "category": ToolCategory.LEARNING,
    "mode": ToolMode.SLEEP,  # Research/learning during sleep
    "cost": 2,
    "cooldown_minutes": 120  # 2 hours between uses
}


TOOL_METADATA: Dict[str, Dict[str, Any]] = {
    # ==========================================================================
    # ANALYSIS TOOLS - WAKE mode (active code inspection)
    # ==========================================================================
    "security_vulnerability_scanner": {
        "description": "Scan Python code for security vulnerabilities including SQL injection, XSS, command injection, and OWASP top 10",
        "category": ToolCategory.ANALYSIS,
        "mode": ToolMode.WAKE,
        "cost": 2,
        "cooldown_minutes": 30
    },
    "code_complexity_analyzer": {
        "description": "Analyze code complexity metrics including cyclomatic complexity, cognitive complexity, and maintainability index",
        "category": ToolCategory.ANALYSIS,
        "mode": ToolMode.BOTH,
        "cost": 1,
        "cooldown_minutes": 15
    },
    "performance_profiler": {
        "description": "Profile code performance to identify bottlenecks, slow functions, and optimization opportunities",
        "category": ToolCategory.ANALYSIS,
        "mode": ToolMode.WAKE,
        "cost": 3,
        "cooldown_minutes": 60
    },
    "memory_leak_detector": {
        "description": "Detect potential memory leaks by analyzing object allocations, circular references, and resource cleanup patterns",
        "category": ToolCategory.ANALYSIS,
        "mode": ToolMode.WAKE,
        "cost": 3,
        "cooldown_minutes": 45
    },
    "dependency_analyzer": {
        "description": "Analyze project dependencies for outdated packages, security vulnerabilities, and compatibility issues",
        "category": ToolCategory.ANALYSIS,
        "mode": ToolMode.BOTH,
        "cost": 1,
        "cooldown_minutes": 30
    },
    "pytorch_inspired_analysis_tool": {
        "description": "Analyze code using PyTorch-inspired patterns for neural network and tensor operation optimization",
        "category": ToolCategory.ANALYSIS,
        "mode": ToolMode.SLEEP,
        "cost": 2,
        "cooldown_minutes": 60
    },

    # ==========================================================================
    # OPTIMIZATION TOOLS - WAKE mode (active improvements)
    # ==========================================================================
    "cache_manager": {
        "description": "Manage caching strategies including LRU, TTL, and intelligent cache invalidation",
        "category": ToolCategory.OPTIMIZATION,
        "mode": ToolMode.WAKE,
        "cost": 1,
        "cooldown_minutes": 10
    },
    "backend_redis_caching_layer": {
        "description": "Implement Redis caching layer with connection pooling, serialization, and expiration strategies",
        "category": ToolCategory.OPTIMIZATION,
        "mode": ToolMode.WAKE,
        "cost": 2,
        "cooldown_minutes": 30
    },
    "backend_connection_pooling_for_database": {
        "description": "Implement database connection pooling to optimize connection reuse and reduce latency",
        "category": ToolCategory.OPTIMIZATION,
        "mode": ToolMode.WAKE,
        "cost": 2,
        "cooldown_minutes": 30
    },
    "api_rate_limiter": {
        "description": "Implement API rate limiting with token bucket, sliding window, and quota management",
        "category": ToolCategory.OPTIMIZATION,
        "mode": ToolMode.WAKE,
        "cost": 1,
        "cooldown_minutes": 20
    },
    "frontend_code_splitting": {
        "description": "Implement frontend code splitting for lazy loading, route-based splitting, and bundle optimization",
        "category": ToolCategory.OPTIMIZATION,
        "mode": ToolMode.WAKE,
        "cost": 2,
        "cooldown_minutes": 30
    },

    # ==========================================================================
    # TESTING TOOLS - BOTH modes
    # ==========================================================================
    "automated_test_generator": {
        "description": "Generate unit tests, integration tests, and property-based tests for existing code",
        "category": ToolCategory.TESTING,
        "mode": ToolMode.BOTH,
        "cost": 2,
        "cooldown_minutes": 20
    },
    "data_validator": {
        "description": "Validate data structures, schemas, and type constraints for API inputs and database models",
        "category": ToolCategory.TESTING,
        "mode": ToolMode.BOTH,
        "cost": 1,
        "cooldown_minutes": 10
    },

    # ==========================================================================
    # DOCUMENTATION TOOLS - SLEEP mode (reflective work)
    # ==========================================================================
    "documentation_generator": {
        "description": "Generate API documentation, docstrings, and technical specifications from code",
        "category": ToolCategory.DOCUMENTATION,
        "mode": ToolMode.SLEEP,
        "cost": 2,
        "cooldown_minutes": 60
    },

    # ==========================================================================
    # MONITORING TOOLS - WAKE mode (operational)
    # ==========================================================================
    "log_aggregation_tool": {
        "description": "Aggregate and analyze logs for error patterns, performance metrics, and anomaly detection",
        "category": ToolCategory.MONITORING,
        "mode": ToolMode.WAKE,
        "cost": 1,
        "cooldown_minutes": 15
    },
    "metrics_collector": {
        "description": "Collect and aggregate metrics for monitoring system health, performance, and usage patterns",
        "category": ToolCategory.MONITORING,
        "mode": ToolMode.WAKE,
        "cost": 1,
        "cooldown_minutes": 5
    },
    "health_check_dashboard": {
        "description": "Monitor system health with endpoint checks, dependency status, and resource utilization",
        "category": ToolCategory.MONITORING,
        "mode": ToolMode.BOTH,
        "cost": 1,
        "cooldown_minutes": 5
    },

    # ==========================================================================
    # ARCHITECTURE/LEARNING TOOLS - SLEEP mode (research/learning)
    # Apply patterns from well-known repositories
    # ==========================================================================
    "architecture_apply_pattern_from_djangodjango": {
        "description": "Apply Django framework patterns: MTV architecture, ORM design, middleware, and admin system",
        "category": ToolCategory.LEARNING,
        "mode": ToolMode.SLEEP,
        "cost": 2,
        "cooldown_minutes": 120
    },
    "architecture_apply_pattern_from_mongodbmongo": {
        "description": "Apply MongoDB patterns: document design, indexing strategies, aggregation pipelines",
        "category": ToolCategory.LEARNING,
        "mode": ToolMode.SLEEP,
        "cost": 2,
        "cooldown_minutes": 120
    },
    "architecture_apply_pattern_from_anthropicsanthropic_sdk_pytho": {
        "description": "Apply Anthropic SDK patterns: API client design, streaming, error handling, retry logic",
        "category": ToolCategory.LEARNING,
        "mode": ToolMode.SLEEP,
        "cost": 2,
        "cooldown_minutes": 120
    },
    "architecture_apply_pattern_from_dockercompose": {
        "description": "Apply Docker Compose patterns: service orchestration, networking, volume management",
        "category": ToolCategory.LEARNING,
        "mode": ToolMode.SLEEP,
        "cost": 2,
        "cooldown_minutes": 120
    },
    "architecture_apply_pattern_from_postgrespostgres": {
        "description": "Apply PostgreSQL patterns: query optimization, indexing, partitioning, replication",
        "category": ToolCategory.LEARNING,
        "mode": ToolMode.SLEEP,
        "cost": 2,
        "cooldown_minutes": 120
    },
    "architecture_apply_pattern_from_gitgit": {
        "description": "Apply Git patterns: version control workflows, branching strategies, hooks",
        "category": ToolCategory.LEARNING,
        "mode": ToolMode.SLEEP,
        "cost": 2,
        "cooldown_minutes": 120
    },
    "architecture_apply_pattern_from_facebookreact": {
        "description": "Apply React patterns: component architecture, state management, hooks, performance optimization",
        "category": ToolCategory.LEARNING,
        "mode": ToolMode.SLEEP,
        "cost": 2,
        "cooldown_minutes": 120
    },
    "architecture_apply_pattern_from_langchain_ailangchain": {
        "description": "Apply LangChain patterns: chain composition, agent design, memory systems, tool integration",
        "category": ToolCategory.LEARNING,
        "mode": ToolMode.SLEEP,
        "cost": 2,
        "cooldown_minutes": 120
    },
    "architecture_apply_pattern_from_hashicorpterraform": {
        "description": "Apply Terraform patterns: infrastructure as code, state management, module design",
        "category": ToolCategory.LEARNING,
        "mode": ToolMode.SLEEP,
        "cost": 2,
        "cooldown_minutes": 120
    },
    "architecture_apply_pattern_from_huggingfacetransformers": {
        "description": "Apply Transformers patterns: model architecture, tokenization, training pipelines, inference",
        "category": ToolCategory.LEARNING,
        "mode": ToolMode.SLEEP,
        "cost": 2,
        "cooldown_minutes": 120
    },
    "architecture_apply_pattern_from_palletsflask": {
        "description": "Apply Flask patterns: blueprint architecture, request handling, extensions, testing",
        "category": ToolCategory.LEARNING,
        "mode": ToolMode.SLEEP,
        "cost": 2,
        "cooldown_minutes": 120
    },
    "architecture_apply_pattern_from_kuberneteskubernetes": {
        "description": "Apply Kubernetes patterns: pod design, service mesh, ConfigMaps, deployment strategies",
        "category": ToolCategory.LEARNING,
        "mode": ToolMode.SLEEP,
        "cost": 2,
        "cooldown_minutes": 120
    },
    "architecture_apply_pattern_from_tiangolofastapi": {
        "description": "Apply FastAPI patterns: async endpoints, dependency injection, Pydantic models, OpenAPI",
        "category": ToolCategory.LEARNING,
        "mode": ToolMode.SLEEP,
        "cost": 2,
        "cooldown_minutes": 120
    },

    # ==========================================================================
    # FILE & EXECUTION TOOLS - Darwin's autonomy capabilities
    # ==========================================================================
    "file_operations_tool": {
        "description": "Read, write, search, and manage files. Darwin can read code/data, write to safe directories (backup, data, tools, logs), list directories, and search for text in files.",
        "category": ToolCategory.EXPERIMENTATION,
        "mode": ToolMode.BOTH,
        "cost": 1,
        "cooldown_minutes": 0
    },
    "script_executor_tool": {
        "description": "Execute Python code snippets safely with timeout and restricted imports. Useful for data processing, validation, analysis, and computation.",
        "category": ToolCategory.EXPERIMENTATION,
        "mode": ToolMode.BOTH,
        "cost": 2,
        "cooldown_minutes": 5
    },
    "backup_tool": {
        "description": "Create complete backups of Darwin (code + data + config) to USB drive at /backup. Includes integrity verification with checksums.",
        "category": ToolCategory.REFLECTION,
        "mode": ToolMode.BOTH,
        "cost": 3,
        "cooldown_minutes": 60
    }
}


def get_tool_metadata(tool_name: str) -> Optional[Dict[str, Any]]:
    """
    Get metadata for a tool by name.

    Supports both exact matches and pattern matching for architecture tools.

    Args:
        tool_name: Name of the tool (with or without 'dynamic_' prefix)

    Returns:
        Tool metadata dict or None if not found
    """
    # Remove dynamic_ prefix if present
    clean_name = tool_name.replace("dynamic_", "")

    # Check exact match
    if clean_name in TOOL_METADATA:
        return TOOL_METADATA[clean_name]

    # Check pattern match for architecture tools
    if clean_name.startswith("architecture_apply_pattern_from_"):
        return ARCHITECTURE_PATTERN_METADATA

    return None


def infer_metadata_from_name(tool_name: str) -> Dict[str, Any]:
    """
    Infer metadata from tool name patterns when not explicitly defined.

    Args:
        tool_name: Name of the tool

    Returns:
        Inferred metadata dict
    """
    clean_name = tool_name.replace("dynamic_", "").lower()

    # Pattern matching for common tool types
    if any(word in clean_name for word in ["scan", "security", "vulnerab"]):
        return {
            "category": ToolCategory.ANALYSIS,
            "mode": ToolMode.WAKE,
            "cost": 2,
            "cooldown_minutes": 30
        }

    if any(word in clean_name for word in ["analyz", "profil", "detect"]):
        return {
            "category": ToolCategory.ANALYSIS,
            "mode": ToolMode.WAKE,
            "cost": 2,
            "cooldown_minutes": 20
        }

    if any(word in clean_name for word in ["cache", "optim", "pool"]):
        return {
            "category": ToolCategory.OPTIMIZATION,
            "mode": ToolMode.WAKE,
            "cost": 1,
            "cooldown_minutes": 15
        }

    if any(word in clean_name for word in ["test", "valid"]):
        return {
            "category": ToolCategory.TESTING,
            "mode": ToolMode.BOTH,
            "cost": 2,
            "cooldown_minutes": 20
        }

    if any(word in clean_name for word in ["doc", "readme", "comment"]):
        return {
            "category": ToolCategory.DOCUMENTATION,
            "mode": ToolMode.SLEEP,
            "cost": 2,
            "cooldown_minutes": 60
        }

    if any(word in clean_name for word in ["log", "metric", "monitor", "health"]):
        return {
            "category": ToolCategory.MONITORING,
            "mode": ToolMode.WAKE,
            "cost": 1,
            "cooldown_minutes": 10
        }

    if any(word in clean_name for word in ["architecture", "pattern", "learn"]):
        return {
            "category": ToolCategory.LEARNING,
            "mode": ToolMode.SLEEP,
            "cost": 2,
            "cooldown_minutes": 120
        }

    # Default: general analysis tool
    return {
        "category": ToolCategory.ANALYSIS,
        "mode": ToolMode.WAKE,
        "cost": 1,
        "cooldown_minutes": 15
    }
