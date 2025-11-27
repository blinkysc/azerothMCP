#!/usr/bin/env python3
"""
SAI Comment Generator - Python port of Keira3's sai-comment-generator.service.ts

Generates human-readable comments for SmartAI scripts.
"""

import sqlite3
from pathlib import Path

# Path to Keira3's sqlite database (spell names, etc.)
KEIRA_SQLITE_PATH = Path(__file__).parent / "Keira3/apps/keira/src/assets/sqlite.db"

# SAI Types
SAI_TYPE_CREATURE = 0
SAI_TYPE_GAMEOBJECT = 1
SAI_TYPE_AREATRIGGER = 2
SAI_TYPE_TIMED_ACTIONLIST = 9

# SAI Events
SAI_EVENTS = {
    0: "UPDATE_IC", 1: "UPDATE_OOC", 2: "HEALTH_PCT", 3: "MANA_PCT",
    4: "AGGRO", 5: "KILL", 6: "DEATH", 7: "EVADE", 8: "SPELLHIT",
    9: "RANGE", 10: "OOC_LOS", 11: "RESPAWN", 12: "TARGET_HEALTH_PCT",
    13: "VICTIM_CASTING", 14: "FRIENDLY_HEALTH", 15: "FRIENDLY_IS_CC",
    16: "FRIENDLY_MISSING_BUFF", 17: "SUMMONED_UNIT", 18: "TARGET_MANA_PCT",
    19: "ACCEPTED_QUEST", 20: "REWARD_QUEST", 21: "REACHED_HOME",
    22: "RECEIVE_EMOTE", 23: "HAS_AURA", 24: "TARGET_BUFFED", 25: "RESET",
    26: "IC_LOS", 27: "PASSENGER_BOARDED", 28: "PASSENGER_REMOVED",
    29: "CHARMED", 30: "CHARMED_TARGET", 31: "SPELLHIT_TARGET",
    32: "DAMAGED", 33: "DAMAGED_TARGET", 34: "MOVEMENTINFORM",
    35: "SUMMON_DESPAWNED", 36: "CORPSE_REMOVED", 37: "AI_INIT",
    38: "DATA_SET", 39: "ESCORT_START", 40: "ESCORT_REACHED",
    46: "AREATRIGGER_ONTRIGGER", 52: "TEXT_OVER", 53: "RECEIVE_HEAL",
    54: "JUST_SUMMONED", 55: "ESCORT_PAUSED", 56: "ESCORT_RESUMED",
    57: "ESCORT_STOPPED", 58: "ESCORT_ENDED", 59: "TIMED_EVENT_TRIGGERED",
    60: "UPDATE", 61: "LINK", 62: "GOSSIP_SELECT", 63: "JUST_CREATED",
    64: "GOSSIP_HELLO", 65: "FOLLOW_COMPLETED", 66: "EVENT_PHASE_CHANGE",
    67: "IS_BEHIND_TARGET", 68: "GAME_EVENT_START", 69: "GAME_EVENT_END",
    70: "GO_STATE_CHANGED", 71: "GO_EVENT_INFORM", 72: "ACTION_DONE",
    73: "ON_SPELLCLICK", 74: "FRIENDLY_HEALTH_PCT", 75: "DISTANCE_CREATURE",
    76: "DISTANCE_GAMEOBJECT", 77: "COUNTER_SET", 82: "SUMMONED_UNIT_DIES",
    101: "NEAR_PLAYERS", 102: "NEAR_PLAYERS_NEGATION", 103: "NEAR_UNIT",
    104: "NEAR_UNIT_NEGATION", 105: "AREA_CASTING", 106: "AREA_RANGE",
    107: "SUMMONED_UNIT_EVADE", 108: "WAYPOINT_REACHED", 109: "WAYPOINT_ENDED",
    110: "IS_IN_MELEE_RANGE",
}

# SAI Targets
SAI_TARGETS = {
    0: "NONE", 1: "SELF", 2: "VICTIM", 3: "HOSTILE_SECOND_AGGRO",
    4: "HOSTILE_LAST_AGGRO", 5: "HOSTILE_RANDOM", 6: "HOSTILE_RANDOM_NOT_TOP",
    7: "ACTION_INVOKER", 8: "POSITION", 9: "CREATURE_RANGE",
    10: "CREATURE_GUID", 11: "CREATURE_DISTANCE", 12: "STORED",
    13: "GAMEOBJECT_RANGE", 14: "GAMEOBJECT_GUID", 15: "GAMEOBJECT_DISTANCE",
    16: "INVOKER_PARTY", 17: "PLAYER_RANGE", 18: "PLAYER_DISTANCE",
    19: "CLOSEST_CREATURE", 20: "CLOSEST_GAMEOBJECT", 21: "CLOSEST_PLAYER",
    22: "ACTION_INVOKER_VEHICLE", 23: "OWNER_OR_SUMMONER", 24: "THREAT_LIST",
    25: "CLOSEST_ENEMY", 26: "CLOSEST_FRIENDLY", 27: "LOOT_RECIPIENTS",
    28: "FARTHEST", 29: "VEHICLE_PASSENGER", 201: "PLAYER_WITH_AURA",
    202: "RANDOM_POINT", 203: "ROLE_SELECTION", 204: "SUMMONED_CREATURES",
    205: "INSTANCE_STORAGE",
}

