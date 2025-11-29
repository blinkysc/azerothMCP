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
AzerothCore MCP Server

A Model Context Protocol server that provides Claude with access to:
- AzerothCore MySQL databases (world, characters, auth)
- Wiki documentation for SmartAI and database schemas
- Helper tools for understanding creature scripts and game mechanics
"""

import os
import json
import glob
import re
from pathlib import Path
from typing import Any
from dotenv import load_dotenv

import mysql.connector
from mysql.connector import Error
from mcp.server.fastmcp import FastMCP

# Import SAI comment generator (Keira3 port)
try:
    from sai_comment_generator import SaiCommentGenerator
    SAI_GENERATOR_AVAILABLE = True
except ImportError:
    SAI_GENERATOR_AVAILABLE = False
    SaiCommentGenerator = None

# Import SOAP client for worldserver commands
try:
    from soap_client import AzerothCoreSOAP, create_soap_client_from_env
    SOAP_AVAILABLE = True
except ImportError:
    SOAP_AVAILABLE = False
    AzerothCoreSOAP = None
    create_soap_client_from_env = None

# Load environment variables
load_dotenv()

# Configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER", "acore"),
    "password": os.getenv("DB_PASSWORD", "acore"),
}

DB_NAMES = {
    "world": os.getenv("DB_WORLD", "acore_world"),
    "characters": os.getenv("DB_CHARACTERS", "acore_characters"),
    "auth": os.getenv("DB_AUTH", "acore_auth"),
}

# Read-only mode (set to "false" to enable write operations)
READ_ONLY = os.getenv("READ_ONLY", "true").lower() != "false"

# Enable spell_dbc tool (only needed for custom spells)
ENABLE_SPELL_DBC = os.getenv("ENABLE_SPELL_DBC", "false").lower() == "true"

WIKI_PATH = Path(os.path.expanduser(os.getenv("WIKI_PATH", "~/wiki/docs")))

# AzerothCore source path (for reading SmartAI implementations)
AZEROTHCORE_SRC_PATH = Path(os.path.expanduser(os.getenv("AZEROTHCORE_SRC_PATH", "~/azerothcore")))

# SOAP client configuration
# Set SOAP_ENABLED=true and provide credentials to enable worldserver commands
SOAP_ENABLED = os.getenv("SOAP_ENABLED", "false").lower() == "true"
_soap_client = None
if SOAP_AVAILABLE and SOAP_ENABLED:
    _soap_client = create_soap_client_from_env()

# Initialize MCP server with SSE settings
mcp = FastMCP(
    "AzerothCore MCP Server",
    host="0.0.0.0",
    port=int(os.getenv("MCP_PORT", 8080))
)


def get_db_connection(database: str = "world"):
    """Create a database connection to specified AzerothCore database."""
    db_name = DB_NAMES.get(database, database)
    try:
        connection = mysql.connector.connect(
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            database=db_name,
        )
        return connection
    except Error as e:
        raise Exception(f"Failed to connect to database {db_name}: {e}")


def execute_query(query: str, database: str = "world", params: tuple = None) -> list[dict]:
    """Execute a SELECT query and return results as list of dicts."""
    query_upper = query.strip().upper()
    is_read_query = query_upper.startswith(("SELECT", "SHOW", "DESCRIBE"))

    if READ_ONLY and not is_read_query:
        raise ValueError("Only SELECT, SHOW, and DESCRIBE queries are allowed (read-only mode). Set READ_ONLY=false to enable write operations.")

    connection = get_db_connection(database)
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, params)

        if is_read_query:
            results = cursor.fetchall()
            return results
        else:
            connection.commit()
            return [{"affected_rows": cursor.rowcount, "last_insert_id": cursor.lastrowid}]
    finally:
        cursor.close()
        connection.close()


# =============================================================================
# DATABASE TOOLS
# =============================================================================

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


# =============================================================================
# CREATURE / NPC TOOLS
# =============================================================================

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


# =============================================================================
# SMART AI TOOLS
# =============================================================================

def _mysql_query_for_sai(query: str, database: str = "world"):
    """Wrapper for execute_query that returns results for SAI generator."""
    return execute_query(query, database)


def _add_sai_comments(scripts: list, name: str) -> list:
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


def _get_entity_name(entryorguid: int, source_type: int) -> str:
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


@mcp.tool()
def get_smart_scripts(entryorguid: int, source_type: int = 0) -> str:
    """
    Get SmartAI scripts for a creature, gameobject, or other source.
    Includes auto-generated human-readable comments for each script row.

    Args:
        entryorguid: The entry or GUID of the source
        source_type: 0=Creature, 1=GameObject, 2=AreaTrigger, 3=Event,
                    4=Gossip, 5=Quest, 6=Spell, 7=Transport, 8=Instance, 9=TimedActionList

    Returns:
        All smart_scripts rows for this entity with generated comments, ordered by id
    """
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

        # Add Keira3-style comments
        name = _get_entity_name(entryorguid, source_type)
        results = _add_sai_comments(results, name)

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
            scripts = _add_sai_comments(scripts, creature_name)

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
                        timed_scripts = _add_sai_comments(timed_scripts, creature_name)
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


@mcp.tool()
def explain_smart_script(event_type: int = None, action_type: int = None, target_type: int = None) -> str:
    """
    Get documentation explaining SmartAI event types, action types, or target types.
    Includes parameter documentation from AzerothCore source code.

    Args:
        event_type: SmartAI event type number to explain
        action_type: SmartAI action type number to explain
        target_type: SmartAI target type number to explain

    Returns:
        Explanation of the requested SmartAI component with parameters
    """
    # SmartAI event types with parameter documentation from SmartScriptMgr.h
    events = {
        0: {"name": "SMART_EVENT_UPDATE_IC", "desc": "In combat pulse", "params": "InitialMin, InitialMax, RepeatMin, RepeatMax"},
        1: {"name": "SMART_EVENT_UPDATE_OOC", "desc": "Out of combat pulse", "params": "InitialMin, InitialMax, RepeatMin, RepeatMax"},
        2: {"name": "SMART_EVENT_HEALTH_PCT", "desc": "Health percentage reached", "params": "HPMin%, HPMax%, RepeatMin, RepeatMax"},
        3: {"name": "SMART_EVENT_MANA_PCT", "desc": "Mana percentage reached", "params": "ManaMin%, ManaMax%, RepeatMin, RepeatMax"},
        4: {"name": "SMART_EVENT_AGGRO", "desc": "On entering combat", "params": "NONE"},
        5: {"name": "SMART_EVENT_KILL", "desc": "On killing a unit", "params": "CooldownMin, CooldownMax, PlayerOnly (0/1), CreatureEntry (0=any)"},
        6: {"name": "SMART_EVENT_DEATH", "desc": "On creature death", "params": "NONE"},
        7: {"name": "SMART_EVENT_EVADE", "desc": "On evade/reset", "params": "NONE"},
        8: {"name": "SMART_EVENT_SPELLHIT", "desc": "When hit by spell", "params": "SpellID (0=any), School (0=any), CooldownMin, CooldownMax"},
        9: {"name": "SMART_EVENT_RANGE", "desc": "Target in range check", "params": "MinDist, MaxDist, RepeatMin, RepeatMax, RangeMin, RangeMax"},
        10: {"name": "SMART_EVENT_OOC_LOS", "desc": "Out of combat, target in LOS", "params": "HostilityMode (0=hostile,1=not hostile,2=any), MaxRange, CooldownMin, CooldownMax, PlayerOnly"},
        11: {"name": "SMART_EVENT_RESPAWN", "desc": "On respawn", "params": "Type (0=any), MapId, ZoneId"},
        12: {"name": "SMART_EVENT_TARGET_HEALTH_PCT", "desc": "Target health percentage", "params": "HPMin%, HPMax%, RepeatMin, RepeatMax"},
        13: {"name": "SMART_EVENT_VICTIM_CASTING", "desc": "Victim is casting", "params": "RepeatMin, RepeatMax, SpellID (0=any)"},
        14: {"name": "SMART_EVENT_FRIENDLY_HEALTH", "desc": "Friendly unit low health", "params": "HPDeficit, Radius, RepeatMin, RepeatMax"},
        15: {"name": "SMART_EVENT_FRIENDLY_IS_CC", "desc": "Friendly unit is CC'd", "params": "Radius, RepeatMin, RepeatMax"},
        16: {"name": "SMART_EVENT_FRIENDLY_MISSING_BUFF", "desc": "Friendly missing buff", "params": "SpellID, Radius, RepeatMin, RepeatMax, OnlyInCombat"},
        17: {"name": "SMART_EVENT_SUMMONED_UNIT", "desc": "Summoned a unit", "params": "CreatureEntry (0=any), CooldownMin, CooldownMax"},
        18: {"name": "SMART_EVENT_TARGET_MANA_PCT", "desc": "Target mana percentage", "params": "ManaMin%, ManaMax%, RepeatMin, RepeatMax"},
        19: {"name": "SMART_EVENT_ACCEPTED_QUEST", "desc": "Quest accepted by player", "params": "QuestID (0=any), CooldownMin, CooldownMax"},
        20: {"name": "SMART_EVENT_REWARD_QUEST", "desc": "Quest rewarded to player", "params": "QuestID (0=any), CooldownMin, CooldownMax"},
        21: {"name": "SMART_EVENT_REACHED_HOME", "desc": "Reached home position", "params": "NONE"},
        22: {"name": "SMART_EVENT_RECEIVE_EMOTE", "desc": "Received emote from player", "params": "EmoteID, CooldownMin, CooldownMax, Condition, Val1, Val2, Val3"},
        23: {"name": "SMART_EVENT_HAS_AURA", "desc": "Unit has aura", "params": "SpellID, StackCount, RepeatMin, RepeatMax"},
        24: {"name": "SMART_EVENT_TARGET_BUFFED", "desc": "Target has aura", "params": "SpellID, StackCount, RepeatMin, RepeatMax"},
        25: {"name": "SMART_EVENT_RESET", "desc": "After combat/respawn/spawn", "params": "NONE"},
        26: {"name": "SMART_EVENT_IC_LOS", "desc": "In combat, target in LOS", "params": "HostilityMode (0=hostile,1=not hostile,2=any), MaxRange, CooldownMin, CooldownMax, PlayerOnly"},
        27: {"name": "SMART_EVENT_PASSENGER_BOARDED", "desc": "Vehicle passenger boarded", "params": "CooldownMin, CooldownMax"},
        28: {"name": "SMART_EVENT_PASSENGER_REMOVED", "desc": "Vehicle passenger removed", "params": "CooldownMin, CooldownMax"},
        29: {"name": "SMART_EVENT_CHARMED", "desc": "Unit charmed/mind controlled", "params": "OnRemove (0=on apply, 1=on remove)"},
        30: {"name": "SMART_EVENT_CHARMED_TARGET", "desc": "Charmed target event", "params": "NONE"},
        31: {"name": "SMART_EVENT_SPELLHIT_TARGET", "desc": "Target hit by spell", "params": "SpellID, School, CooldownMin, CooldownMax"},
        32: {"name": "SMART_EVENT_DAMAGED", "desc": "Creature took damage", "params": "MinDmg, MaxDmg, CooldownMin, CooldownMax"},
        33: {"name": "SMART_EVENT_DAMAGED_TARGET", "desc": "Target took damage", "params": "MinDmg, MaxDmg, CooldownMin, CooldownMax"},
        34: {"name": "SMART_EVENT_MOVEMENTINFORM", "desc": "Movement generator finished", "params": "MovementType (0=any), PointID, PathID (0=any)"},
        35: {"name": "SMART_EVENT_SUMMON_DESPAWNED", "desc": "Summoned unit despawned", "params": "Entry, CooldownMin, CooldownMax"},
        36: {"name": "SMART_EVENT_CORPSE_REMOVED", "desc": "Corpse removed", "params": "NONE"},
        37: {"name": "SMART_EVENT_AI_INIT", "desc": "AI initialized", "params": "NONE"},
        38: {"name": "SMART_EVENT_DATA_SET", "desc": "SetData called on creature", "params": "DataID, Value, CooldownMin, CooldownMax"},
        39: {"name": "SMART_EVENT_WAYPOINT_START", "desc": "Waypoint path started (DEPRECATED: use 108)", "params": "PointID (0=any), PathID (0=any)"},
        40: {"name": "SMART_EVENT_WAYPOINT_REACHED", "desc": "Waypoint reached (DEPRECATED: use 108)", "params": "PointID (0=any), PathID (0=any)"},
        41: {"name": "SMART_EVENT_TRANSPORT_ADDPLAYER", "desc": "Player added to transport", "params": "NONE"},
        42: {"name": "SMART_EVENT_TRANSPORT_ADDCREATURE", "desc": "Creature added to transport", "params": "Entry (0=any)"},
        43: {"name": "SMART_EVENT_TRANSPORT_REMOVE_PLAYER", "desc": "Player removed from transport", "params": "NONE"},
        44: {"name": "SMART_EVENT_TRANSPORT_RELOCATE", "desc": "Transport relocated", "params": "PointID"},
        45: {"name": "SMART_EVENT_INSTANCE_PLAYER_ENTER", "desc": "Player entered instance", "params": "Team (0=any), CooldownMin, CooldownMax"},
        46: {"name": "SMART_EVENT_AREATRIGGER_ONTRIGGER", "desc": "Areatrigger triggered", "params": "TriggerID (0=any)"},
        47: {"name": "SMART_EVENT_QUEST_ACCEPTED", "desc": "Quest accepted (DEPRECATED)", "params": "NONE"},
        48: {"name": "SMART_EVENT_QUEST_OBJ_COMPLETION", "desc": "Quest objective completed", "params": "NONE"},
        49: {"name": "SMART_EVENT_QUEST_COMPLETION", "desc": "Quest completed (DEPRECATED)", "params": "NONE"},
        50: {"name": "SMART_EVENT_QUEST_REWARDED", "desc": "Quest rewarded (DEPRECATED)", "params": "NONE"},
        51: {"name": "SMART_EVENT_QUEST_FAIL", "desc": "Quest failed", "params": "NONE"},
        52: {"name": "SMART_EVENT_TEXT_OVER", "desc": "Creature text finished", "params": "GroupID (creature_text), CreatureEntry (0=any)"},
        53: {"name": "SMART_EVENT_RECEIVE_HEAL", "desc": "Received healing", "params": "MinHeal, MaxHeal, CooldownMin, CooldownMax"},
        54: {"name": "SMART_EVENT_JUST_SUMMONED", "desc": "Just summoned by another unit", "params": "NONE"},
        55: {"name": "SMART_EVENT_WAYPOINT_PAUSED", "desc": "Waypoint paused (DEPRECATED)", "params": "PointID (0=any), PathID (0=any)"},
        56: {"name": "SMART_EVENT_WAYPOINT_RESUMED", "desc": "Waypoint resumed (DEPRECATED)", "params": "PointID (0=any), PathID (0=any)"},
        57: {"name": "SMART_EVENT_WAYPOINT_STOPPED", "desc": "Waypoint stopped (DEPRECATED)", "params": "PointID (0=any), PathID (0=any)"},
        58: {"name": "SMART_EVENT_WAYPOINT_ENDED", "desc": "Waypoint path ended (DEPRECATED)", "params": "PointID (0=any), PathID (0=any)"},
        59: {"name": "SMART_EVENT_TIMED_EVENT_TRIGGERED", "desc": "Timed event triggered", "params": "EventID"},
        60: {"name": "SMART_EVENT_UPDATE", "desc": "Pulse (in or out of combat)", "params": "InitialMin, InitialMax, RepeatMin, RepeatMax"},
        61: {"name": "SMART_EVENT_LINK", "desc": "Linked from another script", "params": "INTERNAL - no params, triggered via 'link' column"},
        62: {"name": "SMART_EVENT_GOSSIP_SELECT", "desc": "Gossip option selected", "params": "MenuID, ActionID"},
        63: {"name": "SMART_EVENT_JUST_CREATED", "desc": "Just created/spawned", "params": "NONE"},
        64: {"name": "SMART_EVENT_GOSSIP_HELLO", "desc": "NPC gossip opened", "params": "Filter (0=none, 1=GossipHello only, 2=reportUse only)"},
        65: {"name": "SMART_EVENT_FOLLOW_COMPLETED", "desc": "Follow action completed", "params": "NONE"},
        66: {"name": "SMART_EVENT_EVENT_PHASE_CHANGE", "desc": "Event phase changed", "params": "PhaseMask"},
        67: {"name": "SMART_EVENT_IS_BEHIND_TARGET", "desc": "Behind target check", "params": "Min, Max, RepeatMin, RepeatMax, RangeMin, RangeMax"},
        68: {"name": "SMART_EVENT_GAME_EVENT_START", "desc": "Game event started", "params": "GameEventID"},
        69: {"name": "SMART_EVENT_GAME_EVENT_END", "desc": "Game event ended", "params": "GameEventID"},
        70: {"name": "SMART_EVENT_GO_STATE_CHANGED", "desc": "GO state changed", "params": "GOState"},
        71: {"name": "SMART_EVENT_GO_EVENT_INFORM", "desc": "GO event inform", "params": "EventID"},
        72: {"name": "SMART_EVENT_ACTION_DONE", "desc": "Action completed", "params": "EventID (SharedDefines.EventId)"},
        73: {"name": "SMART_EVENT_ON_SPELLCLICK", "desc": "Spellclick used", "params": "NONE"},
        74: {"name": "SMART_EVENT_FRIENDLY_HEALTH_PCT", "desc": "Friendly unit health %", "params": "Min%, Max%, RepeatMin, RepeatMax, HPPct, Range"},
        75: {"name": "SMART_EVENT_DISTANCE_CREATURE", "desc": "Distance to creature", "params": "GUID, Entry, Distance, Repeat"},
        76: {"name": "SMART_EVENT_DISTANCE_GAMEOBJECT", "desc": "Distance to gameobject", "params": "GUID, Entry, Distance, Repeat"},
        77: {"name": "SMART_EVENT_COUNTER_SET", "desc": "Counter set to value", "params": "CounterID, Value, CooldownMin, CooldownMax"},
        78: {"name": "SMART_EVENT_SCENE_START", "desc": "Scene started (N/A 3.3.5a)", "params": "UNUSED"},
        79: {"name": "SMART_EVENT_SCENE_TRIGGER", "desc": "Scene trigger (N/A 3.3.5a)", "params": "UNUSED"},
        80: {"name": "SMART_EVENT_SCENE_CANCEL", "desc": "Scene cancelled (N/A 3.3.5a)", "params": "UNUSED"},
        81: {"name": "SMART_EVENT_SCENE_COMPLETE", "desc": "Scene completed (N/A 3.3.5a)", "params": "UNUSED"},
        82: {"name": "SMART_EVENT_SUMMONED_UNIT_DIES", "desc": "Summoned creature died", "params": "CreatureEntry (0=any), CooldownMin, CooldownMax"},
        # AC Custom Events (100+)
        101: {"name": "SMART_EVENT_NEAR_PLAYERS", "desc": "Near minimum players (AC)", "params": "MinPlayers, Radius, FirstTimer, RepeatMin, RepeatMax"},
        102: {"name": "SMART_EVENT_NEAR_PLAYERS_NEGATION", "desc": "Below max players nearby (AC)", "params": "MaxPlayers, Radius, FirstTimer, RepeatMin, RepeatMax"},
        103: {"name": "SMART_EVENT_NEAR_UNIT", "desc": "Near unit count (AC)", "params": "Type (0=creature,1=gob), Entry, Count, Range, Timer"},
        104: {"name": "SMART_EVENT_NEAR_UNIT_NEGATION", "desc": "Below unit count (AC)", "params": "Type (0=creature,1=gob), Entry, Count, Range, Timer"},
        105: {"name": "SMART_EVENT_AREA_CASTING", "desc": "Casting in area (AC)", "params": "Min, Max, RepeatMin, RepeatMax, RangeMin, RangeMax"},
        106: {"name": "SMART_EVENT_AREA_RANGE", "desc": "Targets in area range (AC)", "params": "Min, Max, RepeatMin, RepeatMax, RangeMin, RangeMax"},
        107: {"name": "SMART_EVENT_SUMMONED_UNIT_EVADE", "desc": "Summoned unit evaded (AC)", "params": "CreatureEntry (0=any), CooldownMin, CooldownMax"},
        108: {"name": "SMART_EVENT_WAYPOINT_REACHED", "desc": "Waypoint reached (AC new)", "params": "PointID (0=any), PathID (0=any)"},
        109: {"name": "SMART_EVENT_WAYPOINT_ENDED", "desc": "Waypoint path ended (AC new)", "params": "PointID (0=any), PathID (0=any)"},
        110: {"name": "SMART_EVENT_IS_IN_MELEE_RANGE", "desc": "In melee range check (AC)", "params": "Min, Max, RepeatMin, RepeatMax, Distance, Invert (0/1)"},
    }

    # SmartAI action types with parameter documentation
    actions = {
        0: {"name": "SMART_ACTION_NONE", "desc": "No action", "params": "NONE"},
        1: {"name": "SMART_ACTION_TALK", "desc": "Say/yell/emote from creature_text", "params": "GroupID, Duration (for TEXT_OVER), UseTalkTarget (0/1), Delay"},
        2: {"name": "SMART_ACTION_SET_FACTION", "desc": "Change faction", "params": "FactionID (0=restore default)"},
        3: {"name": "SMART_ACTION_MORPH_TO_ENTRY_OR_MODEL", "desc": "Change model", "params": "CreatureEntry OR ModelID (0 for both = demorph)"},
        4: {"name": "SMART_ACTION_SOUND", "desc": "Play sound", "params": "SoundID, OnlySelf, Distance"},
        5: {"name": "SMART_ACTION_PLAY_EMOTE", "desc": "Play emote animation", "params": "EmoteID"},
        6: {"name": "SMART_ACTION_FAIL_QUEST", "desc": "Fail quest for player", "params": "QuestID"},
        7: {"name": "SMART_ACTION_OFFER_QUEST", "desc": "Offer quest to player", "params": "QuestID, DirectAdd"},
        8: {"name": "SMART_ACTION_SET_REACT_STATE", "desc": "Set react state", "params": "State (0=passive, 1=defensive, 2=aggressive)"},
        9: {"name": "SMART_ACTION_ACTIVATE_GOBJECT", "desc": "Activate gameobject", "params": "NONE"},
        10: {"name": "SMART_ACTION_RANDOM_EMOTE", "desc": "Play random emote", "params": "EmoteID1, EmoteID2, EmoteID3, EmoteID4, EmoteID5, EmoteID6"},
        11: {"name": "SMART_ACTION_CAST", "desc": "Cast spell on target", "params": "SpellID, CastFlags, TriggerFlags, TargetsLimit"},
        12: {"name": "SMART_ACTION_SUMMON_CREATURE", "desc": "Summon creature", "params": "CreatureEntry, SummonType, Duration(ms), AttackInvoker, AttackScriptOwner, Flags"},
        13: {"name": "SMART_ACTION_THREAT_SINGLE_PCT", "desc": "Modify single target threat %", "params": "ThreatPct"},
        14: {"name": "SMART_ACTION_THREAT_ALL_PCT", "desc": "Modify all targets threat %", "params": "ThreatPct"},
        15: {"name": "SMART_ACTION_CALL_AREAEXPLOREDOREVENTHAPPENS", "desc": "Complete quest area/event", "params": "QuestID"},
        16: {"name": "SMART_ACTION_RESERVED_16", "desc": "Reserved (4.3.4+)", "params": "UNUSED"},
        17: {"name": "SMART_ACTION_SET_EMOTE_STATE", "desc": "Set emote state", "params": "EmoteID"},
        18: {"name": "SMART_ACTION_SET_UNIT_FLAG", "desc": "Set unit flags", "params": "Flags, Type"},
        19: {"name": "SMART_ACTION_REMOVE_UNIT_FLAG", "desc": "Remove unit flags", "params": "Flags, Type"},
        20: {"name": "SMART_ACTION_AUTO_ATTACK", "desc": "Enable/disable auto attack", "params": "AllowAttack (0=stop, 1=allow)"},
        21: {"name": "SMART_ACTION_ALLOW_COMBAT_MOVEMENT", "desc": "Allow combat movement", "params": "AllowMovement (0=stop, 1=allow)"},
        22: {"name": "SMART_ACTION_SET_EVENT_PHASE", "desc": "Set event phase", "params": "Phase"},
        23: {"name": "SMART_ACTION_INC_EVENT_PHASE", "desc": "Increment/decrement phase", "params": "Value (negative to decrement)"},
        24: {"name": "SMART_ACTION_EVADE", "desc": "Force evade", "params": "NONE"},
        25: {"name": "SMART_ACTION_FLEE_FOR_ASSIST", "desc": "Flee and call for help", "params": "WithEmote (0/1)"},
        26: {"name": "SMART_ACTION_CALL_GROUPEVENTHAPPENS", "desc": "Group quest event", "params": "QuestID"},
        27: {"name": "SMART_ACTION_COMBAT_STOP", "desc": "Stop combat", "params": "NONE"},
        28: {"name": "SMART_ACTION_REMOVEAURASFROMSPELL", "desc": "Remove auras from spell", "params": "SpellID (0=all), Charges (0=remove aura)"},
        29: {"name": "SMART_ACTION_FOLLOW", "desc": "Follow target", "params": "Distance (0=default), Angle (0=default), EndCreatureEntry, Credit, CreditType (0=kill,1=event)"},
        30: {"name": "SMART_ACTION_RANDOM_PHASE", "desc": "Set random phase", "params": "Phase1, Phase2, Phase3, Phase4, Phase5, Phase6"},
        31: {"name": "SMART_ACTION_RANDOM_PHASE_RANGE", "desc": "Set phase in range", "params": "PhaseMin, PhaseMax"},
        32: {"name": "SMART_ACTION_RESET_GOBJECT", "desc": "Reset gameobject", "params": "NONE"},
        33: {"name": "SMART_ACTION_CALL_KILLEDMONSTER", "desc": "Credit kill for quest", "params": "CreatureEntry"},
        34: {"name": "SMART_ACTION_SET_INST_DATA", "desc": "Set instance data", "params": "Field, Data"},
        35: {"name": "SMART_ACTION_SET_INST_DATA64", "desc": "Set instance data 64-bit", "params": "Field"},
        36: {"name": "SMART_ACTION_UPDATE_TEMPLATE", "desc": "Update creature template", "params": "Entry, UpdateLevel"},
        37: {"name": "SMART_ACTION_DIE", "desc": "Kill self", "params": "Milliseconds (delay)"},
        38: {"name": "SMART_ACTION_SET_IN_COMBAT_WITH_ZONE", "desc": "Zone-wide combat", "params": "Range (if outside dungeon)"},
        39: {"name": "SMART_ACTION_CALL_FOR_HELP", "desc": "Call for help", "params": "Radius, WithEmote"},
        40: {"name": "SMART_ACTION_SET_SHEATH", "desc": "Set sheath state", "params": "Sheath (0=unarmed, 1=melee, 2=ranged)"},
        41: {"name": "SMART_ACTION_FORCE_DESPAWN", "desc": "Despawn creature", "params": "DelayMS"},
        42: {"name": "SMART_ACTION_SET_INVINCIBILITY_HP_LEVEL", "desc": "Set invincibility HP", "params": "MinHP (+pct, -flat)"},
        43: {"name": "SMART_ACTION_MOUNT_TO_ENTRY_OR_MODEL", "desc": "Mount/dismount", "params": "CreatureEntry OR ModelID (0=dismount)"},
        44: {"name": "SMART_ACTION_SET_INGAME_PHASE_MASK", "desc": "Set phase mask", "params": "PhaseMask"},
        45: {"name": "SMART_ACTION_SET_DATA", "desc": "Set data on target", "params": "Field, Data"},
        46: {"name": "SMART_ACTION_MOVE_FORWARD", "desc": "Move forward", "params": "Distance"},
        47: {"name": "SMART_ACTION_SET_VISIBILITY", "desc": "Set visibility", "params": "Visible (0/1)"},
        48: {"name": "SMART_ACTION_SET_ACTIVE", "desc": "Set active (keep updated)", "params": "Active (0/1)"},
        49: {"name": "SMART_ACTION_ATTACK_START", "desc": "Start attacking target", "params": "NONE"},
        50: {"name": "SMART_ACTION_SUMMON_GO", "desc": "Summon gameobject", "params": "GOEntry, DespawnTime, TargetSummon, SummonType (0=time/death, 1=time)"},
        51: {"name": "SMART_ACTION_KILL_UNIT", "desc": "Kill target unit", "params": "NONE"},
        52: {"name": "SMART_ACTION_ACTIVATE_TAXI", "desc": "Activate taxi path", "params": "TaxiID"},
        53: {"name": "SMART_ACTION_WP_START", "desc": "Start waypoint path (DEPRECATED)", "params": "Run/Walk, PathID, CanRepeat, Quest, DespawnTime, ReactState"},
        54: {"name": "SMART_ACTION_WP_PAUSE", "desc": "Pause waypoint (DEPRECATED)", "params": "Time"},
        55: {"name": "SMART_ACTION_WP_STOP", "desc": "Stop waypoint (DEPRECATED)", "params": "DespawnTime, Quest, Fail?"},
        56: {"name": "SMART_ACTION_ADD_ITEM", "desc": "Add item to player", "params": "ItemID, Count"},
        57: {"name": "SMART_ACTION_REMOVE_ITEM", "desc": "Remove item from player", "params": "ItemID, Count"},
        58: {"name": "SMART_ACTION_INSTALL_AI_TEMPLATE", "desc": "Install AI template", "params": "AITemplateID"},
        59: {"name": "SMART_ACTION_SET_RUN", "desc": "Set run/walk", "params": "Run (0/1)"},
        60: {"name": "SMART_ACTION_SET_FLY", "desc": "Set fly mode", "params": "Fly (0/1)"},
        61: {"name": "SMART_ACTION_SET_SWIM", "desc": "Set swim mode", "params": "Swim (0/1)"},
        62: {"name": "SMART_ACTION_TELEPORT", "desc": "Teleport target", "params": "MapID, x, y, z, o (from target coords)"},
        63: {"name": "SMART_ACTION_SET_COUNTER", "desc": "Set counter value", "params": "CounterID, Value, Reset (0/1)"},
        64: {"name": "SMART_ACTION_STORE_TARGET_LIST", "desc": "Store current targets", "params": "VarID"},
        65: {"name": "SMART_ACTION_WP_RESUME", "desc": "Resume waypoint (DEPRECATED)", "params": "NONE"},
        66: {"name": "SMART_ACTION_SET_ORIENTATION", "desc": "Set facing/orientation", "params": "QuickChange, RandomOrientation? (0/1), TurnAngle"},
        67: {"name": "SMART_ACTION_CREATE_TIMED_EVENT", "desc": "Create timed event", "params": "EventID, InitialMin, InitialMax, RepeatMin, RepeatMax, Chance"},
        68: {"name": "SMART_ACTION_PLAYMOVIE", "desc": "Play movie", "params": "MovieEntry"},
        69: {"name": "SMART_ACTION_MOVE_TO_POS", "desc": "Move to position", "params": "PointID, Transport, Controlled, ContactDistance (x,y,z from target)"},
        70: {"name": "SMART_ACTION_RESPAWN_TARGET", "desc": "Respawn target GO/creature", "params": "Force, GORespawnTime"},
        71: {"name": "SMART_ACTION_EQUIP", "desc": "Equip items", "params": "EquipmentID, SlotMask, Slot1, Slot2, Slot3"},
        72: {"name": "SMART_ACTION_CLOSE_GOSSIP", "desc": "Close gossip window", "params": "NONE"},
        73: {"name": "SMART_ACTION_TRIGGER_TIMED_EVENT", "desc": "Trigger timed event", "params": "EventID (>1)"},
        74: {"name": "SMART_ACTION_REMOVE_TIMED_EVENT", "desc": "Remove timed event", "params": "EventID (>1)"},
        75: {"name": "SMART_ACTION_ADD_AURA", "desc": "Add aura to target", "params": "SpellID"},
        76: {"name": "SMART_ACTION_OVERRIDE_SCRIPT_BASE_OBJECT", "desc": "Override script base (DANGEROUS)", "params": "WARNING: Can crash core"},
        77: {"name": "SMART_ACTION_RESET_SCRIPT_BASE_OBJECT", "desc": "Reset script base object", "params": "NONE"},
        78: {"name": "SMART_ACTION_CALL_SCRIPT_RESET", "desc": "Reset all scripts", "params": "NONE"},
        79: {"name": "SMART_ACTION_SET_RANGED_MOVEMENT", "desc": "Set ranged movement", "params": "Distance, Angle"},
        80: {"name": "SMART_ACTION_CALL_TIMED_ACTIONLIST", "desc": "Call timed action list", "params": "ActionListID, StopOnCombat (0/1), TimerType (0=OOC, 1=IC, 2=always)"},
        81: {"name": "SMART_ACTION_SET_NPC_FLAG", "desc": "Set NPC flags", "params": "Flags"},
        82: {"name": "SMART_ACTION_ADD_NPC_FLAG", "desc": "Add NPC flags", "params": "Flags"},
        83: {"name": "SMART_ACTION_REMOVE_NPC_FLAG", "desc": "Remove NPC flags", "params": "Flags"},
        84: {"name": "SMART_ACTION_SIMPLE_TALK", "desc": "Simple talk (targets speak)", "params": "GroupID (no TEXT_OVER, no whisper)"},
        85: {"name": "SMART_ACTION_SELF_CAST", "desc": "Self-cast spell", "params": "SpellID, CastFlags, TriggerFlags, TargetsLimit"},
        86: {"name": "SMART_ACTION_CROSS_CAST", "desc": "Casters cast on targets", "params": "SpellID, CastFlags, CasterTargetType, CasterParam1-3"},
        87: {"name": "SMART_ACTION_CALL_RANDOM_TIMED_ACTIONLIST", "desc": "Call random action list", "params": "ActionList1-6"},
        88: {"name": "SMART_ACTION_CALL_RANDOM_RANGE_TIMED_ACTIONLIST", "desc": "Call random range action list", "params": "ActionListMin, ActionListMax"},
        89: {"name": "SMART_ACTION_RANDOM_MOVE", "desc": "Random movement", "params": "MaxDistance"},
        90: {"name": "SMART_ACTION_SET_UNIT_FIELD_BYTES_1", "desc": "Set unit field bytes", "params": "Bytes, Target"},
        91: {"name": "SMART_ACTION_REMOVE_UNIT_FIELD_BYTES_1", "desc": "Remove unit field bytes", "params": "Bytes, Target"},
        92: {"name": "SMART_ACTION_INTERRUPT_SPELL", "desc": "Interrupt spell cast", "params": "WithDelayed, SpellType, WithInstant"},
        93: {"name": "SMART_ACTION_SEND_GO_CUSTOM_ANIM", "desc": "GO custom animation", "params": "AnimID"},
        94: {"name": "SMART_ACTION_SET_DYNAMIC_FLAG", "desc": "Set dynamic flags", "params": "Flags"},
        95: {"name": "SMART_ACTION_ADD_DYNAMIC_FLAG", "desc": "Add dynamic flags", "params": "Flags"},
        96: {"name": "SMART_ACTION_REMOVE_DYNAMIC_FLAG", "desc": "Remove dynamic flags", "params": "Flags"},
        97: {"name": "SMART_ACTION_JUMP_TO_POS", "desc": "Jump to position", "params": "SpeedXY, SpeedZ, SelfJump"},
        98: {"name": "SMART_ACTION_SEND_GOSSIP_MENU", "desc": "Send gossip menu", "params": "MenuID, OptionID"},
        99: {"name": "SMART_ACTION_GO_SET_LOOT_STATE", "desc": "Set GO loot state", "params": "State"},
        100: {"name": "SMART_ACTION_SEND_TARGET_TO_TARGET", "desc": "Send stored targets", "params": "VarID"},
        101: {"name": "SMART_ACTION_SET_HOME_POS", "desc": "Set home position", "params": "SpawnPos (use current pos)"},
        102: {"name": "SMART_ACTION_SET_HEALTH_REGEN", "desc": "Enable/disable health regen", "params": "Enabled (0/1)"},
        103: {"name": "SMART_ACTION_SET_ROOT", "desc": "Root/unroot", "params": "Rooted (0/1)"},
        104: {"name": "SMART_ACTION_SET_GO_FLAG", "desc": "Set GO flags", "params": "Flags"},
        105: {"name": "SMART_ACTION_ADD_GO_FLAG", "desc": "Add GO flags", "params": "Flags"},
        106: {"name": "SMART_ACTION_REMOVE_GO_FLAG", "desc": "Remove GO flags", "params": "Flags"},
        107: {"name": "SMART_ACTION_SUMMON_CREATURE_GROUP", "desc": "Summon creature group", "params": "GroupID, AttackInvoker, AttackScriptOwner"},
        108: {"name": "SMART_ACTION_SET_POWER", "desc": "Set power value", "params": "PowerType, NewPower"},
        109: {"name": "SMART_ACTION_ADD_POWER", "desc": "Add power", "params": "PowerType, Amount"},
        110: {"name": "SMART_ACTION_REMOVE_POWER", "desc": "Remove power", "params": "PowerType, Amount"},
        111: {"name": "SMART_ACTION_GAME_EVENT_STOP", "desc": "Stop game event", "params": "GameEventID"},
        112: {"name": "SMART_ACTION_GAME_EVENT_START", "desc": "Start game event", "params": "GameEventID"},
        113: {"name": "SMART_ACTION_START_CLOSEST_WAYPOINT", "desc": "Start closest waypoint", "params": "WP1-7"},
        114: {"name": "SMART_ACTION_RISE_UP", "desc": "Rise up (fly)", "params": "Distance"},
        115: {"name": "SMART_ACTION_RANDOM_SOUND", "desc": "Play random sound", "params": "SoundID1-4, OnlySelf, Distance"},
        116: {"name": "SMART_ACTION_SET_CORPSE_DELAY", "desc": "Set corpse despawn delay", "params": "Timer"},
        117: {"name": "SMART_ACTION_DISABLE_EVADE", "desc": "Disable evade", "params": "Disabled (0=enabled, 1=disabled)"},
        118: {"name": "SMART_ACTION_GO_SET_GO_STATE", "desc": "Set GO state", "params": "State"},
        119: {"name": "SMART_ACTION_SET_CAN_FLY", "desc": "Set can fly (NOT SUPPORTED)", "params": "CanFly (0/1)"},
        120: {"name": "SMART_ACTION_REMOVE_AURAS_BY_TYPE", "desc": "Remove auras by type (NOT SUPPORTED)", "params": "AuraType"},
        121: {"name": "SMART_ACTION_SET_SIGHT_DIST", "desc": "Set sight distance", "params": "SightDistance"},
        122: {"name": "SMART_ACTION_FLEE", "desc": "Flee from combat", "params": "FleeTime"},
        123: {"name": "SMART_ACTION_ADD_THREAT", "desc": "Add/remove threat", "params": "+Threat, -Threat"},
        124: {"name": "SMART_ACTION_LOAD_EQUIPMENT", "desc": "Load equipment template", "params": "EquipmentID"},
        125: {"name": "SMART_ACTION_TRIGGER_RANDOM_TIMED_EVENT", "desc": "Trigger random timed event", "params": "IDMin, IDMax"},
        126: {"name": "SMART_ACTION_REMOVE_ALL_GAMEOBJECTS", "desc": "Remove all summoned GOs", "params": "NONE"},
        127: {"name": "SMART_ACTION_REMOVE_MOVEMENT", "desc": "Remove movement (NOT SUPPORTED)", "params": "NONE"},
        128: {"name": "SMART_ACTION_PLAY_ANIMKIT", "desc": "Play animkit (N/A 3.3.5a)", "params": "AnimKitID"},
        134: {"name": "SMART_ACTION_INVOKER_CAST", "desc": "Invoker casts spell", "params": "SpellID, CastFlags, TriggerFlags, TargetsLimit"},
        135: {"name": "SMART_ACTION_PLAY_CINEMATIC", "desc": "Play cinematic", "params": "CinematicEntry"},
        136: {"name": "SMART_ACTION_SET_MOVEMENT_SPEED", "desc": "Set movement speed", "params": "MovementType, SpeedInteger, SpeedFraction"},
        142: {"name": "SMART_ACTION_SET_HEALTH_PCT", "desc": "Set health percentage", "params": "HPPercent"},
        # AC Custom Actions (200+)
        201: {"name": "SMART_ACTION_MOVE_TO_POS_TARGET", "desc": "Move to target position (AC)", "params": "PointID"},
        203: {"name": "SMART_ACTION_EXIT_VEHICLE", "desc": "Exit vehicle (AC)", "params": "NONE"},
        204: {"name": "SMART_ACTION_SET_UNIT_MOVEMENT_FLAGS", "desc": "Set movement flags (AC)", "params": "Flags"},
        205: {"name": "SMART_ACTION_SET_COMBAT_DISTANCE", "desc": "Set combat distance (AC)", "params": "Distance"},
        206: {"name": "SMART_ACTION_DISMOUNT", "desc": "Dismount (AC)", "params": "NONE"},
        207: {"name": "SMART_ACTION_SET_HOVER", "desc": "Set hover (AC)", "params": "Hover (0/1)"},
        208: {"name": "SMART_ACTION_ADD_IMMUNITY", "desc": "Add immunity (AC)", "params": "Type, ID, Value"},
        209: {"name": "SMART_ACTION_REMOVE_IMMUNITY", "desc": "Remove immunity (AC)", "params": "Type, ID, Value"},
        210: {"name": "SMART_ACTION_FALL", "desc": "Fall (AC)", "params": "NONE"},
        211: {"name": "SMART_ACTION_SET_EVENT_FLAG_RESET", "desc": "Set event flag reset (AC)", "params": "Reset (0/1)"},
        212: {"name": "SMART_ACTION_STOP_MOTION", "desc": "Stop motion (AC)", "params": "StopMoving, MovementExpired"},
        213: {"name": "SMART_ACTION_NO_ENVIRONMENT_UPDATE", "desc": "No environment update (AC)", "params": "NONE"},
        214: {"name": "SMART_ACTION_ZONE_UNDER_ATTACK", "desc": "Zone under attack (AC)", "params": "NONE"},
        215: {"name": "SMART_ACTION_LOAD_GRID", "desc": "Load grid (AC)", "params": "NONE"},
        216: {"name": "SMART_ACTION_MUSIC", "desc": "Play music (AC)", "params": "SoundID, OnlySelf, Type"},
        217: {"name": "SMART_ACTION_RANDOM_MUSIC", "desc": "Play random music (AC)", "params": "SoundID1-4, OnlySelf, Type"},
        218: {"name": "SMART_ACTION_CUSTOM_CAST", "desc": "Custom cast (AC)", "params": "SpellID, CastFlags, BP0, BP1, BP2"},
        219: {"name": "SMART_ACTION_CONE_SUMMON", "desc": "Cone summon (AC)", "params": "Entry, Duration, DistBetweenRings, DistBetweenSummons, ConeLength, ConeWidth"},
        220: {"name": "SMART_ACTION_PLAYER_TALK", "desc": "Player talk (AC)", "params": "acore_string.Entry, Yell (0/1)"},
        221: {"name": "SMART_ACTION_VORTEX_SUMMON", "desc": "Vortex summon (AC)", "params": "Entry, Duration, SpiralScaling, SpiralAppearance, RangeMax, PhiDelta"},
        222: {"name": "SMART_ACTION_CU_ENCOUNTER_START", "desc": "Encounter start (AC)", "params": "Resets cooldowns, removes Heroism debuffs"},
        223: {"name": "SMART_ACTION_DO_ACTION", "desc": "Do action (AC)", "params": "ActionID"},
        224: {"name": "SMART_ACTION_ATTACK_STOP", "desc": "Attack stop (AC)", "params": "NONE"},
        225: {"name": "SMART_ACTION_SET_GUID", "desc": "Set GUID (AC)", "params": "Sends invoker/base object GUID to target"},
        226: {"name": "SMART_ACTION_SCRIPTED_SPAWN", "desc": "Scripted spawn (AC)", "params": "State, SpawnTimerMin, SpawnTimerMax, RespawnDelay, CorpseDelay, DontDespawn"},
        227: {"name": "SMART_ACTION_SET_SCALE", "desc": "Set scale (AC)", "params": "Scale"},
        228: {"name": "SMART_ACTION_SUMMON_RADIAL", "desc": "Summon radial (AC)", "params": "Entry, Duration, Repetitions, StartAngle, StepAngle, Distance"},
        229: {"name": "SMART_ACTION_PLAY_SPELL_VISUAL", "desc": "Play spell visual (AC)", "params": "VisualID, VisualIDImpact"},
        230: {"name": "SMART_ACTION_FOLLOW_GROUP", "desc": "Follow group (AC)", "params": "FollowState, FollowType, Distance"},
        231: {"name": "SMART_ACTION_SET_ORIENTATION_TARGET", "desc": "Set orientation to target (AC)", "params": "Type, TargetType, TargetParam1-4"},
        232: {"name": "SMART_ACTION_WAYPOINT_START", "desc": "Start waypoint (AC new)", "params": "PathID, Repeat, PathSource"},
        233: {"name": "SMART_ACTION_WAYPOINT_DATA_RANDOM", "desc": "Random waypoint data (AC)", "params": "PathID1, PathID2, Repeat"},
        234: {"name": "SMART_ACTION_MOVEMENT_STOP", "desc": "Movement stop (AC)", "params": "NONE"},
        235: {"name": "SMART_ACTION_MOVEMENT_PAUSE", "desc": "Movement pause (AC)", "params": "Timer"},
        236: {"name": "SMART_ACTION_MOVEMENT_RESUME", "desc": "Movement resume (AC)", "params": "TimerOverride"},
    }

    # SmartAI target types with parameter documentation
    targets = {
        0: {"name": "SMART_TARGET_NONE", "desc": "No target (self)", "params": "NONE"},
        1: {"name": "SMART_TARGET_SELF", "desc": "Self", "params": "NONE"},
        2: {"name": "SMART_TARGET_VICTIM", "desc": "Current victim (highest aggro)", "params": "NONE"},
        3: {"name": "SMART_TARGET_HOSTILE_SECOND_AGGRO", "desc": "Second highest aggro", "params": "MaxDist, PlayerOnly, PowerType+1, MissingAura"},
        4: {"name": "SMART_TARGET_HOSTILE_LAST_AGGRO", "desc": "Lowest aggro", "params": "MaxDist, PlayerOnly, PowerType+1, MissingAura"},
        5: {"name": "SMART_TARGET_HOSTILE_RANDOM", "desc": "Random hostile on threat list", "params": "MaxDist, PlayerOnly, PowerType+1, MissingAura"},
        6: {"name": "SMART_TARGET_HOSTILE_RANDOM_NOT_TOP", "desc": "Random hostile (not top)", "params": "MaxDist, PlayerOnly, PowerType+1, MissingAura"},
        7: {"name": "SMART_TARGET_ACTION_INVOKER", "desc": "Unit who caused this event", "params": "NONE"},
        8: {"name": "SMART_TARGET_POSITION", "desc": "Position from event params", "params": "Uses x, y, z, o from target coordinates"},
        9: {"name": "SMART_TARGET_CREATURE_RANGE", "desc": "Creature in range", "params": "CreatureEntry (0=any), MinDist, MaxDist, Alive (0=both, 1=alive, 2=dead)"},
        10: {"name": "SMART_TARGET_CREATURE_GUID", "desc": "Creature by GUID", "params": "GUID, Entry"},
        11: {"name": "SMART_TARGET_CREATURE_DISTANCE", "desc": "Creature by distance", "params": "CreatureEntry (0=any), MaxDist, Alive (0=both, 1=alive, 2=dead)"},
        12: {"name": "SMART_TARGET_STORED", "desc": "Previously stored targets", "params": "VarID"},
        13: {"name": "SMART_TARGET_GAMEOBJECT_RANGE", "desc": "GO in range", "params": "Entry (0=any), MinDist, MaxDist"},
        14: {"name": "SMART_TARGET_GAMEOBJECT_GUID", "desc": "GO by GUID", "params": "GUID, Entry"},
        15: {"name": "SMART_TARGET_GAMEOBJECT_DISTANCE", "desc": "GO by distance", "params": "Entry (0=any), MaxDist"},
        16: {"name": "SMART_TARGET_INVOKER_PARTY", "desc": "Invoker's party members", "params": "IncludePets (0/1)"},
        17: {"name": "SMART_TARGET_PLAYER_RANGE", "desc": "Players in range", "params": "MinDist, MaxDist, MaxCount, target.o=1 for all in range"},
        18: {"name": "SMART_TARGET_PLAYER_DISTANCE", "desc": "Players by distance", "params": "MaxDist"},
        19: {"name": "SMART_TARGET_CLOSEST_CREATURE", "desc": "Closest creature", "params": "CreatureEntry (0=any), MaxDist, Dead? (0/1)"},
        20: {"name": "SMART_TARGET_CLOSEST_GAMEOBJECT", "desc": "Closest gameobject", "params": "Entry (0=any), MaxDist"},
        21: {"name": "SMART_TARGET_CLOSEST_PLAYER", "desc": "Closest player", "params": "MaxDist"},
        22: {"name": "SMART_TARGET_ACTION_INVOKER_VEHICLE", "desc": "Invoker's vehicle", "params": "NONE"},
        23: {"name": "SMART_TARGET_OWNER_OR_SUMMONER", "desc": "Owner or summoner", "params": "NONE"},
        24: {"name": "SMART_TARGET_THREAT_LIST", "desc": "All on threat list", "params": "MaxDist, PlayerOnly"},
        25: {"name": "SMART_TARGET_CLOSEST_ENEMY", "desc": "Closest enemy", "params": "MaxDist, PlayerOnly"},
        26: {"name": "SMART_TARGET_CLOSEST_FRIENDLY", "desc": "Closest friendly", "params": "MaxDist, PlayerOnly"},
        27: {"name": "SMART_TARGET_LOOT_RECIPIENTS", "desc": "All players who tagged creature", "params": "NONE"},
        28: {"name": "SMART_TARGET_FARTHEST", "desc": "Farthest target", "params": "MaxDist, PlayerOnly, IsInLOS, MinDist"},
        29: {"name": "SMART_TARGET_VEHICLE_PASSENGER", "desc": "Vehicle passenger", "params": "SeatNumber"},
        # AC Custom Targets (200+)
        201: {"name": "SMART_TARGET_PLAYER_WITH_AURA", "desc": "Player with/without aura (AC)", "params": "SpellID, Negation, MaxDist, MinDist, target.o=resize list"},
        202: {"name": "SMART_TARGET_RANDOM_POINT", "desc": "Random point (AC)", "params": "Range, Amount, SelfAsMiddle (0/1) else use xyz"},
        203: {"name": "SMART_TARGET_ROLE_SELECTION", "desc": "By role (AC)", "params": "RangeMax, TargetMask (1=Tank, 2=Healer, 4=Damage), ResizeList"},
        204: {"name": "SMART_TARGET_SUMMONED_CREATURES", "desc": "Summoned creatures (AC)", "params": "Entry"},
        205: {"name": "SMART_TARGET_INSTANCE_STORAGE", "desc": "Instance storage (AC)", "params": "DataIndex, Type (1=creature, 2=gameobject)"},
    }

    result = {}

    if event_type is not None:
        event_info = events.get(event_type)
        if event_info:
            result["event_type"] = {
                "id": event_type,
                "name": event_info["name"],
                "description": event_info["desc"],
                "parameters": event_info["params"]
            }
        else:
            result["event_type"] = {"error": f"Unknown event type: {event_type}"}

    if action_type is not None:
        action_info = actions.get(action_type)
        if action_info:
            result["action_type"] = {
                "id": action_type,
                "name": action_info["name"],
                "description": action_info["desc"],
                "parameters": action_info["params"]
            }
        else:
            result["action_type"] = {"error": f"Unknown action type: {action_type}"}

    if target_type is not None:
        target_info = targets.get(target_type)
        if target_info:
            result["target_type"] = {
                "id": target_type,
                "name": target_info["name"],
                "description": target_info["desc"],
                "parameters": target_info["params"]
            }
        else:
            result["target_type"] = {"error": f"Unknown target type: {target_type}"}

    if not result:
        return json.dumps({
            "error": "Please provide at least one of: event_type, action_type, target_type",
            "hint": "Example: explain_smart_script(event_type=4) for SMART_EVENT_AGGRO"
        })

    return json.dumps(result, indent=2)


@mcp.tool()
def get_smartai_source(
    event_type: int = None,
    action_type: int = None,
    target_type: int = None,
    context_lines: int = 50
) -> str:
    """
    Get the actual C++ implementation from AzerothCore source for SmartAI types.
    Reads directly from SmartScript.cpp to show exactly how each type is handled.

    Args:
        event_type: SmartAI event type number (handled in SmartScript::ProcessEvent)
        action_type: SmartAI action type number (handled in SmartScript::ProcessAction)
        target_type: SmartAI target type number (handled in SmartScript::GetTargets)
        context_lines: Number of lines to extract after the case statement (default 50)

    Returns:
        The actual C++ source code for the requested SmartAI implementation
    """
    smart_script_cpp = AZEROTHCORE_SRC_PATH / "src/server/game/AI/SmartScripts/SmartScript.cpp"

    if not smart_script_cpp.exists():
        return json.dumps({
            "error": f"SmartScript.cpp not found at {smart_script_cpp}",
            "hint": "Set AZEROTHCORE_SRC_PATH environment variable to your AzerothCore directory"
        })

    try:
        content = smart_script_cpp.read_text(encoding='utf-8', errors='ignore')
        lines = content.split('\n')
        results = {}

        def extract_case_block(search_pattern: str, max_lines: int = 50) -> str:
            """Extract a case block from the source code."""
            for i, line in enumerate(lines):
                if search_pattern in line and 'case ' in line:
                    # Found the case, now extract until we hit the next case or break at same indent
                    block_lines = [lines[i]]
                    brace_depth = 0
                    started = False

                    for j in range(i + 1, min(i + max_lines + 50, len(lines))):
                        block_lines.append(lines[j])

                        # Track braces to know when block ends
                        brace_depth += lines[j].count('{') - lines[j].count('}')

                        if '{' in lines[j]:
                            started = True

                        # Check for end of case block
                        stripped = lines[j].strip()
                        if started and brace_depth <= 0 and (stripped.startswith('break;') or stripped.startswith('case ') or stripped.startswith('default:')):
                            if stripped.startswith('break;'):
                                break
                            else:
                                # Remove the next case line we accidentally included
                                block_lines.pop()
                                break

                        if len(block_lines) >= max_lines:
                            block_lines.append("... [truncated]")
                            break

                    return '\n'.join(block_lines)

            return None

        if event_type is not None:
            # Events are processed in ProcessEvent
            pattern = f"SMART_EVENT_{event_type}" if event_type < 100 else f"case {event_type}:"
            # Try to find the enum name first
            event_names = {
                0: "SMART_EVENT_UPDATE_IC", 1: "SMART_EVENT_UPDATE_OOC", 2: "SMART_EVENT_HEALTH_PCT",
                3: "SMART_EVENT_MANA_PCT", 4: "SMART_EVENT_AGGRO", 5: "SMART_EVENT_KILL",
                6: "SMART_EVENT_DEATH", 7: "SMART_EVENT_EVADE", 8: "SMART_EVENT_SPELLHIT",
                # Add more as needed
            }
            enum_name = event_names.get(event_type, f"SMART_EVENT_{event_type}")
            source = extract_case_block(enum_name, context_lines)
            if source:
                results["event_implementation"] = {
                    "type": event_type,
                    "file": "SmartScript.cpp",
                    "function": "ProcessEvent",
                    "source": source
                }
            else:
                results["event_implementation"] = {"error": f"Could not find case for event_type {event_type}"}

        if action_type is not None:
            # Actions are processed in ProcessAction
            action_names = {
                0: "SMART_ACTION_NONE", 1: "SMART_ACTION_TALK", 2: "SMART_ACTION_SET_FACTION",
                11: "SMART_ACTION_CAST", 12: "SMART_ACTION_SUMMON_CREATURE", 41: "SMART_ACTION_FORCE_DESPAWN",
                45: "SMART_ACTION_SET_DATA", 80: "SMART_ACTION_CALL_TIMED_ACTIONLIST",
                # Add more as needed
            }
            enum_name = action_names.get(action_type, f"SMART_ACTION_{action_type}")
            source = extract_case_block(enum_name, context_lines)
            if source:
                results["action_implementation"] = {
                    "type": action_type,
                    "file": "SmartScript.cpp",
                    "function": "ProcessAction",
                    "source": source
                }
            else:
                results["action_implementation"] = {"error": f"Could not find case for action_type {action_type}"}

        if target_type is not None:
            # Targets are resolved in GetTargets
            target_names = {
                0: "SMART_TARGET_NONE", 1: "SMART_TARGET_SELF", 2: "SMART_TARGET_VICTIM",
                5: "SMART_TARGET_HOSTILE_RANDOM", 7: "SMART_TARGET_ACTION_INVOKER",
                12: "SMART_TARGET_STORED", 19: "SMART_TARGET_CLOSEST_CREATURE",
                21: "SMART_TARGET_CLOSEST_PLAYER", 24: "SMART_TARGET_THREAT_LIST",
                25: "SMART_TARGET_CLOSEST_ENEMY", 26: "SMART_TARGET_CLOSEST_FRIENDLY",
            }
            enum_name = target_names.get(target_type, f"SMART_TARGET_{target_type}")
            source = extract_case_block(enum_name, context_lines)
            if source:
                results["target_implementation"] = {
                    "type": target_type,
                    "file": "SmartScript.cpp",
                    "function": "GetTargets",
                    "source": source
                }
            else:
                results["target_implementation"] = {"error": f"Could not find case for target_type {target_type}"}

        if not results:
            return json.dumps({
                "error": "Please provide at least one of: event_type, action_type, target_type",
                "hint": "Example: get_smartai_source(target_type=25) for SMART_TARGET_CLOSEST_ENEMY"
            })

        return json.dumps(results, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def search_azerothcore_source(
    pattern: str,
    file_pattern: str = "*.cpp",
    max_results: int = 10,
    context_lines: int = 3
) -> str:
    """
    Search the AzerothCore source code for a pattern.
    Useful for finding implementations, definitions, or usages.

    Args:
        pattern: Text or regex pattern to search for
        file_pattern: Glob pattern for files to search (default: *.cpp)
        max_results: Maximum number of matches to return (default: 10)
        context_lines: Lines of context before/after match (default: 3)

    Returns:
        Matching source code snippets with file locations
    """
    src_path = AZEROTHCORE_SRC_PATH / "src"

    if not src_path.exists():
        return json.dumps({
            "error": f"AzerothCore source not found at {src_path}",
            "hint": "Set AZEROTHCORE_SRC_PATH environment variable"
        })

    try:
        results = []
        pattern_lower = pattern.lower()

        for filepath in src_path.glob(f"**/{file_pattern}"):
            try:
                content = filepath.read_text(encoding='utf-8', errors='ignore')
                lines = content.split('\n')

                for i, line in enumerate(lines):
                    if pattern_lower in line.lower() or (pattern in line):
                        # Extract context
                        start = max(0, i - context_lines)
                        end = min(len(lines), i + context_lines + 1)
                        snippet = '\n'.join(f"{start + j + 1}: {lines[start + j]}" for j in range(end - start))

                        results.append({
                            "file": str(filepath.relative_to(AZEROTHCORE_SRC_PATH)),
                            "line": i + 1,
                            "snippet": snippet
                        })

                        if len(results) >= max_results:
                            break

            except Exception:
                continue

            if len(results) >= max_results:
                break

        if not results:
            return json.dumps({"message": f"No matches found for '{pattern}' in {file_pattern}"})

        return json.dumps({
            "matches": len(results),
            "results": results
        }, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def read_source_file(
    relative_path: str,
    start_line: int = 1,
    num_lines: int = 100
) -> str:
    """
    Read a specific file from the AzerothCore source code.

    Args:
        relative_path: Path relative to AzerothCore root (e.g., "src/server/game/AI/SmartScripts/SmartScript.cpp")
        start_line: Line number to start reading from (default: 1)
        num_lines: Number of lines to read (default: 100)

    Returns:
        The requested source code with line numbers
    """
    filepath = AZEROTHCORE_SRC_PATH / relative_path

    if not filepath.exists():
        return json.dumps({
            "error": f"File not found: {filepath}",
            "hint": f"Path should be relative to {AZEROTHCORE_SRC_PATH}"
        })

    try:
        content = filepath.read_text(encoding='utf-8', errors='ignore')
        lines = content.split('\n')

        # Adjust for 1-based line numbers
        start_idx = max(0, start_line - 1)
        end_idx = min(len(lines), start_idx + num_lines)

        snippet_lines = []
        for i in range(start_idx, end_idx):
            snippet_lines.append(f"{i + 1}: {lines[i]}")

        return json.dumps({
            "file": relative_path,
            "start_line": start_idx + 1,
            "end_line": end_idx,
            "total_lines": len(lines),
            "content": '\n'.join(snippet_lines)
        }, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def trace_script_chain(entryorguid: int, source_type: int = 0, start_event: int = None, max_depth: int = 10) -> str:
    """
    Trace the execution flow of SmartAI scripts for debugging.

    Follows:
    - Event links (link column -> triggers another script ID)
    - Timed action list calls (action_type 80)
    - Random timed action lists (action_type 87, 88)
    - SetData triggers (action_type 45 -> can trigger event_type 38)
    - Timed events (action_type 67 creates, event_type 59 triggers)

    Args:
        entryorguid: Entry or GUID of the creature/gameobject
        source_type: 0=Creature, 1=GameObject, 2=AreaTrigger, etc.
        start_event: Optional - only trace from scripts with this event_type
        max_depth: Maximum recursion depth for following chains (default 10)

    Returns:
        Visual execution flow showing script chains and their triggers
    """
    # Event type names for readable output
    event_names = {
        0: "UPDATE_IC", 1: "UPDATE_OOC", 2: "HEALTH_PCT", 3: "MANA_PCT",
        4: "AGGRO", 5: "KILL", 6: "DEATH", 7: "EVADE", 8: "SPELLHIT",
        9: "RANGE", 10: "OOC_LOS", 11: "RESPAWN", 12: "TARGET_HEALTH_PCT",
        17: "SUMMONED_UNIT", 19: "ACCEPTED_QUEST", 20: "REWARD_QUEST",
        21: "REACHED_HOME", 22: "RECEIVE_EMOTE", 25: "RESET", 26: "IC_LOS",
        34: "MOVEMENTINFORM", 37: "AI_INIT", 38: "DATA_SET", 39: "WAYPOINT_START",
        40: "WAYPOINT_REACHED", 52: "TEXT_OVER", 54: "JUST_SUMMONED",
        58: "WAYPOINT_ENDED", 59: "TIMED_EVENT_TRIGGERED", 60: "UPDATE",
        61: "LINK", 62: "GOSSIP_SELECT", 63: "JUST_CREATED", 64: "GOSSIP_HELLO",
        66: "EVENT_PHASE_CHANGE", 77: "COUNTER_SET", 82: "SUMMONED_UNIT_DIES",
        83: "ON_SPELL_CAST", 86: "ON_DESPAWN",
    }

    # Action type names for readable output
    action_names = {
        1: "TALK", 2: "SET_FACTION", 11: "CAST", 12: "SUMMON_CREATURE",
        22: "SET_EVENT_PHASE", 23: "INC_EVENT_PHASE", 24: "EVADE",
        29: "FOLLOW", 37: "DIE", 41: "FORCE_DESPAWN", 45: "SET_DATA",
        53: "WP_START", 54: "WP_PAUSE", 55: "WP_STOP", 63: "SET_COUNTER",
        67: "CREATE_TIMED_EVENT", 69: "MOVE_TO_POS", 73: "TRIGGER_TIMED_EVENT",
        80: "CALL_TIMED_ACTIONLIST", 85: "SELF_CAST",
        87: "CALL_RANDOM_TIMED_ACTIONLIST", 88: "CALL_RANDOM_RANGE_TIMED_ACTIONLIST",
    }

    # Target type names
    target_names = {
        0: "NONE", 1: "SELF", 2: "VICTIM", 5: "HOSTILE_RANDOM",
        7: "ACTION_INVOKER", 8: "POSITION", 12: "STORED",
        17: "PLAYER_RANGE", 19: "CLOSEST_CREATURE", 21: "CLOSEST_PLAYER",
        23: "OWNER_OR_SUMMONER", 24: "THREAT_LIST",
    }

    def get_event_name(event_type):
        return event_names.get(event_type, f"EVENT_{event_type}")

    def get_action_name(action_type):
        return action_names.get(action_type, f"ACTION_{action_type}")

    def get_target_name(target_type):
        return target_names.get(target_type, f"TARGET_{target_type}")

    try:
        # Get all scripts for this entity
        scripts = execute_query(
            """SELECT * FROM smart_scripts
               WHERE entryorguid = %s AND source_type = %s
               ORDER BY id""",
            "world",
            (entryorguid, source_type)
        )

        if not scripts:
            return json.dumps({
                "error": f"No scripts found for entryorguid={entryorguid}, source_type={source_type}"
            })

        # Build a lookup by script ID
        script_by_id = {s["id"]: s for s in scripts}

        # Track visited to prevent infinite loops
        visited = set()

        # Store the trace results
        trace_results = []

        # Timed action lists we need to fetch
        timed_lists_to_fetch = set()

        # Data triggers we discover
        data_triggers = []

        # Timed events created
        timed_events = []

        def format_script(script, indent=0):
            """Format a single script line for display."""
            prefix = "  " * indent
            event = get_event_name(script["event_type"])
            action = get_action_name(script["action_type"])
            target = get_target_name(script["target_type"])

            # Build param info
            params = []
            if script["event_param1"] or script["event_param2"]:
                params.append(f"event_params=({script['event_param1']},{script['event_param2']},{script['event_param3']},{script['event_param4']})")
            if script["action_param1"] or script["action_param2"]:
                params.append(f"action_params=({script['action_param1']},{script['action_param2']},{script['action_param3']},{script['action_param4']},{script['action_param5']},{script['action_param6']})")

            param_str = " " + " ".join(params) if params else ""

            # Phase info
            phase_str = ""
            if script["event_phase_mask"] != 0:
                phase_str = f" [phase_mask={script['event_phase_mask']}]"

            # Chance info
            chance_str = ""
            if script["event_chance"] != 100:
                chance_str = f" [{script['event_chance']}% chance]"

            comment = script.get("comment", "")
            comment_str = f' -- "{comment}"' if comment else ""

            return f"{prefix}[{script['id']}] {event} -> {action} @ {target}{phase_str}{chance_str}{param_str}{comment_str}"

        def trace_script(script_id, depth=0):
            """Recursively trace a script and its chains."""
            if depth > max_depth:
                return [f"{'  ' * depth}... (max depth reached)"]

            if script_id in visited:
                return [f"{'  ' * depth}-> [LOOP] Already visited script {script_id}"]

            if script_id not in script_by_id:
                return [f"{'  ' * depth}-> [ERROR] Script ID {script_id} not found!"]

            visited.add(script_id)
            script = script_by_id[script_id]
            lines = [format_script(script, depth)]

            action_type = script["action_type"]

            # Check for timed action list calls
            if action_type == 80:  # CALL_TIMED_ACTIONLIST
                list_id = script["action_param1"]
                if list_id:
                    timed_lists_to_fetch.add(list_id)
                    lines.append(f"{'  ' * (depth+1)}-> CALLS TimedActionList {list_id}")

            # Check for random timed action list calls
            elif action_type == 87:  # CALL_RANDOM_TIMED_ACTIONLIST
                for i in range(1, 7):
                    list_id = script.get(f"action_param{i}")
                    if list_id:
                        timed_lists_to_fetch.add(list_id)
                lines.append(f"{'  ' * (depth+1)}-> CALLS RANDOM TimedActionList from params")

            elif action_type == 88:  # CALL_RANDOM_RANGE_TIMED_ACTIONLIST
                start_id = script["action_param1"]
                end_id = script["action_param2"]
                if start_id and end_id:
                    for list_id in range(start_id, end_id + 1):
                        timed_lists_to_fetch.add(list_id)
                    lines.append(f"{'  ' * (depth+1)}-> CALLS RANDOM TimedActionList {start_id}-{end_id}")

            # Check for SetData (can trigger DATA_SET events on other creatures)
            elif action_type == 45:  # SET_DATA
                data_id = script["action_param1"]
                data_value = script["action_param2"]
                data_triggers.append({
                    "from_script": script_id,
                    "data_id": data_id,
                    "data_value": data_value,
                    "target": get_target_name(script["target_type"])
                })
                lines.append(f"{'  ' * (depth+1)}-> SETS DATA id={data_id} value={data_value} on {get_target_name(script['target_type'])}")

            # Check for timed event creation
            elif action_type == 67:  # CREATE_TIMED_EVENT
                event_id = script["action_param1"]
                min_time = script["action_param2"]
                max_time = script["action_param3"]
                timed_events.append({
                    "event_id": event_id,
                    "min_time": min_time,
                    "max_time": max_time,
                    "from_script": script_id
                })
                lines.append(f"{'  ' * (depth+1)}-> CREATES TimedEvent {event_id} (fires in {min_time}-{max_time}ms)")

            # Check for timed event trigger
            elif action_type == 73:  # TRIGGER_TIMED_EVENT
                event_id = script["action_param1"]
                lines.append(f"{'  ' * (depth+1)}-> TRIGGERS TimedEvent {event_id}")

            # Follow link chains
            link = script.get("link", 0)
            if link and link != 0:
                lines.append(f"{'  ' * (depth+1)}-> LINKS TO script {link}:")
                lines.extend(trace_script(link, depth + 2))

            return lines

        # Filter scripts by start_event if specified
        if start_event is not None:
            entry_scripts = [s for s in scripts if s["event_type"] == start_event]
        else:
            entry_scripts = scripts

        # Trace each entry point
        for script in entry_scripts:
            if script["id"] not in visited:
                trace_results.append(f"\n=== Event: {get_event_name(script['event_type'])} ===")
                trace_results.extend(trace_script(script["id"]))

        # Fetch and trace timed action lists
        timed_list_traces = {}
        for list_id in timed_lists_to_fetch:
            timed_scripts = execute_query(
                """SELECT * FROM smart_scripts
                   WHERE entryorguid = %s AND source_type = 9
                   ORDER BY id""",
                "world",
                (list_id,)
            )
            if timed_scripts:
                timed_list_traces[list_id] = timed_scripts

        # Format timed action lists
        if timed_list_traces:
            trace_results.append("\n" + "=" * 50)
            trace_results.append("TIMED ACTION LISTS REFERENCED:")
            trace_results.append("=" * 50)

            for list_id, timed_scripts in timed_list_traces.items():
                trace_results.append(f"\n--- TimedActionList {list_id} ---")
                for ts in timed_scripts:
                    delay = ts.get("event_param1", 0)
                    action = get_action_name(ts["action_type"])
                    target = get_target_name(ts["target_type"])
                    comment = ts.get("comment", "")

                    # Action-specific details
                    detail = ""
                    if ts["action_type"] == 11:  # CAST
                        detail = f" spell={ts['action_param1']}"
                    elif ts["action_type"] == 1:  # TALK
                        detail = f" group={ts['action_param1']}"
                    elif ts["action_type"] == 12:  # SUMMON
                        detail = f" creature={ts['action_param1']}"

                    trace_results.append(f"  [{ts['id']}] +{delay}ms: {action}{detail} @ {target} -- {comment}")

        # Show data triggers if any
        if data_triggers:
            trace_results.append("\n" + "=" * 50)
            trace_results.append("DATA TRIGGERS (may trigger DATA_SET events on targets):")
            trace_results.append("=" * 50)
            for dt in data_triggers:
                trace_results.append(f"  Script {dt['from_script']}: SET_DATA({dt['data_id']}, {dt['data_value']}) -> {dt['target']}")

        # Show timed events if any
        if timed_events:
            trace_results.append("\n" + "=" * 50)
            trace_results.append("TIMED EVENTS CREATED:")
            trace_results.append("=" * 50)
            for te in timed_events:
                trace_results.append(f"  Script {te['from_script']}: Event {te['event_id']} (triggers in {te['min_time']}-{te['max_time']}ms)")

            # Check if there are scripts waiting for these events
            trace_results.append("\nScripts listening for TIMED_EVENT_TRIGGERED (event_type=59):")
            for te in timed_events:
                listeners = [s for s in scripts if s["event_type"] == 59 and s["event_param1"] == te["event_id"]]
                if listeners:
                    for l in listeners:
                        trace_results.append(f"  -> Script {l['id']} listens for event {te['event_id']}")
                else:
                    trace_results.append(f"  -> [WARNING] No script found listening for event {te['event_id']}!")

        # Summary
        trace_results.append("\n" + "=" * 50)
        trace_results.append("SUMMARY:")
        trace_results.append("=" * 50)
        trace_results.append(f"  Total scripts: {len(scripts)}")
        trace_results.append(f"  Scripts traced: {len(visited)}")
        trace_results.append(f"  Timed action lists: {len(timed_list_traces)}")
        trace_results.append(f"  Data triggers: {len(data_triggers)}")
        trace_results.append(f"  Timed events: {len(timed_events)}")

        # Check for potential issues
        issues = []
        for script in scripts:
            # Check for broken links
            link = script.get("link", 0)
            if link and link != 0 and link not in script_by_id:
                issues.append(f"Script {script['id']} links to non-existent script {link}")

            # Check for 0% chance
            if script["event_chance"] == 0:
                issues.append(f"Script {script['id']} has 0% event_chance (will never trigger)")

        if issues:
            trace_results.append("\n[!] POTENTIAL ISSUES DETECTED:")
            for issue in issues:
                trace_results.append(f"  - {issue}")

        return "\n".join(trace_results)

    except Exception as e:
        return json.dumps({"error": str(e)})


# =============================================================================
# WIKI / DOCUMENTATION TOOLS
# =============================================================================

@mcp.tool()
def search_wiki(query: str, max_results: int = 10) -> str:
    """
    Search the AzerothCore wiki documentation for relevant information.

    Args:
        query: Search terms (searches file names and content)
        max_results: Maximum number of results to return

    Returns:
        List of matching wiki pages with snippets
    """
    results = []
    query_lower = query.lower()
    query_terms = query_lower.split()

    try:
        # Search through all markdown files in wiki
        for md_file in WIKI_PATH.glob("*.md"):
            try:
                content = md_file.read_text(encoding='utf-8', errors='ignore')
                content_lower = content.lower()
                filename_lower = md_file.stem.lower()

                # Score based on matches
                score = 0

                # Filename matches are worth more
                for term in query_terms:
                    if term in filename_lower:
                        score += 10
                    if term in content_lower:
                        score += content_lower.count(term)

                if score > 0:
                    # Extract a relevant snippet
                    snippet = ""
                    for term in query_terms:
                        idx = content_lower.find(term)
                        if idx != -1:
                            start = max(0, idx - 100)
                            end = min(len(content), idx + 200)
                            snippet = "..." + content[start:end].replace("\n", " ").strip() + "..."
                            break

                    results.append({
                        "file": md_file.name,
                        "score": score,
                        "snippet": snippet[:300] if snippet else content[:200].replace("\n", " ") + "..."
                    })
            except Exception:
                continue

        # Sort by score and limit results
        results.sort(key=lambda x: x["score"], reverse=True)
        results = results[:max_results]

        return json.dumps(results, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def read_wiki_page(filename: str) -> str:
    """
    Read a specific wiki documentation page.

    Args:
        filename: The wiki file name (e.g., 'smart_scripts.md', 'creature_template.md')

    Returns:
        The content of the wiki page (may be truncated if very large)
    """
    try:
        wiki_file = WIKI_PATH / filename
        if not wiki_file.exists():
            # Try adding .md extension
            wiki_file = WIKI_PATH / f"{filename}.md"

        if not wiki_file.exists():
            return json.dumps({
                "error": f"Wiki page '{filename}' not found",
                "hint": "Use search_wiki to find available pages"
            })

        content = wiki_file.read_text(encoding='utf-8', errors='ignore')

        # Truncate if too large
        max_size = 50000
        if len(content) > max_size:
            return json.dumps({
                "warning": f"Content truncated (original: {len(content)} chars)",
                "content": content[:max_size] + "\n\n... [TRUNCATED - use search_wiki for specific sections] ..."
            }, indent=2)

        return content
    except Exception as e:
        return json.dumps({"error": str(e)})


# =============================================================================
# GAMEOBJECT TOOLS
# =============================================================================

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


# =============================================================================
# SPELL TOOLS
# =============================================================================

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


# =============================================================================
# QUEST TOOLS
# =============================================================================

@mcp.tool()
def get_quest_template(quest_id: int) -> str:
    """
    Get quest_template data by ID.

    Args:
        quest_id: The quest ID

    Returns:
        Complete quest template data
    """
    try:
        results = execute_query(
            "SELECT * FROM quest_template WHERE ID = %s",
            "world",
            (quest_id,)
        )
        if not results:
            return json.dumps({"error": f"No quest found with ID {quest_id}"})
        return json.dumps(results[0], indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def search_quests(name_pattern: str, limit: int = 20) -> str:
    """
    Search for quests by name.

    Args:
        name_pattern: Quest name pattern
        limit: Maximum results

    Returns:
        Matching quests with ID, title, and level
    """
    try:
        results = execute_query(
            f"SELECT ID, LogTitle, QuestLevel, MinLevel FROM quest_template WHERE LogTitle LIKE %s LIMIT {min(limit, 100)}",
            "world",
            (f"%{name_pattern}%",)
        )
        return json.dumps(results, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def diagnose_quest(quest_id: int) -> str:
    """
    Comprehensive diagnostic tool for debugging quest issues.
    Gathers all related data from multiple tables in one call.

    Args:
        quest_id: The quest ID to diagnose

    Returns:
        JSON with:
        - quest_template: Basic quest data (title, level, objectives, rewards)
        - quest_addon: Chain info (PrevQuestID, NextQuestID, ExclusiveGroup)
        - quest_givers: NPCs/GameObjects that start this quest
        - quest_enders: NPCs/GameObjects that complete this quest
        - required_items: Items needed with names
        - required_npcs_or_gos: Creatures to kill/interact with or gameobjects
        - reward_items: Items given on completion with names
        - conditions: Any conditions that must be met
        - smart_scripts: Related SAI scripts (source_type=5 for quest scripts)
        - quest_chain: Previous and next quests in chain
        - potential_issues: Auto-detected problems
    """
    try:
        results = {}
        issues = []

        # 1. Get quest_template
        quest = execute_query(
            "SELECT * FROM quest_template WHERE ID = %s",
            "world",
            (quest_id,)
        )
        if not quest:
            return json.dumps({"error": f"Quest {quest_id} not found"})
        results["quest_template"] = quest[0]
        q = quest[0]

        # 2. Get quest_template_addon (chain info)
        addon = execute_query(
            "SELECT * FROM quest_template_addon WHERE ID = %s",
            "world",
            (quest_id,)
        )
        results["quest_addon"] = addon[0] if addon else None

        # 3. Get quest givers (creatures)
        creature_starters = execute_query(
            """SELECT cs.id as npc_entry, ct.name
               FROM creature_queststarter cs
               JOIN creature_template ct ON cs.id = ct.entry
               WHERE cs.quest = %s""",
            "world",
            (quest_id,)
        )
        # Get quest givers (gameobjects)
        go_starters = execute_query(
            """SELECT gs.id as go_entry, gt.name
               FROM gameobject_queststarter gs
               JOIN gameobject_template gt ON gs.id = gt.entry
               WHERE gs.quest = %s""",
            "world",
            (quest_id,)
        )
        results["quest_givers"] = {
            "creatures": creature_starters,
            "gameobjects": go_starters
        }
        if not creature_starters and not go_starters:
            issues.append("WARNING: No quest givers found!")

        # 4. Get quest enders (creatures)
        creature_enders = execute_query(
            """SELECT ce.id as npc_entry, ct.name
               FROM creature_questender ce
               JOIN creature_template ct ON ce.id = ct.entry
               WHERE ce.quest = %s""",
            "world",
            (quest_id,)
        )
        # Get quest enders (gameobjects)
        go_enders = execute_query(
            """SELECT ge.id as go_entry, gt.name
               FROM gameobject_questender ge
               JOIN gameobject_template gt ON ge.id = gt.entry
               WHERE ge.quest = %s""",
            "world",
            (quest_id,)
        )
        results["quest_enders"] = {
            "creatures": creature_enders,
            "gameobjects": go_enders
        }
        if not creature_enders and not go_enders:
            issues.append("WARNING: No quest enders found!")

        # 5. Get required items with names
        required_items = []
        for i in range(1, 7):
            item_id = q.get(f"RequiredItemId{i}", 0)
            count = q.get(f"RequiredItemCount{i}", 0)
            if item_id and count:
                item = execute_query(
                    "SELECT name FROM item_template WHERE entry = %s",
                    "world",
                    (item_id,)
                )
                required_items.append({
                    "entry": item_id,
                    "name": item[0]["name"] if item else "UNKNOWN",
                    "count": count
                })
        results["required_items"] = required_items

        # 6. Get required NPCs/GOs to kill/interact
        required_npcs = []
        for i in range(1, 5):
            npc_or_go = q.get(f"RequiredNpcOrGo{i}", 0)
            count = q.get(f"RequiredNpcOrGoCount{i}", 0)
            if npc_or_go and count:
                if npc_or_go > 0:  # Creature
                    creature = execute_query(
                        "SELECT name FROM creature_template WHERE entry = %s",
                        "world",
                        (npc_or_go,)
                    )
                    required_npcs.append({
                        "type": "creature",
                        "entry": npc_or_go,
                        "name": creature[0]["name"] if creature else "UNKNOWN",
                        "count": count
                    })
                else:  # GameObject (negative value)
                    go = execute_query(
                        "SELECT name FROM gameobject_template WHERE entry = %s",
                        "world",
                        (abs(npc_or_go),)
                    )
                    required_npcs.append({
                        "type": "gameobject",
                        "entry": abs(npc_or_go),
                        "name": go[0]["name"] if go else "UNKNOWN",
                        "count": count
                    })
        results["required_npcs_or_gos"] = required_npcs

        # 7. Get reward items with names
        reward_items = []
        for i in range(1, 5):
            item_id = q.get(f"RewardItem{i}", 0)
            count = q.get(f"RewardAmount{i}", 0)
            if item_id and count:
                item = execute_query(
                    "SELECT name FROM item_template WHERE entry = %s",
                    "world",
                    (item_id,)
                )
                reward_items.append({
                    "entry": item_id,
                    "name": item[0]["name"] if item else "UNKNOWN",
                    "count": count
                })
        results["reward_items"] = reward_items

        # 8. Get choice reward items with names
        reward_choice_items = []
        for i in range(1, 7):
            item_id = q.get(f"RewardChoiceItemID{i}", 0)
            count = q.get(f"RewardChoiceItemQuantity{i}", 0)
            if item_id and count:
                item = execute_query(
                    "SELECT name FROM item_template WHERE entry = %s",
                    "world",
                    (item_id,)
                )
                reward_choice_items.append({
                    "entry": item_id,
                    "name": item[0]["name"] if item else "UNKNOWN",
                    "count": count
                })
        results["reward_choice_items"] = reward_choice_items

        # 9. Get conditions for this quest (SourceTypeOrReferenceId 19 = QUEST_AVAILABLE, 20 = QUEST_SHOW_MARK)
        conditions = execute_query(
            """SELECT * FROM conditions
               WHERE (SourceTypeOrReferenceId IN (19, 20) AND SourceEntry = %s)
                  OR (SourceTypeOrReferenceId = 6 AND SourceGroup = %s)""",
            "world",
            (quest_id, quest_id)
        )
        results["conditions"] = conditions

        # 10. Get related SmartAI scripts (source_type 5 = Quest)
        scripts = execute_query(
            "SELECT * FROM smart_scripts WHERE source_type = 5 AND entryorguid = %s ORDER BY id",
            "world",
            (quest_id,)
        )
        results["smart_scripts"] = scripts

        # 11. Get quest chain
        chain = {"previous": [], "next": []}
        if addon and addon[0].get("PrevQuestID"):
            prev_id = addon[0]["PrevQuestID"]
            prev_quest = execute_query(
                "SELECT ID, LogTitle FROM quest_template WHERE ID = %s",
                "world",
                (abs(prev_id),)
            )
            if prev_quest:
                chain["previous"].append({
                    "id": prev_id,
                    "title": prev_quest[0].get("LogTitle"),
                    "type": "required" if prev_id > 0 else "breadcrumb"
                })
        if addon and addon[0].get("NextQuestID"):
            next_id = addon[0]["NextQuestID"]
            next_quest = execute_query(
                "SELECT ID, LogTitle FROM quest_template WHERE ID = %s",
                "world",
                (next_id,)
            )
            if next_quest:
                chain["next"].append({
                    "id": next_id,
                    "title": next_quest[0].get("LogTitle")
                })
        # Also check RewardNextQuest from quest_template
        if q.get("RewardNextQuest"):
            next_id = q["RewardNextQuest"]
            if not any(n["id"] == next_id for n in chain["next"]):
                next_quest = execute_query(
                    "SELECT ID, LogTitle FROM quest_template WHERE ID = %s",
                    "world",
                    (next_id,)
                )
                if next_quest:
                    chain["next"].append({
                        "id": next_id,
                        "title": next_quest[0].get("LogTitle"),
                        "source": "RewardNextQuest"
                    })
        results["quest_chain"] = chain

        # 12. Auto-detect potential issues
        if q.get("MinLevel", 0) > q.get("QuestLevel", 0) > 0:
            issues.append(f"MinLevel ({q['MinLevel']}) > QuestLevel ({q['QuestLevel']})")

        if q.get("AllowableRaces", 0) == 0:
            issues.append("AllowableRaces is 0 - quest may not be available to any race")

        # Check if required items exist
        for item in required_items:
            if item["name"] == "UNKNOWN":
                issues.append(f"Required item {item['entry']} does not exist in item_template!")

        # Check if required NPCs/GOs exist
        for npc in required_npcs:
            if npc["name"] == "UNKNOWN":
                issues.append(f"Required {npc['type']} {npc['entry']} does not exist!")

        results["potential_issues"] = issues

        return json.dumps(results, indent=2, default=str)

    except Exception as e:
        return json.dumps({"error": str(e)})


# =============================================================================
# ITEM TOOLS
# =============================================================================

@mcp.tool()
def get_item_template(entry: int) -> str:
    """
    Get item_template data by entry ID.

    Args:
        entry: The item entry ID

    Returns:
        Complete item template data
    """
    try:
        results = execute_query(
            "SELECT * FROM item_template WHERE entry = %s",
            "world",
            (entry,)
        )
        if not results:
            return json.dumps({"error": f"No item found with entry {entry}"})
        return json.dumps(results[0], indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def search_items(name_pattern: str, limit: int = 20) -> str:
    """
    Search for items by name.

    Args:
        name_pattern: Item name pattern
        limit: Maximum results

    Returns:
        Matching items with entry, name, and quality
    """
    try:
        results = execute_query(
            f"SELECT entry, name, Quality, ItemLevel FROM item_template WHERE name LIKE %s LIMIT {min(limit, 100)}",
            "world",
            (f"%{name_pattern}%",)
        )
        return json.dumps(results, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


# =============================================================================
# SAI COMMENT GENERATOR (Keira3 Port)
# =============================================================================

@mcp.tool()
def generate_sai_comments(entryorguid: int, source_type: int = 0) -> str:
    """
    Generate human-readable comments for SmartAI scripts using Keira3's comment generator.

    This tool fetches SmartAI scripts and generates descriptive comments explaining
    what each script row does, similar to what Keira3 generates.

    Args:
        entryorguid: The entry or GUID of the creature/gameobject
        source_type: 0=Creature, 1=GameObject, 2=AreaTrigger, 9=TimedActionList

    Returns:
        SmartAI scripts with generated comments
    """
    if not SAI_GENERATOR_AVAILABLE:
        return json.dumps({"error": "SAI comment generator not available. Check sai_comment_generator.py"})

    try:
        # Get the scripts
        scripts = execute_query(
            """SELECT * FROM smart_scripts
               WHERE entryorguid = %s AND source_type = %s
               ORDER BY id""",
            "world",
            (entryorguid, source_type)
        )

        if not scripts:
            return json.dumps({
                "message": f"No SmartAI scripts found for entryorguid={entryorguid}, source_type={source_type}"
            })

        # Get the name
        name = f"Entity {entryorguid}"
        if source_type == 0:  # Creature
            creature = execute_query(
                "SELECT name FROM creature_template WHERE entry = %s",
                "world",
                (abs(entryorguid),)
            )
            if creature:
                name = creature[0].get("name", name)
        elif source_type == 1:  # GameObject
            gameobj = execute_query(
                "SELECT name FROM gameobject_template WHERE entry = %s",
                "world",
                (abs(entryorguid),)
            )
            if gameobj:
                name = gameobj[0].get("name", name)

        # Generate comments
        generator = SaiCommentGenerator(mysql_query_func=_mysql_query_for_sai)
        results = []

        for script in scripts:
            comment = generator.generate_comment(scripts, script, name)
            results.append({
                "id": script.get("id"),
                "event_type": script.get("event_type"),
                "action_type": script.get("action_type"),
                "target_type": script.get("target_type"),
                "comment": comment,
                "full_row": script
            })

        return json.dumps({
            "entity_name": name,
            "entryorguid": entryorguid,
            "source_type": source_type,
            "script_count": len(results),
            "scripts_with_comments": results
        }, indent=2, default=str)

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


@mcp.tool()
def generate_comment_for_script(
    entity_name: str,
    event_type: int,
    action_type: int,
    target_type: int = 1,
    event_param1: int = 0,
    event_param2: int = 0,
    event_param3: int = 0,
    event_param4: int = 0,
    event_param5: int = 0,
    event_param6: int = 0,
    action_param1: int = 0,
    action_param2: int = 0,
    action_param3: int = 0,
    action_param4: int = 0,
    action_param5: int = 0,
    action_param6: int = 0,
    target_param1: int = 0,
    target_param2: int = 0,
    target_param3: int = 0,
    target_param4: int = 0,
    target_o: float = 0,
    event_phase_mask: int = 0,
    event_flags: int = 0,
    source_type: int = 0
) -> str:
    """
    Generate a human-readable comment for a SmartAI script row BEFORE inserting it.
    Use this when creating new SmartAI scripts to get the proper comment field value.

    Args:
        entity_name: Name of the creature/gameobject (e.g. "Hogger")
        event_type: SmartAI event type
        action_type: SmartAI action type
        target_type: SmartAI target type (default 1 = SELF)
        event_param1-6: Event parameters
        action_param1-6: Action parameters
        target_param1-4: Target parameters
        target_o: Target orientation
        event_phase_mask: Phase mask for the event
        event_flags: Event flags (e.g. 1 = NOT_REPEATABLE)
        source_type: 0=Creature, 1=GameObject, 2=AreaTrigger, 9=TimedActionList

    Returns:
        Generated comment string suitable for the 'comment' column
    """
    if not SAI_GENERATOR_AVAILABLE:
        return json.dumps({"error": "SAI comment generator not available"})

    try:
        # Build a script dict matching what the generator expects
        script = {
            "id": 0,
            "link": 0,
            "source_type": source_type,
            "event_type": event_type,
            "event_phase_mask": event_phase_mask,
            "event_flags": event_flags,
            "event_param1": event_param1,
            "event_param2": event_param2,
            "event_param3": event_param3,
            "event_param4": event_param4,
            "event_param5": event_param5,
            "event_param6": event_param6,
            "action_type": action_type,
            "action_param1": action_param1,
            "action_param2": action_param2,
            "action_param3": action_param3,
            "action_param4": action_param4,
            "action_param5": action_param5,
            "action_param6": action_param6,
            "target_type": target_type,
            "target_param1": target_param1,
            "target_param2": target_param2,
            "target_param3": target_param3,
            "target_param4": target_param4,
            "target_o": target_o,
        }

        generator = SaiCommentGenerator(mysql_query_func=_mysql_query_for_sai)
        comment = generator.generate_comment([script], script, entity_name)

        return json.dumps({
            "comment": comment,
            "script_preview": script
        }, indent=2, default=str)

    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def generate_comments_for_scripts_batch(entity_name: str, scripts_json: str) -> str:
    """
    Generate comments for multiple SmartAI script rows at once.
    Use this when creating a full set of scripts for an entity.

    Args:
        entity_name: Name of the creature/gameobject (e.g. "Hogger")
        scripts_json: JSON array of script objects, each with at minimum:
                     event_type, action_type, target_type, and any relevant params

    Example scripts_json:
        [
            {"id": 0, "event_type": 4, "action_type": 11, "action_param1": 12345, "target_type": 2},
            {"id": 1, "event_type": 0, "action_type": 11, "action_param1": 67890, "target_type": 2}
        ]

    Returns:
        The scripts with generated comments added
    """
    if not SAI_GENERATOR_AVAILABLE:
        return json.dumps({"error": "SAI comment generator not available"})

    try:
        scripts = json.loads(scripts_json)

        # Fill in defaults for missing fields
        defaults = {
            "id": 0, "link": 0, "source_type": 0,
            "event_type": 0, "event_phase_mask": 0, "event_flags": 0,
            "event_param1": 0, "event_param2": 0, "event_param3": 0,
            "event_param4": 0, "event_param5": 0, "event_param6": 0,
            "action_type": 0, "action_param1": 0, "action_param2": 0,
            "action_param3": 0, "action_param4": 0, "action_param5": 0,
            "action_param6": 0, "target_type": 1, "target_param1": 0,
            "target_param2": 0, "target_param3": 0, "target_param4": 0,
            "target_o": 0,
        }

        for script in scripts:
            for key, default_val in defaults.items():
                if key not in script:
                    script[key] = default_val

        generator = SaiCommentGenerator(mysql_query_func=_mysql_query_for_sai)

        for script in scripts:
            script["comment"] = generator.generate_comment(scripts, script, entity_name)

        return json.dumps({
            "entity_name": entity_name,
            "script_count": len(scripts),
            "scripts": scripts
        }, indent=2, default=str)

    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON: {e}"})
    except Exception as e:
        return json.dumps({"error": str(e)})


# =============================================================================
# SOAP / WORLDSERVER COMMAND TOOLS
# =============================================================================

@mcp.tool()
def soap_execute_command(command: str) -> str:
    """
    Execute a GM command on a running AzerothCore worldserver via SOAP.

    This allows you to interact with the live server, such as:
    - Server management: server info, server shutdown, server restart
    - Account management: account create, account set gmlevel
    - Character operations: character level, character rename
    - World modifications: reload commands, npc add
    - And any other GM command available in-game

    Args:
        command: The GM command to execute (without leading dot).
                 Example: "server info", "account create testuser testpass"

    Returns:
        JSON with success status and command output or error message.

    Requirements:
        - SOAP must be enabled in worldserver.conf (SOAP.Enabled = 1)
        - Environment variables must be set:
          - SOAP_ENABLED=true
          - SOAP_USERNAME=<admin account>
          - SOAP_PASSWORD=<account password>
        - The account must have administrator privileges (SEC_ADMINISTRATOR)

    Examples:
        - soap_execute_command("server info")
        - soap_execute_command("account create newplayer password123")
        - soap_execute_command("reload creature_template")
    """
    if not SOAP_AVAILABLE:
        return json.dumps({
            "success": False,
            "error": "SOAP client module not available. Check soap_client.py exists."
        })

    if not SOAP_ENABLED:
        return json.dumps({
            "success": False,
            "error": "SOAP is not enabled. Set SOAP_ENABLED=true in environment."
        })

    if _soap_client is None:
        return json.dumps({
            "success": False,
            "error": "SOAP client not configured. Set SOAP_USERNAME and SOAP_PASSWORD."
        })

    try:
        response = _soap_client.execute_command(command)
        return json.dumps({
            "success": response.success,
            "message": response.message if response.success else None,
            "error": response.fault_string if not response.success else None
        }, indent=2)
    except ConnectionError as e:
        return json.dumps({
            "success": False,
            "error": f"Connection failed: {e}"
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


@mcp.tool()
def soap_server_info() -> str:
    """
    Get information about the running AzerothCore worldserver.

    Returns server uptime, connected players, and version information.

    This is a convenience wrapper around soap_execute_command("server info").
    """
    return soap_execute_command("server info")


@mcp.tool()
def soap_reload_table(table_name: str) -> str:
    """
    Reload a database table on the running worldserver.

    This is useful after making database changes to apply them without restart.

    Args:
        table_name: The reload command argument. Common commands include:

            Full table reloads (no arguments needed):
            - smart_scripts
            - conditions
            - gossip_menu
            - gossip_menu_option
            - npc_trainer
            - npc_vendor
            - page_text
            - areatrigger_teleport
            - broadcast_text
            - creature_text

            Entry-specific reloads (append entry ID):
            - creature_template <entry>  (e.g., "creature_template 448")
            - quest_template <quest_id>
            - item_template <entry>
            - gameobject_template <entry>

            Aggregate reloads:
            - all (reload everything)
            - all npc
            - all quest
            - all spell
            - all scripts
            - all gossips
            - all loot

    Returns:
        JSON with success status and reload result.

    Note: Some reload commands may take time on large tables.
    """
    return soap_execute_command(f"reload {table_name}")


@mcp.tool()
def soap_check_connection() -> str:
    """
    Check if the SOAP connection to worldserver is working.

    Returns:
        JSON with connection status and server info if connected.

    Use this to verify SOAP is properly configured before running commands.
    """
    if not SOAP_AVAILABLE:
        return json.dumps({
            "connected": False,
            "error": "SOAP client module not available"
        })

    if not SOAP_ENABLED:
        return json.dumps({
            "connected": False,
            "error": "SOAP not enabled (set SOAP_ENABLED=true)"
        })

    if _soap_client is None:
        return json.dumps({
            "connected": False,
            "error": "SOAP credentials not configured"
        })

    try:
        response = _soap_client.execute_command("server info")
        return json.dumps({
            "connected": response.success,
            "server_info": response.message if response.success else None,
            "error": response.fault_string if not response.success else None
        }, indent=2)
    except ConnectionError as e:
        return json.dumps({
            "connected": False,
            "error": str(e)
        })


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    port = int(os.getenv("MCP_PORT", 8080))
    print(f"Starting AzerothCore MCP Server on http://localhost:{port}/sse")
    print()

    # Database status
    print(f"Database: {DB_CONFIG['host']}:{DB_CONFIG['port']} ({', '.join(DB_NAMES.values())})")
    print(f"Database Mode: {'READ-ONLY' if READ_ONLY else 'READ-WRITE'}")

    # Wiki status
    if WIKI_PATH.exists():
        print(f"Wiki: {WIKI_PATH}")
    else:
        print(f"Wiki: NOT FOUND ({WIKI_PATH})")

    # AzerothCore source status
    if AZEROTHCORE_SRC_PATH.exists():
        print(f"AzerothCore Source: {AZEROTHCORE_SRC_PATH}")
    else:
        print(f"AzerothCore Source: NOT FOUND ({AZEROTHCORE_SRC_PATH})")

    # Optional features
    if ENABLE_SPELL_DBC:
        print("Spell DBC: ENABLED")

    # Keira3 SAI Comment Generator
    if SAI_GENERATOR_AVAILABLE:
        print("Keira3 SAI Generator: ENABLED")
    else:
        print("Keira3 SAI Generator: NOT AVAILABLE (check sai_comment_generator.py)")

    # SOAP client status
    if SOAP_AVAILABLE and SOAP_ENABLED:
        if _soap_client:
            print(f"SOAP: ENABLED ({_soap_client.host}:{_soap_client.port})")
        else:
            print("SOAP: ENABLED but credentials not configured (set SOAP_USERNAME/SOAP_PASSWORD)")
    elif SOAP_AVAILABLE:
        print("SOAP: DISABLED (set SOAP_ENABLED=true to enable)")
    else:
        print("SOAP: NOT AVAILABLE (check soap_client.py)")

    print()
    mcp.run(transport="sse")
