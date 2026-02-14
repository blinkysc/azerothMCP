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
Conditions tools for AzerothCore MCP Server
"""

import json
from typing import Optional

from ..db import execute_query


def _load_source_types():
    """Lazy load condition source types on-demand."""
    from ..data.condition_source_types import SOURCE_TYPES
    return SOURCE_TYPES


def _load_condition_types():
    """Lazy load condition types on-demand."""
    from ..data.condition_types import CONDITION_TYPES
    return CONDITION_TYPES


def register_condition_tools(mcp):
    """Register condition-related tools with the MCP server."""

    @mcp.tool()
    def get_conditions(
        source_type: int,
        source_entry: int,
        source_group: Optional[int] = None,
        source_id: Optional[int] = None
    ) -> str:
        """Get conditions for a specific source (loot, gossip, quest, SmartAI, vendor, etc.)."""
        try:
            SOURCE_TYPES = _load_source_types()
            CONDITION_TYPES = _load_condition_types()

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
        """Get documentation for condition source types and condition types."""
        SOURCE_TYPES = _load_source_types()
        CONDITION_TYPES = _load_condition_types()

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
        """Check conditions for broken references and common issues."""
        try:
            SOURCE_TYPES = _load_source_types()
            CONDITION_TYPES = _load_condition_types()

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
                    "message": f"No conditions found for source_type={source_type}, source_entry={source_entry}"
                })

            issues = []

            # Check each condition
            for cond in conditions:
                cond_type = cond.get("ConditionTypeOrReference", 0)
                value1 = cond.get("ConditionValue1", 0)
                value2 = cond.get("ConditionValue2", 0)
                value3 = cond.get("ConditionValue3", 0)

                # CONDITION_ITEM (2)
                if cond_type == 2 and value1 > 0:
                    item_check = execute_query(
                        "SELECT entry, name FROM item_template WHERE entry = %s",
                        "world",
                        (value1,)
                    )
                    if not item_check:
                        issues.append({
                            "severity": "ERROR",
                            "condition_id": f"ElseGroup={cond['ElseGroup']}",
                            "issue": f"CONDITION_ITEM references non-existent item {value1}",
                            "fix_hint": f"Add item {value1} to item_template or correct ConditionValue1"
                        })

                # CONDITION_QUESTREWARDED (8), CONDITION_QUESTTAKEN (9), CONDITION_QUESTSTATE (47)
                if cond_type in [8, 9, 47] and value1 > 0:
                    quest_check = execute_query(
                        "SELECT ID, LogTitle FROM quest_template WHERE ID = %s",
                        "world",
                        (value1,)
                    )
                    if not quest_check:
                        cond_name = {8: "CONDITION_QUESTREWARDED", 9: "CONDITION_QUESTTAKEN", 47: "CONDITION_QUESTSTATE"}.get(cond_type)
                        issues.append({
                            "severity": "ERROR",
                            "condition_id": f"ElseGroup={cond['ElseGroup']}",
                            "issue": f"{cond_name} references non-existent quest {value1}",
                            "fix_hint": f"Add quest {value1} to quest_template or correct ConditionValue1"
                        })

                # CONDITION_AURA (1)
                if cond_type == 1 and value1 > 0:
                    # Note: spell_dbc may not have all spells, just warn
                    issues.append({
                        "severity": "INFO",
                        "condition_id": f"ElseGroup={cond['ElseGroup']}",
                        "issue": f"CONDITION_AURA checks for spell {value1}. Verify spell exists in client DBC files.",
                        "fix_hint": "Use a spell lookup tool to verify spell ID"
                    })

                # CONDITION_NEAR_CREATURE (29)
                if cond_type == 29 and value1 > 0:
                    creature_check = execute_query(
                        "SELECT entry, name FROM creature_template WHERE entry = %s",
                        "world",
                        (value1,)
                    )
                    if not creature_check:
                        issues.append({
                            "severity": "ERROR",
                            "condition_id": f"ElseGroup={cond['ElseGroup']}",
                            "issue": f"CONDITION_NEAR_CREATURE references non-existent creature {value1}",
                            "fix_hint": f"Add creature {value1} to creature_template or correct ConditionValue1"
                        })

                # CONDITION_NEAR_GAMEOBJECT (30)
                if cond_type == 30 and value1 > 0:
                    go_check = execute_query(
                        "SELECT entry, name FROM gameobject_template WHERE entry = %s",
                        "world",
                        (value1,)
                    )
                    if not go_check:
                        issues.append({
                            "severity": "ERROR",
                            "condition_id": f"ElseGroup={cond['ElseGroup']}",
                            "issue": f"CONDITION_NEAR_GAMEOBJECT references non-existent gameobject {value1}",
                            "fix_hint": f"Add gameobject {value1} to gameobject_template or correct ConditionValue1"
                        })

            # Check for logic issues
            else_groups = {}
            for cond in conditions:
                eg = cond.get("ElseGroup", 0)
                if eg not in else_groups:
                    else_groups[eg] = []
                else_groups[eg].append(cond)

            for eg, group_conds in else_groups.items():
                if len(group_conds) == 0:
                    issues.append({
                        "severity": "WARNING",
                        "condition_id": f"ElseGroup={eg}",
                        "issue": f"ElseGroup {eg} is empty",
                        "fix_hint": "Remove empty ElseGroups"
                    })

            # Compact conditions (15 fields → essentials only)
            conditions_compact = []
            for cond in conditions:
                cond_type = cond.get("ConditionTypeOrReference", 0)
                cond_info = CONDITION_TYPES.get(cond_type, {"name": "UNKNOWN"})

                compact = {
                    "ElseGroup": cond.get("ElseGroup"),
                    "ConditionType": cond_type,
                    "ConditionName": cond_info.get("name", "UNKNOWN"),
                    "Value1": cond.get("ConditionValue1"),
                    "Value2": cond.get("ConditionValue2"),
                }

                if cond.get("ConditionValue3"):
                    compact["Value3"] = cond["ConditionValue3"]
                if cond.get("NegativeCondition"):
                    compact["Inverted"] = True
                if cond.get("Comment"):
                    compact["Comment"] = cond["Comment"]

                conditions_compact.append(compact)

            return json.dumps({
                "source_type": source_type,
                "source_entry": source_entry,
                "source_group": source_group,
                "total_conditions": len(conditions),
                "total_issues": len(issues),
                "issues": issues,
                "conditions": conditions_compact,
                "_hint": "Use get_conditions() for full condition details with explanations"
            }, indent=2, default=str)

        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    def search_conditions(
        condition_type: Optional[int] = None,
        condition_value1: Optional[int] = None,
        source_type: Optional[int] = None,
        limit: int = 50
    ) -> str:
        """Search for conditions by type or value."""
        try:
            SOURCE_TYPES = _load_source_types()
            CONDITION_TYPES = _load_condition_types()

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

    @mcp.tool()
    def list_condition_types() -> str:
        """List all available condition types."""
        CONDITION_TYPES = _load_condition_types()
        types = [
            {"id": k, "name": v["name"], "description": v["description"]}
            for k, v in sorted(CONDITION_TYPES.items())
        ]
        return json.dumps(types, indent=2)

    @mcp.tool()
    def list_condition_source_types() -> str:
        """List all available condition source types."""
        SOURCE_TYPES = _load_source_types()
        types = [
            {"id": k, "name": v["name"], "description": v["description"]}
            for k, v in sorted(SOURCE_TYPES.items())
        ]
        return json.dumps(types, indent=2)