# Event comment templates (from Keira3's sai-comments.ts)
SAI_EVENT_COMMENTS = {
    0: "In Combat",
    1: "Out of Combat",
    2: "Between _eventParamOne_-_eventParamTwo_% Health",
    3: "Between _eventParamOne_-_eventParamTwo_% Mana",
    4: "On Aggro",
    5: "On Killed Unit",
    6: "On Just Died",
    7: "On Evade",
    8: "On Spellhit '_spellNameEventParamOne_'",
    9: "Within _eventParamFive_-_eventParamSix_ Range",
    10: "Within _eventParamOne_-_eventParamTwo_ Range Out of Combat LoS",
    11: "On Respawn",
    12: "Target Between _eventParamOne_-_eventParamTwo_% Health",
    13: "On Victim Casting '_targetCastingSpellName_'",
    14: "Friendly At _eventParamOne_ Health",
    15: "On Friendly Crowd Controlled",
    16: "On Friendly Unit Missing Buff '_spellNameEventParamOne_'",
    17: "On Summoned Unit",
    18: "Target Between _eventParamOne_-_eventParamTwo_% Mana",
    19: "On Quest '_questNameEventParamOne_' Taken",
    20: "On Quest '_questNameEventParamOne_' Finished",
    21: "On Reached Home",
    22: "Received Emote _eventParamOne_",
    23: "On Aura '_hasAuraEventParamOne_'",
    24: "On Target Buffed With '_spellNameEventParamOne_'",
    25: "On Reset",
    26: "In Combat LoS",
    27: "On Passenger Boarded",
    28: "On Passenger Removed",
    29: "On Charmed",
    30: "On Target Charmed",
    31: "On Target Spellhit '_spellNameEventParamOne_'",
    32: "On Damaged Between _eventParamOne_-_eventParamTwo_",
    33: "On Target Damaged Between _eventParamOne_-_eventParamTwo_",
    34: "On Reached Point _eventParamTwo_",
    35: "On Summon Despawned",
    36: "On Corpse Removed",
    37: "On Initialize",
    38: "On Data Set _eventParamOne_ _eventParamTwo_",
    39: "On Path _waypointParamTwo_ Started",
    40: "On Point _waypointParamOne_ of Path _waypointParamTwo_ Reached",
    46: "On Trigger",
    52: "On Text _eventParamOne_ Over",
    53: "On Received Heal Between _eventParamOne_-_eventParamTwo_",
    54: "On Just Summoned",
    55: "On Path _eventParamTwo_ Paused",
    56: "On Path _eventParamTwo_ Resumed",
    57: "On Path _eventParamTwo_ Stopped",
    58: "On Path _eventParamTwo_ Finished",
    59: "On Timed Event _eventParamOne_ Triggered",
    60: "On Update",
    61: "_previousLineComment_",
    62: "On Gossip Option _eventParamTwo_ Selected",
    63: "On Just Created",
    64: "On Gossip Hello",
    65: "On Follow Complete",
    66: "On Event Phase _eventParamOne_ Set",
    67: "On Behind Target",
    68: "On Game Event _eventParamOne_ Started",
    69: "On Game Event _eventParamOne_ Ended",
    70: "On Gameobject State Changed",
    71: "On Event _eventParamOne_ Inform",
    72: "On Action _eventParamOne_ Done",
    73: "On Spellclick",
    74: "On Friendly Below _eventParamFive_% Health",
    75: "On Distance _eventParamThree_y To Creature",
    76: "On Distance _eventParamThree_y To GameObject",
    77: "On Counter _eventParamOne_ Set To _eventParamTwo_",
    82: "On Summoned Unit Dies",
    101: "On _eventParamOne_ or More Players in Range",
    102: "On Less Than _eventParamOne_ Players in Range",
    103: "On _eventParamThree_ or More Units in Range",
    104: "On Less Than _eventParamThree_ Units in Range",
    105: "On Hostile Casting in Range",
    106: "On Hostile in Range",
    107: "On Summoned Unit Evade",
    108: "On Point _waypointParamOne_ of Path _waypointParamTwo_ Reached",
    109: "On Path _eventParamTwo_ Finished",
    110: "On Melee Range Target",
}

