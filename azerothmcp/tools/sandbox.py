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
Sandbox tool for programmatic multi-query investigations.

Implements "Programmatic Tool Calling" pattern from Anthropic's advanced tool use guide.
Allows Claude to write Python code that orchestrates multiple database queries,
reducing context window pollution and round-trip latency.
"""

import json
import time
import re
from typing import Any

from ..db import execute_query
from ..config import LOG_TOOL_CALLS

if LOG_TOOL_CALLS:
    from ..logging import tool_logger


# Restricted builtins for sandbox safety
SAFE_BUILTINS = {
    "len": len,
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "list": list,
    "dict": dict,
    "set": set,
    "tuple": tuple,
    "range": range,
    "enumerate": enumerate,
    "zip": zip,
    "map": map,
    "filter": filter,
    "sorted": sorted,
    "reversed": reversed,
    "sum": sum,
    "min": min,
    "max": max,
    "abs": abs,
    "round": round,
    "any": any,
    "all": all,
    "isinstance": isinstance,
    "print": lambda *args: None,  # Silently ignore prints
    "True": True,
    "False": False,
    "None": None,
}

# Forbidden patterns in code (security)
FORBIDDEN_PATTERNS = [
    r"__\w+__",  # Dunder methods
    r"\bimport\b",  # Import statements
    r"\bexec\b",  # Exec calls
    r"\beval\b",  # Eval calls
    r"\bopen\b",  # File operations
    r"\bcompile\b",  # Code compilation
    r"\bglobals\b",  # Global access
    r"\blocals\b",  # Local access
    r"\bgetattr\b",  # Attribute access
    r"\bsetattr\b",  # Attribute modification
    r"\bdelattr\b",  # Attribute deletion
    r"\bvars\b",  # Variable access
    r"\bdir\b",  # Directory listing
    r"\btype\b",  # Type manipulation
    r"\b__builtins__\b",  # Builtins access
]


class QueryTracker:
    """Tracks queries executed within sandbox for logging."""

    def __init__(self):
        self.queries = []

    def track(self, query_type: str, params: dict, result_count: int):
        self.queries.append({
            "type": query_type,
            "params": params,
            "results": result_count,
        })


def validate_code(code: str) -> tuple[bool, str]:
    """Validate code for safety before execution."""
    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, code):
            return False, f"Forbidden pattern detected: {pattern}"

    # Check for balanced brackets/parens
    brackets = {"(": ")", "[": "]", "{": "}"}
    stack = []
    for char in code:
        if char in brackets:
            stack.append(brackets[char])
        elif char in brackets.values():
            if not stack or stack.pop() != char:
                return False, "Unbalanced brackets"

    if stack:
        return False, "Unbalanced brackets"

    return True, ""


def validate_sql(sql: str) -> tuple[bool, str]:
    """Validate SQL query is read-only."""
    sql_upper = sql.strip().upper()

    # Only allow SELECT, SHOW, DESCRIBE
    if not sql_upper.startswith(("SELECT", "SHOW", "DESCRIBE")):
        return False, "Only SELECT, SHOW, and DESCRIBE queries are allowed"

    # Block dangerous patterns even in SELECT
    dangerous = ["INTO OUTFILE", "INTO DUMPFILE", "LOAD_FILE", "BENCHMARK", "SLEEP"]
    for pattern in dangerous:
        if pattern in sql_upper:
            return False, f"Dangerous SQL pattern detected: {pattern}"

    return True, ""


def create_sandbox_functions(tracker: QueryTracker) -> dict:
    """Create the sandboxed query functions."""

    def query(sql: str, db: str = "world", params: tuple = None) -> list:
        """Execute a read-only SQL query."""
        valid, error = validate_sql(sql)
        if not valid:
            raise ValueError(error)

        result = execute_query(sql, db, params)
        tracker.track("raw_sql", {"db": db, "sql": sql[:100]}, len(result))
        return result

    def get_creature(entry: int) -> dict | None:
        """Get creature_template by entry."""
        result = execute_query(
            "SELECT * FROM creature_template WHERE entry = %s",
            "world", (entry,)
        )
        tracker.track("get_creature", {"entry": entry}, len(result))
        return result[0] if result else None

    def search_creatures(name: str, limit: int = 20) -> list:
        """Search creatures by name pattern."""
        result = execute_query(
            "SELECT entry, name, subname, minlevel, maxlevel, AIName FROM creature_template WHERE name LIKE %s LIMIT %s",
            "world", (f"%{name}%", limit)
        )
        tracker.track("search_creatures", {"name": name}, len(result))
        return result

    def get_scripts(entryorguid: int, source_type: int = 0) -> list:
        """Get SmartAI scripts for entity."""
        result = execute_query(
            "SELECT * FROM smart_scripts WHERE entryorguid = %s AND source_type = %s ORDER BY id",
            "world", (entryorguid, source_type)
        )
        tracker.track("get_scripts", {"entryorguid": entryorguid, "source_type": source_type}, len(result))
        return result

    def get_quest(entry: int) -> dict | None:
        """Get quest_template by ID."""
        result = execute_query(
            "SELECT * FROM quest_template WHERE ID = %s",
            "world", (entry,)
        )
        tracker.track("get_quest", {"entry": entry}, len(result))
        return result[0] if result else None

    def search_quests(name: str, limit: int = 20) -> list:
        """Search quests by name pattern."""
        result = execute_query(
            "SELECT ID, LogTitle, QuestLevel, MinLevel, QuestSortID FROM quest_template WHERE LogTitle LIKE %s LIMIT %s",
            "world", (f"%{name}%", limit)
        )
        tracker.track("search_quests", {"name": name}, len(result))
        return result

    def get_conditions(source_type: int, source_group: int = 0, source_entry: int = 0) -> list:
        """Get conditions from conditions table."""
        result = execute_query(
            """SELECT * FROM conditions
               WHERE SourceTypeOrReferenceId = %s
               AND SourceGroup = %s
               AND SourceEntry = %s""",
            "world", (source_type, source_group, source_entry)
        )
        tracker.track("get_conditions", {
            "source_type": source_type,
            "source_group": source_group,
            "source_entry": source_entry
        }, len(result))
        return result

    def get_gameobject(entry: int) -> dict | None:
        """Get gameobject_template by entry."""
        result = execute_query(
            "SELECT * FROM gameobject_template WHERE entry = %s",
            "world", (entry,)
        )
        tracker.track("get_gameobject", {"entry": entry}, len(result))
        return result[0] if result else None

    def get_item(entry: int) -> dict | None:
        """Get item_template by entry."""
        result = execute_query(
            "SELECT * FROM item_template WHERE entry = %s",
            "world", (entry,)
        )
        tracker.track("get_item", {"entry": entry}, len(result))
        return result[0] if result else None

    def get_spawns(creature_entry: int, limit: int = 50) -> list:
        """Get creature spawn points."""
        result = execute_query(
            """SELECT guid, id1, map, zoneId, areaId, position_x, position_y, position_z
               FROM creature WHERE id1 = %s LIMIT %s""",
            "world", (creature_entry, limit)
        )
        tracker.track("get_spawns", {"creature_entry": creature_entry}, len(result))
        return result

    def get_loot(entry: int, loot_type: str = "creature") -> list:
        """Get loot table entries. loot_type: creature, gameobject, item, reference, etc."""
        table_map = {
            "creature": "creature_loot_template",
            "gameobject": "gameobject_loot_template",
            "item": "item_loot_template",
            "reference": "reference_loot_template",
            "skinning": "skinning_loot_template",
            "fishing": "fishing_loot_template",
            "pickpocketing": "pickpocketing_loot_template",
        }
        table = table_map.get(loot_type)
        if not table:
            raise ValueError(f"Unknown loot type: {loot_type}")

        result = execute_query(
            f"SELECT * FROM {table} WHERE Entry = %s",
            "world", (entry,)
        )
        tracker.track("get_loot", {"entry": entry, "loot_type": loot_type}, len(result))
        return result

    def get_npc_vendor(entry: int) -> list:
        """Get vendor items for NPC."""
        result = execute_query(
            "SELECT * FROM npc_vendor WHERE entry = %s",
            "world", (entry,)
        )
        tracker.track("get_npc_vendor", {"entry": entry}, len(result))
        return result

    def get_gossip_menu(menu_id: int) -> list:
        """Get gossip menu options."""
        result = execute_query(
            "SELECT * FROM gossip_menu_option WHERE MenuId = %s ORDER BY OptionId",
            "world", (menu_id,)
        )
        tracker.track("get_gossip_menu", {"menu_id": menu_id}, len(result))
        return result

    return {
        "query": query,
        "get_creature": get_creature,
        "search_creatures": search_creatures,
        "get_scripts": get_scripts,
        "get_quest": get_quest,
        "search_quests": search_quests,
        "get_conditions": get_conditions,
        "get_gameobject": get_gameobject,
        "get_item": get_item,
        "get_spawns": get_spawns,
        "get_loot": get_loot,
        "get_npc_vendor": get_npc_vendor,
        "get_gossip_menu": get_gossip_menu,
    }


def register_sandbox_tools(mcp):
    """Register sandbox tool for programmatic investigations."""

    @mcp.tool()
    def execute_investigation(python_code: str) -> str:
        """Execute Python code to orchestrate multiple database queries in a single call.

        This reduces context pollution and latency for complex investigations.
        Your code must assign results to the `result` variable.

        Available functions:
        - query(sql, db="world", params=None) - Raw SQL (SELECT only)
        - get_creature(entry) - Get creature_template row
        - search_creatures(name, limit=20) - Search by name
        - get_scripts(entryorguid, source_type=0) - Get SmartAI scripts
        - get_quest(entry) - Get quest_template row
        - search_quests(name, limit=20) - Search quests
        - get_conditions(source_type, source_group=0, source_entry=0) - Get conditions
        - get_gameobject(entry) - Get gameobject_template
        - get_item(entry) - Get item_template
        - get_spawns(creature_entry, limit=50) - Get spawn points
        - get_loot(entry, loot_type="creature") - Get loot table
        - get_npc_vendor(entry) - Get vendor items
        - get_gossip_menu(menu_id) - Get gossip options

        Example - Find creatures with SmartAI but no scripts:
        ```python
        creatures = query("SELECT entry, name FROM creature_template WHERE AIName = 'SmartAI' LIMIT 100")
        missing = []
        for c in creatures:
            scripts = get_scripts(c['entry'])
            if not scripts:
                missing.append({"entry": c['entry'], "name": c['name']})
        result = {"missing_scripts": missing[:10], "total": len(missing)}
        ```

        Example - Check quest prerequisites:
        ```python
        quest = get_quest(123)
        conditions = get_conditions(19, 0, 123)  # CONDITION_SOURCE_QUEST_AVAILABLE
        prereqs = []
        for c in conditions:
            if c['ConditionTypeOrReference'] == 8:  # CONDITION_QUESTREWARDED
                prereq = get_quest(c['ConditionValue1'])
                prereqs.append({"id": c['ConditionValue1'], "name": prereq['LogTitle'] if prereq else "MISSING"})
        result = {"quest": quest['LogTitle'], "prerequisites": prereqs}
        ```
        """
        start_time = time.time()
        tracker = QueryTracker()
        error = None

        try:
            # Validate code safety
            valid, err_msg = validate_code(python_code)
            if not valid:
                raise ValueError(f"Code validation failed: {err_msg}")

            # Create sandbox environment
            sandbox_funcs = create_sandbox_functions(tracker)
            sandbox_globals = {
                "__builtins__": SAFE_BUILTINS,
                "result": None,
                "json": json,
                **sandbox_funcs,
            }

            # Execute the code
            exec(python_code, sandbox_globals)

            # Get result
            result = sandbox_globals.get("result")
            if result is None:
                return json.dumps({
                    "error": "No result assigned. Your code must assign to the 'result' variable.",
                    "queries_executed": len(tracker.queries),
                })

            return json.dumps({
                "result": result,
                "queries_executed": len(tracker.queries),
                "query_details": tracker.queries,
            }, indent=2, default=str)

        except SyntaxError as e:
            error = f"Syntax error: {e}"
            return json.dumps({"error": error, "line": e.lineno})
        except Exception as e:
            error = f"{type(e).__name__}: {e}"
            return json.dumps({"error": error})
        finally:
            if LOG_TOOL_CALLS:
                duration = time.time() - start_time
                tool_logger.log_sandbox_execution(
                    code=python_code,
                    queries_executed=tracker.queries,
                    duration=duration,
                    error=error,
                )

    @mcp.tool()
    def list_sandbox_functions() -> str:
        """List all available functions in the sandbox environment."""
        functions = {
            "query": {
                "signature": "query(sql, db='world', params=None) -> list",
                "description": "Execute raw SQL SELECT query",
            },
            "get_creature": {
                "signature": "get_creature(entry) -> dict | None",
                "description": "Get creature_template row by entry ID",
            },
            "search_creatures": {
                "signature": "search_creatures(name, limit=20) -> list",
                "description": "Search creature_template by name pattern",
            },
            "get_scripts": {
                "signature": "get_scripts(entryorguid, source_type=0) -> list",
                "description": "Get SmartAI scripts (source_type: 0=creature, 1=gameobject, 9=actionlist)",
            },
            "get_quest": {
                "signature": "get_quest(entry) -> dict | None",
                "description": "Get quest_template row by ID",
            },
            "search_quests": {
                "signature": "search_quests(name, limit=20) -> list",
                "description": "Search quest_template by name pattern",
            },
            "get_conditions": {
                "signature": "get_conditions(source_type, source_group=0, source_entry=0) -> list",
                "description": "Get conditions table entries",
            },
            "get_gameobject": {
                "signature": "get_gameobject(entry) -> dict | None",
                "description": "Get gameobject_template by entry",
            },
            "get_item": {
                "signature": "get_item(entry) -> dict | None",
                "description": "Get item_template by entry",
            },
            "get_spawns": {
                "signature": "get_spawns(creature_entry, limit=50) -> list",
                "description": "Get creature spawn locations",
            },
            "get_loot": {
                "signature": "get_loot(entry, loot_type='creature') -> list",
                "description": "Get loot table (types: creature, gameobject, item, reference, skinning, fishing, pickpocketing)",
            },
            "get_npc_vendor": {
                "signature": "get_npc_vendor(entry) -> list",
                "description": "Get vendor items for NPC",
            },
            "get_gossip_menu": {
                "signature": "get_gossip_menu(menu_id) -> list",
                "description": "Get gossip menu options",
            },
        }
        return json.dumps(functions, indent=2)
