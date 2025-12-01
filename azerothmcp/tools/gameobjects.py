#!/usr/bin/env python3
"""GameObject tools"""

import json

from ..db import execute_query


def register_gameobject_tools(mcp):
    """Register gameobject-related tools."""

    @mcp.tool()
    def get_gameobject_template(entry: int, full: bool = False) -> str:
        """Get gameobject_template data (compacted by default, use full=True for all 36 fields)."""
        try:
            results = execute_query(
                "SELECT * FROM gameobject_template WHERE entry = %s",
                "world",
                (entry,)
            )
            if not results:
                return json.dumps({"error": f"No gameobject found with entry {entry}"})

            go = results[0]

            if full:
                return json.dumps(go, indent=2, default=str)

            # Return essential fields only (36 → ~8 + non-zero Data fields)
            compact = {
                "entry": go["entry"],
                "name": go.get("name"),
                "type": go.get("type"),
                "displayId": go.get("displayId"),
                "size": go.get("size"),
            }

            # Add optional fields only if non-empty
            if go.get("IconName"):
                compact["IconName"] = go["IconName"]
            if go.get("castBarCaption"):
                compact["castBarCaption"] = go["castBarCaption"]

            # Add non-zero Data fields
            data_fields = {}
            for i in range(24):  # Data0-Data23
                field_name = f"Data{i}"
                if go.get(field_name):
                    data_fields[field_name] = go[field_name]
            if data_fields:
                compact["data"] = data_fields

            # Add AIName if present
            if go.get("AIName"):
                compact["AIName"] = go["AIName"]
            if go.get("ScriptName"):
                compact["ScriptName"] = go["ScriptName"]

            compact["_hint"] = "Use full=True for all 36 fields"
            return json.dumps(compact, indent=2, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    def search_gameobjects(name_pattern: str, limit: int = 20) -> str:
        """Search gameobjects by name pattern."""
        try:
            results = execute_query(
                f"SELECT entry, name, type FROM gameobject_template WHERE name LIKE %s LIMIT {min(limit, 100)}",
                "world",
                (f"%{name_pattern}%",)
            )
            return json.dumps(results, indent=2, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})
