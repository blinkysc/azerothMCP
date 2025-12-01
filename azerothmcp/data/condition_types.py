#!/usr/bin/env python3
"""Condition Types Reference Data"""

CONDITION_TYPES = {
    0: {
        "name": "CONDITION_NONE",
        "description": "Never used",
        "value1": "N/A",
        "value2": "N/A",
        "value3": "N/A"
    },
    1: {
        "name": "CONDITION_AURA",
        "description": "Target has aura from spell",
        "value1": "Spell ID",
        "value2": "Effect index (0-2)",
        "value3": "Always 0"
    },
    2: {
        "name": "CONDITION_ITEM",
        "description": "Target has item(s) in inventory",
        "value1": "Item entry",
        "value2": "Item count required",
        "value3": "0 = not in bank, 1 = check bank too"
    },
    3: {
        "name": "CONDITION_ITEM_EQUIPPED",
        "description": "Target has item equipped",
        "value1": "Item entry",
        "value2": "Always 0",
        "value3": "Always 0"
    },
    4: {
        "name": "CONDITION_ZONEID",
        "description": "Target is in zone",
        "value1": "Zone ID",
        "value2": "Always 0",
        "value3": "Always 0"
    },
    5: {
        "name": "CONDITION_REPUTATION_RANK",
        "description": "Target has reputation rank with faction",
        "value1": "Faction ID (from Faction.dbc)",
        "value2": "Rank mask: 1=Hated, 2=Hostile, 4=Unfriendly, 8=Neutral, 16=Friendly, 32=Honored, 64=Revered, 128=Exalted",
        "value3": "Always 0"
    },
    6: {
        "name": "CONDITION_TEAM",
        "description": "Target is on team (Alliance/Horde)",
        "value1": "469 = Alliance, 67 = Horde",
        "value2": "Always 0",
        "value3": "Always 0"
    },
    7: {
        "name": "CONDITION_SKILL",
        "description": "Target has skill at level",
        "value1": "Skill ID (from SkillLine.dbc)",
        "value2": "Minimum skill value",
        "value3": "Always 0"
    },
    8: {
        "name": "CONDITION_QUESTREWARDED",
        "description": "Target has completed and been rewarded quest",
        "value1": "Quest ID",
        "value2": "Always 0",
        "value3": "Always 0"
    },
    9: {
        "name": "CONDITION_QUESTTAKEN",
        "description": "Target has quest in log (active)",
        "value1": "Quest ID",
        "value2": "Always 0",
        "value3": "Always 0"
    },
    10: {
        "name": "CONDITION_DRUNKENSTATE",
        "description": "Target's drunken state",
        "value1": "0=Sober, 1=Tipsy, 2=Drunk, 3=Smashed",
        "value2": "Always 0",
        "value3": "Always 0"
    },
    11: {
        "name": "CONDITION_WORLD_STATE",
        "description": "World state has value",
        "value1": "World state index",
        "value2": "World state value",
        "value3": "Always 0"
    },
    12: {
        "name": "CONDITION_ACTIVE_EVENT",
        "description": "Game event is active",
        "value1": "game_event.eventEntry",
        "value2": "Always 0",
        "value3": "Always 0"
    },
    13: {
        "name": "CONDITION_INSTANCE_INFO",
        "description": "Instance script data check",
        "value1": "Entry (script-specific)",
        "value2": "Data value (script-specific)",
        "value3": "0=INSTANCE_INFO_DATA, 1=GUID_DATA, 2=BOSS_STATE, 3=DATA64"
    },
    14: {
        "name": "CONDITION_QUEST_NONE",
        "description": "Target has never accepted quest",
        "value1": "Quest ID",
        "value2": "Always 0",
        "value3": "Always 0"
    },
    15: {
        "name": "CONDITION_CLASS",
        "description": "Target is class(es)",
        "value1": "Class mask (1=Warrior, 2=Paladin, 4=Hunter, 8=Rogue, 16=Priest, 32=DK, 64=Shaman, 128=Mage, 256=Warlock, 1024=Druid)",
        "value2": "Always 0",
        "value3": "Always 0"
    },
    16: {
        "name": "CONDITION_RACE",
        "description": "Target is race(s)",
        "value1": "Race mask (1=Human, 2=Orc, 4=Dwarf, 8=NightElf, 16=Undead, 32=Tauren, 64=Gnome, 128=Troll, 512=BloodElf, 1024=Draenei)",
        "value2": "Always 0",
        "value3": "Always 0"
    },
    17: {
        "name": "CONDITION_ACHIEVEMENT",
        "description": "Target has achievement",
        "value1": "Achievement ID",
        "value2": "Always 0",
        "value3": "Always 0"
    },
    18: {
        "name": "CONDITION_TITLE",
        "description": "Target has title",
        "value1": "Title ID (from CharTitles.dbc)",
        "value2": "Always 0",
        "value3": "Always 0"
    },
    19: {
        "name": "CONDITION_SPAWNMASK",
        "description": "Difficulty/spawnmask check",
        "value1": "SpawnMask value",
        "value2": "Always 0",
        "value3": "Always 0"
    },
    20: {
        "name": "CONDITION_GENDER",
        "description": "Target is gender",
        "value1": "0=Male, 1=Female, 2=None",
        "value2": "Always 0",
        "value3": "Always 0"
    },
    21: {
        "name": "CONDITION_UNIT_STATE",
        "description": "Target has unit state",
        "value1": "UnitState enum value",
        "value2": "Always 0",
        "value3": "Always 0"
    },
    22: {
        "name": "CONDITION_MAPID",
        "description": "Target is on map",
        "value1": "Map ID (0=Eastern Kingdoms, 1=Kalimdor, etc.)",
        "value2": "Always 0",
        "value3": "Always 0"
    },
    23: {
        "name": "CONDITION_AREAID",
        "description": "Target is in area",
        "value1": "Area ID (from AreaTable.dbc)",
        "value2": "Always 0",
        "value3": "Always 0"
    },
    24: {
        "name": "CONDITION_CREATURE_TYPE",
        "description": "Target creature is type",
        "value1": "Creature type (0=Beast, 1=Dragonkin, etc.)",
        "value2": "Always 0",
        "value3": "Always 0"
    },
    25: {
        "name": "CONDITION_SPELL",
        "description": "Target knows spell",
        "value1": "Spell ID",
        "value2": "Always 0",
        "value3": "Always 0"
    },
    26: {
        "name": "CONDITION_PHASEMASK",
        "description": "Target is in phase",
        "value1": "Phase mask value",
        "value2": "Always 0",
        "value3": "Always 0"
    },
    27: {
        "name": "CONDITION_LEVEL",
        "description": "Target level comparison",
        "value1": "Level value",
        "value2": "0=equal, 1=higher, 2=lower, 3=higher or equal, 4=lower or equal",
        "value3": "Always 0"
    },
    28: {
        "name": "CONDITION_QUEST_COMPLETE",
        "description": "Target has quest objectives complete (not yet rewarded)",
        "value1": "Quest ID",
        "value2": "Always 0",
        "value3": "Always 0"
    },
    29: {
        "name": "CONDITION_NEAR_CREATURE",
        "description": "Target is near creature",
        "value1": "Creature entry",
        "value2": "Distance in yards",
        "value3": "0=Alive, 1=Dead"
    },
    30: {
        "name": "CONDITION_NEAR_GAMEOBJECT",
        "description": "Target is near gameobject",
        "value1": "Gameobject entry",
        "value2": "Distance in yards",
        "value3": "GoState: 0=ignore, 1=Ready, 2=Not Ready"
    },
    31: {
        "name": "CONDITION_OBJECT_ENTRY_GUID",
        "description": "Target is specific object type/entry/guid",
        "value1": "TypeID: 3=Unit, 4=Player, 5=GameObject, 7=Corpse",
        "value2": "Entry (0=any of type)",
        "value3": "GUID (0=any)"
    },
    32: {
        "name": "CONDITION_TYPE_MASK",
        "description": "Target matches type mask",
        "value1": "TypeMask: 8=Unit, 16=Player, 32=GameObject, 128=Corpse",
        "value2": "Always 0",
        "value3": "Always 0"
    },
    33: {
        "name": "CONDITION_RELATION_TO",
        "description": "Target has relation to another condition target",
        "value1": "Other ConditionTarget (0 or 1)",
        "value2": "Relation: 0=Self, 1=InParty, 2=InRaidOrParty, 3=OwnedBy, 4=PassengerOf, 5=CreatedBy",
        "value3": "Always 0"
    },
    34: {
        "name": "CONDITION_REACTION_TO",
        "description": "Target has reaction to another condition target",
        "value1": "Other ConditionTarget (0 or 1)",
        "value2": "Reaction mask (same as reputation rank mask)",
        "value3": "Always 0"
    },
    35: {
        "name": "CONDITION_DISTANCE_TO",
        "description": "Target is distance from another condition target",
        "value1": "Other ConditionTarget (0 or 1)",
        "value2": "Distance in yards",
        "value3": "Comparison: 0=equal, 1=higher, 2=lower, 3=higher/equal, 4=lower/equal"
    },
    36: {
        "name": "CONDITION_ALIVE",
        "description": "Target alive state",
        "value1": "Always 0",
        "value2": "Always 0",
        "value3": "Always 0",
        "notes": "Use NegativeCondition: 0=must be alive, 1=must be dead"
    },
    37: {
        "name": "CONDITION_HP_VAL",
        "description": "Target HP value",
        "value1": "HP value",
        "value2": "Comparison: 0=equal, 1=higher, 2=lower, 3=higher/equal, 4=lower/equal",
        "value3": "Always 0"
    },
    38: {
        "name": "CONDITION_HP_PCT",
        "description": "Target HP percentage",
        "value1": "HP percentage",
        "value2": "Comparison: 0=equal, 1=higher, 2=lower, 3=higher/equal, 4=lower/equal",
        "value3": "Always 0"
    },
    39: {
        "name": "CONDITION_REALM_ACHIEVEMENT",
        "description": "Realm has achievement (any player completed)",
        "value1": "Achievement ID",
        "value2": "Always 0",
        "value3": "Always 0"
    },
    40: {
        "name": "CONDITION_IN_WATER",
        "description": "Target in water",
        "value1": "Always 0",
        "value2": "Always 0",
        "value3": "Always 0",
        "notes": "Use NegativeCondition: 0=on land, 1=in water"
    },
    42: {
        "name": "CONDITION_STAND_STATE",
        "description": "Target stand state",
        "value1": "0=Exact state, 1=Any state type",
        "value2": "If Value1=0: exact state; If Value1=1: 0=Standing, 1=Sitting",
        "value3": "Always 0"
    },
    43: {
        "name": "CONDITION_DAILY_QUEST_DONE",
        "description": "Target has done daily quest today",
        "value1": "Quest ID",
        "value2": "Always 0",
        "value3": "Always 0"
    },
    44: {
        "name": "CONDITION_CHARMED",
        "description": "Target is charmed",
        "value1": "Always 0",
        "value2": "Always 0",
        "value3": "Always 0"
    },
    45: {
        "name": "CONDITION_PET_TYPE",
        "description": "Target has pet type",
        "value1": "Pet type mask",
        "value2": "Always 0",
        "value3": "Always 0"
    },
    46: {
        "name": "CONDITION_TAXI",
        "description": "Target is on taxi/flight path",
        "value1": "Always 0",
        "value2": "Always 0",
        "value3": "Always 0"
    },
    47: {
        "name": "CONDITION_QUESTSTATE",
        "description": "Target quest state matches",
        "value1": "Quest ID",
        "value2": "State mask: 1=NotTaken, 2=Completed, 8=InProgress, 32=Failed, 64=Rewarded",
        "value3": "Always 0"
    },
    48: {
        "name": "CONDITION_QUEST_OBJECTIVE_PROGRESS",
        "description": "Target has quest objective progress",
        "value1": "Quest ID",
        "value2": "Objective ID (RequiredNpcOrGo index)",
        "value3": "Objective count",
        "notes": "True when objective count >= ConditionValue3"
    },
    49: {
        "name": "CONDITION_DIFFICULTY_ID",
        "description": "Current difficulty matches",
        "value1": "Difficulty ID",
        "value2": "Always 0",
        "value3": "Always 0"
    },
    101: {
        "name": "CONDITION_QUEST_SATISFY_EXCLUSIVE",
        "description": "Player satisfies quest exclusive group",
        "value1": "Quest ID",
        "value2": "Always 0",
        "value3": "Always 0"
    },
    102: {
        "name": "CONDITION_HAS_AURA_TYPE",
        "description": "Target has aura of type",
        "value1": "Aura type",
        "value2": "Always 0",
        "value3": "Always 0"
    },
    103: {
        "name": "CONDITION_WORLD_SCRIPT",
        "description": "World script condition check",
        "value1": "Condition ID",
        "value2": "State",
        "value3": "Always 0"
    }
}
