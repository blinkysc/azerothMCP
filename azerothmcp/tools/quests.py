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

            results["potential_issues"] = issues

            return json.dumps(results, indent=2, default=str)

        except Exception as e:
            return json.dumps({"error": str(e)})
