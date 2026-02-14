#!/usr/bin/env python3
"""Database tools"""

import json
import re
import time

from ..db import execute_query
from ..config import LOG_TOOL_CALLS

if LOG_TOOL_CALLS:
    from ..logging import tool_logger


def register_database_tools(mcp):
    """Register database-related tools."""

    @mcp.tool()
    def query_database(query: str, database: str = "world") -> str:
        """Execute SQL query on AzerothCore database (world/characters/auth)."""
        start_time = time.time()
        error = None
        result = None
        try:
            results = execute_query(query, database)
            # Limit results to prevent huge responses
            if len(results) > 100:
                result = json.dumps({
                    "warning": f"Query returned {len(results)} rows, showing first 100",
                    "results": results[:100],
                    "total_count": len(results)
                }, indent=2, default=str)
            else:
                result = json.dumps(results, indent=2, default=str)
            return result
        except Exception as e:
            error_str = str(e)
            error = error_str
            # Provide helpful hint for unknown column errors
            if "Unknown column" in error_str:
                # Try to extract table name from query
                table_match = re.search(r'FROM\s+`?(\w+)`?', query, re.IGNORECASE)
                table_hint = f" Use get_table_schema('{table_match.group(1)}') to see valid columns." if table_match else " Use get_table_schema() to check valid column names."
                result = json.dumps({
                    "error": error_str,
                    "hint": f"Column name not found.{table_hint}"
                })
            else:
                result = json.dumps({"error": error_str})
            return result
        finally:
            if LOG_TOOL_CALLS:
                tool_logger.log_tool_call(
                    tool_name="query_database",
                    category="database",
                    params={"query": query[:100], "database": database},
                    result=result,
                    duration=time.time() - start_time,
                    error=error,
                )

    @mcp.tool()
    def get_table_schema(table_name: str, database: str = "world") -> str:
        """Get column definitions for a database table."""
        start_time = time.time()
        error = None
        result = None
        try:
            results = execute_query(f"DESCRIBE `{table_name}`", database)
            result = json.dumps(results, indent=2)
            return result
        except Exception as e:
            error = str(e)
            result = json.dumps({"error": error})
            return result
        finally:
            if LOG_TOOL_CALLS:
                tool_logger.log_tool_call(
                    tool_name="get_table_schema",
                    category="database",
                    params={"table_name": table_name, "database": database},
                    result=result,
                    duration=time.time() - start_time,
                    error=error,
                )

    @mcp.tool()
    def list_tables(database: str = "world", filter_pattern: str = None) -> str:
        """List all tables in a database with optional filtering."""
        start_time = time.time()
        error = None
        result = None
        try:
            if filter_pattern:
                results = execute_query("SHOW TABLES LIKE %s", database, (filter_pattern,))
            else:
                results = execute_query("SHOW TABLES", database)

            # Extract table names from result dicts
            tables = [list(row.values())[0] for row in results]
            result = json.dumps(tables, indent=2)
            return result
        except Exception as e:
            error = str(e)
            result = json.dumps({"error": error})
            return result
        finally:
            if LOG_TOOL_CALLS:
                tool_logger.log_tool_call(
                    tool_name="list_tables",
                    category="database",
                    params={"database": database, "filter_pattern": filter_pattern},
                    result=result,
                    duration=time.time() - start_time,
                    error=error,
                )