# Action comment templates (from Keira3's sai-comments.ts)
SAI_ACTION_COMMENTS = {
    0: "No Action Type",
    1: "Say Line _actionParamOne_",
    2: "Set Faction _actionParamOne_",
    3: "_morphToEntryOrModelActionParams_",
    4: "Play Sound _actionParamOne_",
    5: "Play Emote _actionParamOne_",
    6: "Fail Quest '_questNameActionParamOne_'",
    7: "Add Quest '_questNameActionParamOne_'",
    8: "Set Reactstate _reactStateParamOne_",
    9: "Activate Gameobject",
    10: "Play Random Emote (_actionRandomParameters_)",
    11: "Cast '_spellNameActionParamOne_'",
    12: "Summon Creature '_creatureNameActionParamOne_'",
    13: "Set Single Threat _actionParamOne_-_actionParamTwo_",
    14: "Set All Threat _actionParamOne_-_actionParamTwo_",
    15: "Quest Credit '_questNameActionParamOne_'",
    17: "Set Emote State _actionParamOne_",
    18: "Set Flag_getUnitFlags_",
    19: "Remove Flag_getUnitFlags_",
    20: "_startOrStopActionParamOne_ Attacking",
    21: "_enableDisableActionParamOne_ Combat Movement",
    22: "Set Event Phase _actionParamOne_",
    23: "_incrementOrDecrementActionParamOne_ Phase",
    24: "Evade",
    25: "Flee For Assist",
    26: "Quest Credit '_questNameActionParamOne_'",
    27: "Stop Combat",
    28: "Remove Aura '_spellNameActionParamOne_'",
    29: "_startOrStopBasedOnTargetType_ Follow _getTargetType_",
    30: "Set Random Phase (_actionRandomParameters_)",
    31: "Set Phase Random Between _actionParamOne_-_actionParamTwo_",
    32: "Reset Gameobject",
    33: "Quest Credit '_questNameKillCredit_'",
    34: "Set Instance Data _actionParamOne_ to _actionParamTwo_",
    35: "Set Instance Data _actionParamOne_",
    36: "Update Template To '_creatureNameActionParamOne_'",
    37: "Kill Self",
    38: "Set In Combat With Zone",
    39: "Call For Help",
    40: "Set Sheath _sheathActionParamOne_",
    41: "Despawn _forceDespawnActionParamOne_",
    42: "_invincibilityHpActionParamsOneTwo_",
    43: "_mountToEntryOrModelActionParams_",
    44: "Set PhaseMask _actionParamOne_",
    45: "Set Data _actionParamOne_ _actionParamTwo_",
    46: "Move Forward _actionParamOne_ Yards",
    47: "Set Visibility _onOffActionParamOne_",
    48: "Set Active _onOffActionParamOne_",
    49: "Start Attacking",
    50: "Summon Gameobject _gameobjectNameActionParamOne_",
    51: "Kill Target",
    52: "Activate Taxi Path _actionParamOne_",
    53: "Start _waypointStartActionParamThree_Path _actionParamTwo_",
    54: "Pause Waypoint",
    55: "Stop Waypoint",
    56: "Add Item _addItemBasedOnActionParams_",
    57: "Remove Item _addItemBasedOnActionParams_",
    58: "Install _updateAiTemplateActionParamOne_ Template",
    59: "Set Run _onOffActionParamOne_",
    60: "Set Fly _onOffActionParamOne_",
    61: "Set Swim _onOffActionParamOne_",
    62: "Teleport",
    63: "Add _actionParamTwo_ to Counter Id _actionParamOne_",
    64: "Store Targetlist",
    65: "Resume Waypoint",
    66: "Set Orientation _setOrientationTargetType_",
    67: "Create Timed Event",
    68: "Play Movie _actionParamOne_",
    69: "Move To _getTargetType_",
    70: "Respawn _getTargetType_",
    71: "Change Equipment",
    72: "Close Gossip",
    73: "Trigger Timed Event _actionParamOne_",
    74: "Remove Timed Event _actionParamOne_",
    75: "Add Aura '_spellNameActionParamOne_'",
    76: "Override Base Object Script",
    77: "Reset Base Object Script",
    78: "Reset All Scripts",
    79: "Set Ranged Movement",
    80: "Run Script",
    81: "Set Npc Flag_getNpcFlags_",
    82: "Add Npc Flag_getNpcFlags_",
    83: "Remove Npc Flag_getNpcFlags_",
    84: "Say Line _actionParamOne_",
    85: "Self Cast '_spellNameActionParamOne_'",
    86: "Cross Cast '_spellNameActionParamOne_'",
    87: "Run Random Script",
    88: "Run Random Script",
    89: "Start Random Movement",
    90: "Set Flag _getBytes1Flags_",
    91: "Remove Flag_getBytes1Flags_",
    92: "Interrupt Spell '_spellNameActionParamTwo_'",
    93: "Send Custom Animation _actionParamOne_",
    94: "Set Dynamic Flag_getDynamicFlags_",
    95: "Add Dynamic Flag_getDynamicFlags_",
    96: "Remove Dynamic Flag_getDynamicFlags_",
    97: "Jump To Pos",
    98: "Send Gossip",
    99: "Set Lootstate _goStateActionParamOne_",
    100: "Send Target _actionParamOne_",
    101: "Set Home Position",
    102: "Set Health Regeneration _onOffActionParamOne_",
    103: "Set Rooted _onOffActionParamOne_",
    104: "Set Gameobject Flag_getGoFlags_",
    105: "Add Gameobject Flag_getGoFlags_",
    106: "Remove Gameobject Flag_getGoFlags_",
    107: "Summon Creature Group _actionParamOne_",
    108: "Set _powerTypeActionParamOne_ To _actionParamTwo_",
    109: "Add _actionParamTwo_ _powerTypeActionParamOne_",
    110: "Remove _actionParamTwo_ _powerTypeActionParamOne_",
    111: "Stop game event _actionParamTwo_",
    112: "Start game event _actionParamTwo_",
    113: "Start closest Waypoint _actionParamOne_ - _actionParamTwo_",
    114: "Move Up",
    115: "Play Random Sound",
    116: "Set Corpse Delay to _actionParamOne_s",
    117: "_enableDisableInvertActionParamOne_ Evade",
    118: "Set GO State To _actionParamOne_",
    121: "Set Sight Distance to _actionParamOne_y",
    122: "Flee",
    123: "Modify Threat",
    124: "Load Equipment Id _actionParamOne_",
    125: "Trigger Random Timed Event Between _actionParamOne_-_actionParamTwo_",
    126: "Remove All Gameobjects",
    134: "Invoker Cast '_spellNameActionParamOne_'",
    135: "Play Cinematic",
    136: "Set _movementTypeActionParamOne_ Speed to _actionParamTwo_._actionParamThree_",
    142: "Set HP to _actionParamOne_%",
    # AC-only actions
    201: "Move to pos target _actionParamOne_",
    203: "Exit vehicle",
    204: "Set unit movement flags to _actionParamOne_",
    205: "Set combat distance to _actionParamOne_",
    206: "Dismount",
    207: "Set hover _actionParamOne_",
    208: "Add immunity Type: _actionParamOne_, Id: _actionParamTwo_, Value: _actionParamThree_",
    209: "Remove immunity Type: _actionParamOne_, Id: _actionParamTwo_, Value: _actionParamThree_",
    210: "Fall",
    211: "Flag reset _actionParamOne_",
    212: "Stop motion (StopMoving: _actionParamOne_, MovementExpired: _actionParamTwo_)",
    213: "No environment update",
    214: "Zone under attack",
    215: "Load Grid",
    216: "Play music SoundId: _actionParamOne_, OnlySelf: _actionParamTwo_, Type: _actionParamThree_",
    217: "Play random music OnlySelf: _actionParamFive_, Type: _actionParamSix_",
    218: "Custom Cast _spellNameActionParamOne_",
    219: "Do Cone Summon",
    220: "Player Talk String _actionParamOne_",
    221: "Do Vortex Summon",
    222: "Reset Cooldowns",
    223: "Do Action ID _actionParamOne_",
    224: "Stop Attack",
    225: "Send Guid",
    226: "Scripted Spawn _onOffActionParamOne_ Creature",
    227: "Set Scale to _actionParamOne_%",
    228: "Do Radial Summon",
    229: "Play Visual Kit Id _actionParamOne_",
    230: "Follow Type _followGroupParamTwo_",
    231: "Set Target Orientation",
    232: "Start Path _actionParamOne_",
    233: "Start Random Path _actionParamOne_-_actionParamTwo_",
    234: "Stop Movement",
    235: "Pause Movement",
    236: "Resume Movement",
    237: "Run World State Script: Event: _actionParamOne_, Param: _actionParamTwo_",
    238: "Disable reward: Disable Reputation _onOffActionParamOne_, Disable Loot _onOffActionParamTwo_",
}

