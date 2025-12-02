#!/usr/bin/env python3
#
# This file is part of the AzerothCore Project. See AUTHORS file for Copyright information
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <http://www.gnu.org/licenses/>.
#
"""
Logging infrastructure for observing AI tool usage.
Provides structured logging of all tool calls, parameters, and results.
"""

import logging
import json
import time
import functools
from datetime import datetime
from typing import Any, Callable

# ANSI color codes for terminal output
COLORS = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "red": "\033[91m",
    "green": "\033[92m",
    "yellow": "\033[93m",
    "blue": "\033[94m",
    "magenta": "\033[95m",
    "cyan": "\033[96m",
}

# Tool category colors for visual distinction
CATEGORY_COLORS = {
    "database": "blue",
    "creatures": "green",
    "smartai": "magenta",
    "conditions": "yellow",
    "quests": "cyan",
    "gameobjects": "green",
    "items": "yellow",
    "spells": "magenta",
    "waypoints": "blue",
    "soap": "red",
    "wiki": "cyan",
    "source": "dim",
    "sandbox": "red",
    "discovery": "dim",
}


def colorize(text: str, color: str) -> str:
    """Apply ANSI color to text."""
    return f"{COLORS.get(color, '')}{text}{COLORS['reset']}"


class ToolLogger:
    """Structured logger for MCP tool calls."""

    def __init__(self, name: str = "azerothmcp"):
        self.logger = logging.getLogger(name)
        self._setup_handler()
        self.call_count = 0
        self.total_time = 0.0

    def _setup_handler(self):
        """Configure console handler with custom formatting."""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(ToolLogFormatter())
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def log_tool_call(self, tool_name: str, category: str, params: dict,
                      result: Any, duration: float, error: str = None):
        """Log a tool call with all details."""
        self.call_count += 1
        self.total_time += duration

        log_data = {
            "call_id": self.call_count,
            "timestamp": datetime.now().isoformat(),
            "tool": tool_name,
            "category": category,
            "params": params,
            "duration_ms": round(duration * 1000, 2),
            "error": error,
            "result_size": len(str(result)) if result else 0,
        }

        if error:
            self.logger.error(json.dumps(log_data))
        else:
            self.logger.info(json.dumps(log_data))

    def log_sandbox_execution(self, code: str, queries_executed: list,
                               duration: float, error: str = None):
        """Log a sandbox code execution with query details."""
        self.call_count += 1
        self.total_time += duration

        log_data = {
            "call_id": self.call_count,
            "timestamp": datetime.now().isoformat(),
            "tool": "execute_investigation",
            "category": "sandbox",
            "code_lines": len(code.strip().split('\n')),
            "queries_executed": len(queries_executed),
            "query_details": queries_executed,
            "duration_ms": round(duration * 1000, 2),
            "error": error,
        }

        if error:
            self.logger.error(json.dumps(log_data))
        else:
            self.logger.info(json.dumps(log_data))

    def get_stats(self) -> dict:
        """Return cumulative statistics."""
        return {
            "total_calls": self.call_count,
            "total_time_ms": round(self.total_time * 1000, 2),
            "avg_time_ms": round((self.total_time / self.call_count) * 1000, 2) if self.call_count > 0 else 0,
        }


class ToolLogFormatter(logging.Formatter):
    """Custom formatter for readable tool call logs."""

    def format(self, record: logging.LogRecord) -> str:
        try:
            data = json.loads(record.getMessage())
            return self._format_tool_call(data, record.levelno)
        except (json.JSONDecodeError, KeyError):
            return super().format(record)

    def _format_tool_call(self, data: dict, level: int) -> str:
        """Format a tool call log entry."""
        category = data.get("category", "unknown")
        color = CATEGORY_COLORS.get(category, "reset")

        # Build the log line
        parts = []

        # Timestamp (dim)
        timestamp = datetime.fromisoformat(data["timestamp"]).strftime("%H:%M:%S.%f")[:-3]
        parts.append(colorize(f"[{timestamp}]", "dim"))

        # Call ID
        parts.append(colorize(f"#{data['call_id']:04d}", "bold"))

        # Category and tool name
        parts.append(colorize(f"[{category}]", color))
        parts.append(colorize(data["tool"], "bold"))

        # Parameters (truncated)
        params = data.get("params", {})
        if params:
            param_str = ", ".join(f"{k}={_truncate(v)}" for k, v in params.items())
            parts.append(f"({param_str})")

        # Duration
        duration = data.get("duration_ms", 0)
        duration_color = "green" if duration < 100 else "yellow" if duration < 500 else "red"
        parts.append(colorize(f"{duration}ms", duration_color))

        # Result size or error
        if data.get("error"):
            parts.append(colorize(f"ERROR: {data['error'][:50]}", "red"))
        else:
            result_size = data.get("result_size", 0)
            parts.append(colorize(f"→ {result_size} chars", "dim"))

        # Special handling for sandbox
        if data.get("queries_executed"):
            parts.append(colorize(f"[{data['queries_executed']} queries]", "cyan"))

        return " ".join(parts)


def _truncate(value: Any, max_len: int = 50) -> str:
    """Truncate value for display."""
    s = str(value)
    if len(s) > max_len:
        return s[:max_len-3] + "..."
    return s


# Global logger instance
tool_logger = ToolLogger()


def logged_tool(category: str):
    """Decorator to add logging to a tool function."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            error = None
            result = None

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                error = str(e)
                raise
            finally:
                duration = time.time() - start_time
                # Build params dict from args/kwargs
                params = kwargs.copy()
                tool_logger.log_tool_call(
                    tool_name=func.__name__,
                    category=category,
                    params=params,
                    result=result,
                    duration=duration,
                    error=error,
                )
        return wrapper
    return decorator
