#!/usr/bin/env python3
"""Item tools"""

import json

from ..db import execute_query


def register_item_tools(mcp):
    """Register item-related tools."""

    @mcp.tool()
    def get_item_template(entry: int, full: bool = False) -> str:
        """Get item_template data (compacted by default, use full=True for all 139 fields)."""
        try:
            results = execute_query(
                "SELECT * FROM item_template WHERE entry = %s",
                "world",
                (entry,)
            )
            if not results:
                return json.dumps({"error": f"No item found with entry {entry}"})

            item = results[0]

            if full:
                return json.dumps(item, indent=2, default=str)

            # Return essential fields only (139 → ~12 + non-zero values)
            compact = {
                "entry": item["entry"],
                "name": item.get("name"),
                "class": item.get("class"),
                "subclass": item.get("subclass"),
                "Quality": item.get("Quality"),
                "displayid": item.get("displayid"),
                "ItemLevel": item.get("ItemLevel"),
                "RequiredLevel": item.get("RequiredLevel"),
                "InventoryType": item.get("InventoryType"),
            }

            # Add optional fields only if non-zero/non-empty
            if item.get("BuyPrice"):
                compact["BuyPrice"] = item["BuyPrice"]
            if item.get("SellPrice"):
                compact["SellPrice"] = item["SellPrice"]
            if item.get("AllowableClass") and item.get("AllowableClass") != -1:
                compact["AllowableClass"] = item["AllowableClass"]
            if item.get("AllowableRace") and item.get("AllowableRace") != -1:
                compact["AllowableRace"] = item["AllowableRace"]
            if item.get("RequiredSkill"):
                compact["RequiredSkill"] = item["RequiredSkill"]
            if item.get("RequiredSkillRank"):
                compact["RequiredSkillRank"] = item["RequiredSkillRank"]

            # Add non-zero stats
            stats = []
            for i in range(1, 11):  # stat_type1-10
                stat_type = item.get(f"stat_type{i}")
                stat_value = item.get(f"stat_value{i}")
                if stat_type and stat_value:
                    stats.append({"type": stat_type, "value": stat_value})
            if stats:
                compact["stats"] = stats

            # Add non-zero spells
            spells = []
            for i in range(1, 6):  # spellid_1-5
                spell_id = item.get(f"spellid_{i}")
                if spell_id:
                    spells.append({
                        "spell": spell_id,
                        "trigger": item.get(f"spelltrigger_{i}"),
                        "charges": item.get(f"spellcharges_{i}")
                    })
            if spells:
                compact["spells"] = spells

            compact["_hint"] = "Use full=True for all 139 fields"
            return json.dumps(compact, indent=2, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    def search_items(name_pattern: str, limit: int = 20) -> str:
        """Search items by name pattern."""
        try:
            results = execute_query(
                f"SELECT entry, name, Quality, ItemLevel FROM item_template WHERE name LIKE %s LIMIT {min(limit, 100)}",
                "world",
                (f"%{name_pattern}%",)
            )
            return json.dumps(results, indent=2, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})
