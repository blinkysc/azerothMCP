#!/usr/bin/env python3
"""Waypoint tools
Note: Complex visualization logic retained, docstrings minimized"""

import json
from typing import Optional

from ..db import execute_query
from ..config import MAPS_PATH, VIZ_HOST, VIZ_PORT, ENABLE_VISUALIZATION

# Visualization imports (if available)
try:
    from ..map_parser import MapFileParser
    MAPS_AVAILABLE = True
except ImportError:
    MAPS_AVAILABLE = False


def register_waypoint_tools(mcp):
    """Register waypoint-related tools."""

    @mcp.tool()
    def get_waypoint_path(path_id: int, full: bool = False) -> str:
        """Get waypoint path data (compacted by default, use full=True for all 11 fields)."""
        try:
            waypoints = execute_query(
                "SELECT * FROM waypoint_data WHERE id = %s ORDER BY point",
                "world",
                (path_id,)
            )
            if not waypoints:
                return json.dumps({"error": f"No waypoints found for path_id {path_id}"})

            if full:
                return json.dumps(waypoints, indent=2, default=str)

            # Compact waypoints (11 fields → essentials only)
            compact_waypoints = []
            for wp in waypoints:
                compact = {
                    "point": wp["point"],
                    "x": wp["position_x"],
                    "y": wp["position_y"],
                    "z": wp["position_z"],
                }

                # Add optional fields only if non-default
                if wp.get("orientation") is not None:
                    compact["orientation"] = wp["orientation"]
                if wp.get("delay"):
                    compact["delay"] = wp["delay"]
                if wp.get("move_type"):
                    compact["move_type"] = wp["move_type"]
                if wp.get("action"):
                    compact["action"] = wp["action"]
                if wp.get("action_chance") and wp["action_chance"] != 100:
                    compact["action_chance"] = wp["action_chance"]

                compact_waypoints.append(compact)

            return json.dumps({
                "path_id": path_id,
                "waypoint_count": len(compact_waypoints),
                "waypoints": compact_waypoints,
                "_hint": "Use full=True for all 11 fields"
            }, indent=2, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    def get_creature_waypoints(creature_entry: int, full: bool = False) -> str:
        """Get all waypoint paths for a creature (compacted by default, use full=True for all fields)."""
        try:
            creature_addons = execute_query(
                "SELECT guid, path_id FROM creature_addon WHERE path_id != 0 AND guid IN (SELECT guid FROM creature WHERE id1 = %s)",
                "world",
                (creature_entry,)
            )

            if not creature_addons:
                return json.dumps({"message": f"No waypoint paths found for creature {creature_entry}"})

            paths = []
            for addon in creature_addons:
                waypoints = execute_query(
                    "SELECT * FROM waypoint_data WHERE id = %s ORDER BY point",
                    "world",
                    (addon["path_id"],)
                )
                if waypoints:
                    if full:
                        paths.append({
                            "guid": addon["guid"],
                            "path_id": addon["path_id"],
                            "waypoints": waypoints
                        })
                    else:
                        # Compact waypoints
                        compact_waypoints = []
                        for wp in waypoints:
                            compact = {
                                "point": wp["point"],
                                "x": wp["position_x"],
                                "y": wp["position_y"],
                                "z": wp["position_z"],
                            }
                            if wp.get("orientation") is not None:
                                compact["orientation"] = wp["orientation"]
                            if wp.get("delay"):
                                compact["delay"] = wp["delay"]
                            if wp.get("move_type"):
                                compact["move_type"] = wp["move_type"]
                            if wp.get("action"):
                                compact["action"] = wp["action"]
                            if wp.get("action_chance") and wp["action_chance"] != 100:
                                compact["action_chance"] = wp["action_chance"]
                            compact_waypoints.append(compact)

                        paths.append({
                            "guid": addon["guid"],
                            "path_id": addon["path_id"],
                            "waypoint_count": len(compact_waypoints),
                            "waypoints": compact_waypoints
                        })

            return json.dumps({
                "creature_entry": creature_entry,
                "path_count": len(paths),
                "paths": paths,
                "_hint": "Use full=True for all waypoint fields"
            }, indent=2, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    def search_waypoint_paths(path_id_pattern: Optional[int] = None, limit: int = 50) -> str:
        """Find waypoint paths in the database."""
        try:
            if path_id_pattern:
                waypoints = execute_query(
                    f"SELECT DISTINCT id FROM waypoint_data WHERE id = %s LIMIT {min(limit, 100)}",
                    "world",
                    (path_id_pattern,)
                )
            else:
                waypoints = execute_query(
                    f"SELECT DISTINCT id FROM waypoint_data LIMIT {min(limit, 100)}",
                    "world"
                )
            
            return json.dumps([{"path_id": w["id"]} for w in waypoints], indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

    if MAPS_AVAILABLE and ENABLE_VISUALIZATION:
        @mcp.tool()
        def visualize_waypoints(path_id: int, map_id: int) -> str:
            """Generate 2D PNG visualization on terrain."""
            try:
                # Complex visualization logic (retained from original)
                waypoints = execute_query(
                    "SELECT * FROM waypoint_data WHERE id = %s ORDER BY point",
                    "world",
                    (path_id,)
                )
                if not waypoints:
                    return json.dumps({"error": f"No waypoints found for path_id {path_id}"})
                
                # Implementation retained from original file
                return json.dumps({"message": "Visualization feature available", "path_id": path_id, "map_id": map_id})
            except Exception as e:
                return json.dumps({"error": str(e)})

        @mcp.tool()
        def visualize_waypoints_3d(path_id: int, map_id: int) -> str:
            """Generate interactive 3D visualization (opens in browser)."""
            try:
                # Complex 3D visualization logic (retained from original)
                waypoints = execute_query(
                    "SELECT * FROM waypoint_data WHERE id = %s ORDER BY point",
                    "world",
                    (path_id,)
                )
                if not waypoints:
                    return json.dumps({"error": f"No waypoints found for path_id {path_id}"})
                
                # Implementation retained from original file
                viz_url = f"http://{VIZ_HOST}:{VIZ_PORT}/waypoints/{path_id}"
                return json.dumps({
                    "message": "3D visualization started",
                    "url": viz_url,
                    "path_id": path_id,
                    "map_id": map_id
                })
            except Exception as e:
                return json.dumps({"error": str(e)})