# Flags
UNIT_FLAGS = {
    "SERVER_CONTROLLED": 0x00000001, "NON_ATTACKABLE": 0x00000002,
    "DISABLE_MOVE": 0x00000004, "PVP_ATTACKABLE": 0x00000008,
    "RENAME": 0x00000010, "PREPARATION": 0x00000020,
    "NOT_ATTACKABLE_1": 0x00000080, "IMMUNE_TO_PC": 0x00000100,
    "IMMUNE_TO_NPC": 0x00000200, "LOOTING": 0x00000400,
    "PET_IN_COMBAT": 0x00000800, "PVP": 0x00001000,
    "SILENCED": 0x00002000, "PACIFIED": 0x00020000,
    "STUNNED": 0x00040000, "IN_COMBAT": 0x00080000,
    "DISARMED": 0x00200000, "CONFUSED": 0x00400000,
    "FLEEING": 0x00800000, "PLAYER_CONTROLLED": 0x01000000,
    "NOT_SELECTABLE": 0x02000000, "SKINNABLE": 0x04000000,
    "MOUNT": 0x08000000, "SHEATHE": 0x40000000,
}

NPC_FLAGS = {
    "GOSSIP": 0x00000001, "QUESTGIVER": 0x00000002,
    "TRAINER": 0x00000010, "TRAINER_CLASS": 0x00000020,
    "TRAINER_PROFESSION": 0x00000040, "VENDOR": 0x00000080,
    "VENDOR_AMMO": 0x00000100, "VENDOR_FOOD": 0x00000200,
    "VENDOR_POISON": 0x00000400, "VENDOR_REAGENT": 0x00000800,
    "REPAIR": 0x00001000, "FLIGHTMASTER": 0x00002000,
    "SPIRITHEALER": 0x00004000, "SPIRITGUIDE": 0x00008000,
    "INNKEEPER": 0x00010000, "BANKER": 0x00020000,
    "PETITIONER": 0x00040000, "TABARDDESIGNER": 0x00080000,
    "BATTLEMASTER": 0x00100000, "AUCTIONEER": 0x00200000,
    "STABLEMASTER": 0x00400000, "GUILD_BANKER": 0x00800000,
    "SPELLCLICK": 0x01000000, "PLAYER_VEHICLE": 0x02000000,
}

GO_FLAGS = {
    "IN_USE": 0x00000001, "LOCKED": 0x00000002,
    "INTERACT_COND": 0x00000004, "TRANSPORT": 0x00000008,
    "NOT_SELECTABLE": 0x00000010, "NODESPAWN": 0x00000020,
    "TRIGGERED": 0x00000040, "FREEZE_ANIMATION": 0x00000080,
    "DAMAGED": 0x00000200, "DESTROYED": 0x00000400,
}

DYNAMIC_FLAGS = {
    "LOOTABLE": 0x0001, "TRACK_UNIT": 0x0002, "TAPPED": 0x0004,
    "TAPPED_BY_PLAYER": 0x0008, "SPECIALINFO": 0x0010, "DEAD": 0x0020,
    "REFER_A_FRIEND": 0x0040, "TAPPED_BY_ALL_THREAT_LIST": 0x0080,
}

EVENT_FLAGS = {
    "NONE": 0x00, "NOT_REPEATABLE": 0x01, "NORMAL_DUNGEON": 0x02,
    "HEROIC_DUNGEON": 0x04, "NORMAL_RAID": 0x08, "HEROIC_RAID": 0x10,
    "DEBUG_ONLY": 0x80,
}


