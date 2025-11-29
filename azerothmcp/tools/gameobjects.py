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
GameObject tools for AzerothCore MCP Server.
"""

import json

from ..db import execute_query


def register_gameobject_tools(mcp):
    """Register gameobject-related tools with the MCP server."""

    @mcp.tool()
    def get_gameobject_template(entry: int) -> str:
        """
        Get gameobject_template data by entry ID.

        Args:
            entry: The gameobject entry ID

        Returns:
            Complete gameobject template data
        """
        try:
            results = execute_query(
                "SELECT * FROM gameobject_template WHERE entry = %s",
                "world",
                (entry,)
            )
            if not results:
                return json.dumps({"error": f"No gameobject found with entry {entry}"})
            return json.dumps(results[0], indent=2, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    def search_gameobjects(name_pattern: str, limit: int = 20) -> str:
        """
        Search for gameobjects by name.

        Args:
            name_pattern: Name to search for (uses SQL LIKE)
            limit: Maximum results

        Returns:
            Matching gameobjects with entry, name, and type
        """
        try:
            results = execute_query(
                f"SELECT entry, name, type FROM gameobject_template WHERE name LIKE %s LIMIT {min(limit, 100)}",
                "world",
                (f"%{name_pattern}%",)
            )
            return json.dumps(results, indent=2, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})
