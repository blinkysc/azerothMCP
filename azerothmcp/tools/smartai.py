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
SmartAI tools for AzerothCore MCP Server.
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


# SmartAI event types with parameter documentation from SmartScriptMgr.h
SMART_EVENTS = {
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
    52: {"name": "SMART_EVENT_TEXT_OVER", "desc": "Creature text finished", "params": "GroupID (creature_text), CreatureEntry (0=any)"},
    53: {"name": "SMART_EVENT_RECEIVE_HEAL", "desc": "Received healing", "params": "MinHeal, MaxHeal, CooldownMin, CooldownMax"},
    54: {"name": "SMART_EVENT_JUST_SUMMONED", "desc": "Just summoned by another unit", "params": "NONE"},
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
    82: {"name": "SMART_EVENT_SUMMONED_UNIT_DIES", "desc": "Summoned creature died", "params": "CreatureEntry (0=any), CooldownMin, CooldownMax"},
    # AC Custom Events (100+)
    101: {"name": "SMART_EVENT_NEAR_PLAYERS", "desc": "Near minimum players (AC)", "params": "MinPlayers, Radius, FirstTimer, RepeatMin, RepeatMax"},
    102: {"name": "SMART_EVENT_NEAR_PLAYERS_NEGATION", "desc": "Below max players nearby (AC)", "params": "MaxPlayers, Radius, FirstTimer, RepeatMin, RepeatMax"},
    107: {"name": "SMART_EVENT_SUMMONED_UNIT_EVADE", "desc": "Summoned unit evaded (AC)", "params": "CreatureEntry (0=any), CooldownMin, CooldownMax"},
    108: {"name": "SMART_EVENT_WAYPOINT_REACHED", "desc": "Waypoint reached (AC new)", "params": "PointID (0=any), PathID (0=any)"},
    109: {"name": "SMART_EVENT_WAYPOINT_ENDED", "desc": "Waypoint path ended (AC new)", "params": "PointID (0=any), PathID (0=any)"},
    110: {"name": "SMART_EVENT_IS_IN_MELEE_RANGE", "desc": "In melee range check (AC)", "params": "Min, Max, RepeatMin, RepeatMax, Distance, Invert (0/1)"},
}

