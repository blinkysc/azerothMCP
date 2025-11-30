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
Conditions tools for AzerothCore MCP Server.

The conditions system allows defining prerequisites for various game systems:
- Loot drops
- Gossip menus and options
- Quest availability
- Spell casting/targeting
- SmartAI script execution
- NPC vendors
- And more
"""

import json
from typing import Optional

from ..db import execute_query


# Source Type definitions
SOURCE_TYPES = {
    0: {
        "name": "CONDITION_SOURCE_TYPE_NONE",
        "description": "Reference template. Only used when SourceTypeOrReferenceId is negative.",
        "source_group": "Reference ID (negative value)",
        "source_entry": "N/A",
        "condition_targets": {0: "Depends on reference usage"}
    },
    1: {
        "name": "CONDITION_SOURCE_TYPE_CREATURE_LOOT_TEMPLATE",
        "description": "Condition for creature loot drops",
        "source_group": "creature_loot_template.Entry",
        "source_entry": "Item ID from loot_template.Item",
        "condition_targets": {0: "Player looting"}
    },
    2: {
        "name": "CONDITION_SOURCE_TYPE_DISENCHANT_LOOT_TEMPLATE",
        "description": "Condition for disenchant results",
        "source_group": "disenchant_loot_template.Entry",
        "source_entry": "Item ID",
        "condition_targets": {0: "Player disenchanting"}
    },
    3: {
        "name": "CONDITION_SOURCE_TYPE_FISHING_LOOT_TEMPLATE",
        "description": "Condition for fishing loot",
        "source_group": "fishing_loot_template.Entry (zone ID)",
        "source_entry": "Item ID",
        "condition_targets": {0: "Player fishing"}
    },
    4: {
        "name": "CONDITION_SOURCE_TYPE_GAMEOBJECT_LOOT_TEMPLATE",
        "description": "Condition for gameobject loot (chests, etc.)",
        "source_group": "gameobject_loot_template.Entry",
        "source_entry": "Item ID",
        "condition_targets": {0: "Player looting"}
    },
    5: {
        "name": "CONDITION_SOURCE_TYPE_ITEM_LOOT_TEMPLATE",
        "description": "Condition for item container loot (bags, lockboxes)",
        "source_group": "item_loot_template.Entry",
        "source_entry": "Item ID",
        "condition_targets": {0: "Player opening"}
    },
    6: {
        "name": "CONDITION_SOURCE_TYPE_MAIL_LOOT_TEMPLATE",
        "description": "Condition for mail attachment loot",
        "source_group": "mail_loot_template.Entry",
        "source_entry": "Item ID",
        "condition_targets": {0: "Player receiving mail"}
    },
    7: {
        "name": "CONDITION_SOURCE_TYPE_MILLING_LOOT_TEMPLATE",
        "description": "Condition for milling results (Inscription)",
        "source_group": "milling_loot_template.Entry",
        "source_entry": "Item ID",
        "condition_targets": {0: "Player milling"}
    },
    8: {
        "name": "CONDITION_SOURCE_TYPE_PICKPOCKETING_LOOT_TEMPLATE",
        "description": "Condition for pickpocket loot",
        "source_group": "pickpocketing_loot_template.Entry",
        "source_entry": "Item ID",
        "condition_targets": {0: "Player pickpocketing"}
    },
    9: {
        "name": "CONDITION_SOURCE_TYPE_PROSPECTING_LOOT_TEMPLATE",
        "description": "Condition for prospecting results (Jewelcrafting)",
        "source_group": "prospecting_loot_template.Entry",
        "source_entry": "Item ID",
        "condition_targets": {0: "Player prospecting"}
    },
    10: {
        "name": "CONDITION_SOURCE_TYPE_REFERENCE_LOOT_TEMPLATE",
        "description": "Condition for reference loot template",
        "source_group": "reference_loot_template.Entry",
        "source_entry": "Item ID",
        "condition_targets": {0: "Player looting"}
    },
    11: {
        "name": "CONDITION_SOURCE_TYPE_SKINNING_LOOT_TEMPLATE",
        "description": "Condition for skinning loot",
        "source_group": "skinning_loot_template.Entry",
        "source_entry": "Item ID",
        "condition_targets": {0: "Player skinning"}
    },
    12: {
        "name": "CONDITION_SOURCE_TYPE_SPELL_LOOT_TEMPLATE",
        "description": "Condition for spell-created loot",
        "source_group": "spell_loot_template.Entry",
        "source_entry": "Item ID",
        "condition_targets": {0: "Player casting"}
    },
    13: {
        "name": "CONDITION_SOURCE_TYPE_SPELL_IMPLICIT_TARGET",
        "description": "Filter for spell implicit targets (area/nearby/cone targets)",
        "source_group": "Effect mask (1=EFFECT_0, 2=EFFECT_1, 4=EFFECT_2)",
        "source_entry": "Spell ID",
        "condition_targets": {
            0: "Potential spell target",
            1: "Spell caster"
        },
        "notes": "Use for filtering area targets. For explicit targets, use source type 17."
    },
    14: {
        "name": "CONDITION_SOURCE_TYPE_GOSSIP_MENU",
        "description": "Condition for showing gossip menu text",
        "source_group": "gossip_menu.MenuID",
        "source_entry": "gossip_menu.TextID (npc_text.ID)",
        "condition_targets": {
            0: "Player viewing gossip",
            1: "WorldObject providing gossip (NPC/GO)"
        }
    },
    15: {
        "name": "CONDITION_SOURCE_TYPE_GOSSIP_MENU_OPTION",
        "description": "Condition for showing gossip menu options",
        "source_group": "gossip_menu_option.MenuID",
        "source_entry": "gossip_menu_option.OptionID",
        "condition_targets": {
            0: "Player viewing gossip",
            1: "WorldObject providing gossip (NPC/GO)"
        }
    },
    16: {
        "name": "CONDITION_SOURCE_TYPE_CREATURE_TEMPLATE_VEHICLE",
        "description": "Condition for vehicle usage",
        "source_group": "Always 0",
        "source_entry": "creature_template.entry (vehicle)",
        "condition_targets": {
            0: "Player riding vehicle",
            1: "Vehicle creature"
        }
    },
    17: {
        "name": "CONDITION_SOURCE_TYPE_SPELL",
        "description": "Condition for spell casting (caster/explicit target requirements)",
        "source_group": "Always 0",
        "source_entry": "Spell ID",
        "condition_targets": {
            0: "Spell caster",
            1: "Explicit target (player-selected target)"
        },
        "notes": "Use for cast requirements. For area targets, use source type 13."
    },
    18: {
        "name": "CONDITION_SOURCE_TYPE_SPELL_CLICK_EVENT",
        "description": "Condition for npc_spellclick_spells",
        "source_group": "npc_spellclick_spells.npc_entry",
        "source_entry": "npc_spellclick_spells.spell_id",
        "condition_targets": {
            0: "Player clicking",
            1: "Spellclick target (clickee)"
        }
    },
    19: {
        "name": "CONDITION_SOURCE_TYPE_QUEST_AVAILABLE",
        "description": "Condition for quest to be available/shown",
        "source_group": "Always 0",
        "source_entry": "Quest ID",
        "condition_targets": {0: "Player"}
    },
    20: {
        "name": "CONDITION_SOURCE_TYPE_UNUSED_20",
        "description": "Unused",
        "source_group": "N/A",
        "source_entry": "N/A",
        "condition_targets": {}
    },
    21: {
        "name": "CONDITION_SOURCE_TYPE_VEHICLE_SPELL",
        "description": "Show/hide spells in vehicle spell bar",
        "source_group": "creature_template.entry (vehicle)",
        "source_entry": "Spell ID",
        "condition_targets": {
            0: "Player in vehicle",
            1: "Vehicle creature"
        }
    },
    22: {
        "name": "CONDITION_SOURCE_TYPE_SMART_EVENT",
        "description": "Condition for SmartAI script execution",
        "source_group": "smart_scripts.id + 1",
        "source_entry": "smart_scripts.entryorguid",
        "source_id": "smart_scripts.source_type",
        "condition_targets": {
            0: "Invoker (usually player)",
            1: "Object (creature/gameobject running the script)"
        }
    },
    23: {
        "name": "CONDITION_SOURCE_TYPE_NPC_VENDOR",
        "description": "Condition for vendor item availability",
        "source_group": "npc_vendor.entry (creature entry)",
        "source_entry": "npc_vendor.item (item entry)",
        "condition_targets": {0: "Player shopping"}
    },
    24: {
        "name": "CONDITION_SOURCE_TYPE_SPELL_PROC",
        "description": "Condition for spell proc triggering",
        "source_group": "Always 0",
        "source_entry": "Spell ID of aura triggering the proc",
        "condition_targets": {
            0: "Actor (aura holder)",
            1: "ActionTarget"
        }
    },
    28: {
        "name": "CONDITION_SOURCE_TYPE_PLAYER_LOOT_TEMPLATE",
        "description": "Condition for player loot (PvP, etc.)",
        "source_group": "player_loot_template.entry",
        "source_entry": "Always 0",
        "condition_targets": {0: "Player"}
    },
    29: {
        "name": "CONDITION_SOURCE_TYPE_CREATURE_VISIBILITY",
        "description": "Condition for creature visibility to players",
        "source_group": "Always 0",
        "source_entry": "creature_template.entry",
        "condition_targets": {
            0: "Player",
            1: "Creature"
        }
    }
}

# Condition Type definitions
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


def register_condition_tools(mcp):
    """Register condition-related tools with the MCP server."""

    @mcp.tool()
    def get_conditions(
        source_type: int,
        source_entry: int,
        source_group: Optional[int] = None,
        source_id: Optional[int] = None
    ) -> str:
        """
        Get conditions for a specific source.

        Args:
            source_type: The condition source type (see explain_condition for list):
                - 1-12: Loot templates (creature, gameobject, fishing, etc.)
                - 13: Spell implicit targets
                - 14: Gossip menu text
                - 15: Gossip menu options
                - 17: Spell cast requirements
                - 19: Quest availability
                - 22: SmartAI script conditions
                - 23: NPC vendor items
            source_entry: The entry ID (meaning depends on source_type):
                - For loot: Item ID
                - For gossip_menu: TextID
                - For gossip_menu_option: OptionID
                - For spells: Spell ID
                - For quests: Quest ID
                - For SmartAI: entryorguid
                - For vendor: Item entry
            source_group: Optional. Additional grouping (meaning depends on source_type):
                - For loot: Loot table entry
                - For gossip: MenuID
                - For SmartAI: script id + 1
                - For vendor: NPC entry
            source_id: Optional. For SmartAI conditions, this is the source_type (0=creature, 1=gameobject, etc.)

        Returns:
            List of conditions with human-readable explanations
        """
        try:
            # Build query
            query = "SELECT * FROM conditions WHERE SourceTypeOrReferenceId = %s AND SourceEntry = %s"
            params = [source_type, source_entry]

            if source_group is not None:
                query += " AND SourceGroup = %s"
                params.append(source_group)

            if source_id is not None:
                query += " AND SourceId = %s"
                params.append(source_id)

            query += " ORDER BY ElseGroup, ConditionTypeOrReference"

            results = execute_query(query, "world", tuple(params))

            if not results:
                return json.dumps({
                    "message": f"No conditions found for source_type={source_type}, source_entry={source_entry}",
                    "source_type_info": SOURCE_TYPES.get(source_type, {"name": "UNKNOWN"})
                }, indent=2)

            # Enhance results with explanations
            enhanced = []
            for row in results:
                cond_type = row.get("ConditionTypeOrReference", 0)
                cond_info = CONDITION_TYPES.get(cond_type, {"name": "UNKNOWN", "description": "Unknown condition type"})

                enhanced_row = dict(row)
                enhanced_row["_condition_type_name"] = cond_info.get("name", "UNKNOWN")
                enhanced_row["_condition_description"] = cond_info.get("description", "")
                enhanced_row["_value1_meaning"] = cond_info.get("value1", "")
                enhanced_row["_value2_meaning"] = cond_info.get("value2", "")
                enhanced_row["_value3_meaning"] = cond_info.get("value3", "")

                # Add inverted explanation if applicable
                if row.get("NegativeCondition"):
                    enhanced_row["_inverted"] = "YES - condition is INVERTED (must NOT match)"

                enhanced.append(enhanced_row)

            source_info = SOURCE_TYPES.get(source_type, {"name": "UNKNOWN"})

            return json.dumps({
                "source_type_info": source_info,
                "conditions": enhanced,
                "logic_explanation": (
                    "Conditions with the SAME ElseGroup are ANDed together. "
                    "Different ElseGroups are ORed. "
                    "The overall condition passes if ANY ElseGroup passes."
                )
            }, indent=2, default=str)

        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    def explain_condition(
        source_type: Optional[int] = None,
        condition_type: Optional[int] = None
    ) -> str:
        """
        Get documentation for condition source types or condition types.

        Args:
            source_type: The source type to explain (where conditions are applied):
                Common values:
                - 1: Creature loot
                - 4: Gameobject loot
                - 14: Gossip menu
                - 15: Gossip menu option
                - 17: Spell requirements
                - 19: Quest availability
                - 22: SmartAI conditions
                - 23: NPC vendor
            condition_type: The condition type to explain (what is being checked):
                Common values:
                - 1: Has aura
                - 2: Has item
                - 5: Reputation rank
                - 6: Team (Alliance/Horde)
                - 8: Quest rewarded
                - 9: Quest taken
                - 15: Class
                - 16: Race
                - 27: Level comparison
                - 47: Quest state

        Returns:
            Documentation for the requested type(s)
        """
        result = {}

        if source_type is not None:
            if source_type in SOURCE_TYPES:
                result["source_type"] = SOURCE_TYPES[source_type]
            else:
                result["source_type"] = {
                    "error": f"Unknown source type {source_type}",
                    "valid_range": "0-24, 28-29"
                }

        if condition_type is not None:
            if condition_type in CONDITION_TYPES:
                result["condition_type"] = CONDITION_TYPES[condition_type]
            else:
                result["condition_type"] = {
                    "error": f"Unknown condition type {condition_type}",
                    "valid_range": "0-49, 101-103"
                }

        if source_type is None and condition_type is None:
            # Return summary of all types
            result["source_types_summary"] = {
                k: {"name": v["name"], "description": v["description"]}
                for k, v in SOURCE_TYPES.items()
            }
            result["common_condition_types"] = {
                k: {"name": v["name"], "description": v["description"]}
                for k, v in CONDITION_TYPES.items()
                if k in [1, 2, 5, 6, 8, 9, 12, 15, 16, 27, 29, 30, 36, 47]
            }
            result["usage_tip"] = (
                "Call with source_type=X or condition_type=X for detailed info. "
                "Example: explain_condition(source_type=15) for gossip menu option details."
            )

        return json.dumps(result, indent=2)

    @mcp.tool()
    def diagnose_conditions(
        source_type: int,
        source_entry: int,
        source_group: Optional[int] = None
    ) -> str:
        """
        Diagnose conditions for broken references and common issues.

        Checks for:
        - Invalid item references (CONDITION_ITEM)
        - Invalid quest references (CONDITION_QUESTREWARDED, CONDITION_QUESTTAKEN, etc.)
        - Invalid creature references (CONDITION_NEAR_CREATURE)
        - Invalid gameobject references (CONDITION_NEAR_GAMEOBJECT)
        - Invalid spell references (CONDITION_AURA, CONDITION_SPELL)
        - Logic issues (empty ElseGroups, conflicting conditions)

        Args:
            source_type: The condition source type
            source_entry: The entry ID
            source_group: Optional source group

        Returns:
            Diagnostic report with issues found and the conditions
        """
        try:
            # First get the conditions
            query = "SELECT * FROM conditions WHERE SourceTypeOrReferenceId = %s AND SourceEntry = %s"
            params = [source_type, source_entry]

            if source_group is not None:
                query += " AND SourceGroup = %s"
                params.append(source_group)

            query += " ORDER BY ElseGroup, ConditionTypeOrReference"
            conditions = execute_query(query, "world", tuple(params))

            if not conditions:
                return json.dumps({
                    "message": f"No conditions found for source_type={source_type}, source_entry={source_entry}",
                    "issues": []
                }, indent=2)

            issues = []
            warnings = []

            for cond in conditions:
                cond_type = cond.get("ConditionTypeOrReference", 0)
                val1 = cond.get("ConditionValue1", 0)
                val2 = cond.get("ConditionValue2", 0)
                val3 = cond.get("ConditionValue3", 0)
                else_group = cond.get("ElseGroup", 0)

                # Check item references
                if cond_type == 2:  # CONDITION_ITEM
                    item = execute_query(
                        "SELECT entry, name FROM item_template WHERE entry = %s",
                        "world", (val1,)
                    )
                    if not item:
                        issues.append({
                            "severity": "ERROR",
                            "else_group": else_group,
                            "condition_type": "CONDITION_ITEM",
                            "problem": f"Item {val1} does not exist in item_template",
                            "fix": "Check item entry or remove condition"
                        })

                # Check quest references
                elif cond_type in [8, 9, 14, 28, 43, 47, 48]:  # Quest-related conditions
                    quest = execute_query(
                        "SELECT ID, LogTitle FROM quest_template WHERE ID = %s",
                        "world", (val1,)
                    )
                    if not quest:
                        issues.append({
                            "severity": "ERROR",
                            "else_group": else_group,
                            "condition_type": CONDITION_TYPES.get(cond_type, {}).get("name", f"TYPE_{cond_type}"),
                            "problem": f"Quest {val1} does not exist in quest_template",
                            "fix": "Check quest ID or remove condition"
                        })

                # Check creature references
                elif cond_type == 29:  # CONDITION_NEAR_CREATURE
                    creature = execute_query(
                        "SELECT entry, name FROM creature_template WHERE entry = %s",
                        "world", (val1,)
                    )
                    if not creature:
                        issues.append({
                            "severity": "ERROR",
                            "else_group": else_group,
                            "condition_type": "CONDITION_NEAR_CREATURE",
                            "problem": f"Creature {val1} does not exist in creature_template",
                            "fix": "Check creature entry or remove condition"
                        })

                # Check gameobject references
                elif cond_type == 30:  # CONDITION_NEAR_GAMEOBJECT
                    go = execute_query(
                        "SELECT entry, name FROM gameobject_template WHERE entry = %s",
                        "world", (val1,)
                    )
                    if not go:
                        issues.append({
                            "severity": "ERROR",
                            "else_group": else_group,
                            "condition_type": "CONDITION_NEAR_GAMEOBJECT",
                            "problem": f"Gameobject {val1} does not exist in gameobject_template",
                            "fix": "Check gameobject entry or remove condition"
                        })

                # Check for equipped item references
                elif cond_type == 3:  # CONDITION_ITEM_EQUIPPED
                    item = execute_query(
                        "SELECT entry, name FROM item_template WHERE entry = %s",
                        "world", (val1,)
                    )
                    if not item:
                        issues.append({
                            "severity": "ERROR",
                            "else_group": else_group,
                            "condition_type": "CONDITION_ITEM_EQUIPPED",
                            "problem": f"Item {val1} does not exist in item_template",
                            "fix": "Check item entry or remove condition"
                        })

                # Check achievement references
                elif cond_type in [17, 39]:  # CONDITION_ACHIEVEMENT, CONDITION_REALM_ACHIEVEMENT
                    # Note: We can't easily verify achievement IDs without achievement DBC
                    if val1 == 0:
                        issues.append({
                            "severity": "WARNING",
                            "else_group": else_group,
                            "condition_type": CONDITION_TYPES.get(cond_type, {}).get("name", f"TYPE_{cond_type}"),
                            "problem": f"Achievement ID is 0",
                            "fix": "This is likely an error - achievement ID should be > 0"
                        })

                # Check for suspicious values
                if cond_type == 27:  # CONDITION_LEVEL
                    if val1 > 80 or val1 < 1:
                        warnings.append({
                            "severity": "WARNING",
                            "else_group": else_group,
                            "condition_type": "CONDITION_LEVEL",
                            "problem": f"Level {val1} is outside normal range (1-80)",
                            "note": "This may be intentional for special cases"
                        })

                if cond_type == 5:  # CONDITION_REPUTATION_RANK
                    # Check if faction exists (basic check)
                    if val1 == 0:
                        issues.append({
                            "severity": "ERROR",
                            "else_group": else_group,
                            "condition_type": "CONDITION_REPUTATION_RANK",
                            "problem": "Faction ID is 0",
                            "fix": "Set a valid faction ID from Faction.dbc"
                        })

            # Check for logic issues
            else_groups = set(c.get("ElseGroup", 0) for c in conditions)
            for eg in else_groups:
                eg_conditions = [c for c in conditions if c.get("ElseGroup", 0) == eg]
                if len(eg_conditions) == 0:
                    warnings.append({
                        "severity": "WARNING",
                        "else_group": eg,
                        "problem": "Empty ElseGroup",
                        "note": "This shouldn't happen - may indicate data corruption"
                    })

            # Build report
            report = {
                "source_type": source_type,
                "source_type_name": SOURCE_TYPES.get(source_type, {}).get("name", "UNKNOWN"),
                "source_entry": source_entry,
                "source_group": source_group,
                "total_conditions": len(conditions),
                "else_groups": len(else_groups),
                "errors": [i for i in issues if i.get("severity") == "ERROR"],
                "warnings": [i for i in issues if i.get("severity") == "WARNING"] + warnings,
                "conditions": conditions
            }

            if not issues and not warnings:
                report["status"] = "OK - No issues found"
            elif not [i for i in issues if i.get("severity") == "ERROR"]:
                report["status"] = f"WARNINGS - {len(warnings)} warning(s) found"
            else:
                report["status"] = f"ERRORS - {len([i for i in issues if i.get('severity') == 'ERROR'])} error(s) found"

            return json.dumps(report, indent=2, default=str)

        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    def search_conditions(
        condition_type: Optional[int] = None,
        condition_value1: Optional[int] = None,
        source_type: Optional[int] = None,
        limit: int = 50
    ) -> str:
        """
        Search for conditions by type or value.

        Useful for finding all conditions that reference a specific:
        - Quest (condition_type=8 or 9, condition_value1=quest_id)
        - Item (condition_type=2, condition_value1=item_id)
        - Creature (condition_type=29, condition_value1=creature_entry)
        - Spell/Aura (condition_type=1 or 25, condition_value1=spell_id)

        Args:
            condition_type: Filter by condition type
            condition_value1: Filter by ConditionValue1 (usually the main reference ID)
            source_type: Filter by source type
            limit: Maximum results (default 50)

        Returns:
            Matching conditions with context
        """
        try:
            query_parts = ["SELECT * FROM conditions WHERE 1=1"]
            params = []

            if condition_type is not None:
                query_parts.append("AND ConditionTypeOrReference = %s")
                params.append(condition_type)

            if condition_value1 is not None:
                query_parts.append("AND ConditionValue1 = %s")
                params.append(condition_value1)

            if source_type is not None:
                query_parts.append("AND SourceTypeOrReferenceId = %s")
                params.append(source_type)

            query_parts.append(f"LIMIT {min(limit, 100)}")

            results = execute_query(" ".join(query_parts), "world", tuple(params))

            if not results:
                return json.dumps({"message": "No conditions found matching criteria"})

            # Enhance with type names
            enhanced = []
            for row in results:
                enhanced_row = dict(row)
                st = row.get("SourceTypeOrReferenceId", 0)
                ct = row.get("ConditionTypeOrReference", 0)
                enhanced_row["_source_type_name"] = SOURCE_TYPES.get(st, {}).get("name", "UNKNOWN")
                enhanced_row["_condition_type_name"] = CONDITION_TYPES.get(ct, {}).get("name", "UNKNOWN")
                enhanced.append(enhanced_row)

            return json.dumps({
                "count": len(enhanced),
                "conditions": enhanced
            }, indent=2, default=str)

        except Exception as e:
            return json.dumps({"error": str(e)})
