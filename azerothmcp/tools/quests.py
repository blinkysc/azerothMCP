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
Quest tools for AzerothCore MCP Server.
"""

import json

from ..db import execute_query


def register_quest_tools(mcp):
    """Register quest-related tools with the MCP server."""

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
            - breadcrumb_quests: Quests that lead to this one (breadcrumbs)
            - exclusive_group_quests: Other quests in the same ExclusiveGroup
            - potential_issues: Auto-detected problems (including breadcrumb issues)
            - hints: Guidance for fixing common issues (breadcrumb setup, ExclusiveGroup, etc.)
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

            # 9. Get conditions for this quest
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

            # 11b. Find breadcrumb quests pointing to this quest
            # A breadcrumb is a quest where NextQuestID or RewardNextQuest points to this quest
            breadcrumb_quests = execute_query(
                """SELECT qta.ID, qt.LogTitle, qta.NextQuestID, qta.ExclusiveGroup,
                          qt2.RewardNextQuest, qta.PrevQuestID
                   FROM quest_template_addon qta
                   JOIN quest_template qt ON qta.ID = qt.ID
                   LEFT JOIN quest_template qt2 ON qt2.ID = qta.ID
                   WHERE qta.NextQuestID = %s OR qt2.RewardNextQuest = %s""",
                "world",
                (quest_id, quest_id)
            )
            results["breadcrumb_quests"] = breadcrumb_quests

            # Also check if this quest's PrevQuestID is in the same ExclusiveGroup (breadcrumb pattern)
            prev_quest_is_breadcrumb = False
            if addon and addon[0].get("PrevQuestID") and addon[0].get("ExclusiveGroup"):
                prev_id = addon[0]["PrevQuestID"]
                eg = addon[0]["ExclusiveGroup"]
                if prev_id > 0:  # Positive = required prerequisite
                    # Check if the prev quest is in the same ExclusiveGroup
                    prev_in_eg = execute_query(
                        """SELECT qta.ID, qt.LogTitle, qta.ExclusiveGroup
                           FROM quest_template_addon qta
                           JOIN quest_template qt ON qta.ID = qt.ID
                           WHERE qta.ID = %s AND qta.ExclusiveGroup = %s""",
                        "world",
                        (prev_id, eg)
                    )
                    if prev_in_eg:
                        prev_quest_is_breadcrumb = True
                        # Add this to breadcrumb_quests if not already there
                        if not any(bc["ID"] == prev_id for bc in breadcrumb_quests):
                            breadcrumb_quests.append({
                                "ID": prev_in_eg[0]["ID"],
                                "LogTitle": prev_in_eg[0]["LogTitle"],
                                "ExclusiveGroup": prev_in_eg[0]["ExclusiveGroup"],
                                "NextQuestID": 0,
                                "RewardNextQuest": 0,
                                "PrevQuestID": None,
                                "detected_via": "same_exclusive_group_as_prevquest"
                            })

            # 11c. Find quests in the same ExclusiveGroup
            exclusive_group_quests = []
            if addon and addon[0].get("ExclusiveGroup"):
                eg = addon[0]["ExclusiveGroup"]
                exclusive_group_quests = execute_query(
                    """SELECT qta.ID, qt.LogTitle, qta.ExclusiveGroup
                       FROM quest_template_addon qta
                       JOIN quest_template qt ON qta.ID = qt.ID
                       WHERE qta.ExclusiveGroup = %s AND qta.ID != %s""",
                    "world",
                    (eg, quest_id)
                )
            results["exclusive_group_quests"] = exclusive_group_quests

            # 12. Auto-detect potential issues
            if q.get("MinLevel", 0) > q.get("QuestLevel", 0) > 0:
                issues.append(f"MinLevel ({q['MinLevel']}) > QuestLevel ({q['QuestLevel']})")

            if q.get("AllowableRaces", 0) == 0:
                issues.append("AllowableRaces is 0 - quest may not be available to any race")

            for item in required_items:
                if item["name"] == "UNKNOWN":
                    issues.append(f"Required item {item['entry']} does not exist in item_template!")

            for npc in required_npcs:
                if npc["name"] == "UNKNOWN":
                    issues.append(f"Required {npc['type']} {npc['entry']} does not exist!")

            # 12b. Breadcrumb quest issue detection
            # Check if this quest has breadcrumbs pointing to it that aren't in an ExclusiveGroup
            if breadcrumb_quests:
                current_eg = addon[0].get("ExclusiveGroup") if addon else None
                for bc in breadcrumb_quests:
                    bc_eg = bc.get("ExclusiveGroup")
                    # If breadcrumb exists but no ExclusiveGroup set up, this may cause issues
                    if not bc_eg and not current_eg:
                        issues.append(
                            f"BREADCRUMB: Quest {bc['ID']} ('{bc['LogTitle']}') leads to this quest "
                            f"but neither quest has ExclusiveGroup set. "
                            f"Players may be able to accept both quests simultaneously."
                        )
                    # If breadcrumb has ExclusiveGroup but this quest doesn't share it
                    elif bc_eg and current_eg != bc_eg:
                        issues.append(
                            f"BREADCRUMB: Quest {bc['ID']} has ExclusiveGroup={bc_eg} "
                            f"but this quest has ExclusiveGroup={current_eg}. "
                            f"They should share the same ExclusiveGroup for proper breadcrumb behavior."
                        )

            # Check if this quest incorrectly requires a breadcrumb as prerequisite
            if addon and addon[0].get("PrevQuestID"):
                prev_id = addon[0]["PrevQuestID"]
                if prev_id > 0:  # Positive = required prerequisite
                    # Check if that prev quest is actually a breadcrumb TO this quest
                    for bc in breadcrumb_quests:
                        if bc["ID"] == prev_id:
                            issues.append(
                                f"BREADCRUMB BUG: Quest {prev_id} ('{bc['LogTitle']}') is set as a "
                                f"REQUIRED prerequisite (PrevQuestID > 0), but it appears to be a "
                                f"breadcrumb quest leading to this one. Breadcrumbs should be optional. "
                                f"Consider removing the prerequisite requirement."
                            )
                            break

            # Additional check: if prev quest is in the same ExclusiveGroup, it's likely a breadcrumb
            if prev_quest_is_breadcrumb and addon[0].get("PrevQuestID", 0) > 0:
                prev_id = addon[0]["PrevQuestID"]
                issues.append(
                    f"BREADCRUMB PATTERN: Quest {prev_id} is in the same ExclusiveGroup ({addon[0]['ExclusiveGroup']}) "
                    f"but is also set as a REQUIRED prerequisite (PrevQuestID > 0). "
                    f"If {prev_id} is a breadcrumb quest, players won't be able to skip it. "
                    f"Consider setting PrevQuestID to 0 or making it negative (-{prev_id}) if the breadcrumb "
                    f"should disappear after this quest is completed."
                )

            results["potential_issues"] = issues

            # 13. Add hints for common breadcrumb quest fixes
            hints = []

            # If breadcrumb issues detected, provide fix guidance
            if breadcrumb_quests or prev_quest_is_breadcrumb:
                hints.append({
                    "category": "breadcrumb_setup",
                    "description": "Breadcrumb Quest Configuration",
                    "explanation": (
                        "Breadcrumb quests are introductory quests that lead players to another quest. "
                        "They should be OPTIONAL - players can skip them and go directly to the main quest. "
                        "Accepting the main quest should prevent accepting the breadcrumb."
                    ),
                    "solution_pattern": [
                        "1. Set both quests to the same ExclusiveGroup (usually the breadcrumb quest ID)",
                        "2. Clear NextQuestID from the breadcrumb's quest_template_addon (set to 0)",
                        "3. Clear RewardNextQuest from the breadcrumb's quest_template (set to 0)",
                        "4. Ensure PrevQuestID on the main quest is NOT set to the breadcrumb ID (or use negative value for optional)"
                    ],
                    "example_sql": f"""-- Example fix for breadcrumb quest pointing to quest {quest_id}:
-- Replace BREADCRUMB_ID with the actual breadcrumb quest ID

-- Step 1: Clear the chain links from breadcrumb
UPDATE `quest_template` SET `RewardNextQuest` = 0 WHERE (`ID` = BREADCRUMB_ID);
UPDATE `quest_template_addon` SET `NextQuestID` = 0 WHERE (`ID` = BREADCRUMB_ID);

-- Step 2: Put both quests in same ExclusiveGroup (use breadcrumb ID as the group)
UPDATE `quest_template_addon` SET `ExclusiveGroup` = BREADCRUMB_ID WHERE `ID` IN (BREADCRUMB_ID, {quest_id});

-- Step 3: If this quest incorrectly requires the breadcrumb, remove it
-- UPDATE `quest_template_addon` SET `PrevQuestID` = 0 WHERE `ID` = {quest_id};""",
                    "reference": "https://github.com/azerothcore/azerothcore-wotlk/pull/23847"
                })

            # If PrevQuestID is negative, explain what that means
            if addon and addon[0].get("PrevQuestID", 0) < 0:
                hints.append({
                    "category": "negative_prevquest",
                    "description": "Negative PrevQuestID Meaning",
                    "explanation": (
                        f"PrevQuestID = {addon[0]['PrevQuestID']} (negative) means the quest "
                        f"{abs(addon[0]['PrevQuestID'])} must NOT be completed for this quest to be available. "
                        "This is often used when a breadcrumb should disappear once the main quest is done."
                    )
                })

            # ExclusiveGroup explanation
            if addon and addon[0].get("ExclusiveGroup"):
                eg = addon[0]["ExclusiveGroup"]
                eg_count = len(exclusive_group_quests) + 1
                hints.append({
                    "category": "exclusive_group",
                    "description": "ExclusiveGroup Behavior",
                    "explanation": (
                        f"This quest is in ExclusiveGroup {eg} with {eg_count} total quest(s). "
                        "Only ONE quest from an ExclusiveGroup can be active at a time. "
                        "Accepting one will prevent accepting others in the same group. "
                        "Completing one may auto-complete others (depending on flags). "
                        "Commonly used for: breadcrumb+main quest pairs, faction-choice quests, "
                        "or quests with multiple starting NPCs."
                    )
                })

            results["hints"] = hints

            return json.dumps(results, indent=2, default=str)

        except Exception as e:
            return json.dumps({"error": str(e)})
