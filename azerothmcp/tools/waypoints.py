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
Waypoint tools for AzerothCore MCP Server.

Provides tools for querying and visualizing creature waypoints and spawn data.
"""

import json
import os
import base64
import socket
import subprocess
from io import BytesIO
from typing import Optional, List, Dict, Any

from ..db import execute_query
from ..config import get_config, ENABLE_VISUALIZATION

# Try to import visualization libraries (optional)
try:
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

try:
    from ..map_parser import MapParser, SIZE_OF_GRIDS, CENTER_GRID_ID
    HAS_MAP_PARSER = True
except ImportError:
    HAS_MAP_PARSER = False

try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False


# Track if we've started the viz server
_viz_server_process = None


def _get_local_ip() -> str:
    """Get the local IP address of this machine."""
    try:
        result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split()[0]
    except Exception:
        pass
    return 'localhost'


def _is_port_in_use(port: int) -> bool:
    """Check if a port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


def _ensure_viz_server(viz_dir: str, port: int) -> bool:
    """
    Ensure the visualization HTTP server is running.

    Returns True if server is available, False otherwise.
    """
    global _viz_server_process

    # Check if port is already in use (server might already be running)
    if _is_port_in_use(port):
        return True

    # Start the server
    try:
        os.makedirs(viz_dir, exist_ok=True)
        _viz_server_process = subprocess.Popen(
            ['python3', '-m', 'http.server', str(port)],
            cwd=viz_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True  # Detach from parent process
        )
        # Give it a moment to start
        import time
        time.sleep(0.5)
        return _is_port_in_use(port)
    except Exception:
        return False


