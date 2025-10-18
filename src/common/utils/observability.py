"""Observability: logging, callbacks, and tracing hooks."""

import sys
from typing import Any, Dict, List, Optional
from datetime import datetime
import json

from loguru import logger
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from src.config import get_config


def setup_logging(log_level: Optional[str] = None) -> None:
    """Setup loguru logging with proper formatting.
    
    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR). Uses config if None.
    """
    config = get_config()
    level = log_level or config.log_level
    
    # Remove default logger
    logger.remove()
    
    # Add custom format
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    # Add stdout handler
    logger.add(
        sys.stdout,
        format=log_format,
        level=level,
        colorize=True,
    )
    
    # Optionally add file handler
    logger.add(
        "logs/reppy_{time:YYYY-MM-DD}.log",
        format=log_format,
        level=level,
        rotation="1 day",
        retention="7 days",
        compression="zip",
    )
    
    logger.info(f"Logging initialized at level: {level}")


def setup_langsmith() -> None:
    """Setup LangSmith tracing if enabled in config."""
    config = get_config()
    
    if config.enable_langsmith and config.langsmith_api_key:
        import os
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = config.langsmith_api_key
        os.environ["LANGCHAIN_PROJECT"] = config.langsmith_project or "reppy-rag"
        logger.info(f"LangSmith tracing enabled for project: {config.langsmith_project}")
    else:
        logger.info("LangSmith tracing disabled")


class ReppyCallbackHandler(BaseCallbackHandler):
    """Custom callback handler for Reppy pipeline events."""
    
    def __init__(self, user_id: Optional[str] = None, session_id: Optional[str] = None):
        """Initialize callback handler.
        
        Args:
            user_id: Optional user ID for context.
            session_id: Optional session ID for tracking.
        """
        super().__init__()
        self.user_id = user_id
        self.session_id = session_id
        self.tool_calls: List[Dict[str, Any]] = []
        self.llm_calls: List[Dict[str, Any]] = []
        self.errors: List[Dict[str, Any]] = []
    
    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        **kwargs: Any,
    ) -> None:
        """Called when LLM starts running."""
        logger.debug(f"LLM started with {len(prompts)} prompt(s)")
        self.llm_calls.append({
            "event": "llm_start",
            "timestamp": datetime.utcnow().isoformat(),
            "prompt_count": len(prompts),
        })
    
    def on_llm_end(
        self,
        response: LLMResult,
        **kwargs: Any,
    ) -> None:
        """Called when LLM ends running."""
        logger.debug("LLM completed")
        self.llm_calls.append({
            "event": "llm_end",
            "timestamp": datetime.utcnow().isoformat(),
            "generation_count": len(response.generations),
        })
    
    def on_llm_error(
        self,
        error: Exception,
        **kwargs: Any,
    ) -> None:
        """Called when LLM errors."""
        logger.error(f"LLM error: {error}")
        self.errors.append({
            "event": "llm_error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(error),
        })
    
    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        **kwargs: Any,
    ) -> None:
        """Called when tool starts running."""
        tool_name = serialized.get("name", "unknown")
        logger.info(f"Tool started: {tool_name}")
        self.tool_calls.append({
            "event": "tool_start",
            "timestamp": datetime.utcnow().isoformat(),
            "tool_name": tool_name,
            "input": input_str,
        })
    
    def on_tool_end(
        self,
        output: str,
        **kwargs: Any,
    ) -> None:
        """Called when tool ends running."""
        logger.info("Tool completed")
        if self.tool_calls:
            self.tool_calls[-1]["event"] = "tool_end"
            self.tool_calls[-1]["output"] = output[:500]  # Truncate for logging
    
    def on_tool_error(
        self,
        error: Exception,
        **kwargs: Any,
    ) -> None:
        """Called when tool errors."""
        logger.error(f"Tool error: {error}")
        self.errors.append({
            "event": "tool_error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(error),
        })
    
    def on_agent_action(
        self,
        action: Any,
        **kwargs: Any,
    ) -> None:
        """Called when agent takes an action."""
        logger.info(f"Agent action: {action.tool}")
    
    def on_agent_finish(
        self,
        finish: Any,
        **kwargs: Any,
    ) -> None:
        """Called when agent finishes."""
        logger.info("Agent finished")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the callback events.
        
        Returns:
            Dict with summary statistics.
        """
        return {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "tool_calls_count": len([tc for tc in self.tool_calls if tc.get("event") == "tool_end"]),
            "llm_calls_count": len([lc for lc in self.llm_calls if lc.get("event") == "llm_end"]),
            "errors_count": len(self.errors),
            "tool_calls": self.tool_calls,
            "errors": self.errors,
        }


class MetricsCollector:
    """Collect metrics for monitoring and alerting."""
    
    def __init__(self):
        """Initialize metrics collector."""
        self.metrics: Dict[str, List[float]] = {}
    
    def record_latency(self, operation: str, latency_ms: float) -> None:
        """Record operation latency.
        
        Args:
            operation: Name of the operation.
            latency_ms: Latency in milliseconds.
        """
        if operation not in self.metrics:
            self.metrics[operation] = []
        self.metrics[operation].append(latency_ms)
        logger.debug(f"Recorded latency for {operation}: {latency_ms:.2f}ms")
    
    def get_stats(self, operation: str) -> Dict[str, float]:
        """Get statistics for an operation.
        
        Args:
            operation: Name of the operation.
            
        Returns:
            Dict with min, max, avg, count.
        """
        if operation not in self.metrics or not self.metrics[operation]:
            return {}
        
        values = self.metrics[operation]
        return {
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "count": len(values),
        }
    
    def clear(self) -> None:
        """Clear all metrics."""
        self.metrics.clear()


# Singleton instances
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get the singleton metrics collector.
    
    Returns:
        MetricsCollector instance.
    """
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


# Initialize logging on module import
try:
    setup_logging()
    setup_langsmith()
except Exception as e:
    print(f"Failed to initialize observability: {e}")

