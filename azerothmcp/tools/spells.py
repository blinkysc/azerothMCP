#!/usr/bin/env python3
"""Spell tools"""

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
    """Register spell-related tools."""

    # Only register spell_dbc search if enabled
    if ENABLE_SPELL_DBC:
        @mcp.tool()
        def search_spells(name_or_id: str, limit: int = 20) -> str:
            """Search for custom spells in spell_dbc by name or ID."""
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
        """Look up spell name by ID from Keira3's offline database."""
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
        """Batch lookup multiple spell names (comma-separated IDs)."""
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
