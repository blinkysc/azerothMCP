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
Spell tools for AzerothCore MCP Server.
"""

import json

from ..db import execute_query
from ..config import ENABLE_SPELL_DBC

# Import SAI comment generator for spell lookups
try:
    from sai_comment_generator import SaiCommentGenerator
    SAI_GENERATOR_AVAILABLE = True
except ImportError:
    SAI_GENERATOR_AVAILABLE = False
    SaiCommentGenerator = None


def register_spell_tools(mcp):
    """Register spell-related tools with the MCP server."""

    # Only register spell_dbc search if enabled
    if ENABLE_SPELL_DBC:
        @mcp.tool()
        def search_spells(name_or_id: str, limit: int = 20) -> str:
            """
            Search for spells by name or ID in spell_dbc (custom spells only).

            Args:
                name_or_id: Spell name pattern or ID number
                limit: Maximum results

            Returns:
                Matching spells
            """
            try:
                if name_or_id.isdigit():
                    results = execute_query(
                        "SELECT ID, SpellName, Description FROM spell_dbc WHERE ID = %s",
                        "world",
                        (int(name_or_id),)
                    )
                else:
                    results = execute_query(
                        f"SELECT ID, SpellName, Description FROM spell_dbc WHERE SpellName LIKE %s LIMIT {min(limit, 100)}",
                        "world",
                        (f"%{name_or_id}%",)
                    )
                return json.dumps(results, indent=2, default=str)
            except Exception as e:
                return json.dumps({"error": str(e)})

    @mcp.tool()
    def get_spell_name(spell_id: int) -> str:
        """
        Get a spell name from Keira3's sqlite database.

        This uses the offline spell database bundled with Keira3, which contains
        all spell names from the WoW 3.3.5a client data.

        Args:
            spell_id: The spell ID to look up

        Returns:
            Spell name and ID
        """
        if not SAI_GENERATOR_AVAILABLE:
            return json.dumps({"error": "SAI comment generator not available"})

        try:
            generator = SaiCommentGenerator()
            name = generator.get_spell_name(spell_id)
            return json.dumps({
                "spell_id": spell_id,
                "spell_name": name
            }, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    def lookup_spell_names(spell_ids: str) -> str:
        """
        Look up multiple spell names at once from Keira3's sqlite database.

        Args:
            spell_ids: Comma-separated list of spell IDs (e.g. "1234,5678,9012")

        Returns:
            Dictionary mapping spell IDs to names
        """
        if not SAI_GENERATOR_AVAILABLE:
            return json.dumps({"error": "SAI comment generator not available"})

        try:
            generator = SaiCommentGenerator()
            ids = [int(x.strip()) for x in spell_ids.split(",") if x.strip().isdigit()]

            results = {}
            for spell_id in ids:
                results[spell_id] = generator.get_spell_name(spell_id)

            return json.dumps(results, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})
