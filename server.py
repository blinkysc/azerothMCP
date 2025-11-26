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

WIKI_PATH = Path(os.getenv("WIKI_PATH", os.path.expanduser("~/wiki/docs")))

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
    Execute a read-only SQL query against an AzerothCore database.

    Args:
        query: SQL SELECT query to execute
        database: Which database to query - 'world', 'characters', or 'auth'

    Returns:
        JSON string of query results (list of row dicts)

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
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_table_schema(table_name: str, database: str = "world") -> str:
    """
    Get the schema/structure of a database table.

    Args:
        table_name: Name of the table to describe
        database: Which database - 'world', 'characters', or 'auth'

    Returns:
        Table column definitions
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

@mcp.tool()
def get_smart_scripts(entryorguid: int, source_type: int = 0) -> str:
    """
    Get SmartAI scripts for a creature, gameobject, or other source.

    Args:
        entryorguid: The entry or GUID of the source
        source_type: 0=Creature, 1=GameObject, 2=AreaTrigger, 3=Event,
                    4=Gossip, 5=Quest, 6=Spell, 7=Transport, 8=Instance, 9=TimedActionList

    Returns:
        All smart_scripts rows for this entity, ordered by id
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
        return json.dumps(results, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_creature_with_scripts(entry: int) -> str:
    """
    Get creature template AND its SmartAI scripts together.
    Useful for understanding a creature's complete behavior.

    Args:
        entry: Creature entry ID

    Returns:
        Combined creature template data and SmartAI scripts
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

        # Check if creature uses SmartAI
        ai_name = creature_data.get("AIName", "")

        scripts = []
        if ai_name == "SmartAI":
            scripts = execute_query(
                "SELECT * FROM smart_scripts WHERE entryorguid = %s AND source_type = 0 ORDER BY id",
                "world",
                (entry,)
            )

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

    Args:
        event_type: SmartAI event type number to explain
        action_type: SmartAI action type number to explain
        target_type: SmartAI target type number to explain

    Returns:
        Explanation of the requested SmartAI component
    """
    # SmartAI event types
    events = {
        0: "SMART_EVENT_UPDATE_IC - While in combat, triggers every X ms",
        1: "SMART_EVENT_UPDATE_OOC - While out of combat, triggers every X ms",
        2: "SMART_EVENT_HEALTH_PCT - Health percentage between min/max",
        3: "SMART_EVENT_MANA_PCT - Mana percentage between min/max",
        4: "SMART_EVENT_AGGRO - On entering combat",
        5: "SMART_EVENT_KILL - On killing a unit",
        6: "SMART_EVENT_DEATH - On creature death",
        7: "SMART_EVENT_EVADE - When creature evades/resets",
        8: "SMART_EVENT_SPELLHIT - When hit by specific spell",
        9: "SMART_EVENT_RANGE - Target in range (min/max yards)",
        10: "SMART_EVENT_OOC_LOS - Out of combat, target enters line of sight",
        11: "SMART_EVENT_RESPAWN - On creature respawn",
        12: "SMART_EVENT_TARGET_HEALTH_PCT - Target health percentage",
        13: "SMART_EVENT_VICTIM_CASTING - Current victim is casting",
        14: "SMART_EVENT_FRIENDLY_HEALTH - Friendly unit health percentage",
        15: "SMART_EVENT_FRIENDLY_IS_CC - Friendly unit is crowd controlled",
        16: "SMART_EVENT_FRIENDLY_MISSING_BUFF - Friendly missing specific buff",
        17: "SMART_EVENT_SUMMONED_UNIT - Unit was summoned",
        18: "SMART_EVENT_TARGET_MANA_PCT - Target mana percentage",
        19: "SMART_EVENT_ACCEPTED_QUEST - Quest accepted",
        20: "SMART_EVENT_REWARD_QUEST - Quest rewarded/completed",
        21: "SMART_EVENT_REACHED_HOME - Reached home position",
        22: "SMART_EVENT_RECEIVE_EMOTE - Received emote from player",
        23: "SMART_EVENT_HAS_AURA - Unit has aura stacks",
        24: "SMART_EVENT_TARGET_BUFFED - Target has aura stacks",
        25: "SMART_EVENT_RESET - On AI reset (respawn/evade)",
        26: "SMART_EVENT_IC_LOS - In combat, target enters line of sight",
        27: "SMART_EVENT_PASSENGER_BOARDED - Passenger boarded vehicle",
        28: "SMART_EVENT_PASSENGER_REMOVED - Passenger left vehicle",
        29: "SMART_EVENT_CHARMED - Unit was charmed/mind controlled",
        30: "SMART_EVENT_CHARMED_TARGET - Charmed target specific",
        31: "SMART_EVENT_SPELLHIT_TARGET - Target hit by spell",
        32: "SMART_EVENT_DAMAGED - Creature took damage",
        33: "SMART_EVENT_DAMAGED_TARGET - Target took damage",
        34: "SMART_EVENT_MOVEMENTINFORM - Movement generator finished",
        35: "SMART_EVENT_SUMMON_DESPAWNED - Summoned unit despawned",
        36: "SMART_EVENT_CORPSE_REMOVED - Corpse removed",
        37: "SMART_EVENT_AI_INIT - AI initialized",
        38: "SMART_EVENT_DATA_SET - SetData called on creature",
        39: "SMART_EVENT_WAYPOINT_START - Started waypoint path",
        40: "SMART_EVENT_WAYPOINT_REACHED - Reached waypoint",
        41: "SMART_EVENT_TRANSPORT_ADDPLAYER - Player added to transport",
        42: "SMART_EVENT_TRANSPORT_ADDCREATURE - Creature added to transport",
        43: "SMART_EVENT_TRANSPORT_REMOVE_PLAYER - Player removed from transport",
        44: "SMART_EVENT_TRANSPORT_RELOCATE - Transport relocated",
        45: "SMART_EVENT_INSTANCE_PLAYER_ENTER - Player entered instance",
        46: "SMART_EVENT_AREATRIGGER_ONTRIGGER - Areatrigger triggered",
        47: "SMART_EVENT_QUEST_ACCEPTED - (deprecated, use 19)",
        48: "SMART_EVENT_QUEST_OBJ_COMPLETION - Quest objective completed",
        49: "SMART_EVENT_QUEST_COMPLETION - (deprecated)",
        50: "SMART_EVENT_QUEST_REWARDED - (deprecated, use 20)",
        51: "SMART_EVENT_QUEST_FAIL - Quest failed",
        52: "SMART_EVENT_TEXT_OVER - Creature text finished",
        53: "SMART_EVENT_RECEIVE_HEAL - Received healing",
        54: "SMART_EVENT_JUST_SUMMONED - Just summoned",
        55: "SMART_EVENT_WAYPOINT_PAUSED - Waypoint paused",
        56: "SMART_EVENT_WAYPOINT_RESUMED - Waypoint resumed",
        57: "SMART_EVENT_WAYPOINT_STOPPED - Waypoint stopped",
        58: "SMART_EVENT_WAYPOINT_ENDED - Waypoint path ended",
        59: "SMART_EVENT_TIMED_EVENT_TRIGGERED - Timed event triggered",
        60: "SMART_EVENT_UPDATE - Every X ms (in or out of combat)",
        61: "SMART_EVENT_LINK - Linked from another SmartAI event",
        62: "SMART_EVENT_GOSSIP_SELECT - Gossip option selected",
        63: "SMART_EVENT_JUST_CREATED - Just created/spawned",
        64: "SMART_EVENT_GOSSIP_HELLO - Gossip hello (NPC clicked)",
        65: "SMART_EVENT_FOLLOW_COMPLETED - Follow completed",
        66: "SMART_EVENT_EVENT_PHASE_CHANGE - Phase changed (SetPhase)",
        67: "SMART_EVENT_IS_BEHIND_TARGET - Behind target check",
        68: "SMART_EVENT_GAME_EVENT_START - Game event started",
        69: "SMART_EVENT_GAME_EVENT_END - Game event ended",
        70: "SMART_EVENT_GO_LOOT_STATE_CHANGED - GameObject loot state changed",
        71: "SMART_EVENT_GO_EVENT_INFORM - GameObject event inform",
        72: "SMART_EVENT_ACTION_DONE - Action completed",
        73: "SMART_EVENT_ON_SPELLCLICK - Spellclick used",
        74: "SMART_EVENT_FRIENDLY_HEALTH_PCT - Friendly health percentage",
        75: "SMART_EVENT_DISTANCE_CREATURE - Distance to creature",
        76: "SMART_EVENT_DISTANCE_GAMEOBJECT - Distance to gameobject",
        77: "SMART_EVENT_COUNTER_SET - Counter set to value",
        78: "SMART_EVENT_SCENE_START - (unused)",
        79: "SMART_EVENT_SCENE_TRIGGER - (unused)",
        80: "SMART_EVENT_SCENE_CANCEL - (unused)",
        81: "SMART_EVENT_SCENE_COMPLETE - (unused)",
        82: "SMART_EVENT_SUMMONED_UNIT_DIES - Summoned creature died",
        83: "SMART_EVENT_ON_SPELL_CAST - Creature started casting spell",
        84: "SMART_EVENT_ON_SPELL_FAILED - Creature spell cast failed",
        85: "SMART_EVENT_ON_SPELL_START - Creature spell started",
        86: "SMART_EVENT_ON_DESPAWN - Creature despawned",
    }

    # SmartAI action types
    actions = {
        0: "SMART_ACTION_NONE - No action",
        1: "SMART_ACTION_TALK - Say/Yell/Emote text from creature_text",
        2: "SMART_ACTION_SET_FACTION - Change faction",
        3: "SMART_ACTION_MORPH_TO_ENTRY_OR_MODEL - Change model",
        4: "SMART_ACTION_SOUND - Play sound",
        5: "SMART_ACTION_PLAY_EMOTE - Play emote animation",
        6: "SMART_ACTION_FAIL_QUEST - Fail quest for player",
        7: "SMART_ACTION_OFFER_QUEST - Offer quest",
        8: "SMART_ACTION_SET_REACT_STATE - Set react state (passive/defensive/aggressive)",
        9: "SMART_ACTION_ACTIVATE_GOBJECT - Activate gameobject",
        10: "SMART_ACTION_RANDOM_EMOTE - Play random emote",
        11: "SMART_ACTION_CAST - Cast spell",
        12: "SMART_ACTION_SUMMON_CREATURE - Summon creature",
        13: "SMART_ACTION_THREAT_SINGLE_PCT - Modify threat percentage",
        14: "SMART_ACTION_THREAT_ALL_PCT - Modify threat for all",
        15: "SMART_ACTION_CALL_AREAEXPLOREDOREVENTHAPPENS - Complete quest objective",
        16: "SMART_ACTION_SET_INGAME_PHASE_GROUP - Unused",
        17: "SMART_ACTION_SET_EMOTE_STATE - Set emote state",
        18: "SMART_ACTION_SET_UNIT_FLAG - Set unit flags",
        19: "SMART_ACTION_REMOVE_UNIT_FLAG - Remove unit flags",
        20: "SMART_ACTION_AUTO_ATTACK - Enable/disable auto attack",
        21: "SMART_ACTION_ALLOW_COMBAT_MOVEMENT - Allow combat movement",
        22: "SMART_ACTION_SET_EVENT_PHASE - Set event phase",
        23: "SMART_ACTION_INC_EVENT_PHASE - Increment event phase",
        24: "SMART_ACTION_EVADE - Force evade",
        25: "SMART_ACTION_FLEE_FOR_ASSIST - Flee and call for help",
        26: "SMART_ACTION_CALL_GROUPEVENTHAPPENS - Group quest objective",
        27: "SMART_ACTION_COMBAT_STOP - Stop combat",
        28: "SMART_ACTION_REMOVEAURASFROMSPELL - Remove auras",
        29: "SMART_ACTION_FOLLOW - Follow target",
        30: "SMART_ACTION_RANDOM_PHASE - Set random phase",
        31: "SMART_ACTION_RANDOM_PHASE_RANGE - Set phase in range",
        32: "SMART_ACTION_RESET_GOBJECT - Reset gameobject",
        33: "SMART_ACTION_CALL_KILLEDMONSTER - Credit kill for quest",
        34: "SMART_ACTION_SET_INST_DATA - Set instance data",
        35: "SMART_ACTION_SET_INST_DATA64 - Set instance data (64-bit)",
        36: "SMART_ACTION_UPDATE_TEMPLATE - Update creature template",
        37: "SMART_ACTION_DIE - Kill self",
        38: "SMART_ACTION_SET_IN_COMBAT_WITH_ZONE - Zone-wide combat",
        39: "SMART_ACTION_CALL_FOR_HELP - Call for help (radius)",
        40: "SMART_ACTION_SET_SHEATH - Set sheath state",
        41: "SMART_ACTION_FORCE_DESPAWN - Despawn creature",
        42: "SMART_ACTION_SET_INVINCIBILITY_HP_LEVEL - Set invincibility HP",
        43: "SMART_ACTION_MOUNT_TO_ENTRY_OR_MODEL - Mount creature",
        44: "SMART_ACTION_SET_INGAME_PHASE_ID - Set phase ID",
        45: "SMART_ACTION_SET_DATA - Set data on creature",
        46: "SMART_ACTION_ATTACK_STOP - Stop attacking",
        47: "SMART_ACTION_SET_VISIBILITY - Set visibility",
        48: "SMART_ACTION_SET_ACTIVE - Set active (keep updated)",
        49: "SMART_ACTION_ATTACK_START - Start attacking",
        50: "SMART_ACTION_SUMMON_GO - Summon gameobject",
        51: "SMART_ACTION_KILL_UNIT - Kill target",
        52: "SMART_ACTION_ACTIVATE_TAXI - Activate taxi path",
        53: "SMART_ACTION_WP_START - Start waypoint path",
        54: "SMART_ACTION_WP_PAUSE - Pause waypoint",
        55: "SMART_ACTION_WP_STOP - Stop waypoint",
        56: "SMART_ACTION_ADD_ITEM - Add item to player",
        57: "SMART_ACTION_REMOVE_ITEM - Remove item from player",
        58: "SMART_ACTION_INSTALL_AI_TEMPLATE - Install AI template",
        59: "SMART_ACTION_SET_RUN - Set run/walk",
        60: "SMART_ACTION_SET_DISABLE_GRAVITY - Disable gravity",
        61: "SMART_ACTION_SET_SWIM - Enable swimming",
        62: "SMART_ACTION_TELEPORT - Teleport target",
        63: "SMART_ACTION_SET_COUNTER - Set stored counter",
        64: "SMART_ACTION_STORE_TARGET_LIST - Store targets",
        65: "SMART_ACTION_WP_RESUME - Resume waypoint",
        66: "SMART_ACTION_SET_ORIENTATION - Set facing",
        67: "SMART_ACTION_CREATE_TIMED_EVENT - Create timed event",
        68: "SMART_ACTION_PLAYMOVIE - Play movie",
        69: "SMART_ACTION_MOVE_TO_POS - Move to position",
        70: "SMART_ACTION_ENABLE_TEMP_GOBJ - (Deprecated)",
        71: "SMART_ACTION_EQUIP - Equip items",
        72: "SMART_ACTION_CLOSE_GOSSIP - Close gossip window",
        73: "SMART_ACTION_TRIGGER_TIMED_EVENT - Trigger timed event",
        74: "SMART_ACTION_REMOVE_TIMED_EVENT - Remove timed event",
        75: "SMART_ACTION_ADD_AURA - Add aura",
        76: "SMART_ACTION_OVERRIDE_SCRIPT_BASE_OBJECT - Override script base",
        77: "SMART_ACTION_RESET_SCRIPT_BASE_OBJECT - Reset script base",
        78: "SMART_ACTION_CALL_SCRIPT_RESET - Reset all scripts",
        79: "SMART_ACTION_SET_RANGED_MOVEMENT - Set ranged movement",
        80: "SMART_ACTION_CALL_TIMED_ACTIONLIST - Call timed action list",
        81: "SMART_ACTION_SET_NPC_FLAG - Set NPC flags",
        82: "SMART_ACTION_ADD_NPC_FLAG - Add NPC flags",
        83: "SMART_ACTION_REMOVE_NPC_FLAG - Remove NPC flags",
        84: "SMART_ACTION_SIMPLE_TALK - Simple creature text",
        85: "SMART_ACTION_SELF_CAST - Self-cast spell",
        86: "SMART_ACTION_CROSS_CAST - Cross-cast spell",
        87: "SMART_ACTION_CALL_RANDOM_TIMED_ACTIONLIST - Random timed list",
        88: "SMART_ACTION_CALL_RANDOM_RANGE_TIMED_ACTIONLIST - Random range list",
        89: "SMART_ACTION_RANDOM_MOVE - Random movement",
        90: "SMART_ACTION_SET_UNIT_FIELD_BYTES_1 - Set unit bytes",
        91: "SMART_ACTION_REMOVE_UNIT_FIELD_BYTES_1 - Remove unit bytes",
        92: "SMART_ACTION_INTERRUPT_SPELL - Interrupt spell",
        93: "SMART_ACTION_SEND_GO_CUSTOM_ANIM - GO custom animation",
        94: "SMART_ACTION_SET_DYNAMIC_FLAG - Set dynamic flags",
        95: "SMART_ACTION_ADD_DYNAMIC_FLAG - Add dynamic flags",
        96: "SMART_ACTION_REMOVE_DYNAMIC_FLAG - Remove dynamic flags",
        97: "SMART_ACTION_JUMP_TO_POS - Jump to position",
        98: "SMART_ACTION_SEND_GOSSIP_MENU - Send gossip menu",
        99: "SMART_ACTION_GO_SET_LOOT_STATE - Set GO loot state",
        100: "SMART_ACTION_SEND_TARGET_TO_TARGET - Send targets",
        101: "SMART_ACTION_SET_HOME_POS - Set home position",
        102: "SMART_ACTION_SET_HEALTH_REGEN - Set health regen",
        103: "SMART_ACTION_SET_ROOT - Set rooted",
        104: "SMART_ACTION_SET_GO_FLAG - Set GO flags",
        105: "SMART_ACTION_ADD_GO_FLAG - Add GO flags",
        106: "SMART_ACTION_REMOVE_GO_FLAG - Remove GO flags",
        107: "SMART_ACTION_SUMMON_CREATURE_GROUP - Summon creature group",
        108: "SMART_ACTION_SET_POWER - Set power",
        109: "SMART_ACTION_ADD_POWER - Add power",
        110: "SMART_ACTION_REMOVE_POWER - Remove power",
        111: "SMART_ACTION_GAME_EVENT_STOP - Stop game event",
        112: "SMART_ACTION_GAME_EVENT_START - Start game event",
        113: "SMART_ACTION_START_CLOSEST_WAYPOINT - Start closest waypoint",
        114: "SMART_ACTION_MOVE_OFFSET - Move with offset",
        115: "SMART_ACTION_RANDOM_SOUND - Random sound",
        116: "SMART_ACTION_SET_CORPSE_DELAY - Set corpse delay",
        117: "SMART_ACTION_DISABLE_EVADE - Disable evade",
        118: "SMART_ACTION_GO_SET_GO_STATE - Set GO state",
        119: "SMART_ACTION_SET_CAN_FLY - Set can fly",
        120: "SMART_ACTION_REMOVE_AURAS_BY_TYPE - Remove auras by type",
        121: "SMART_ACTION_SET_SIGHT_DIST - Set sight distance",
        122: "SMART_ACTION_FLEE - Flee combat",
        123: "SMART_ACTION_ADD_THREAT - Add threat",
        124: "SMART_ACTION_LOAD_EQUIPMENT - Load equipment template",
        125: "SMART_ACTION_TRIGGER_RANDOM_TIMED_EVENT - Trigger random event",
        126: "SMART_ACTION_REMOVE_ALL_GAMEOBJECTS - Remove all summoned GOs",
        127: "SMART_ACTION_PAUSE_MOVEMENT - Pause movement",
        128: "SMART_ACTION_PLAY_ANIMKIT - Play animkit",
        129: "SMART_ACTION_SCENE_PLAY - (Unused)",
        130: "SMART_ACTION_SCENE_CANCEL - (Unused)",
        131: "SMART_ACTION_SPAWN_SPAWNGROUP - Spawn spawngroup",
        132: "SMART_ACTION_DESPAWN_SPAWNGROUP - Despawn spawngroup",
        133: "SMART_ACTION_RESPAWN_BY_SPAWNID - Respawn by spawn ID",
        134: "SMART_ACTION_INVOKER_CAST - Invoker casts spell",
        135: "SMART_ACTION_PLAY_CINEMATIC - Play cinematic",
        136: "SMART_ACTION_SET_MOVEMENT_SPEED - Set movement speed",
        137: "SMART_ACTION_PLAY_SPELL_VISUAL_KIT - (Unused)",
        138: "SMART_ACTION_OVERRIDE_LIGHT - Override light",
        139: "SMART_ACTION_OVERRIDE_WEATHER - Override weather",
        140: "SMART_ACTION_SET_AI_ANIM_KIT - (Unused)",
        141: "SMART_ACTION_SET_HOVER - Set hover",
        142: "SMART_ACTION_SET_HEALTH_PCT - Set health percent",
        143: "SMART_ACTION_CREATE_CONVERSATION - (Unused)",
        144: "SMART_ACTION_SET_IMMUNE_PC - Set immune to PC",
        145: "SMART_ACTION_SET_IMMUNE_NPC - Set immune to NPC",
        146: "SMART_ACTION_SET_UNINTERACTIBLE - Set uninteractible",
        147: "SMART_ACTION_ACTIVATE_GAMEOBJECT - Activate GO",
        148: "SMART_ACTION_ADD_TO_STORED_TARGET_LIST - Add to target list",
        149: "SMART_ACTION_BECOME_PERSONAL_CLONE_FOR_PLAYER - Personal clone",
        150: "SMART_ACTION_TRIGGER_GAME_EVENT - Trigger game event",
        151: "SMART_ACTION_DO_ACTION - Do action",
        152: "SMART_ACTION_ATTACK_STOP_ALL_TARGETS - Stop attacking all",
    }

    # SmartAI target types
    targets = {
        0: "SMART_TARGET_NONE - No target (self)",
        1: "SMART_TARGET_SELF - Self",
        2: "SMART_TARGET_VICTIM - Current victim/target",
        3: "SMART_TARGET_HOSTILE_SECOND_AGGRO - Second on threat list",
        4: "SMART_TARGET_HOSTILE_LAST_AGGRO - Last on threat list",
        5: "SMART_TARGET_HOSTILE_RANDOM - Random hostile",
        6: "SMART_TARGET_HOSTILE_RANDOM_NOT_TOP - Random hostile (not top)",
        7: "SMART_TARGET_ACTION_INVOKER - Action invoker (player/creature that triggered)",
        8: "SMART_TARGET_POSITION - Position (x, y, z, o)",
        9: "SMART_TARGET_CREATURE_RANGE - Creature in range",
        10: "SMART_TARGET_CREATURE_GUID - Creature by GUID",
        11: "SMART_TARGET_CREATURE_DISTANCE - Creature by distance",
        12: "SMART_TARGET_STORED - Previously stored targets",
        13: "SMART_TARGET_GAMEOBJECT_RANGE - GO in range",
        14: "SMART_TARGET_GAMEOBJECT_GUID - GO by GUID",
        15: "SMART_TARGET_GAMEOBJECT_DISTANCE - GO by distance",
        16: "SMART_TARGET_INVOKER_PARTY - Invoker's party",
        17: "SMART_TARGET_PLAYER_RANGE - Players in range",
        18: "SMART_TARGET_PLAYER_DISTANCE - Players by distance",
        19: "SMART_TARGET_CLOSEST_CREATURE - Closest creature",
        20: "SMART_TARGET_CLOSEST_GAMEOBJECT - Closest GO",
        21: "SMART_TARGET_CLOSEST_PLAYER - Closest player",
        22: "SMART_TARGET_ACTION_INVOKER_VEHICLE - Invoker's vehicle",
        23: "SMART_TARGET_OWNER_OR_SUMMONER - Owner/summoner",
        24: "SMART_TARGET_THREAT_LIST - Entire threat list",
        25: "SMART_TARGET_CLOSEST_ENEMY - Closest enemy",
        26: "SMART_TARGET_CLOSEST_FRIENDLY - Closest friendly",
        27: "SMART_TARGET_LOOT_RECIPIENTS - Loot recipients",
        28: "SMART_TARGET_FARTHEST - Farthest target",
        29: "SMART_TARGET_VEHICLE_PASSENGER - Vehicle passengers",
        30: "SMART_TARGET_CLOSEST_UNSPAWNED_GAMEOBJECT - Closest unspawned GO",
    }

    result = {}

    if event_type is not None:
        result["event_type"] = events.get(event_type, f"Unknown event type: {event_type}")

    if action_type is not None:
        result["action_type"] = actions.get(action_type, f"Unknown action type: {action_type}")

    if target_type is not None:
        result["target_type"] = targets.get(target_type, f"Unknown target type: {target_type}")

    if not result:
        return json.dumps({
            "error": "Please provide at least one of: event_type, action_type, target_type",
            "hint": "Example: explain_smart_script(event_type=4) for SMART_EVENT_AGGRO"
        })

    return json.dumps(result, indent=2)


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

@mcp.tool()
def search_spells(name_or_id: str, limit: int = 20) -> str:
    """
    Search for spells by name or ID in spell_dbc.

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
# MAIN
# =============================================================================

if __name__ == "__main__":
    port = int(os.getenv("MCP_PORT", 8080))
    print(f"Starting AzerothCore MCP Server on http://localhost:{port}/sse")
    mcp.run(transport="sse")
