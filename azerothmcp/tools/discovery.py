#!/usr/bin/env python3
"""
Progressive Disclosure - Tool Discovery Layer
Minimal tool catalog for navigation only.
"""

import json
from ..config import ENABLE_WIKI, ENABLE_SOURCE_CODE

# Minimal tool catalog - just categories and basic info
def _get_tool_catalog():
    """Build tool catalog based on enabled features."""
    catalog = {
        "database": {
            "description": "SQL queries and schema inspection",
            "tools": ["query_database", "get_table_schema", "list_tables"]
        },
        "creatures": {
            "description": "NPC/creature data and search",
            "tools": ["get_creature_template", "search_creatures", "get_creature_with_scripts"]
        },
        "smartai": {
            "description": "SmartAI scripting system",
            "tools": [
                "get_smart_scripts", "explain_smart_script", "list_smart_event_types",
                "list_smart_action_types", "list_smart_target_types", "trace_script_chain",
                "get_smartai_source", "generate_sai_comments", "generate_comment_for_script",
                "generate_comments_for_scripts_batch"
            ]
        },
        "conditions": {
            "description": "Database conditions for loot, gossip, quests, etc.",
            "tools": [
                "get_conditions", "explain_condition", "diagnose_conditions",
                "search_conditions", "list_condition_types", "list_condition_source_types"
            ]
        },
        "quests": {
            "description": "Quest data and diagnostics",
            "tools": ["get_quest_template", "search_quests", "diagnose_quest"]
        },
        "gameobjects": {
            "description": "GameObject data and search",
            "tools": ["get_gameobject_template", "search_gameobjects"]
        },
        "items": {
            "description": "Item data and search",
            "tools": ["get_item_template", "search_items"]
        },
        "spells": {
            "description": "Spell lookups from offline database",
            "tools": ["get_spell_name", "lookup_spell_names", "search_spells"]
        },
        "waypoints": {
            "description": "Waypoint paths and visualization",
            "tools": [
                "get_waypoint_path", "get_creature_waypoints", "search_waypoint_paths",
                "visualize_waypoints", "visualize_waypoints_3d"
            ]
        },
        "soap": {
            "description": "Live server GM commands via SOAP",
            "tools": ["soap_execute_command", "soap_server_info", "soap_reload_table", "soap_check_connection"]
        }
    }

    # Add optional categories if enabled
    if ENABLE_WIKI:
        catalog["wiki"] = {
            "description": "AzerothCore wiki documentation",
            "tools": ["search_wiki", "read_wiki_page"]
        }

    if ENABLE_SOURCE_CODE:
        catalog["source"] = {
            "description": "C++ source code search and reading",
            "tools": ["search_azerothcore_source", "read_source_file"]
        }

    return catalog


def register_discovery_tools(mcp):
    """Register minimal tool discovery."""

    @mcp.tool()
    def list_tool_categories() -> str:
        """List all available tool categories."""
        TOOL_CATALOG = _get_tool_catalog()
        categories = [
            {
                "category": cat,
                "description": info["description"],
                "tool_count": len(info["tools"])
            }
            for cat, info in TOOL_CATALOG.items()
        ]
        return json.dumps(categories, indent=2)

    @mcp.tool()
    def list_tools_in_category(category: str) -> str:
        """List tools in a specific category."""
        TOOL_CATALOG = _get_tool_catalog()
        if category not in TOOL_CATALOG:
            return json.dumps({
                "error": f"Unknown category '{category}'",
                "available": list(TOOL_CATALOG.keys())
            })

        return json.dumps({
            "category": category,
            "description": TOOL_CATALOG[category]["description"],
            "tools": TOOL_CATALOG[category]["tools"]
        }, indent=2)

    @mcp.tool()
    def search_tools(query: str) -> str:
        """Search for tools by keyword."""
        TOOL_CATALOG = _get_tool_catalog()
        query_lower = query.lower()
        results = []

        for category, info in TOOL_CATALOG.items():
            if query_lower in category.lower() or query_lower in info["description"].lower():
                results.append({
                    "category": category,
                    "description": info["description"],
                    "tools": info["tools"]
                })

        return json.dumps({
            "query": query,
            "matches": len(results),
            "results": results
        }, indent=2)
