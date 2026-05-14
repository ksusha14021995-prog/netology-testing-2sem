"""Logging middleware: decorator @logged that captures function calls,
results, and re-raises ValueError/KeyError after logging.

Structured JSON logging — each record is a single line of valid JSON,
ready to be ingested by ELK/Loki/Datadog without regex parsing.
"""
from __future__ import annotations

import functools
import json
import logging
import sys
import traceback
from datetime import datetime
from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


class JsonFormatter(logging.Formatter):
    """Render each LogRecord as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        extra = getattr(record, "extra_payload", None)
        if isinstance(extra, dict):
            payload.update(extra)
        if record.exc_info:
            exc_type, exc_value, _ = record.exc_info
            payload["error"] = {
                "type": exc_type.__name__ if exc_type else None,
                "message": str(exc_value) if exc_value is not None else None,
                "traceback": traceback.format_exception(*record.exc_info),
            }
        return json.dumps(payload, ensure_ascii=False, default=str)


def setup_logger(name: str = "app", level: int = logging.INFO) -> logging.Logger:
    """Configure (once) and return a JSON-formatted logger by name."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
    logger.propagate = False
    return logger


def logged(logger_name: str = "app") -> Callable[[F], F]:
    """Decorator factory: log call args, result, and re-raise ValueError/KeyError
    after logging them as ERROR with traceback.

    Usage:
        @logged("booking")
        def create_booking(event_id: int, user_id: int) -> dict: ...
    """

    def decorator(func: F) -> F:
        logger = setup_logger(logger_name)

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            call_payload = {
                "function": func.__qualname__,
                "args": [repr(a) for a in args],
                "kwargs": {k: repr(v) for k, v in kwargs.items()},
            }
            logger.info(
                "call %s",
                func.__qualname__,
                extra={"extra_payload": {**call_payload, "event": "call"}},
            )
            try:
                result = func(*args, **kwargs)
            except (ValueError, KeyError) as exc:
                logger.error(
                    "%s raised %s: %s",
                    func.__qualname__,
                    type(exc).__name__,
                    exc,
                    exc_info=True,
                    extra={
                        "extra_payload": {
                            **call_payload,
                            "event": "error",
                            "error_type": type(exc).__name__,
                        }
                    },
                )
                raise
            logger.info(
                "ok %s",
                func.__qualname__,
                extra={
                    "extra_payload": {
                        **call_payload,
                        "event": "ok",
                        "result_type": type(result).__name__,
                        "result_repr": repr(result)[:200],
                    }
                },
            )
            return result

        return wrapper  # type: ignore[return-value]

    return decorator
