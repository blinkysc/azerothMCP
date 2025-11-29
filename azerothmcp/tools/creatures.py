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
Creature/NPC tools for AzerothCore MCP Server.
"""

import json

from ..db import execute_query
from .smartai import add_sai_comments


def register_creature_tools(mcp):
    """Register creature-related tools with the MCP server."""

    @mcp.tool()
    def get_creature_template(entry: int) -> str:
        """
        Get full creature_template data for an NPC by entry ID.

        Args:
            entry: The creature entry ID

        Returns:
            Complete creature template data including name, stats, flags, etc.
        """
        try:
            results = execute_query(
                "SELECT * FROM creature_template WHERE entry = %s",
                "world",
                (entry,)
            )
            if not results:
                return json.dumps({"error": f"No creature found with entry {entry}"})
            return json.dumps(results[0], indent=2, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    def search_creatures(name_pattern: str, limit: int = 20) -> str:
        """
        Search for creatures by name pattern.

        Args:
            name_pattern: Name to search for (uses SQL LIKE, so % is wildcard)
            limit: Maximum results to return (default 20)

        Returns:
            List of matching creatures with entry, name, and subname
        """
        try:
            results = execute_query(
                f"SELECT entry, name, subname, minlevel, maxlevel FROM creature_template WHERE name LIKE %s LIMIT {min(limit, 100)}",
                "world",
                (f"%{name_pattern}%",)
            )
            return json.dumps(results, indent=2, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    def get_creature_with_scripts(entry: int) -> str:
        """
        Get creature template AND its SmartAI scripts together.
        Useful for understanding a creature's complete behavior.
        Includes auto-generated human-readable comments for each script row.

        Args:
            entry: Creature entry ID

        Returns:
            Combined creature template data and SmartAI scripts with generated comments
        """
        try:
            creature = execute_query(
                "SELECT * FROM creature_template WHERE entry = %s",
                "world",
                (entry,)
            )

            if not creature:
                return json.dumps({"error": f"No creature found with entry {entry}"})

            creature_data = creature[0]
            creature_name = creature_data.get("name", f"Creature {entry}")

            # Check if creature uses SmartAI
            ai_name = creature_data.get("AIName", "")

            scripts = []
            if ai_name == "SmartAI":
                scripts = execute_query(
                    "SELECT * FROM smart_scripts WHERE entryorguid = %s AND source_type = 0 ORDER BY id",
                    "world",
                    (entry,)
                )
                # Add Keira3-style comments
                scripts = add_sai_comments(scripts, creature_name)

            # Also check for timed action lists referenced by this creature
            timed_lists = []
            for script in scripts:
                action_type = script.get("action_type")
                # Action type 80 = SMART_ACTION_CALL_TIMED_ACTIONLIST
                if action_type == 80:
                    list_id = script.get("action_param1")
                    if list_id:
                        timed_scripts = execute_query(
                            "SELECT * FROM smart_scripts WHERE entryorguid = %s AND source_type = 9 ORDER BY id",
                            "world",
                            (list_id,)
                        )
                        if timed_scripts:
                            # Add comments to timed action list scripts too
                            timed_scripts = add_sai_comments(timed_scripts, creature_name)
                            timed_lists.append({
                                "list_id": list_id,
                                "scripts": timed_scripts
                            })

            return json.dumps({
                "creature_template": creature_data,
                "uses_smart_ai": ai_name == "SmartAI",
                "smart_scripts": scripts,
                "timed_action_lists": timed_lists
            }, indent=2, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})
