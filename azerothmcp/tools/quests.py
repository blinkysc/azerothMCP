#!/usr/bin/env python3
"""Quest tools"""

import json
from typing import Optional

from ..db import execute_query


def register_quest_tools(mcp):
    """Register quest-related tools."""

    @mcp.tool()
    def get_quest_template(entry: int, full: bool = False) -> str:
        """Get quest_template data (compacted by default, use full=True for all 105 fields)."""
        try:
            results = execute_query(
                "SELECT * FROM quest_template WHERE ID = %s",
                "world",
                (entry,)
            )
            if not results:
                return json.dumps({"error": f"No quest found with ID {entry}"})

            quest = results[0]

            if full:
                return json.dumps(quest, indent=2, default=str)

            # Return essential fields only (105 → ~15)
            compact = {
                "ID": quest["ID"],
                "LogTitle": quest.get("LogTitle"),
                "LogDescription": quest.get("LogDescription"),
                "QuestLevel": quest.get("QuestLevel"),
                "MinLevel": quest.get("MinLevel"),
                "QuestType": quest.get("QuestType"),
            }

            # Add optional fields only if non-zero/non-empty
            if quest.get("RequiredRaces"):
                compact["RequiredRaces"] = quest["RequiredRaces"]
            if quest.get("RequiredClasses"):
                compact["RequiredClasses"] = quest["RequiredClasses"]
            if quest.get("PrevQuestId"):
                compact["PrevQuestId"] = quest["PrevQuestId"]
            if quest.get("NextQuestId"):
                compact["NextQuestId"] = quest["NextQuestId"]
            if quest.get("RewardMoney"):
                compact["RewardMoney"] = quest["RewardMoney"]
            if quest.get("RewardXPDifficulty"):
                compact["RewardXPDifficulty"] = quest["RewardXPDifficulty"]

            # Add objectives if present
            objectives = []
            for i in range(1, 5):
                if quest.get(f"RequiredNpcOrGo{i}"):
                    objectives.append({
                        "type": "npc_or_go",
                        "id": quest[f"RequiredNpcOrGo{i}"],
                        "count": quest.get(f"RequiredNpcOrGoCount{i}", 0)
                    })
                if quest.get(f"RequiredItemId{i}"):
                    objectives.append({
                        "type": "item",
                        "id": quest[f"RequiredItemId{i}"],
                        "count": quest.get(f"RequiredItemCount{i}", 0)
                    })
            if objectives:
                compact["objectives"] = objectives

            compact["_hint"] = "Use full=True for all 105 fields"
            return json.dumps(compact, indent=2, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    def search_quests(name_pattern: str, limit: int = 20) -> str:
        """Search quests by name or ID pattern."""
        try:
            if name_pattern.isdigit():
                results = execute_query(
                    "SELECT ID, QuestLevel, MinLevel, LogTitle FROM quest_template WHERE ID = %s",
                    "world",
                    (int(name_pattern),)
                )
            else:
                results = execute_query(
                    f"SELECT ID, QuestLevel, MinLevel, LogTitle FROM quest_template WHERE LogTitle LIKE %s LIMIT {min(limit, 100)}",
                    "world",
                    (f"%{name_pattern}%",)
                )
            return json.dumps(results, indent=2, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    def diagnose_quest(quest_id: int) -> str:
        """Comprehensive quest diagnostics with fix hints."""
        try:
            quest = execute_query(
                "SELECT * FROM quest_template WHERE ID = %s",
                "world",
                (quest_id,)
            )
            
            if not quest:
                return json.dumps({"error": f"Quest {quest_id} not found"})
            
            quest_data = quest[0]
            issues = []
            
            # Check quest givers
            givers = []
            creature_givers = execute_query(
                "SELECT id, quest FROM creature_queststarter WHERE quest = %s",
                "world",
                (quest_id,)
            )
            if creature_givers:
                for giver in creature_givers:
                    creature = execute_query(
                        "SELECT entry, name FROM creature_template WHERE entry = %s",
                        "world",
                        (giver["id"],)
                    )
                    if creature:
                        givers.append({"type": "creature", "entry": giver["id"], "name": creature[0]["name"]})
            
            go_givers = execute_query(
                "SELECT id, quest FROM gameobject_queststarter WHERE quest = %s",
                "world",
                (quest_id,)
            )
            if go_givers:
                for giver in go_givers:
                    go = execute_query(
                        "SELECT entry, name FROM gameobject_template WHERE entry = %s",
                        "world",
                        (giver["id"],)
                    )
                    if go:
                        givers.append({"type": "gameobject", "entry": giver["id"], "name": go[0]["name"]})
            
            if not givers:
                issues.append({
                    "severity": "WARNING",
                    "issue": "No quest givers found",
                    "fix_hint": "Add entries to creature_queststarter or gameobject_queststarter"
                })
            
            # Check quest enders
            enders = []
            creature_enders = execute_query(
                "SELECT id, quest FROM creature_questender WHERE quest = %s",
                "world",
                (quest_id,)
            )
            if creature_enders:
                for ender in creature_enders:
                    creature = execute_query(
                        "SELECT entry, name FROM creature_template WHERE entry = %s",
                        "world",
                        (ender["id"],)
                    )
                    if creature:
                        enders.append({"type": "creature", "entry": ender["id"], "name": creature[0]["name"]})
            
            go_enders = execute_query(
                "SELECT id, quest FROM gameobject_questender WHERE quest = %s",
                "world",
                (quest_id,)
            )
            if go_enders:
                for ender in go_enders:
                    go = execute_query(
                        "SELECT entry, name FROM gameobject_template WHERE entry = %s",
                        "world",
                        (ender["id"],)
                    )
                    if go:
                        enders.append({"type": "gameobject", "entry": ender["id"], "name": go[0]["name"]})
            
            if not enders:
                issues.append({
                    "severity": "WARNING",
                    "issue": "No quest enders found",
                    "fix_hint": "Add entries to creature_questender or gameobject_questender"
                })

            # Compact quest data
            quest_compact = {
                "ID": quest_data["ID"],
                "LogTitle": quest_data.get("LogTitle"),
                "QuestLevel": quest_data.get("QuestLevel"),
                "MinLevel": quest_data.get("MinLevel"),
                "QuestType": quest_data.get("QuestType"),
            }

            return json.dumps({
                "quest": quest_compact,
                "givers": givers,
                "enders": enders,
                "issues": issues,
                "_hint": "Use get_quest_template(quest_id, full=True) for all quest fields"
            }, indent=2, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})
