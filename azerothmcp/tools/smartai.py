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
SmartAI tools for AzerothCore MCP Server
"""

import json

from ..db import execute_query
from ..config import AZEROTHCORE_SRC_PATH

# Import SAI comment generator (Keira3 port)
try:
    from sai_comment_generator import SaiCommentGenerator
    SAI_GENERATOR_AVAILABLE = True
except ImportError:
    SAI_GENERATOR_AVAILABLE = False
    SaiCommentGenerator = None


def _mysql_query_for_sai(query: str, database: str = "world"):
    """Wrapper for execute_query that returns results for SAI generator."""
    return execute_query(query, database)


def add_sai_comments(scripts: list, name: str) -> list:
    """Add Keira3-style comments to SmartAI scripts."""
    if not SAI_GENERATOR_AVAILABLE or not scripts:
        return scripts

    try:
        generator = SaiCommentGenerator(mysql_query_func=_mysql_query_for_sai)
        for script in scripts:
            script["_comment"] = generator.generate_comment(scripts, script, name)
        return scripts
    except Exception:
        return scripts


def get_entity_name(entryorguid: int, source_type: int) -> str:
    """Get entity name for SAI comment generation."""
    name = f"Entity {entryorguid}"
    try:
        if source_type == 0:  # Creature
            result = execute_query(
                "SELECT name FROM creature_template WHERE entry = %s",
                "world", (abs(entryorguid),)
            )
            if result:
                name = result[0].get("name", name)
        elif source_type == 1:  # GameObject
            result = execute_query(
                "SELECT name FROM gameobject_template WHERE entry = %s",
                "world", (abs(entryorguid),)
            )
            if result:
                name = result[0].get("name", name)
    except Exception:
        pass
    return name


def _load_smart_events():
    """Lazy load smart events reference data on-demand."""
    from ..data.smart_events import SMART_EVENTS
    return SMART_EVENTS


def _load_smart_actions():
    """Lazy load smart actions reference data on-demand."""
    from ..data.smart_actions import SMART_ACTIONS
    return SMART_ACTIONS


def _load_smart_targets():
    """Lazy load smart targets reference data on-demand."""
    from ..data.smart_targets import SMART_TARGETS
    return SMART_TARGETS


def register_smartai_tools(mcp):
    """Register SmartAI-related tools with the MCP server."""

    @mcp.tool()
    def get_smart_scripts(entryorguid: int, source_type: int = 0, full: bool = False) -> str:
        """Get SmartAI scripts (compacted by default, use full=True for all 33 fields)."""
        try:
            results = execute_query(
                """SELECT * FROM smart_scripts
                   WHERE entryorguid = %s AND source_type = %s
                   ORDER BY id""",
                "world",
                (entryorguid, source_type)
            )
            if not results:
                return json.dumps({
                    "message": f"No SmartAI scripts found for entryorguid={entryorguid}, source_type={source_type}",
                    "hint": "If this is a creature, check if it uses SmartAI (AIName='SmartAI' in creature_template)"
                })

            name = get_entity_name(entryorguid, source_type)

            if full:
                # Return full data with comments
                results = add_sai_comments(results, name)
                return json.dumps(results, indent=2, default=str)

            # Compact version (33 fields → essentials + non-zero params)
            compact_scripts = []
            for script in results:
                compact = {
                    "id": script["id"],
                    "link": script["link"] if script["link"] else None,
                    "event": script["event_type"],
                    "action": script["action_type"],
                    "target": script["target_type"],
                }

                # Add non-zero event params
                event_params = [script[f"event_param{i}"] for i in range(1, 7) if script.get(f"event_param{i}")]
                if event_params:
                    compact["event_params"] = event_params

                # Add non-zero action params
                action_params = [script[f"action_param{i}"] for i in range(1, 7) if script.get(f"action_param{i}")]
                if action_params:
                    compact["action_params"] = action_params

                # Add non-zero target params
                target_params = [script[f"target_param{i}"] for i in range(1, 5) if script.get(f"target_param{i}")]
                if target_params:
                    compact["target_params"] = target_params

                if script.get("comment"):
                    compact["comment"] = script["comment"]

                compact_scripts.append(compact)

            return json.dumps({
                "entity": {"entryorguid": entryorguid, "source_type": source_type, "name": name},
                "script_count": len(compact_scripts),
                "scripts": compact_scripts,
                "_hint": "Use full=True for all 33 fields per script"
            }, indent=2, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    def explain_smart_script(event_type: int = None, action_type: int = None, target_type: int = None) -> str:
        """Get documentation for SmartAI event/action/target types."""
        if not any([event_type is not None, action_type is not None, target_type is not None]):
            return json.dumps({
                "error": "Must specify at least one of: event_type, action_type, or target_type"
            })

        result = {}

        if event_type is not None:
            SMART_EVENTS = _load_smart_events()
            if event_type in SMART_EVENTS:
                result["event"] = {
                    "id": event_type,
                    **SMART_EVENTS[event_type]
                }
            else:
                result["event"] = {"error": f"Unknown event type {event_type}"}

        if action_type is not None:
            SMART_ACTIONS = _load_smart_actions()
            if action_type in SMART_ACTIONS:
                result["action"] = {
                    "id": action_type,
                    **SMART_ACTIONS[action_type]
                }
            else:
                result["action"] = {"error": f"Unknown action type {action_type}"}

        if target_type is not None:
            SMART_TARGETS = _load_smart_targets()
            if target_type in SMART_TARGETS:
                result["target"] = {
                    "id": target_type,
                    **SMART_TARGETS[target_type]
                }
            else:
                result["target"] = {"error": f"Unknown target type {target_type}"}

        return json.dumps(result, indent=2)

    @mcp.tool()
    def list_smart_event_types() -> str:
        """List all available SmartAI event types."""
        SMART_EVENTS = _load_smart_events()
        events = [
            {"id": k, "name": v["name"], "description": v["desc"]}
            for k, v in sorted(SMART_EVENTS.items())
        ]
        return json.dumps(events, indent=2)

    @mcp.tool()
    def list_smart_action_types() -> str:
        """List all available SmartAI action types."""
        SMART_ACTIONS = _load_smart_actions()
        actions = [
            {"id": k, "name": v["name"], "description": v["desc"]}
            for k, v in sorted(SMART_ACTIONS.items())
        ]
        return json.dumps(actions, indent=2)

    @mcp.tool()
    def list_smart_target_types() -> str:
        """List all available SmartAI target types."""
        SMART_TARGETS = _load_smart_targets()
        targets = [
            {"id": k, "name": v["name"], "description": v["desc"]}
            for k, v in sorted(SMART_TARGETS.items())
        ]
        return json.dumps(targets, indent=2)

    @mcp.tool()
    def trace_script_chain(entryorguid: int, source_type: int = 0) -> str:
        """Debug SmartAI execution flow with links and action lists."""
        try:
            # Get main scripts
            main_scripts = execute_query(
                """SELECT * FROM smart_scripts
                   WHERE entryorguid = %s AND source_type = %s
                   ORDER BY id""",
                "world",
                (entryorguid, source_type)
            )

            if not main_scripts:
                return json.dumps({
                    "message": f"No scripts found for entryorguid={entryorguid}, source_type={source_type}"
                })

            name = get_entity_name(entryorguid, source_type)
            main_scripts = add_sai_comments(main_scripts, name)

            # Build execution chain
            chain = []
            linked_scripts = {}
            action_lists = {}

            for script in main_scripts:
                script_info = {
                    "id": script["id"],
                    "comment": script.get("_comment", ""),
                    "event_type": script["event_type"],
                    "action_type": script["action_type"],
                    "link": script.get("link", 0)
                }

                # Check for timed action lists (action type 80)
                if script["action_type"] == 80:
                    list_id = script.get("action_param1")
                    if list_id and list_id not in action_lists:
                        action_list_scripts = execute_query(
                            """SELECT * FROM smart_scripts
                               WHERE entryorguid = %s AND source_type = 9
                               ORDER BY id""",
                            "world",
                            (list_id,)
                        )
                        if action_list_scripts:
                            action_list_scripts = add_sai_comments(action_list_scripts, name)
                            action_lists[list_id] = action_list_scripts
                            script_info["calls_action_list"] = list_id

                # Track links
                if script.get("link", 0) > 0:
                    script_info["links_to"] = script["link"]

                chain.append(script_info)

            result = {
                "entity": {
                    "entryorguid": entryorguid,
                    "source_type": source_type,
                    "name": name
                },
                "main_scripts": chain,
                "timed_action_lists": {
                    str(list_id): [
                        {
                            "id": s["id"],
                            "comment": s.get("_comment", ""),
                            "event_type": s["event_type"],
                            "action_type": s["action_type"]
                        }
                        for s in scripts
                    ]
                    for list_id, scripts in action_lists.items()
                }
            }

            return json.dumps(result, indent=2, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    def get_smartai_source(event_type: int = None, action_type: int = None, target_type: int = None) -> str:
        """Get C++ implementation from SmartScript.cpp."""
        if not AZEROTHCORE_SRC_PATH.exists():
            return json.dumps({
                "error": "AzerothCore source path not configured or not found",
                "hint": "Set AZEROTHCORE_SRC_PATH in your .env file"
            })

        if not any([event_type is not None, action_type is not None, target_type is not None]):
            return json.dumps({
                "error": "Must specify at least one of: event_type, action_type, or target_type"
            })

        smartscript_cpp = AZEROTHCORE_SRC_PATH / "src" / "server" / "game" / "AI" / "SmartScripts" / "SmartScript.cpp"
        if not smartscript_cpp.exists():
            return json.dumps({
                "error": f"SmartScript.cpp not found at {smartscript_cpp}"
            })

        try:
            import re

            with open(smartscript_cpp, 'r') as f:
                content = f.read()

            results = {}

            def find_case_block(prefix, type_id, ref_data, context_before=200, context_after=1500):
                """Find a case block by looking up the enum name from reference data."""
                # Get enum name from reference data
                enum_name = None
                if type_id in ref_data:
                    enum_name = ref_data[type_id].get("name")

                if enum_name:
                    # Search for exact enum name
                    pattern = rf"case {re.escape(enum_name)}\b"
                else:
                    # Fallback: search by prefix pattern
                    pattern = rf"case {prefix}[A-Z_]+:"

                match = re.search(pattern, content)
                if match:
                    start = max(0, match.start() - context_before)
                    end = min(len(content), match.end() + context_after)
                    return content[start:end]
                return None

            if event_type is not None:
                SMART_EVENTS = _load_smart_events()
                source = find_case_block("SMART_EVENT_", event_type, SMART_EVENTS, 200, 1000)
                results["event_source"] = source or f"Event type {event_type} not found in SmartScript.cpp"

            if action_type is not None:
                SMART_ACTIONS = _load_smart_actions()
                source = find_case_block("SMART_ACTION_", action_type, SMART_ACTIONS)
                results["action_source"] = source or f"Action type {action_type} not found in SmartScript.cpp"

            if target_type is not None:
                SMART_TARGETS = _load_smart_targets()
                source = find_case_block("SMART_TARGET_", target_type, SMART_TARGETS)
                results["target_source"] = source or f"Target type {target_type} not found in SmartScript.cpp"

            return json.dumps(results, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    def generate_sai_comments(entryorguid: int, source_type: int = 0) -> str:
        """Generate Keira3-style comments for scripts."""
        if not SAI_GENERATOR_AVAILABLE:
            return json.dumps({
                "error": "SAI comment generator not available",
                "hint": "Check sai_comment_generator.py installation"
            })

        try:
            scripts = execute_query(
                """SELECT * FROM smart_scripts
                   WHERE entryorguid = %s AND source_type = %s
                   ORDER BY id""",
                "world",
                (entryorguid, source_type)
            )

            if not scripts:
                return json.dumps({
                    "message": f"No scripts found for entryorguid={entryorguid}, source_type={source_type}"
                })

            name = get_entity_name(entryorguid, source_type)
            scripts_with_comments = add_sai_comments(scripts, name)

            return json.dumps(scripts_with_comments, indent=2, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    def generate_comment_for_script(script_dict: dict, entity_name: str) -> str:
        """Generate comment for a single new script row."""
        if not SAI_GENERATOR_AVAILABLE:
            return json.dumps({
                "error": "SAI comment generator not available"
            })

        try:
            generator = SaiCommentGenerator(mysql_query_func=_mysql_query_for_sai)
            comment = generator.generate_comment([script_dict], script_dict, entity_name)
            return json.dumps({"comment": comment})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    def generate_comments_for_scripts_batch(script_list: list, entity_name: str) -> str:
        """Generate comments for multiple script rows at once."""
        if not SAI_GENERATOR_AVAILABLE:
            return json.dumps({
                "error": "SAI comment generator not available"
            })

        try:
            generator = SaiCommentGenerator(mysql_query_func=_mysql_query_for_sai)
            for script in script_list:
                script["_comment"] = generator.generate_comment(script_list, script, entity_name)
            return json.dumps(script_list, indent=2, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})
