#!/usr/bin/env python3
"""Creature/NPC tools"""

import json
import time

from ..db import execute_query
from ..config import LOG_TOOL_CALLS
from .smartai import add_sai_comments

if LOG_TOOL_CALLS:
    from ..logging import tool_logger


def register_creature_tools(mcp):
    """Register creature-related tools."""

    @mcp.tool()
    def get_creature_template(entry: int, full: bool = False) -> str:
        """Get creature_template data (compacted by default, use full=True for all 61 fields)."""
        start_time = time.time()
        error = None
        result = None
        try:
            results = execute_query(
                "SELECT * FROM creature_template WHERE entry = %s",
                "world",
                (entry,)
            )
            if not results:
                result = json.dumps({"error": f"No creature found with entry {entry}"})
                return result

            creature = results[0]

            if full:
                result = json.dumps(creature, indent=2, default=str)
                return result

            # Return essential fields only (61 → ~15)
            compact = {
                "entry": creature["entry"],
                "name": creature["name"],
                "subname": creature.get("subname"),
                "level": f"{creature['minlevel']}-{creature['maxlevel']}",
                "faction": creature["faction"],
                "type": creature["type"],
                "rank": creature["rank"],
                "AIName": creature.get("AIName"),
                "ScriptName": creature.get("ScriptName"),
            }

            # Add optional fields only if non-zero/non-empty
            if creature.get("npcflag"):
                compact["npcflag"] = creature["npcflag"]
            if creature.get("gossip_menu_id"):
                compact["gossip_menu_id"] = creature["gossip_menu_id"]
            if creature.get("lootid"):
                compact["lootid"] = creature["lootid"]
            if creature.get("trainer_type"):
                compact["trainer_type"] = creature["trainer_type"]

            compact["_hint"] = "Use full=True for all 61 fields"
            result = json.dumps(compact, indent=2, default=str)
            return result
        except Exception as e:
            error = str(e)
            result = json.dumps({"error": error})
            return result
        finally:
            if LOG_TOOL_CALLS:
                tool_logger.log_tool_call(
                    tool_name="get_creature_template",
                    category="creatures",
                    params={"entry": entry, "full": full},
                    result=result,
                    duration=time.time() - start_time,
                    error=error,
                )

    @mcp.tool()
    def search_creatures(name_pattern: str, limit: int = 20) -> str:
        """Search for creatures by name pattern."""
        start_time = time.time()
        error = None
        result = None
        try:
            results = execute_query(
                f"SELECT entry, name, subname, minlevel, maxlevel FROM creature_template WHERE name LIKE %s LIMIT {min(limit, 100)}",
                "world",
                (f"%{name_pattern}%",)
            )
            result = json.dumps(results, indent=2, default=str)
            return result
        except Exception as e:
            error = str(e)
            result = json.dumps({"error": error})
            return result
        finally:
            if LOG_TOOL_CALLS:
                tool_logger.log_tool_call(
                    tool_name="search_creatures",
                    category="creatures",
                    params={"name_pattern": name_pattern, "limit": limit},
                    result=result,
                    duration=time.time() - start_time,
                    error=error,
                )

    @mcp.tool()
    def get_creature_with_scripts(entry: int) -> str:
        """Get creature template AND SmartAI scripts (compacted)."""
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

            # Compact creature info
            creature_compact = {
                "entry": entry,
                "name": creature_name,
                "subname": creature_data.get("subname"),
                "level": f"{creature_data['minlevel']}-{creature_data['maxlevel']}",
                "AIName": creature_data.get("AIName"),
            }

            ai_name = creature_data.get("AIName", "")
            if ai_name != "SmartAI":
                return json.dumps({
                    "creature": creature_compact,
                    "uses_smartai": False,
                    "note": f"Creature uses {ai_name or 'default AI'}, not SmartAI"
                })

            # Get scripts
            scripts = execute_query(
                "SELECT * FROM smart_scripts WHERE entryorguid = %s AND source_type = 0 ORDER BY id",
                "world",
                (entry,)
            )

            if not scripts:
                return json.dumps({
                    "creature": creature_compact,
                    "uses_smartai": True,
                    "smart_scripts": [],
                    "note": "No scripts found (creature has SmartAI but no scripts)"
                })

            # Compact scripts (33 fields → essentials + non-zero params)
            scripts_compact = []
            for script in scripts:
                compact = {
                    "id": script["id"],
                    "link": script["link"],
                    "event": script["event_type"],
                    "action": script["action_type"],
                    "target": script["target_type"],
                }

                # Add non-zero event params
                event_params = [script[f"event_param{i}"] for i in range(1, 7) if script[f"event_param{i}"]]
                if event_params:
                    compact["event_params"] = event_params

                # Add non-zero action params
                action_params = [script[f"action_param{i}"] for i in range(1, 7) if script[f"action_param{i}"]]
                if action_params:
                    compact["action_params"] = action_params

                # Add non-zero target params
                target_params = [script[f"target_param{i}"] for i in range(1, 5) if script[f"target_param{i}"]]
                if target_params:
                    compact["target_params"] = target_params

                if script.get("comment"):
                    compact["comment"] = script["comment"]

                scripts_compact.append(compact)

            return json.dumps({
                "creature": creature_compact,
                "uses_smartai": True,
                "script_count": len(scripts_compact),
                "scripts": scripts_compact,
                "_hint": "Use get_smart_scripts() for full script details"
            }, indent=2, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})