# SmartAI action types with parameter documentation
SMART_ACTIONS = {
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
    56: {"name": "SMART_ACTION_ADD_ITEM", "desc": "Add item to player", "params": "ItemID, Count"},
    57: {"name": "SMART_ACTION_REMOVE_ITEM", "desc": "Remove item from player", "params": "ItemID, Count"},
    59: {"name": "SMART_ACTION_SET_RUN", "desc": "Set run/walk", "params": "Run (0/1)"},
    60: {"name": "SMART_ACTION_SET_FLY", "desc": "Set fly mode", "params": "Fly (0/1)"},
    61: {"name": "SMART_ACTION_SET_SWIM", "desc": "Set swim mode", "params": "Swim (0/1)"},
    62: {"name": "SMART_ACTION_TELEPORT", "desc": "Teleport target", "params": "MapID, x, y, z, o (from target coords)"},
    63: {"name": "SMART_ACTION_SET_COUNTER", "desc": "Set counter value", "params": "CounterID, Value, Reset (0/1)"},
    64: {"name": "SMART_ACTION_STORE_TARGET_LIST", "desc": "Store current targets", "params": "VarID"},
    66: {"name": "SMART_ACTION_SET_ORIENTATION", "desc": "Set facing/orientation", "params": "QuickChange, RandomOrientation? (0/1), TurnAngle"},
    67: {"name": "SMART_ACTION_CREATE_TIMED_EVENT", "desc": "Create timed event", "params": "EventID, InitialMin, InitialMax, RepeatMin, RepeatMax, Chance"},
    69: {"name": "SMART_ACTION_MOVE_TO_POS", "desc": "Move to position", "params": "PointID, Transport, Controlled, ContactDistance (x,y,z from target)"},
    70: {"name": "SMART_ACTION_RESPAWN_TARGET", "desc": "Respawn target GO/creature", "params": "Force, GORespawnTime"},
    71: {"name": "SMART_ACTION_EQUIP", "desc": "Equip items", "params": "EquipmentID, SlotMask, Slot1, Slot2, Slot3"},
    72: {"name": "SMART_ACTION_CLOSE_GOSSIP", "desc": "Close gossip window", "params": "NONE"},
    73: {"name": "SMART_ACTION_TRIGGER_TIMED_EVENT", "desc": "Trigger timed event", "params": "EventID (>1)"},
    74: {"name": "SMART_ACTION_REMOVE_TIMED_EVENT", "desc": "Remove timed event", "params": "EventID (>1)"},
    75: {"name": "SMART_ACTION_ADD_AURA", "desc": "Add aura to target", "params": "SpellID"},
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
    92: {"name": "SMART_ACTION_INTERRUPT_SPELL", "desc": "Interrupt spell cast", "params": "WithDelayed, SpellType, WithInstant"},
    97: {"name": "SMART_ACTION_JUMP_TO_POS", "desc": "Jump to position", "params": "SpeedXY, SpeedZ, SelfJump"},
    98: {"name": "SMART_ACTION_SEND_GOSSIP_MENU", "desc": "Send gossip menu", "params": "MenuID, OptionID"},
    99: {"name": "SMART_ACTION_GO_SET_LOOT_STATE", "desc": "Set GO loot state", "params": "State"},
    100: {"name": "SMART_ACTION_SEND_TARGET_TO_TARGET", "desc": "Send stored targets", "params": "VarID"},
    101: {"name": "SMART_ACTION_SET_HOME_POS", "desc": "Set home position", "params": "SpawnPos (use current pos)"},
    102: {"name": "SMART_ACTION_SET_HEALTH_REGEN", "desc": "Enable/disable health regen", "params": "Enabled (0/1)"},
    103: {"name": "SMART_ACTION_SET_ROOT", "desc": "Root/unroot", "params": "Rooted (0/1)"},
    107: {"name": "SMART_ACTION_SUMMON_CREATURE_GROUP", "desc": "Summon creature group", "params": "GroupID, AttackInvoker, AttackScriptOwner"},
    117: {"name": "SMART_ACTION_DISABLE_EVADE", "desc": "Disable evade", "params": "Disabled (0=enabled, 1=disabled)"},
    122: {"name": "SMART_ACTION_FLEE", "desc": "Flee from combat", "params": "FleeTime"},
    123: {"name": "SMART_ACTION_ADD_THREAT", "desc": "Add/remove threat", "params": "+Threat, -Threat"},
    124: {"name": "SMART_ACTION_LOAD_EQUIPMENT", "desc": "Load equipment template", "params": "EquipmentID"},
    142: {"name": "SMART_ACTION_SET_HEALTH_PCT", "desc": "Set health percentage", "params": "HPPercent"},
    # AC Custom Actions (200+)
    232: {"name": "SMART_ACTION_WAYPOINT_START", "desc": "Start waypoint (AC new)", "params": "PathID, Repeat, PathSource"},
    234: {"name": "SMART_ACTION_MOVEMENT_STOP", "desc": "Movement stop (AC)", "params": "NONE"},
    235: {"name": "SMART_ACTION_MOVEMENT_PAUSE", "desc": "Movement pause (AC)", "params": "Timer"},
    236: {"name": "SMART_ACTION_MOVEMENT_RESUME", "desc": "Movement resume (AC)", "params": "TimerOverride"},
}

# SmartAI target types with parameter documentation
SMART_TARGETS = {
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


def register_smartai_tools(mcp):
    """Register SmartAI-related tools with the MCP server."""

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
            name = get_entity_name(entryorguid, source_type)
            results = add_sai_comments(results, name)

            return json.dumps(results, indent=2, default=str)
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
        result = {}

        if event_type is not None:
            event_info = SMART_EVENTS.get(event_type)
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
            action_info = SMART_ACTIONS.get(action_type)
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
            target_info = SMART_TARGETS.get(target_type)
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

        def get_event_name(et):
            return event_names.get(et, f"EVENT_{et}")

        def get_action_name(at):
            return action_names.get(at, f"ACTION_{at}")

        def get_target_name(tt):
            return target_names.get(tt, f"TARGET_{tt}")

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

                return f"{prefix}[{script['id']}] {event} -> {action} @ {target}{phase_str}{chance_str}{comment_str}"

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

                # Check for SetData
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
                link = script.get("link", 0)
                if link and link != 0 and link not in script_by_id:
                    issues.append(f"Script {script['id']} links to non-existent script {link}")

                if script["event_chance"] == 0:
                    issues.append(f"Script {script['id']} has 0% event_chance (will never trigger)")

            if issues:
                trace_results.append("\n[!] POTENTIAL ISSUES DETECTED:")
                for issue in issues:
                    trace_results.append(f"  - {issue}")

            return "\n".join(trace_results)

        except Exception as e:
            return json.dumps({"error": str(e)})

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

            name = get_entity_name(entryorguid, source_type)

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