def register_waypoint_tools(mcp):
    """Register waypoint-related tools with the MCP server."""

    @mcp.tool()
    def get_waypoint_path(path_id: int) -> str:
        """
        Get waypoint path data by path ID.

        Args:
            path_id: The waypoint path ID (from waypoint_data.id)

        Returns:
            All waypoints in the path with coordinates, delays, and move types
        """
        try:
            waypoints = execute_query(
                """SELECT id, point, position_x, position_y, position_z,
                          orientation, delay, move_type, action, action_chance
                   FROM waypoint_data
                   WHERE id = %s
                   ORDER BY point""",
                "world",
                (path_id,)
            )

            if not waypoints:
                return json.dumps({"error": f"No waypoints found for path {path_id}"})

            # Get path info
            path_info = {
                "path_id": path_id,
                "total_points": len(waypoints),
                "waypoints": waypoints
            }

            # Calculate total path length
            total_distance = 0.0
            for i in range(1, len(waypoints)):
                dx = waypoints[i]["position_x"] - waypoints[i-1]["position_x"]
                dy = waypoints[i]["position_y"] - waypoints[i-1]["position_y"]
                dz = waypoints[i]["position_z"] - waypoints[i-1]["position_z"]
                total_distance += (dx*dx + dy*dy + dz*dz) ** 0.5

            path_info["total_distance"] = round(total_distance, 2)

            # Get bounding box
            xs = [w["position_x"] for w in waypoints]
            ys = [w["position_y"] for w in waypoints]
            path_info["bounds"] = {
                "min_x": min(xs),
                "max_x": max(xs),
                "min_y": min(ys),
                "max_y": max(ys)
            }

            return json.dumps(path_info, indent=2, default=str)

        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    def get_creature_waypoints(creature_entry: int) -> str:
        """
        Get all waypoint paths associated with a creature entry.

        Checks both creature_addon (for spawned creatures) and
        creature_template_addon (for template-based paths).

        Args:
            creature_entry: The creature template entry ID

        Returns:
            Waypoint paths with creature spawn info
        """
        try:
            result = {
                "creature_entry": creature_entry,
                "paths": []
            }

            # Get creature name
            creature = execute_query(
                "SELECT name FROM creature_template WHERE entry = %s",
                "world",
                (creature_entry,)
            )
            if creature:
                result["creature_name"] = creature[0]["name"]

            # Check creature_template_addon for template-level path
            template_addon = execute_query(
                """SELECT path_id FROM creature_template_addon
                   WHERE entry = %s AND path_id > 0""",
                "world",
                (creature_entry,)
            )

            if template_addon:
                path_id = template_addon[0]["path_id"]
                waypoints = execute_query(
                    """SELECT point, position_x, position_y, position_z,
                              orientation, delay, move_type
                       FROM waypoint_data WHERE id = %s ORDER BY point""",
                    "world",
                    (path_id,)
                )
                result["paths"].append({
                    "source": "creature_template_addon",
                    "path_id": path_id,
                    "waypoints": waypoints
                })

            # Check creature_addon for spawn-specific paths
            spawn_paths = execute_query(
                """SELECT c.guid, c.position_x as spawn_x, c.position_y as spawn_y,
                          c.position_z as spawn_z, c.map, ca.path_id
                   FROM creature c
                   JOIN creature_addon ca ON c.guid = ca.guid
                   WHERE c.id1 = %s AND ca.path_id > 0""",
                "world",
                (creature_entry,)
            )

            for spawn in spawn_paths:
                waypoints = execute_query(
                    """SELECT point, position_x, position_y, position_z,
                              orientation, delay, move_type
                       FROM waypoint_data WHERE id = %s ORDER BY point""",
                    "world",
                    (spawn["path_id"],)
                )
                result["paths"].append({
                    "source": "creature_addon",
                    "guid": spawn["guid"],
                    "spawn_position": {
                        "x": spawn["spawn_x"],
                        "y": spawn["spawn_y"],
                        "z": spawn["spawn_z"],
                        "map": spawn["map"]
                    },
                    "path_id": spawn["path_id"],
                    "waypoints": waypoints
                })

            if not result["paths"]:
                result["message"] = "No waypoint paths found for this creature"

            return json.dumps(result, indent=2, default=str)

        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    def get_creature_spawns(
        creature_entry: int,
        map_id: Optional[int] = None
    ) -> str:
        """
        Get all spawn locations for a creature.

        Args:
            creature_entry: The creature template entry ID
            map_id: Optional - filter by map ID

        Returns:
            List of spawn locations with GUIDs and positions
        """
        try:
            query = """SELECT guid, id1 as entry, map, position_x, position_y, position_z,
                              orientation, spawntimesecs, MovementType
                       FROM creature WHERE id1 = %s"""
            params = [creature_entry]

            if map_id is not None:
                query += " AND map = %s"
                params.append(map_id)

            query += " ORDER BY map, guid"

            spawns = execute_query(query, "world", tuple(params))

            if not spawns:
                return json.dumps({"error": f"No spawns found for creature {creature_entry}"})

            # Get creature name
            creature = execute_query(
                "SELECT name FROM creature_template WHERE entry = %s",
                "world",
                (creature_entry,)
            )

            result = {
                "creature_entry": creature_entry,
                "creature_name": creature[0]["name"] if creature else "Unknown",
                "total_spawns": len(spawns),
                "spawns": spawns
            }

            # Group by map
            by_map = {}
            for spawn in spawns:
                m = spawn["map"]
                if m not in by_map:
                    by_map[m] = []
                by_map[m].append(spawn)

            result["spawns_by_map"] = {k: len(v) for k, v in by_map.items()}

            return json.dumps(result, indent=2, default=str)

        except Exception as e:
            return json.dumps({"error": str(e)})

    # Conditionally register visualization tools
    if ENABLE_VISUALIZATION:
        @mcp.tool()
        def visualize_waypoints(
            path_id: Optional[int] = None,
            creature_entry: Optional[int] = None,
            creature_guid: Optional[int] = None,
            map_id: int = 0,
            show_terrain: bool = True,
            output_file: Optional[str] = None
        ) -> str:
            """
            Generate a PNG visualization of waypoints on terrain.

            Requires matplotlib and numpy to be installed.

            Args:
                path_id: Waypoint path ID to visualize
                creature_entry: OR creature entry (will find all paths)
                creature_guid: OR specific creature GUID
                map_id: Map ID for terrain background (0=Eastern Kingdoms, 1=Kalimdor, 530=Outland, 571=Northrend)
                show_terrain: Whether to show terrain heightmap background
                output_file: Optional file path to save PNG (if not provided, returns base64)

            Returns:
                JSON with either base64 PNG data or file path, plus visualization info
            """
            if not HAS_MATPLOTLIB:
                return json.dumps({
                    "error": "matplotlib not installed. Install with: pip install matplotlib numpy"
                })

            try:
                waypoints = []
                spawn_points = []
                title_parts = []

                # Get waypoints based on input
                if path_id:
                    wp_data = execute_query(
                        """SELECT point, position_x, position_y, position_z
                           FROM waypoint_data WHERE id = %s ORDER BY point""",
                        "world",
                        (path_id,)
                    )
                    if wp_data:
                        waypoints.append({"path_id": path_id, "points": wp_data})
                        title_parts.append(f"Path {path_id}")

                elif creature_entry:
                    # Get all paths for creature
                    # Template addon
                    template_path = execute_query(
                        """SELECT path_id FROM creature_template_addon
                           WHERE entry = %s AND path_id > 0""",
                        "world",
                        (creature_entry,)
                    )
                    if template_path:
                        pid = template_path[0]["path_id"]
                        wp_data = execute_query(
                            """SELECT point, position_x, position_y, position_z
                               FROM waypoint_data WHERE id = %s ORDER BY point""",
                            "world",
                            (pid,)
                        )
                        if wp_data:
                            waypoints.append({"path_id": pid, "points": wp_data})

                    # Spawn-specific paths
                    spawn_paths = execute_query(
                        """SELECT c.guid, ca.path_id, c.position_x, c.position_y, c.position_z
                           FROM creature c
                           JOIN creature_addon ca ON c.guid = ca.guid
                           WHERE c.id1 = %s AND ca.path_id > 0 AND c.map = %s""",
                        "world",
                        (creature_entry, map_id)
                    )
                    for sp in spawn_paths:
                        wp_data = execute_query(
                            """SELECT point, position_x, position_y, position_z
                               FROM waypoint_data WHERE id = %s ORDER BY point""",
                            "world",
                            (sp["path_id"],)
                        )
                        if wp_data:
                            waypoints.append({"path_id": sp["path_id"], "guid": sp["guid"], "points": wp_data})
                        spawn_points.append((sp["position_x"], sp["position_y"]))

                    # Get creature name
                    creature = execute_query(
                        "SELECT name FROM creature_template WHERE entry = %s",
                        "world",
                        (creature_entry,)
                    )
                    name = creature[0]["name"] if creature else f"Entry {creature_entry}"
                    title_parts.append(name)

                    # Get all spawns for this creature on this map (for display)
                    all_spawns = execute_query(
                        """SELECT position_x, position_y FROM creature
                           WHERE id1 = %s AND map = %s""",
                        "world",
                        (creature_entry, map_id)
                    )
                    for s in all_spawns:
                        if (s["position_x"], s["position_y"]) not in spawn_points:
                            spawn_points.append((s["position_x"], s["position_y"]))

                elif creature_guid:
                    # Get specific GUID's path
                    guid_info = execute_query(
                        """SELECT c.id1 as entry, c.map, c.position_x, c.position_y, c.position_z, ca.path_id
                           FROM creature c
                           LEFT JOIN creature_addon ca ON c.guid = ca.guid
                           WHERE c.guid = %s""",
                        "world",
                        (creature_guid,)
                    )
                    if guid_info:
                        gi = guid_info[0]
                        spawn_points.append((gi["position_x"], gi["position_y"]))
                        map_id = gi["map"]

                        if gi.get("path_id"):
                            wp_data = execute_query(
                                """SELECT point, position_x, position_y, position_z
                                   FROM waypoint_data WHERE id = %s ORDER BY point""",
                                "world",
                                (gi["path_id"],)
                            )
                            if wp_data:
                                waypoints.append({"path_id": gi["path_id"], "points": wp_data})

                        title_parts.append(f"GUID {creature_guid}")

                if not waypoints and not spawn_points:
                    return json.dumps({"error": "No waypoints or spawns found for the given parameters"})

                # Calculate bounds
                all_x = []
                all_y = []
                for wp in waypoints:
                    for p in wp["points"]:
                        all_x.append(p["position_x"])
                        all_y.append(p["position_y"])
                for sp in spawn_points:
                    all_x.append(sp[0])
                    all_y.append(sp[1])

                if not all_x:
                    return json.dumps({"error": "No coordinate data found"})

                min_x, max_x = min(all_x), max(all_x)
                min_y, max_y = min(all_y), max(all_y)

                # Add padding
                padding = max(50, (max_x - min_x) * 0.1, (max_y - min_y) * 0.1)
                min_x -= padding
                max_x += padding
                min_y -= padding
                max_y += padding

                # Create figure
                fig, ax = plt.subplots(1, 1, figsize=(12, 10))

                # Load terrain if requested and available
                terrain_loaded = False
                if show_terrain and HAS_MAP_PARSER:
                    config = get_config()
                    maps_path = config.get("MAPS_PATH", "/home/arthas/azerothcore/data/maps")

                    if os.path.exists(maps_path):
                        try:
                            parser = MapParser(maps_path)
                            tiles = parser.load_tiles_for_area(map_id, min_x, min_y, max_x, max_y)

                            if tiles:
                                # Combine heightmaps
                                for tile in tiles:
                                    if tile.height_data and tile.height_data.has_height:
                                        # v9 array: row 0 = world_x_max, col 0 = world_y_max
                                        # imshow extent = [left, right, bottom, top]
                                        # With origin='upper': row 0 at top, last row at bottom
                                        extent = [
                                            tile.world_y_max, tile.world_y_min,  # left=y_max, right=y_min (inverted)
                                            tile.world_x_min, tile.world_x_max   # bottom=x_min, top=x_max
                                        ]
                                        ax.imshow(
                                            tile.height_data.v9,
                                            extent=extent,
                                            cmap='terrain',
                                            alpha=0.6,
                                            origin='upper'
                                        )
                                        terrain_loaded = True
                        except Exception as e:
                            # Terrain loading failed, continue without it
                            pass

                # Plot waypoint paths
                colors = plt.cm.tab10.colors
                for i, wp in enumerate(waypoints):
                    color = colors[i % len(colors)]
                    points = wp["points"]

                    xs = [p["position_x"] for p in points]
                    ys = [p["position_y"] for p in points]

                    # Plot line
                    ax.plot(ys, xs, '-', color=color, linewidth=2, alpha=0.8,
                           label=f"Path {wp['path_id']}")

                    # Plot points with numbers
                    ax.scatter(ys, xs, c=[color], s=50, zorder=5, edgecolors='black', linewidths=0.5)

                    # Add point numbers
                    for j, (x, y) in enumerate(zip(xs, ys)):
                        ax.annotate(str(j), (y, x), fontsize=7, ha='center', va='bottom',
                                   color='black', weight='bold')

                    # Mark start and end
                    if points:
                        ax.scatter([ys[0]], [xs[0]], c='green', s=150, marker='^',
                                  zorder=6, edgecolors='black', linewidths=1, label='Start' if i == 0 else '')
                        ax.scatter([ys[-1]], [xs[-1]], c='red', s=150, marker='s',
                                  zorder=6, edgecolors='black', linewidths=1, label='End' if i == 0 else '')

                # Plot spawn points
                if spawn_points:
                    sp_x = [s[0] for s in spawn_points]
                    sp_y = [s[1] for s in spawn_points]
                    ax.scatter(sp_y, sp_x, c='yellow', s=100, marker='*',
                              zorder=7, edgecolors='black', linewidths=1, label='Spawn')

                # Configure plot
                ax.set_xlabel('Y (World Coordinate)')
                ax.set_ylabel('X (World Coordinate)')
                ax.set_title(' - '.join(title_parts) + f' (Map {map_id})')
                ax.legend(loc='upper right')
                ax.grid(True, alpha=0.3)
                ax.set_aspect('equal')

                # Set axis limits
                ax.set_xlim(min_y, max_y)
                ax.set_ylim(min_x, max_x)

                plt.tight_layout()

                # Save or return base64
                if output_file:
                    plt.savefig(output_file, dpi=150, bbox_inches='tight')
                    plt.close(fig)
                    return json.dumps({
                        "success": True,
                        "file": output_file,
                        "bounds": {"min_x": min_x, "max_x": max_x, "min_y": min_y, "max_y": max_y},
                        "waypoint_paths": len(waypoints),
                        "spawn_points": len(spawn_points),
                        "terrain_loaded": terrain_loaded
                    })
                else:
                    buf = BytesIO()
                    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
                    plt.close(fig)
                    buf.seek(0)
                    img_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')

                    return json.dumps({
                        "success": True,
                        "image_base64": img_base64,
                        "bounds": {"min_x": min_x, "max_x": max_x, "min_y": min_y, "max_y": max_y},
                        "waypoint_paths": len(waypoints),
                        "spawn_points": len(spawn_points),
                        "terrain_loaded": terrain_loaded,
                        "note": "Image is base64 encoded PNG. Save to file or view in browser."
                    })

            except Exception as e:
                import traceback
                return json.dumps({"error": str(e), "traceback": traceback.format_exc()})

        @mcp.tool()
        def search_waypoint_paths(
            min_points: int = 3,
            map_id: Optional[int] = None,
            limit: int = 50
        ) -> str:
            """
            Search for waypoint paths in the database.

            Args:
                min_points: Minimum number of waypoints in path (default 3)
                map_id: Optional - only paths for creatures on this map
                limit: Maximum results

            Returns:
                List of waypoint paths with creature info
            """
            try:
                # Simple fast query - just get paths with point counts
                query = """
                    SELECT id as path_id, COUNT(*) as point_count,
                           MIN(position_x) as min_x, MAX(position_x) as max_x,
                           MIN(position_y) as min_y, MAX(position_y) as max_y
                    FROM waypoint_data
                    GROUP BY id
                    HAVING COUNT(*) >= %s
                    ORDER BY point_count DESC
                    LIMIT %s
                """
                paths = execute_query(query, "world", (min_points, limit))

                if not paths:
                    return json.dumps({"total_found": 0, "paths": []})

                # Batch lookup creature info for all paths at once
                path_ids = [p["path_id"] for p in paths]
                path_ids_str = ",".join(str(pid) for pid in path_ids)

                # Get creatures from creature_addon (spawn-specific paths)
                addon_creatures = execute_query(
                    f"""SELECT ca.path_id, c.id1 as entry, ct.name
                        FROM creature_addon ca
                        JOIN creature c ON c.guid = ca.guid
                        JOIN creature_template ct ON ct.entry = c.id1
                        WHERE ca.path_id IN ({path_ids_str})
                        GROUP BY ca.path_id, c.id1""",
                    "world"
                )

                # Get creatures from creature_template_addon (template paths)
                template_creatures = execute_query(
                    f"""SELECT cta.path_id, cta.entry, ct.name
                        FROM creature_template_addon cta
                        JOIN creature_template ct ON ct.entry = cta.entry
                        WHERE cta.path_id IN ({path_ids_str})""",
                    "world"
                )

                # Build lookup dict
                creature_lookup = {}
                for c in (addon_creatures or []):
                    pid = c["path_id"]
                    if pid not in creature_lookup:
                        creature_lookup[pid] = []
                    creature_lookup[pid].append({"entry": c["entry"], "name": c["name"]})

                for c in (template_creatures or []):
                    pid = c["path_id"]
                    if pid not in creature_lookup:
                        creature_lookup[pid] = []
                    if not any(x["entry"] == c["entry"] for x in creature_lookup[pid]):
                        creature_lookup[pid].append({"entry": c["entry"], "name": c["name"]})

                # Enrich paths
                for path in paths:
                    path["creatures"] = creature_lookup.get(path["path_id"], [])[:5]

                # Filter by map_id if specified (post-filter for speed)
                if map_id is not None:
                    # Get path_ids that have creatures on this map
                    map_paths = execute_query(
                        f"""SELECT DISTINCT ca.path_id FROM creature_addon ca
                            JOIN creature c ON c.guid = ca.guid
                            WHERE ca.path_id IN ({path_ids_str}) AND c.map = %s
                            UNION
                            SELECT DISTINCT cta.path_id FROM creature_template_addon cta
                            JOIN creature c ON c.id1 = cta.entry
                            WHERE cta.path_id IN ({path_ids_str}) AND c.map = %s
                            LIMIT %s""",
                        "world",
                        (map_id, map_id, limit)
                    )
                    valid_pids = {p["path_id"] for p in (map_paths or [])}
                    paths = [p for p in paths if p["path_id"] in valid_pids]

                return json.dumps({
                    "total_found": len(paths),
                    "paths": paths
                }, indent=2, default=str)

            except Exception as e:
                return json.dumps({"error": str(e)})

        @mcp.tool()
        def visualize_waypoints_3d(
            path_id: Optional[int] = None,
            creature_entry: Optional[int] = None,
            map_id: int = 0,
            output_file: str = "/tmp/waypoint_viz/waypoints_3d.html"
        ) -> str:
            """
            Generate an interactive 3D visualization of waypoints on terrain.

            Opens in browser - rotate with mouse, scroll to zoom. Read-only view.

            Args:
                path_id: Waypoint path ID to visualize
                creature_entry: OR creature entry (will find all paths)
                map_id: Map ID (0=Eastern Kingdoms, 1=Kalimdor, 530=Outland, 571=Northrend)
                output_file: HTML file path to save (default: /tmp/waypoint_viz/waypoints_3d.html)

            Returns:
                JSON with file path and view URL
            """
            if not HAS_PLOTLY:
                return json.dumps({"error": "plotly not installed. pip install plotly"})

            if not HAS_MAP_PARSER:
                return json.dumps({"error": "map_parser not available"})

            try:
                import numpy as np

                waypoints = []
                title_parts = []

                # Get waypoints based on input
                if path_id:
                    wp_data = execute_query(
                        """SELECT point, position_x, position_y, position_z
                           FROM waypoint_data WHERE id = %s ORDER BY point""",
                        "world",
                        (path_id,)
                    )
                    if wp_data:
                        waypoints.append({"path_id": path_id, "points": wp_data})
                        title_parts.append(f"Path {path_id}")

                elif creature_entry:
                    # Template addon path
                    template_path = execute_query(
                        """SELECT path_id FROM creature_template_addon
                           WHERE entry = %s AND path_id > 0""",
                        "world",
                        (creature_entry,)
                    )
                    if template_path:
                        pid = template_path[0]["path_id"]
                        wp_data = execute_query(
                            """SELECT point, position_x, position_y, position_z
                               FROM waypoint_data WHERE id = %s ORDER BY point""",
                            "world",
                            (pid,)
                        )
                        if wp_data:
                            waypoints.append({"path_id": pid, "points": wp_data})

                    # Spawn-specific paths
                    spawn_paths = execute_query(
                        """SELECT ca.path_id FROM creature_addon ca
                           JOIN creature c ON c.guid = ca.guid
                           WHERE c.id1 = %s AND ca.path_id > 0 AND c.map = %s
                           GROUP BY ca.path_id""",
                        "world",
                        (creature_entry, map_id)
                    )
                    for sp in (spawn_paths or []):
                        if not any(w["path_id"] == sp["path_id"] for w in waypoints):
                            wp_data = execute_query(
                                """SELECT point, position_x, position_y, position_z
                                   FROM waypoint_data WHERE id = %s ORDER BY point""",
                                "world",
                                (sp["path_id"],)
                            )
                            if wp_data:
                                waypoints.append({"path_id": sp["path_id"], "points": wp_data})

                    # Get creature name
                    creature = execute_query(
                        "SELECT name FROM creature_template WHERE entry = %s",
                        "world",
                        (creature_entry,)
                    )
                    name = creature[0]["name"] if creature else f"Entry {creature_entry}"
                    title_parts.append(name)

                if not waypoints:
                    return json.dumps({"error": "No waypoints found"})

                # Calculate bounds from waypoints
                all_x, all_y, all_z = [], [], []
                for wp in waypoints:
                    for p in wp["points"]:
                        all_x.append(p["position_x"])
                        all_y.append(p["position_y"])
                        all_z.append(p["position_z"])

                min_x, max_x = min(all_x), max(all_x)
                min_y, max_y = min(all_y), max(all_y)

                # Add padding
                padding = max(50, (max_x - min_x) * 0.15, (max_y - min_y) * 0.15)
                min_x -= padding
                max_x += padding
                min_y -= padding
                max_y += padding

                # Load terrain
                config = get_config()
                maps_path = config.get("MAPS_PATH", "/home/arthas/azerothcore/data/maps")
                parser = MapParser(maps_path)
                tiles = parser.load_tiles_for_area(map_id, min_x, min_y, max_x, max_y)

                fig = go.Figure()

                # Add terrain surfaces
                for tile in tiles:
                    if tile.height_data and tile.height_data.has_height:
                        # Get properly oriented coordinate arrays
                        x_coords, y_coords = tile.get_world_coords()

                        # Plotly Surface: z[i][j] corresponds to point (x[j], y[i])
                        fig.add_trace(go.Surface(
                            x=y_coords,  # plotly x-axis = world Y
                            y=x_coords,  # plotly y-axis = world X
                            z=tile.height_data.v9,
                            colorscale=[[0, 'rgb(144, 184, 134)'], [1, 'rgb(144, 184, 134)']],  # Light sage green
                            opacity=0.85,
                            showscale=False,
                            name='Terrain',
                            hovertemplate='X: %{y:.1f}<br>Y: %{x:.1f}<br>Z: %{z:.1f}<extra></extra>'
                        ))

                # Add waypoint paths
                colors = ['red', 'blue', 'green', 'orange', 'purple', 'cyan']
                waypoint_data_for_js = []  # Store data for JavaScript interactivity

                for i, wp in enumerate(waypoints):
                    points = wp["points"]
                    color = colors[i % len(colors)]
                    path_id = wp["path_id"]

                    wp_x = [p["position_x"] for p in points]
                    wp_y = [p["position_y"] for p in points]
                    wp_z = [p["position_z"] + 2 for p in points]  # Raise slightly above terrain
                    wp_z_original = [p["position_z"] for p in points]

                    # Store waypoint data for JS
                    for p in points:
                        waypoint_data_for_js.append({
                            "path_id": path_id,
                            "point": p["point"],
                            "x": p["position_x"],
                            "y": p["position_y"],
                            "z": p["position_z"]
                        })

                    # Path line with clickable points
                    fig.add_trace(go.Scatter3d(
                        x=wp_y, y=wp_x, z=wp_z,
                        mode='lines+markers',
                        line=dict(color=color, width=6),
                        marker=dict(size=14, color=color),
                        name=f"Path {wp['path_id']}",
                        text=[f"Point {p['point']}" for p in points],
                        customdata=[[path_id, p["point"], p["position_x"], p["position_y"], p["position_z"]] for p in points],
                        hovertemplate="<b>Point %{customdata[1]}</b><br>Path: %{customdata[0]}<br>X: %{customdata[2]:.2f}<br>Y: %{customdata[3]:.2f}<br>Z: %{customdata[4]:.2f}<br><i>Click to edit</i><extra></extra>"
                    ))

                    # Start marker
                    fig.add_trace(go.Scatter3d(
                        x=[wp_y[0]], y=[wp_x[0]], z=[wp_z[0] + 3],
                        mode='markers',
                        marker=dict(size=12, color='lime', symbol='diamond'),
                        name='Start',
                        showlegend=(i == 0),
                        hovertemplate="<b>START</b><br>X: %{y:.1f}<br>Y: %{x:.1f}<extra></extra>"
                    ))

                    # End marker
                    fig.add_trace(go.Scatter3d(
                        x=[wp_y[-1]], y=[wp_x[-1]], z=[wp_z[-1] + 3],
                        mode='markers',
                        marker=dict(size=12, color='red', symbol='square'),
                        name='End',
                        showlegend=(i == 0),
                        hovertemplate="<b>END</b><br>X: %{y:.1f}<br>Y: %{x:.1f}<extra></extra>"
                    ))

                # Add landmark labels (nearby named creatures and gameobjects)
                landmarks = []

                # Get nearby creatures (excluding the waypoint creature itself)
                nearby_creatures = execute_query(
                    """SELECT ct.name, MIN(c.position_x) as position_x, MIN(c.position_y) as position_y,
                              MIN(c.position_z) as position_z, ct.entry
                       FROM creature c
                       JOIN creature_template ct ON c.id1 = ct.entry
                       WHERE c.map = %s
                       AND c.position_x BETWEEN %s AND %s
                       AND c.position_y BETWEEN %s AND %s
                       AND ct.name NOT LIKE '%%Trigger%%'
                       AND ct.name NOT LIKE '%%Invisible%%'
                       AND ct.name NOT LIKE '%%Bunny%%'
                       AND ct.flags_extra & 128 = 0
                       GROUP BY ct.entry, ct.name
                       ORDER BY RAND()
                       LIMIT 15""",
                    "world",
                    (map_id, min_x, max_x, min_y, max_y)
                )
                for c in (nearby_creatures or []):
                    if creature_entry and c["entry"] == creature_entry:
                        continue  # Skip the waypoint creature itself
                    landmarks.append({
                        "name": c["name"],
                        "x": c["position_x"],
                        "y": c["position_y"],
                        "z": c["position_z"] + 5,
                        "type": "creature"
                    })

                # Get nearby gameobjects
                nearby_gos = execute_query(
                    """SELECT gt.name, MIN(g.position_x) as position_x, MIN(g.position_y) as position_y,
                              MIN(g.position_z) as position_z
                       FROM gameobject g
                       JOIN gameobject_template gt ON g.id = gt.entry
                       WHERE g.map = %s
                       AND g.position_x BETWEEN %s AND %s
                       AND g.position_y BETWEEN %s AND %s
                       AND gt.name NOT LIKE '%%Trigger%%'
                       AND gt.name NOT LIKE '%%Aura%%'
                       AND gt.type IN (3, 5, 6, 8, 10)
                       GROUP BY gt.entry, gt.name
                       ORDER BY RAND()
                       LIMIT 8""",
                    "world",
                    (map_id, min_x, max_x, min_y, max_y)
                )
                for g in (nearby_gos or []):
                    landmarks.append({
                        "name": g["name"],
                        "x": g["position_x"],
                        "y": g["position_y"],
                        "z": g["position_z"] + 5,
                        "type": "gameobject"
                    })

                # Add landmark markers with text - separate traces for legend
                creature_landmarks = [lm for lm in landmarks if lm["type"] == "creature"]
                go_landmarks = [lm for lm in landmarks if lm["type"] == "gameobject"]

                if creature_landmarks:
                    fig.add_trace(go.Scatter3d(
                        x=[lm["y"] for lm in creature_landmarks],
                        y=[lm["x"] for lm in creature_landmarks],
                        z=[lm["z"] for lm in creature_landmarks],
                        mode='markers+text',
                        marker=dict(size=8, color='orange', symbol='diamond'),
                        text=[lm["name"] for lm in creature_landmarks],
                        textposition='top center',
                        textfont=dict(size=12, color='white', family='Arial Black'),
                        name='NPCs',
                        hovertemplate="<b style='font-size:18px'>%{text}</b><br><br>Type: NPC<br>X: %{y:.1f}<br>Y: %{x:.1f}<br>Z: %{z:.1f}<extra></extra>"
                    ))

                if go_landmarks:
                    fig.add_trace(go.Scatter3d(
                        x=[lm["y"] for lm in go_landmarks],
                        y=[lm["x"] for lm in go_landmarks],
                        z=[lm["z"] for lm in go_landmarks],
                        mode='markers+text',
                        marker=dict(size=8, color='cyan', symbol='square'),
                        text=[lm["name"] for lm in go_landmarks],
                        textposition='top center',
                        textfont=dict(size=12, color='white', family='Arial Black'),
                        name='Objects',
                        hovertemplate="<b style='font-size:18px'>%{text}</b><br><br>Type: GameObject<br>X: %{y:.1f}<br>Y: %{x:.1f}<br>Z: %{z:.1f}<extra></extra>"
                    ))

                # Layout
                title = ' - '.join(title_parts) if title_parts else 'Waypoints'
                fig.update_layout(
                    title=dict(text=f"{title} (Map {map_id})", font=dict(size=20)),
                    scene=dict(
                        xaxis_title='Y',
                        yaxis_title='X',
                        zaxis_title='Z (Height)',
                        aspectmode='data',
                        camera=dict(
                            eye=dict(x=1.5, y=1.5, z=1.2)
                        )
                    ),
                    hoverdistance=20,  # Increase click/hover detection radius
                    margin=dict(l=0, r=0, t=40, b=0),
                    legend=dict(
                        x=0.02, y=0.98,
                        bgcolor='rgba(0,0,0,0.7)',
                        bordercolor='white',
                        borderwidth=1,
                        font=dict(size=14, color='white'),
                        itemsizing='constant'
                    ),
                    hoverlabel=dict(
                        bgcolor='rgba(0,0,0,0.8)',
                        font_size=16,
                        font_family='Arial'
                    )
                )

                # Save HTML with interactive editor
                os.makedirs(os.path.dirname(output_file), exist_ok=True)

                # Generate base HTML from plotly
                html_content = fig.to_html(include_plotlyjs=True, full_html=True)

                # Add custom CSS and JavaScript for waypoint editing
                editor_html = f'''
    <style>
    #waypoint-editor {{
        position: fixed;
        top: 60px;
        right: 20px;
        background: rgba(0,0,0,0.9);
        border: 2px solid #666;
        border-radius: 8px;
        padding: 15px;
        color: white;
        font-family: Arial, sans-serif;
        z-index: 1000;
        min-width: 300px;
        display: none;
    }}
    #waypoint-editor h3 {{
        margin: 0 0 10px 0;
        color: #ffa500;
    }}
    #waypoint-editor label {{
        display: block;
        margin: 8px 0 4px 0;
        font-size: 12px;
        color: #aaa;
    }}
    #waypoint-editor input {{
        width: 100%;
        padding: 8px;
        border: 1px solid #444;
        border-radius: 4px;
        background: #222;
        color: white;
        font-size: 14px;
        box-sizing: border-box;
    }}
    #waypoint-editor input:focus {{
        border-color: #ffa500;
        outline: none;
    }}
    #waypoint-editor button {{
        margin-top: 12px;
        padding: 10px 15px;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        font-size: 14px;
        margin-right: 8px;
    }}
    #generate-sql {{
        background: #ffa500;
        color: black;
    }}
    #close-editor {{
        background: #444;
        color: white;
    }}
    #sql-output {{
        margin-top: 12px;
        padding: 10px;
        background: #111;
        border: 1px solid #333;
        border-radius: 4px;
        font-family: monospace;
        font-size: 12px;
        white-space: pre-wrap;
        word-break: break-all;
        display: none;
        max-height: 150px;
        overflow-y: auto;
    }}
    #copy-sql {{
        background: #28a745;
        color: white;
        display: none;
    }}
    .coord-row {{
        display: flex;
        gap: 10px;
    }}
    .coord-row > div {{
        flex: 1;
    }}
    </style>

    <div id="waypoint-editor">
        <h3>Edit Waypoint</h3>
        <div>Path ID: <span id="edit-path-id"></span>, Point: <span id="edit-point"></span></div>
        <div id="drag-hint" style="display:none; color:#0f0; font-size:11px; margin:5px 0;"><b>Shift+click</b> on terrain to move here. Arrow keys also work.</div>
        <div class="coord-row">
            <div>
                <label>X (position_x)</label>
                <input type="number" id="edit-x" step="0.1">
            </div>
            <div>
                <label>Y (position_y)</label>
                <input type="number" id="edit-y" step="0.1">
            </div>
            <div>
                <label>Z (position_z)</label>
                <input type="number" id="edit-z" step="0.1">
            </div>
        </div>
        <div>
            <button id="generate-sql">Update Waypoint</button>
            <button id="close-editor">Close</button>
        </div>
        <div id="sql-output"></div>
    </div>

    <div id="changes-panel" style="position:fixed; bottom:20px; right:20px; background:rgba(0,0,0,0.9); border:2px solid #ffa500; border-radius:8px; padding:15px; color:white; font-family:Arial; z-index:1000; max-width:500px;">
        <div style="margin-bottom:10px;">
            <span id="changes-count" style="font-weight:bold;">0 changes</span>
            <button id="export-all" style="margin-left:10px; padding:8px 12px; background:#28a745; color:white; border:none; border-radius:4px; cursor:pointer;">Copy All SQL</button>
            <button id="clear-changes" style="margin-left:5px; padding:8px 12px; background:#dc3545; color:white; border:none; border-radius:4px; cursor:pointer;">Clear</button>
        </div>
        <pre id="all-sql-preview" style="background:#111; border:1px solid #333; border-radius:4px; padding:10px; margin:0; max-height:200px; overflow-y:auto; font-size:11px; white-space:pre-wrap; word-break:break-all; display:none;"></pre>
    </div>

    <script>
    var waypointData = {json.dumps(waypoint_data_for_js)};
    var originalX, originalY, originalZ, currentPathId, currentPoint;
    var dragPointIndex = -1;
    var dragTraceIndex = -1;
    var pendingChanges = [];  // Store all changes

    document.getElementById('close-editor').onclick = function() {{
        document.getElementById('waypoint-editor').style.display = 'none';
    }};

    document.getElementById('generate-sql').onclick = function() {{
        var newX = parseFloat(document.getElementById('edit-x').value);
        var newY = parseFloat(document.getElementById('edit-y').value);
        var newZ = parseFloat(document.getElementById('edit-z').value);

        var updates = [];
        if (Math.abs(newX - originalX) > 0.001) updates.push("position_x = " + newX.toFixed(4));
        if (Math.abs(newY - originalY) > 0.001) updates.push("position_y = " + newY.toFixed(4));
        if (Math.abs(newZ - originalZ) > 0.001) updates.push("position_z = " + newZ.toFixed(4));

        if (updates.length === 0) {{
            document.getElementById('sql-output').textContent = "-- No changes";
            document.getElementById('sql-output').style.display = 'block';
            return;
        }}

        var sql = "UPDATE waypoint_data SET " + updates.join(", ") + " WHERE id = " + currentPathId + " AND point = " + currentPoint + ";";

        // Check if we already have a change for this waypoint, update it
        var existingIdx = pendingChanges.findIndex(function(c) {{ return c.pathId === currentPathId && c.point === currentPoint; }});
        if (existingIdx >= 0) {{
            pendingChanges[existingIdx] = {{ pathId: currentPathId, point: currentPoint, sql: sql }};
        }} else {{
            pendingChanges.push({{ pathId: currentPathId, point: currentPoint, sql: sql }});
        }}

        // Update the original values so further edits are relative to new position
        originalX = newX;
        originalY = newY;
        originalZ = newZ;

        // Update UI
        document.getElementById('sql-output').innerHTML = "<span style='color:#0f0;'>✓ Saved</span>";
        document.getElementById('sql-output').style.display = 'block';
        updateSqlPreview();
    }};

    function updateSqlPreview() {{
        var count = pendingChanges.length;
        document.getElementById('changes-count').textContent = count + " change" + (count !== 1 ? "s" : "");
        var preview = document.getElementById('all-sql-preview');
        if (count > 0) {{
            var allSql = "-- Waypoint changes\\n" + pendingChanges.map(function(c) {{ return c.sql; }}).join("\\n");
            preview.textContent = allSql;
            preview.style.display = 'block';
        }} else {{
            preview.style.display = 'none';
        }}
    }}

    document.getElementById('export-all').onclick = function() {{
        if (pendingChanges.length === 0) return;
        var allSql = "-- Waypoint changes\\n" + pendingChanges.map(function(c) {{ return c.sql; }}).join("\\n");
        navigator.clipboard.writeText(allSql);
        var btn = document.getElementById('export-all');
        btn.textContent = '✓ Copied!';
        setTimeout(function() {{ btn.textContent = 'Copy All SQL'; }}, 1500);
    }};

    document.getElementById('clear-changes').onclick = function() {{
        if (pendingChanges.length > 0 && !confirm('Clear all ' + pendingChanges.length + ' pending changes?')) return;
        pendingChanges = [];
        updateSqlPreview();
    }};

    var plotDiv = document.getElementsByClassName('plotly-graph-div')[0];
    var globalShiftHeld = false;

    // Track shift key globally as fallback
    document.addEventListener('keydown', function(e) {{ if (e.key === 'Shift') globalShiftHeld = true; }});
    document.addEventListener('keyup', function(e) {{ if (e.key === 'Shift') globalShiftHeld = false; }});

    // Click handler - select waypoint OR shift+click to move
    plotDiv.on('plotly_click', function(data) {{
        var point = data.points[0];

        // Get shift state
        var shiftHeld = globalShiftHeld;
        if (data.event && data.event.shiftKey) shiftHeld = true;
        else if (window.event && window.event.shiftKey) shiftHeld = true;

        // Shift+click = move selected waypoint there
        if (shiftHeld && dragPointIndex >= 0) {{

            // Get clicked position (plotly x = world Y, plotly y = world X)
            // For surface plots, use the actual x/y values
            var newWorldY, newWorldX, newZ;

            if (point.x !== undefined && point.y !== undefined) {{
                newWorldY = point.x;
                newWorldX = point.y;
                newZ = point.z;
            }} else {{
                console.log('No x/y on point, cannot move');
                return;
            }}


            // Update the form
            document.getElementById('edit-x').value = newWorldX.toFixed(4);
            document.getElementById('edit-y').value = newWorldY.toFixed(4);
            if (newZ !== undefined) {{
                document.getElementById('edit-z').value = newZ.toFixed(4);
            }}

            // Visually update the waypoint position on the plot
            var traceIdx = dragTraceIndex;
            var pointIdx = dragPointIndex;
            setTimeout(function() {{
                var traceData = plotDiv.data[traceIdx];
                if (traceData && traceData.x && traceData.y && traceData.z) {{
                    traceData.x[pointIdx] = newWorldY;
                    traceData.y[pointIdx] = newWorldX;
                    if (newZ !== undefined) {{
                        traceData.z[pointIdx] = newZ;
                    }}
                    Plotly.redraw(plotDiv);
                }}
            }}, 10);

            // Auto-save the change
            document.getElementById('generate-sql').click();
            return;
        }}

        // Regular click on waypoint = select it
        if (point.customdata && point.customdata.length >= 5) {{
            currentPathId = point.customdata[0];
            currentPoint = point.customdata[1];
            originalX = point.customdata[2];
            originalY = point.customdata[3];
            originalZ = point.customdata[4];
            dragTraceIndex = point.curveNumber;
            dragPointIndex = point.pointNumber;

            document.getElementById('edit-path-id').textContent = currentPathId;
            document.getElementById('edit-point').textContent = currentPoint;
            document.getElementById('edit-x').value = originalX.toFixed(4);
            document.getElementById('edit-y').value = originalY.toFixed(4);
            document.getElementById('edit-z').value = originalZ.toFixed(4);
            document.getElementById('sql-output').style.display = 'none';
            document.getElementById('waypoint-editor').style.display = 'block';
            document.getElementById('drag-hint').style.display = 'block';
        }}
    }});

    // Double-click to deselect
    plotDiv.on('plotly_doubleclick', function() {{
        if (dragPointIndex >= 0) {{
            dragPointIndex = -1;
            dragTraceIndex = -1;
            document.getElementById('drag-hint').style.display = 'none';
            document.getElementById('waypoint-editor').style.display = 'none';
        }}
    }});

    // Arrow keys still work too
    document.addEventListener('keydown', function(e) {{
        if (dragPointIndex < 0 || document.activeElement.tagName === 'INPUT') return;

        var step = e.shiftKey ? 5 : 1;
        var newX = parseFloat(document.getElementById('edit-x').value);
        var newY = parseFloat(document.getElementById('edit-y').value);
        var newZ = parseFloat(document.getElementById('edit-z').value);
        var changed = false;

        switch(e.key) {{
            case 'ArrowUp': newX += step; changed = true; e.preventDefault(); break;
            case 'ArrowDown': newX -= step; changed = true; e.preventDefault(); break;
            case 'ArrowLeft': newY -= step; changed = true; e.preventDefault(); break;
            case 'ArrowRight': newY += step; changed = true; e.preventDefault(); break;
            case 'PageUp': newZ += step; changed = true; e.preventDefault(); break;
            case 'PageDown': newZ -= step; changed = true; e.preventDefault(); break;
            case 'Escape':
                document.getElementById('waypoint-editor').style.display = 'none';
                if (dragTraceIndex >= 0) {{
                    var update = {{'marker.size': Array(plotDiv.data[dragTraceIndex].x.length).fill(8)}};
                    Plotly.restyle(plotDiv, update, [dragTraceIndex]);
                }}
                dragPointIndex = -1;
                break;
        }}

        if (changed) {{
            document.getElementById('edit-x').value = newX.toFixed(4);
            document.getElementById('edit-y').value = newY.toFixed(4);
            document.getElementById('edit-z').value = newZ.toFixed(4);
            document.getElementById('generate-sql').click();
        }}
    }});
    </script>
    '''
                # Insert editor HTML before </body>
                html_content = html_content.replace('</body>', editor_html + '</body>')

                with open(output_file, 'w') as f:
                    f.write(html_content)

                # Ensure visualization server is running
                viz_port = config.get('VIZ_PORT', 8888)
                viz_dir = os.path.dirname(output_file)
                server_started = _ensure_viz_server(viz_dir, viz_port)

                # Get host - use auto-detected IP if VIZ_HOST is localhost
                viz_host = config.get('VIZ_HOST', 'localhost')
                if viz_host == 'localhost':
                    viz_host = _get_local_ip()

                return json.dumps({
                    "success": True,
                    "file": output_file,
                    "view_url": f"http://{viz_host}:{viz_port}/{os.path.basename(output_file)}",
                    "waypoint_paths": len(waypoints),
                    "terrain_tiles": len([t for t in tiles if t.height_data]),
                    "server_running": server_started,
                    "instructions": "Open view_url in browser. Drag to rotate, scroll to zoom."
                }, indent=2)

            except Exception as e:
                import traceback
                return json.dumps({"error": str(e), "traceback": traceback.format_exc()})