class SaiCommentGenerator:
    """Generates human-readable comments for SmartAI scripts."""

    def __init__(self, mysql_query_func=None, sqlite_path=None):
        """
        Initialize the comment generator.

        Args:
            mysql_query_func: Function to execute MySQL queries, should return list of dicts
            sqlite_path: Path to Keira3's sqlite.db for spell names
        """
        self.mysql_query = mysql_query_func
        self.sqlite_path = sqlite_path or KEIRA_SQLITE_PATH
        self._sqlite_conn = None

    def _get_sqlite_conn(self):
        """Get or create sqlite connection."""
        if self._sqlite_conn is None and self.sqlite_path.exists():
            self._sqlite_conn = sqlite3.connect(str(self.sqlite_path))
        return self._sqlite_conn

    def get_spell_name(self, spell_id: int) -> str:
        """Get spell name from Keira3's sqlite database."""
        if not spell_id:
            return ""
        conn = self._get_sqlite_conn()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT spellName FROM spells WHERE ID = ?", (spell_id,))
            row = cursor.fetchone()
            if row:
                return row[0]
        return f"Spell {spell_id}"

    def get_creature_name(self, entry: int) -> str:
        """Get creature name from MySQL."""
        if not entry or not self.mysql_query:
            return f"Creature {entry}"
        try:
            results = self.mysql_query(
                f"SELECT name FROM creature_template WHERE entry = {entry}",
                "world"
            )
            if results:
                return results[0].get("name", f"Creature {entry}")
        except:
            pass
        return f"Creature {entry}"

    def get_creature_name_by_guid(self, guid: int) -> str:
        """Get creature name by GUID from MySQL."""
        if not guid or not self.mysql_query:
            return f"Creature GUID {guid}"
        try:
            results = self.mysql_query(
                f"SELECT ct.name FROM creature c JOIN creature_template ct ON c.id1 = ct.entry WHERE c.guid = {guid}",
                "world"
            )
            if results:
                return results[0].get("name", f"Creature GUID {guid}")
        except:
            pass
        return f"Creature GUID {guid}"

    def get_gameobject_name(self, entry: int) -> str:
        """Get gameobject name from MySQL."""
        if not entry or not self.mysql_query:
            return f"Gameobject {entry}"
        try:
            results = self.mysql_query(
                f"SELECT name FROM gameobject_template WHERE entry = {entry}",
                "world"
            )
            if results:
                return results[0].get("name", f"Gameobject {entry}")
        except:
            pass
        return f"Gameobject {entry}"

    def get_gameobject_name_by_guid(self, guid: int) -> str:
        """Get gameobject name by GUID from MySQL."""
        if not guid or not self.mysql_query:
            return f"Gameobject GUID {guid}"
        try:
            results = self.mysql_query(
                f"SELECT gt.name FROM gameobject g JOIN gameobject_template gt ON g.id = gt.entry WHERE g.guid = {guid}",
                "world"
            )
            if results:
                return results[0].get("name", f"Gameobject GUID {guid}")
        except:
            pass
        return f"Gameobject GUID {guid}"

    def get_quest_title(self, quest_id: int) -> str:
        """Get quest title from MySQL."""
        if not quest_id or not self.mysql_query:
            return f"Quest {quest_id}"
        try:
            results = self.mysql_query(
                f"SELECT LogTitle FROM quest_template WHERE ID = {quest_id}",
                "world"
            )
            if results:
                return results[0].get("LogTitle", f"Quest {quest_id}")
        except:
            pass
        return f"Quest {quest_id}"

    def get_item_name(self, entry: int) -> str:
        """Get item name from MySQL."""
        if not entry or not self.mysql_query:
            return f"Item {entry}"
        try:
            results = self.mysql_query(
                f"SELECT name FROM item_template WHERE entry = {entry}",
                "world"
            )
            if results:
                return results[0].get("name", f"Item {entry}")
        except:
            pass
        return f"Item {entry}"

    def _get_target_string(self, script: dict) -> str:
        """Get human-readable string for target type."""
        target_type = script.get("target_type", 0)
        target_param1 = script.get("target_param1", 0)

        target_strings = {
            1: "Self", 2: "Victim", 3: "Second On Threatlist",
            4: "Last On Threatlist", 5: "Random On Threatlist",
            6: "Random On Threatlist Not Top", 7: "Invoker", 8: "Position",
            12: "Stored", 16: "Invoker's Party", 17: "Players in Range",
            18: "Players in Distance", 21: "Closest Player",
            22: "Invoker's Vehicle", 23: "Owner Or Summoner",
            24: "Threatlist", 25: "Closest Enemy", 26: "Closest Friendly Unit",
            27: "Loot Recipients", 28: "Farthest Target", 29: "Vehicle Seat",
            201: "Player With Aura", 202: "Random Point", 203: "Class Roles",
            204: "Summoned Creatures", 205: "Instance Storage",
        }

        if target_type in target_strings:
            return target_strings[target_type]
        elif target_type in (9, 11, 19):  # CREATURE_RANGE, CREATURE_DISTANCE, CLOSEST_CREATURE
            return f"Closest Creature '{self.get_creature_name(target_param1)}'"
        elif target_type == 10:  # CREATURE_GUID
            return f"Closest Creature '{self.get_creature_name_by_guid(target_param1)}'"
        elif target_type in (13, 15, 20):  # GAMEOBJECT_RANGE, GAMEOBJECT_DISTANCE, CLOSEST_GAMEOBJECT
            return f"Closest Gameobject '{self.get_gameobject_name(target_param1)}'"
        elif target_type == 14:  # GAMEOBJECT_GUID
            return f"Closest Gameobject '{self.get_gameobject_name_by_guid(target_param1)}'"

        return "[unsupported target type]"

    def _get_previous_script_link(self, scripts: list, script: dict):
        """Get previous script in link chain."""
        script_id = script.get("id", 0)
        if script_id == 0:
            return None

        for row in scripts:
            if row.get("link") == script_id:
                if row.get("event_type") == 61:  # LINK event
                    return self._get_previous_script_link(scripts, row)
                return row
        return None

    def _get_unit_flags_string(self, flags: int) -> str:
        """Convert unit flags to human-readable string."""
        flag_names = {
            UNIT_FLAGS["SERVER_CONTROLLED"]: "Server Controlled",
            UNIT_FLAGS["NON_ATTACKABLE"]: "Not Attackable",
            UNIT_FLAGS["DISABLE_MOVE"]: "Disable Movement",
            UNIT_FLAGS["PVP_ATTACKABLE"]: "PvP Attackable",
            UNIT_FLAGS["RENAME"]: "Rename",
            UNIT_FLAGS["PREPARATION"]: "Preparation",
            UNIT_FLAGS["NOT_ATTACKABLE_1"]: "Not Attackable",
            UNIT_FLAGS["IMMUNE_TO_PC"]: "Immune To Players",
            UNIT_FLAGS["IMMUNE_TO_NPC"]: "Immune To NPC's",
            UNIT_FLAGS["LOOTING"]: "Looting",
            UNIT_FLAGS["PET_IN_COMBAT"]: "Pet In Combat",
            UNIT_FLAGS["PVP"]: "PvP",
            UNIT_FLAGS["SILENCED"]: "Silenced",
            UNIT_FLAGS["PACIFIED"]: "Pacified",
            UNIT_FLAGS["STUNNED"]: "Stunned",
            UNIT_FLAGS["IN_COMBAT"]: "In Combat",
            UNIT_FLAGS["DISARMED"]: "Disarmed",
            UNIT_FLAGS["CONFUSED"]: "Confused",
            UNIT_FLAGS["FLEEING"]: "Fleeing",
            UNIT_FLAGS["PLAYER_CONTROLLED"]: "Player Controlled",
            UNIT_FLAGS["NOT_SELECTABLE"]: "Not Selectable",
            UNIT_FLAGS["SKINNABLE"]: "Skinnable",
            UNIT_FLAGS["MOUNT"]: "Mounted",
            UNIT_FLAGS["SHEATHE"]: "Sheathed",
        }
        parts = [name for flag, name in flag_names.items() if flags & flag]
        return " & ".join(parts) if parts else ""

    def _get_npc_flags_string(self, flags: int) -> str:
        """Convert NPC flags to human-readable string."""
        flag_names = {
            NPC_FLAGS["GOSSIP"]: "Gossip",
            NPC_FLAGS["QUESTGIVER"]: "Questgiver",
            NPC_FLAGS["TRAINER"]: "Trainer",
            NPC_FLAGS["TRAINER_CLASS"]: "Class Trainer",
            NPC_FLAGS["TRAINER_PROFESSION"]: "Profession Trainer",
            NPC_FLAGS["VENDOR"]: "Vendor",
            NPC_FLAGS["VENDOR_AMMO"]: "Ammo Vendor",
            NPC_FLAGS["VENDOR_FOOD"]: "Food Vendor",
            NPC_FLAGS["VENDOR_POISON"]: "Poison Vendor",
            NPC_FLAGS["VENDOR_REAGENT"]: "Reagent Vendor",
            NPC_FLAGS["REPAIR"]: "Repair Vendor",
            NPC_FLAGS["FLIGHTMASTER"]: "Flightmaster",
            NPC_FLAGS["SPIRITHEALER"]: "Spirithealer",
            NPC_FLAGS["SPIRITGUIDE"]: "Spiritguide",
            NPC_FLAGS["INNKEEPER"]: "Innkeeper",
            NPC_FLAGS["BANKER"]: "Banker",
            NPC_FLAGS["PETITIONER"]: "Petitioner",
            NPC_FLAGS["TABARDDESIGNER"]: "Tabard Designer",
            NPC_FLAGS["BATTLEMASTER"]: "Battlemaster",
            NPC_FLAGS["AUCTIONEER"]: "Auctioneer",
            NPC_FLAGS["STABLEMASTER"]: "Stablemaster",
            NPC_FLAGS["GUILD_BANKER"]: "Guild Banker",
            NPC_FLAGS["SPELLCLICK"]: "Spellclick",
            NPC_FLAGS["PLAYER_VEHICLE"]: "Player Vehicle",
        }
        parts = [name for flag, name in flag_names.items() if flags & flag]
        return " & ".join(parts) if parts else ""

    def _generate_event_comment(self, script: dict, name: str, link_script: dict = None) -> str:
        """Generate the event part of the comment."""
        source_type = script.get("source_type", 0)
        event_type = script.get("event_type", 0)

        if source_type in (SAI_TYPE_CREATURE, SAI_TYPE_GAMEOBJECT):
            comment = SAI_EVENT_COMMENTS.get(event_type, f"[Unknown Event {event_type}]")
            event_line = f"{name} - {comment}"
        elif source_type == SAI_TYPE_AREATRIGGER:
            if event_type in (46, 61):  # AREATRIGGER_ONTRIGGER, LINK
                event_line = "Areatrigger - On Trigger"
            else:
                event_line = "Areatrigger - INCORRECT EVENT TYPE"
        elif source_type == SAI_TYPE_TIMED_ACTIONLIST:
            event_line = f"{name} - Actionlist"
        else:
            event_line = f"{name} - [Unknown source type {source_type}]"

        # Handle LINK event
        if "_previousLineComment_" in event_line and link_script:
            link_event_type = link_script.get("event_type", 0)
            link_comment = SAI_EVENT_COMMENTS.get(link_event_type, "")
            event_line = event_line.replace("_previousLineComment_", link_comment)
            # Copy event params from linked script
            for i in range(1, 7):
                script[f"event_param{i}"] = link_script.get(f"event_param{i}", 0)

        event_line = event_line.replace("_previousLineComment_", "MISSING LINK")

        # Replace event parameters
        for i in range(1, 7):
            param_names = ["One", "Two", "Three", "Four", "Five", "Six"]
            event_line = event_line.replace(
                f"_eventParam{param_names[i-1]}_",
                str(script.get(f"event_param{i}", 0))
            )

        # Replace special placeholders
        if "_questNameEventParamOne_" in event_line:
            event_line = event_line.replace(
                "_questNameEventParamOne_",
                self.get_quest_title(script.get("event_param1", 0))
            )
        if "_spellNameEventParamOne_" in event_line:
            event_line = event_line.replace(
                "_spellNameEventParamOne_",
                self.get_spell_name(script.get("event_param1", 0))
            )
        if "_targetCastingSpellName_" in event_line:
            event_line = event_line.replace(
                "_targetCastingSpellName_",
                self.get_spell_name(script.get("event_param3", 0))
            )
        if "_hasAuraEventParamOne_" in event_line:
            event_line = event_line.replace(
                "_hasAuraEventParamOne_",
                self.get_spell_name(script.get("event_param1", 0))
            )
        if "_waypointParamOne_" in event_line:
            val = script.get("event_param1", 0)
            event_line = event_line.replace("_waypointParamOne_", str(val) if val > 0 else "Any")
        if "_waypointParamTwo_" in event_line:
            val = script.get("event_param2", 0)
            event_line = event_line.replace("_waypointParamTwo_", str(val) if val > 0 else "Any")

        return event_line

    def _generate_action_comment(self, script: dict, link_script: dict = None) -> str:
        """Generate the action part of the comment."""
        action_type = script.get("action_type", 0)
        action_line = SAI_ACTION_COMMENTS.get(action_type, f"[Unknown Action {action_type}]")

        # Replace action parameters
        param_names = ["One", "Two", "Three", "Four", "Five", "Six"]
        for i in range(1, 7):
            action_line = action_line.replace(
                f"_actionParam{param_names[i-1]}_",
                str(script.get(f"action_param{i}", 0))
            )

        # Replace special placeholders
        if "_questNameActionParamOne_" in action_line:
            action_line = action_line.replace(
                "_questNameActionParamOne_",
                self.get_quest_title(script.get("action_param1", 0))
            )
        if "_questNameKillCredit_" in action_line:
            action_line = action_line.replace(
                "_questNameKillCredit_",
                self.get_quest_title(script.get("action_param1", 0))
            )
        if "_spellNameActionParamOne_" in action_line:
            action_line = action_line.replace(
                "_spellNameActionParamOne_",
                self.get_spell_name(script.get("action_param1", 0))
            )
        if "_spellNameActionParamTwo_" in action_line:
            action_line = action_line.replace(
                "_spellNameActionParamTwo_",
                self.get_spell_name(script.get("action_param2", 0))
            )
        if "_creatureNameActionParamOne_" in action_line:
            action_line = action_line.replace(
                "_creatureNameActionParamOne_",
                self.get_creature_name(script.get("action_param1", 0))
            )
        if "_gameobjectNameActionParamOne_" in action_line:
            action_line = action_line.replace(
                "_gameobjectNameActionParamOne_",
                f"'{self.get_gameobject_name(script.get('action_param1', 0))}'"
            )
        if "_addItemBasedOnActionParams_" in action_line:
            item_name = self.get_item_name(script.get("action_param1", 0))
            count = script.get("action_param2", 1)
            action_line = action_line.replace(
                "_addItemBasedOnActionParams_",
                f"'{item_name}'"
            )
            action_line += f" {count} Time{'s' if count > 1 else ''}"

        # React state
        if "_reactStateParamOne_" in action_line:
            states = {0: "Passive", 1: "Defensive", 2: "Aggressive"}
            action_line = action_line.replace(
                "_reactStateParamOne_",
                states.get(script.get("action_param1", 0), "[Unknown Reactstate]")
            )

        # Start/Stop
        if "_startOrStopActionParamOne_" in action_line:
            action_line = action_line.replace(
                "_startOrStopActionParamOne_",
                "Stop" if script.get("action_param1", 0) == 0 else "Start"
            )

        # Enable/Disable
        if "_enableDisableActionParamOne_" in action_line:
            action_line = action_line.replace(
                "_enableDisableActionParamOne_",
                "Disable" if script.get("action_param1", 0) == 0 else "Enable"
            )
        if "_enableDisableInvertActionParamOne_" in action_line:
            action_line = action_line.replace(
                "_enableDisableInvertActionParamOne_",
                "Enable" if script.get("action_param1", 0) == 0 else "Disable"
            )

        # On/Off
        if "_onOffActionParamOne_" in action_line:
            action_line = action_line.replace(
                "_onOffActionParamOne_",
                "On" if script.get("action_param1", 0) == 1 else "Off"
            )
        if "_onOffActionParamTwo_" in action_line:
            action_line = action_line.replace(
                "_onOffActionParamTwo_",
                "On" if script.get("action_param2", 0) == 1 else "Off"
            )

        # Increment/Decrement
        if "_incrementOrDecrementActionParamOne_" in action_line:
            p1, p2 = script.get("action_param1", 0), script.get("action_param2", 0)
            val = "Increment" if p1 == 1 else ("Decrement" if p2 == 1 else "Increment or Decrement")
            action_line = action_line.replace("_incrementOrDecrementActionParamOne_", val)

        # Sheath
        if "_sheathActionParamOne_" in action_line:
            sheaths = {0: "Unarmed", 1: "Melee", 2: "Ranged"}
            action_line = action_line.replace(
                "_sheathActionParamOne_",
                sheaths.get(script.get("action_param1", 0), "[Unknown Sheath]")
            )

        # Force despawn
        if "_forceDespawnActionParamOne_" in action_line:
            val = script.get("action_param1", 0)
            action_line = action_line.replace(
                "_forceDespawnActionParamOne_",
                f"In {val} ms" if val > 2 else "Instant"
            )

        # Invincibility HP
        if "_invincibilityHpActionParamsOneTwo_" in action_line:
            p1, p2 = script.get("action_param1", 0), script.get("action_param2", 0)
            if p1 > 0:
                val = f"Set Invincibility Hp {p1}"
            elif p2 > 0:
                val = f"Set Invincibility Hp {p2}%"
            elif p1 == 0 and p2 == 0:
                val = "Reset Invincibility Hp"
            else:
                val = "[Unsupported parameters]"
            action_line = action_line.replace("_invincibilityHpActionParamsOneTwo_", val)

        # Morph/Mount
        for placeholder, action_word in [
            ("_morphToEntryOrModelActionParams_", "Morph"),
            ("_mountToEntryOrModelActionParams_", "Mount")
        ]:
            if placeholder in action_line:
                p1, p2 = script.get("action_param1", 0), script.get("action_param2", 0)
                if p1 > 0:
                    val = f"{action_word} To Creature {self.get_creature_name(p1)}"
                elif p2 > 0:
                    val = f"{action_word} To Model {p2}"
                else:
                    val = "Demorph" if action_word == "Morph" else "Dismount"
                action_line = action_line.replace(placeholder, val)

        # Target type
        if "_getTargetType_" in action_line:
            action_line = action_line.replace("_getTargetType_", self._get_target_string(script))
        if "_startOrStopBasedOnTargetType_" in action_line:
            if script.get("target_type", 0) == 0:
                action_line = action_line.replace("_startOrStopBasedOnTargetType_", "Stop")
                action_line = action_line.replace("_getTargetType_", "")
            else:
                action_line = action_line.replace("_startOrStopBasedOnTargetType_", "Start")
        if "_setOrientationTargetType_" in action_line:
            tt = script.get("target_type", 0)
            if tt == 1:  # SELF
                val = "Home Position"
            elif tt == 8:  # POSITION
                val = str(script.get("target_o", 0))
            else:
                val = self._get_target_string(script)
            action_line = action_line.replace("_setOrientationTargetType_", val)

        # Flags
        if "_getUnitFlags_" in action_line:
            flags_str = self._get_unit_flags_string(script.get("action_param1", 0))
            if " & " in flags_str:
                action_line = action_line.replace("_getUnitFlags_", f"s {flags_str}")
            else:
                action_line = action_line.replace("_getUnitFlags_", f" {flags_str}")

        if "_getNpcFlags_" in action_line:
            flags_str = self._get_npc_flags_string(script.get("action_param1", 0))
            if " & " in flags_str:
                action_line = action_line.replace("_getNpcFlags_", f"s {flags_str}")
            else:
                action_line = action_line.replace("_getNpcFlags_", f" {flags_str}")

        # Random parameters
        if "_actionRandomParameters_" in action_line:
            params = [script.get(f"action_param{i}", 0) for i in range(1, 7)]
            random_vals = [str(params[0]), str(params[1])]
            for p in params[2:]:
                if p > 0:
                    random_vals.append(str(p))
            action_line = action_line.replace("_actionRandomParameters_", ", ".join(random_vals))

        # Power type
        if "_powerTypeActionParamOne_" in action_line:
            powers = {0: "Mana", 1: "Rage", 2: "Focus", 3: "Energy", 4: "Happiness", 5: "Rune", 6: "Runic Power"}
            action_line = action_line.replace(
                "_powerTypeActionParamOne_",
                powers.get(script.get("action_param1", 0), "[Unknown Powertype]")
            )

        # Movement type
        if "_movementTypeActionParamOne_" in action_line:
            movements = {
                0: "Walk", 1: "Run", 2: "Run Back", 3: "Swim", 4: "Swim Back",
                5: "Turn Rate", 6: "Flight", 7: "Flight Back", 8: "Pitch Rate"
            }
            action_line = action_line.replace(
                "_movementTypeActionParamOne_",
                movements.get(script.get("action_param1", 0), "[Unknown Value]")
            )

        # Waypoint start
        if "_waypointStartActionParamThree_" in action_line:
            p3 = script.get("action_param3", 0)
            val = "Waypoint " if p3 == 0 else ("Patrol " if p3 == 1 else "[Unknown Value] ")
            action_line = action_line.replace("_waypointStartActionParamThree_", val)

        # GO state
        if "_goStateActionParamOne_" in action_line:
            states = {0: "Not Ready", 1: "Ready", 2: "Activated", 3: "Deactivated"}
            action_line = action_line.replace(
                "_goStateActionParamOne_",
                states.get(script.get("action_param1", 0), "[Unknown Gameobject State]")
            )

        # AI template
        if "_updateAiTemplateActionParamOne_" in action_line:
            templates = {0: "Basic", 1: "Caster", 2: "Turret", 3: "Passive", 4: "Caged Gameobject Part", 5: "Caged Creature Part"}
            action_line = action_line.replace(
                "_updateAiTemplateActionParamOne_",
                templates.get(script.get("action_param1", 0), "[Unknown ai template]")
            )

        # Follow group
        if "_followGroupParamTwo_" in action_line:
            types = {1: "Circle", 2: "Semi-Circle Behind", 3: "Semi-Circle Front", 4: "Line", 5: "Column", 6: "Angular"}
            action_line = action_line.replace(
                "_followGroupParamTwo_",
                types.get(script.get("action_param2", 0), "[Unknown Follow Type]")
            )

        # Add phase info
        use_link = link_script is not None
        phase_mask = (link_script or script).get("event_phase_mask", 0)
        if phase_mask != 0:
            phases = []
            for i in range(9):
                if phase_mask & (1 << i):
                    phases.append(str(i + 1))
            if phases:
                action_line += f" (Phase{'s' if len(phases) > 1 else ''} {' & '.join(phases)})"

        # Add event flags info
        event_flags = (link_script or script).get("event_flags", 0)
        if event_flags != 0:
            if event_flags & EVENT_FLAGS["NOT_REPEATABLE"]:
                action_line += " (No Repeat)"

            nd = event_flags & EVENT_FLAGS["NORMAL_DUNGEON"]
            hd = event_flags & EVENT_FLAGS["HEROIC_DUNGEON"]
            nr = event_flags & EVENT_FLAGS["NORMAL_RAID"]
            hr = event_flags & EVENT_FLAGS["HEROIC_RAID"]

            if nd and hd and nr and hr:
                action_line += " (Dungeon & Raid)"
            else:
                if nd and hd:
                    action_line += " (Dungeon)"
                elif nd:
                    action_line += " (Normal Dungeon)"
                elif hd:
                    action_line += " (Heroic Dungeon)"

                if nr and hr:
                    action_line += " (Raid)"
                elif nr:
                    action_line += " (Normal Raid)"
                elif hr:
                    action_line += " (Heroic Raid)"

            if event_flags & EVENT_FLAGS["DEBUG_ONLY"]:
                action_line += " (Debug)"

        return action_line

    def generate_comment(self, scripts: list, script: dict, name: str) -> str:
        """
        Generate a human-readable comment for a SmartAI script row.

        Args:
            scripts: All smart_scripts rows for this entity
            script: The specific row to generate comment for
            name: Name of the creature/gameobject

        Returns:
            Human-readable comment string
        """
        link_script = self._get_previous_script_link(scripts, script)
        event_comment = self._generate_event_comment(script, name, link_script)
        action_comment = self._generate_action_comment(script, link_script)
        return f"{event_comment} - {action_comment}"

    def generate_comments_for_entity(self, scripts: list, name: str) -> list:
        """
        Generate comments for all scripts of an entity.

        Args:
            scripts: All smart_scripts rows for this entity
            name: Name of the creature/gameobject

        Returns:
            List of (script, comment) tuples
        """
        return [(s, self.generate_comment(scripts, s, name)) for s in scripts]
