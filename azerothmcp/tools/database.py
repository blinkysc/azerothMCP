#!/usr/bin/env python3
"""Database tools"""

import json
import re

from ..db import execute_query


def register_database_tools(mcp):
    """Register database-related tools."""

    @mcp.tool()
    def query_database(query: str, database: str = "world") -> str:
        """Execute SQL query on AzerothCore database (world/characters/auth)."""
        try:
            results = execute_query(query, database)
            # Limit results to prevent huge responses
            if len(results) > 100:
                return json.dumps({
                    "warning": f"Query returned {len(results)} rows, showing first 100",
                    "results": results[:100],
                    "total_count": len(results)
                }, indent=2, default=str)
            return json.dumps(results, indent=2, default=str)
        except Exception as e:
            error_str = str(e)
            # Provide helpful hint for unknown column errors
            if "Unknown column" in error_str:
                # Try to extract table name from query
                table_match = re.search(r'FROM\s+`?(\w+)`?', query, re.IGNORECASE)
                table_hint = f" Use get_table_schema('{table_match.group(1)}') to see valid columns." if table_match else " Use get_table_schema() to check valid column names."
                return json.dumps({
                    "error": error_str,
                    "hint": f"Column name not found.{table_hint}"
                })
            return json.dumps({"error": error_str})

    @mcp.tool()
    def get_table_schema(table_name: str, database: str = "world") -> str:
        """Get column definitions for a database table."""
        try:
            results = execute_query(f"DESCRIBE `{table_name}`", database)
            return json.dumps(results, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    def list_tables(database: str = "world", filter_pattern: str = None) -> str:
        """List all tables in a database with optional filtering."""
        try:
            if filter_pattern:
                results = execute_query(f"SHOW TABLES LIKE '{filter_pattern}'", database)
            else:
                results = execute_query("SHOW TABLES", database)

            # Extract table names from result dicts
            tables = [list(row.values())[0] for row in results]
            return json.dumps(tables, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})
