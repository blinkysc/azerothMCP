#!/usr/bin/env python3
"""Condition Source Types Reference Data"""

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
        "condition_targets": {0: "Player looting"},
        "notes": (
            "IMPORTANT: For items with StartQuest set, conditions are checked FIRST, "
            "but the core then checks if player can start the quest. If the quest has "
            "PrevQuestID set, the item won't drop unless PrevQuestID is REWARDED (not just taken). "
            "To allow drops while a prereq quest is active, set PrevQuestID=0 on the quest "
            "and use loot conditions to control prerequisites instead."
        )
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
        "condition_targets": {0: "Player looting"},
        "notes": (
            "IMPORTANT: For items with StartQuest set, conditions are checked FIRST, "
            "but the core then checks if player can start the quest. If the quest has "
            "PrevQuestID set, the item won't drop unless PrevQuestID is REWARDED (not just taken). "
            "To allow drops while a prereq quest is active, set PrevQuestID=0 on the quest "
            "and use loot conditions to control prerequisites instead."
        )
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
