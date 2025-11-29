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
Database tools for AzerothCore MCP Server.
"""

import json
import re

from ..db import execute_query


def register_database_tools(mcp):
    """Register database-related tools with the MCP server."""

    @mcp.tool()
    def query_database(query: str, database: str = "world") -> str:
        """
        Execute a SQL query against an AzerothCore database.

        Args:
            query: SQL query to execute
            database: Which database to query - 'world', 'characters', or 'auth'

        Returns:
            JSON string of query results (list of row dicts)

        IMPORTANT - Before querying unfamiliar tables:
            1. Use get_table_schema(table_name) to see the actual column names
            2. Do NOT assume column names - AzerothCore tables often use non-standard naming
               (e.g., 'entry' instead of 'id', 'guid' instead of 'id')
            3. Common primary keys: creature_template uses 'entry', areatrigger_scripts uses 'entry',
               smart_scripts uses 'entryorguid', characters uses 'guid'

        Notes:
            - Do NOT query spell_dbc for spell lookups. This table only contains custom spells,
              not standard WoW spells. Standard spell IDs are from the game client's DBC files.
            - If READ_ONLY=true (default), only SELECT/SHOW/DESCRIBE queries are allowed.

        Examples:
            - query_database("SELECT * FROM creature_template WHERE entry = 1234")
            - query_database("SELECT * FROM characters WHERE guid = 1", "characters")
        """
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
        """
        Get the schema/structure of a database table. ALWAYS use this before querying
        unfamiliar tables to discover the correct column names.

        Args:
            table_name: Name of the table to describe
            database: Which database - 'world', 'characters', or 'auth'

        Returns:
            Table column definitions including column names, types, and keys

        Usage:
            Call this BEFORE writing queries for tables you haven't queried before.
            AzerothCore tables use non-standard column names (e.g., 'entry' not 'id').
        """
        try:
            results = execute_query(f"DESCRIBE `{table_name}`", database)
            return json.dumps(results, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    def list_tables(database: str = "world", filter_pattern: str = None) -> str:
        """
        List all tables in a database, optionally filtered by pattern.

        Args:
            database: Which database - 'world', 'characters', or 'auth'
            filter_pattern: Optional SQL LIKE pattern (e.g., '%creature%')

        Returns:
            List of table names
        """
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
