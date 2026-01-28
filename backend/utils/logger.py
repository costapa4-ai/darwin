"""Logging configuration for Darwin System"""
import logging
import json
from datetime import datetime
from pathlib import Path


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        if hasattr(record, "task_id"):
            log_data["task_id"] = record.task_id

        return json.dumps(log_data)


def setup_logger(name: str) -> logging.Logger:
    """Setup logger with JSON formatting"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(JSONFormatter())
    logger.addHandler(console_handler)

    # File handler
    log_dir = Path("/app/logs")
    log_dir.mkdir(exist_ok=True)
    file_handler = logging.FileHandler(log_dir / "darwin.log")
    file_handler.setFormatter(JSONFormatter())
    logger.addHandler(file_handler)

    return logger


# Alias for compatibility
get_logger = setup_logger
