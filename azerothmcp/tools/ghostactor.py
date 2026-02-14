#!/usr/bin/env python3
"""Ghost Actor System 3D Visualization Tool"""

import json
import random
import math

from ..db import execute_query

CELL_SIZE = 66.0  # yards (same as AzerothCore grid cells)
CELL_HEIGHT = 20.0  # visualization height


def generate_demo_data(grid_size, entities_per_cell, show_messages):
    """Generate simulated Ghost Actor System data for visualization."""
    cells = []
    entities = []
    ghosts = []
    messages = []

    # Generate cell grid
    for x in range(grid_size):
        for y in range(grid_size):
            cell_id = x * grid_size + y
            cells.append({
                "id": cell_id,
                "x": x * CELL_SIZE,
                "y": y * CELL_SIZE,
                "grid_x": x,
                "grid_y": y
            })

            # Generate entities in this cell
            num_entities = random.randint(max(1, entities_per_cell - 2), entities_per_cell + 3)
            for i in range(num_entities):
                entity = {
                    "id": len(entities),
                    "cell_id": cell_id,
                    "type": random.choice(["player", "player", "creature", "creature", "creature"]),
                    "x": x * CELL_SIZE + random.uniform(5, CELL_SIZE - 5),
                    "y": y * CELL_SIZE + random.uniform(5, CELL_SIZE - 5),
                    "z": random.uniform(0, 5)
                }
                entities.append(entity)

                # Generate ghosts in neighbor cells (up to 8 neighbors)
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        if dx == 0 and dy == 0:
                            continue
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < grid_size and 0 <= ny < grid_size:
                            ghosts.append({
                                "entity_id": entity["id"],
                                "entity_type": entity["type"],
                                "home_cell": cell_id,
                                "ghost_cell": nx * grid_size + ny,
                                "x": entity["x"],
                                "y": entity["y"],
                                "z": entity["z"]
                            })

    # Generate cross-cell messages
    if show_messages:
        num_messages = grid_size * grid_size * 2
        for _ in range(num_messages):
            src_cell = random.randint(0, len(cells) - 1)
            src_x = cells[src_cell]["grid_x"]
            src_y = cells[src_cell]["grid_y"]

            # Pick adjacent cell
            neighbors = []
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)]:
                nx, ny = src_x + dx, src_y + dy
                if 0 <= nx < grid_size and 0 <= ny < grid_size:
                    neighbors.append(nx * grid_size + ny)

            if neighbors:
                dst_cell = random.choice(neighbors)
                messages.append({
                    "type": random.choice(["SPELL_CAST", "DAMAGE", "HEALTH_CHANGED", "POSITION_UPDATE"]),
                    "src_cell": src_cell,
                    "dst_cell": dst_cell
                })

    return cells, entities, ghosts, messages


def fetch_real_creature_data(map_id, center_x, center_y, radius):
    """Fetch real creature spawn data from the database."""
    query = """
        SELECT c.guid, c.id1 as entry, ct.name, c.position_x, c.position_y, c.position_z
        FROM creature c
        JOIN creature_template ct ON c.id1 = ct.entry
        WHERE c.map = %s
          AND c.position_x BETWEEN %s AND %s
          AND c.position_y BETWEEN %s AND %s
          AND ct.name NOT LIKE '%%DND%%'
          AND ct.name NOT LIKE '%%Bunny%%'
          AND ct.name NOT LIKE '%%Trigger%%'
          AND ct.name NOT LIKE '%%Invisible%%'
        ORDER BY c.position_x, c.position_y
        LIMIT 200
    """
    params = (
        map_id,
        center_x - radius,
        center_x + radius,
        center_y - radius,
        center_y + radius
    )
    return execute_query(query, "world", params)


def generate_real_data(map_id, center_x, center_y, radius, show_messages):
    """Generate visualization data from real creature spawns with hypothetical players."""

    # Fetch real creatures
    creatures = fetch_real_creature_data(map_id, center_x, center_y, radius)
    if not creatures:
        return [], [], [], [], []  # Added terrain_points

    # Calculate bounds from actual data
    min_x = min(c["position_x"] for c in creatures)
    max_x = max(c["position_x"] for c in creatures)
    min_y = min(c["position_y"] for c in creatures)
    max_y = max(c["position_y"] for c in creatures)

    # Add padding
    min_x -= 10
    min_y -= 10
    max_x += 10
    max_y += 10

    # Calculate grid dimensions
    grid_cols = int(math.ceil((max_x - min_x) / CELL_SIZE))
    grid_rows = int(math.ceil((max_y - min_y) / CELL_SIZE))

    # Cap grid size
    grid_cols = min(grid_cols, 8)
    grid_rows = min(grid_rows, 8)

    # Generate cells
    cells = []
    for gx in range(grid_cols):
        for gy in range(grid_rows):
            cell_id = gx * grid_rows + gy
            cells.append({
                "id": cell_id,
                "x": min_x + gx * CELL_SIZE,
                "y": min_y + gy * CELL_SIZE,
                "grid_x": gx,
                "grid_y": gy,
                "world_x": min_x + gx * CELL_SIZE,
                "world_y": min_y + gy * CELL_SIZE
            })

    def get_cell_id(x, y):
        """Get cell ID for a world position."""
        gx = int((x - min_x) / CELL_SIZE)
        gy = int((y - min_y) / CELL_SIZE)
        gx = max(0, min(gx, grid_cols - 1))
        gy = max(0, min(gy, grid_rows - 1))
        return gx * grid_rows + gy

    entities = []
    ghosts = []

    # Collect terrain points from creature positions
    terrain_points = []

    # Add real creatures
    for c in creatures:
        cell_id = get_cell_id(c["position_x"], c["position_y"])
        entity = {
            "id": len(entities),
            "guid": c["guid"],
            "entry": c["entry"],
            "name": c["name"],
            "cell_id": cell_id,
            "type": "creature",
            "x": c["position_x"],
            "y": c["position_y"],
            "z": c["position_z"]
        }
        entities.append(entity)

        # Add terrain point for this creature
        terrain_points.append({
            "x": c["position_x"],
            "y": c["position_y"],
            "z": c["position_z"]
        })

        # Calculate ghost cells (entities near cell boundaries)
        gx = int((c["position_x"] - min_x) / CELL_SIZE)
        gy = int((c["position_y"] - min_y) / CELL_SIZE)

        # Check if near any cell boundary (within 15 yards = ghost visibility range)
        local_x = (c["position_x"] - min_x) % CELL_SIZE
        local_y = (c["position_y"] - min_y) % CELL_SIZE

        near_left = local_x < 15
        near_right = local_x > CELL_SIZE - 15
        near_bottom = local_y < 15
        near_top = local_y > CELL_SIZE - 15

        # Add ghosts to adjacent cells if near boundary
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue

                should_ghost = False
                if dx == -1 and near_left:
                    should_ghost = True
                if dx == 1 and near_right:
                    should_ghost = True
                if dy == -1 and near_bottom:
                    should_ghost = True
                if dy == 1 and near_top:
                    should_ghost = True
                if dx != 0 and dy != 0:  # Diagonal
                    if (dx == -1 and near_left) or (dx == 1 and near_right):
                        if (dy == -1 and near_bottom) or (dy == 1 and near_top):
                            should_ghost = True

                if should_ghost:
                    nx, ny = gx + dx, gy + dy
                    if 0 <= nx < grid_cols and 0 <= ny < grid_rows:
                        ghost_cell_id = nx * grid_rows + ny
                        ghosts.append({
                            "entity_id": entity["id"],
                            "entity_type": "creature",
                            "name": c["name"],
                            "home_cell": cell_id,
                            "ghost_cell": ghost_cell_id,
                            "x": c["position_x"],
                            "y": c["position_y"],
                            "z": c["position_z"],
                            "is_ghost": True
                        })

    # Add hypothetical players
    # Find a cell with some creatures to place 2 players together
    cell_creature_counts = {}
    for e in entities:
        if e["type"] == "creature":
            cell_creature_counts[e["cell_id"]] = cell_creature_counts.get(e["cell_id"], 0) + 1

    # Pick a populated cell for the 2 players together
    if cell_creature_counts:
        populated_cell_id = max(cell_creature_counts, key=cell_creature_counts.get)
    else:
        populated_cell_id = 0

    populated_cell = next((c for c in cells if c["id"] == populated_cell_id), cells[0])

    # Place players in the center of the populated cell
    player1_x = populated_cell["x"] + CELL_SIZE / 2 - 3
    player1_y = populated_cell["y"] + CELL_SIZE / 2
    player2_x = populated_cell["x"] + CELL_SIZE / 2 + 3
    player2_y = populated_cell["y"] + CELL_SIZE / 2

    # Find average Z in this cell from nearby creatures
    cell_creatures = [e for e in entities if e["cell_id"] == populated_cell_id and e["type"] == "creature"]
    avg_z = sum(e["z"] for e in cell_creatures) / len(cell_creatures) if cell_creatures else 60.0

    # "You" - The main player
    player1 = {
        "id": len(entities),
        "cell_id": populated_cell_id,
        "type": "player",
        "name": "You (The Player)",
        "is_main_player": True,
        "x": player1_x,
        "y": player1_y,
        "z": avg_z
    }
    entities.append(player1)
    terrain_points.append({"x": player1_x, "y": player1_y, "z": avg_z})

    # Party member
    player2 = {
        "id": len(entities),
        "cell_id": populated_cell_id,
        "type": "player",
        "name": "Party Member",
        "x": player2_x,
        "y": player2_y,
        "z": avg_z
    }
    entities.append(player2)
    terrain_points.append({"x": player2_x, "y": player2_y, "z": avg_z})

    # Place 3rd player just outside cell boundary (will create a ghost)
    # Put them 8 yards from cell edge inside next cell
    player3_x = populated_cell["x"] + CELL_SIZE + 8  # Just outside right edge
    player3_y = populated_cell["y"] + CELL_SIZE / 2

    # Find the cell for player3
    player3_cell_id = get_cell_id(player3_x, player3_y)

    player3 = {
        "id": len(entities),
        "cell_id": player3_cell_id,
        "type": "player",
        "name": "Nearby Player",
        "x": player3_x,
        "y": player3_y,
        "z": avg_z
    }
    entities.append(player3)
    terrain_points.append({"x": player3_x, "y": player3_y, "z": avg_z})

    # Player3 is close to boundary - add ghost in adjacent cell
    ghosts.append({
        "entity_id": player3["id"],
        "entity_type": "player",
        "name": "Nearby Player (Ghost)",
        "home_cell": player3_cell_id,
        "ghost_cell": populated_cell_id,
        "x": player3_x,
        "y": player3_y,
        "z": avg_z,
        "is_ghost": True
    })

    # Generate cross-cell messages if enabled
    messages = []
    if show_messages and len(cells) > 1:
        # Player1 casting spell on a creature in adjacent cell (via ghost)
        for e in entities:
            if e["type"] == "creature" and e["cell_id"] != populated_cell_id:
                messages.append({
                    "type": "SPELL_CAST",
                    "src_cell": populated_cell_id,
                    "dst_cell": e["cell_id"]
                })
                break

        # Creature damaging player (cross-cell)
        messages.append({
            "type": "DAMAGE",
            "src_cell": player3_cell_id,
            "dst_cell": populated_cell_id
        })

        # Position updates from ghost
        messages.append({
            "type": "POSITION_UPDATE",
            "src_cell": player3_cell_id,
            "dst_cell": populated_cell_id
        })

    return cells, entities, ghosts, messages, terrain_points


def generate_3d_html(cells, entities, ghosts, messages, title="Ghost Actor System", use_world_coords=False, terrain_points=None):
    """Generate interactive 3D HTML visualization using plotly.js."""

    traces = []

    # Calculate Z normalization from entities
    all_z = [e["z"] for e in entities]
    if all_z:
        min_z = min(all_z) - 2  # Slightly below lowest entity
        max_z = max(all_z)
    else:
        min_z = 0
        max_z = 20

    def norm_z(z):
        return z - min_z + 1  # Place entities slightly above terrain

    terrain_base = 0  # Ground level after normalization

    # Add terrain surface if we have terrain points
    if terrain_points and len(terrain_points) >= 4:
        # Create a grid-based terrain from the points
        xs = [p["x"] for p in terrain_points]
        ys = [p["y"] for p in terrain_points]
        zs = [p["z"] for p in terrain_points]

        terrain_min_x = min(xs) - 10
        terrain_max_x = max(xs) + 10
        terrain_min_y = min(ys) - 10
        terrain_max_y = max(ys) + 10

        # Create a simple gridded terrain (10x10 grid)
        grid_res = 10
        grid_x = []
        grid_y = []
        grid_z = []

        for i in range(grid_res + 1):
            row_x = []
            row_y = []
            row_z = []
            for j in range(grid_res + 1):
                px = terrain_min_x + (terrain_max_x - terrain_min_x) * i / grid_res
                py = terrain_min_y + (terrain_max_y - terrain_min_y) * j / grid_res
                row_x.append(px)
                row_y.append(py)

                # Simple inverse distance weighted interpolation
                total_weight = 0
                weighted_z = 0
                for tp in terrain_points:
                    dist = math.sqrt((tp["x"] - px)**2 + (tp["y"] - py)**2)
                    if dist < 0.1:
                        dist = 0.1
                    weight = 1.0 / (dist * dist)
                    weighted_z += tp["z"] * weight
                    total_weight += weight

                if total_weight > 0:
                    pz = weighted_z / total_weight
                else:
                    pz = sum(zs) / len(zs)

                row_z.append(pz - min_z)  # Normalize to ground level

            grid_x.append(row_x)
            grid_y.append(row_y)
            grid_z.append(row_z)

        # Add terrain surface
        traces.append({
            "type": "surface",
            "x": grid_x,
            "y": grid_y,
            "z": grid_z,
            "colorscale": [[0, "rgb(34, 85, 34)"], [0.5, "rgb(68, 119, 68)"], [1, "rgb(102, 153, 102)"]],
            "opacity": 0.7,
            "showscale": False,
            "name": "Terrain",
            "hoverinfo": "skip"
        })

    # Cell boundaries (wireframe boxes, on top of terrain)
    for cell in cells:
        x0 = cell.get("world_x", cell["x"]) if use_world_coords else cell["x"]
        y0 = cell.get("world_y", cell["y"]) if use_world_coords else cell["y"]
        x1, y1 = x0 + CELL_SIZE, y0 + CELL_SIZE
        z0, z1 = terrain_base, CELL_HEIGHT + 5

        # Create wireframe edges for the cell (just bottom plane)
        edges_x = [x0, x1, x1, x0, x0]
        edges_y = [y0, y0, y1, y1, y0]
        edges_z = [z0, z0, z0, z0, z0]

        traces.append({
            "type": "scatter3d",
            "mode": "lines",
            "x": edges_x,
            "y": edges_y,
            "z": edges_z,
            "line": {"color": "rgba(255, 255, 0, 0.8)", "width": 4},
            "name": f"Cell {cell['id']}",
            "showlegend": False,
            "hoverinfo": "name"
        })

        # Add vertical lines at corners
        for cx, cy in [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]:
            traces.append({
                "type": "scatter3d",
                "mode": "lines",
                "x": [cx, cx],
                "y": [cy, cy],
                "z": [z0, z1],
                "line": {"color": "rgba(255, 255, 0, 0.3)", "width": 1},
                "showlegend": False,
                "hoverinfo": "skip"
            })

        # Add cell label at center, elevated
        traces.append({
            "type": "scatter3d",
            "mode": "text",
            "x": [x0 + CELL_SIZE / 2],
            "y": [y0 + CELL_SIZE / 2],
            "z": [z1 + 3],
            "text": [f"Cell {cell['id']}"],
            "textfont": {"size": 12, "color": "#ffff00"},
            "showlegend": False,
            "hoverinfo": "skip"
        })

    # Entities - Main player (gold star)
    main_player_x, main_player_y, main_player_z, main_player_text = [], [], [], []
    # Other players (blue spheres)
    player_x, player_y, player_z, player_text = [], [], [], []

    for e in entities:
        if e["type"] == "player":
            if e.get("is_main_player"):
                main_player_x.append(e["x"])
                main_player_y.append(e["y"])
                main_player_z.append(norm_z(e["z"]))
                main_player_text.append(f"<b>{e['name']}</b><br>Cell: {e['cell_id']}")
            else:
                player_x.append(e["x"])
                player_y.append(e["y"])
                player_z.append(norm_z(e["z"]))
                name = e.get("name", f"Player #{e['id']}")
                player_text.append(f"{name}<br>Cell: {e['cell_id']}")

    if main_player_x:
        traces.append({
            "type": "scatter3d",
            "mode": "markers",
            "x": main_player_x,
            "y": main_player_y,
            "z": main_player_z,
            "marker": {"size": 14, "color": "gold", "symbol": "diamond", "line": {"color": "black", "width": 2}},
            "name": "You (Main Player)",
            "text": main_player_text,
            "hoverinfo": "text"
        })

    if player_x:
        traces.append({
            "type": "scatter3d",
            "mode": "markers",
            "x": player_x,
            "y": player_y,
            "z": player_z,
            "marker": {"size": 10, "color": "blue", "opacity": 1.0},
            "name": "Other Players",
            "text": player_text,
            "hoverinfo": "text"
        })

    # Entities - Creatures (red spheres)
    creature_x, creature_y, creature_z, creature_text = [], [], [], []
    for e in entities:
        if e["type"] == "creature":
            creature_x.append(e["x"])
            creature_y.append(e["y"])
            creature_z.append(norm_z(e["z"]))
            name = e.get("name", f"Creature #{e['id']}")
            creature_text.append(f"{name}<br>Cell: {e['cell_id']}")

    if creature_x:
        traces.append({
            "type": "scatter3d",
            "mode": "markers",
            "x": creature_x,
            "y": creature_y,
            "z": creature_z,
            "marker": {"size": 6, "color": "red", "opacity": 1.0},
            "name": "Creatures",
            "text": creature_text,
            "hoverinfo": "text"
        })

    # Ghost projections (transparent with rings)
    ghost_player_x, ghost_player_y, ghost_player_z, ghost_player_text = [], [], [], []
    ghost_creature_x, ghost_creature_y, ghost_creature_z, ghost_creature_text = [], [], [], []

    for g in ghosts:
        if g["entity_type"] == "player":
            ghost_player_x.append(g["x"])
            ghost_player_y.append(g["y"])
            ghost_player_z.append(norm_z(g["z"]) + 1)  # Slightly elevated to show as ghost
            name = g.get("name", f"Player #{g['entity_id']}")
            ghost_player_text.append(f"👻 GHOST: {name}<br>Home: Cell {g['home_cell']}<br>Visible in: Cell {g['ghost_cell']}")
        else:
            ghost_creature_x.append(g["x"])
            ghost_creature_y.append(g["y"])
            ghost_creature_z.append(norm_z(g["z"]) + 1)
            name = g.get("name", f"Creature #{g['entity_id']}")
            ghost_creature_text.append(f"👻 GHOST: {name}<br>Home: Cell {g['home_cell']}<br>Visible in: Cell {g['ghost_cell']}")

    if ghost_player_x:
        traces.append({
            "type": "scatter3d",
            "mode": "markers",
            "x": ghost_player_x,
            "y": ghost_player_y,
            "z": ghost_player_z,
            "marker": {"size": 12, "color": "rgba(100, 150, 255, 0.3)", "symbol": "circle",
                       "line": {"color": "cyan", "width": 2}},
            "name": "Player Ghosts 👻",
            "text": ghost_player_text,
            "hoverinfo": "text"
        })

    if ghost_creature_x:
        traces.append({
            "type": "scatter3d",
            "mode": "markers",
            "x": ghost_creature_x,
            "y": ghost_creature_y,
            "z": ghost_creature_z,
            "marker": {"size": 8, "color": "rgba(255, 100, 100, 0.3)", "symbol": "circle",
                       "line": {"color": "orange", "width": 2}},
            "name": "Creature Ghosts 👻",
            "text": ghost_creature_text,
            "hoverinfo": "text"
        })

    # Messages (lines between cell centers)
    msg_colors = {
        "SPELL_CAST": "orange",
        "DAMAGE": "red",
        "HEALTH_CHANGED": "green",
        "POSITION_UPDATE": "cyan"
    }

    for msg in messages:
        src_cell = next((c for c in cells if c["id"] == msg["src_cell"]), None)
        dst_cell = next((c for c in cells if c["id"] == msg["dst_cell"]), None)

        if not src_cell or not dst_cell:
            continue

        src_x = (src_cell.get("world_x", src_cell["x"]) if use_world_coords else src_cell["x"]) + CELL_SIZE / 2
        src_y = (src_cell.get("world_y", src_cell["y"]) if use_world_coords else src_cell["y"]) + CELL_SIZE / 2
        dst_x = (dst_cell.get("world_x", dst_cell["x"]) if use_world_coords else dst_cell["x"]) + CELL_SIZE / 2
        dst_y = (dst_cell.get("world_y", dst_cell["y"]) if use_world_coords else dst_cell["y"]) + CELL_SIZE / 2
        msg_z = CELL_HEIGHT / 2 + random.uniform(-2, 2)

        traces.append({
            "type": "scatter3d",
            "mode": "lines",
            "x": [src_x, dst_x],
            "y": [src_y, dst_y],
            "z": [msg_z, msg_z],
            "line": {"color": msg_colors.get(msg["type"], "yellow"), "width": 3},
            "name": msg["type"],
            "showlegend": False,
            "hoverinfo": "name"
        })

    # Calculate bounds for camera
    all_x = [e["x"] for e in entities] + [c.get("world_x", c["x"]) if use_world_coords else c["x"] for c in cells]
    all_y = [e["y"] for e in entities] + [c.get("world_y", c["y"]) if use_world_coords else c["y"] for c in cells]

    if all_x and all_y:
        min_plot_x = min(all_x) - 10
        max_plot_x = max(all_x) + CELL_SIZE + 10
        min_plot_y = min(all_y) - 10
        max_plot_y = max(all_y) + CELL_SIZE + 10
    else:
        min_plot_x, max_plot_x = -10, 200
        min_plot_y, max_plot_y = -10, 200

    # Count ghosts by type
    num_player_ghosts = sum(1 for g in ghosts if g["entity_type"] == "player")
    num_creature_ghosts = sum(1 for g in ghosts if g["entity_type"] == "creature")
    num_players = sum(1 for e in entities if e["type"] == "player")
    num_creatures = sum(1 for e in entities if e["type"] == "creature")

    html = f'''<!DOCTYPE html>
<html>
<head>
    <title>{title} - 3D Visualization</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #1a1a2e; color: #eee; }}
        h1 {{ color: #00d4ff; }}
        #viz {{ width: 100%; height: 700px; border: 1px solid #333; border-radius: 8px; }}
        .legend {{ display: flex; flex-wrap: wrap; gap: 20px; margin-top: 20px; padding: 15px; background: #16213e; border-radius: 8px; }}
        .legend-item {{ display: flex; align-items: center; gap: 8px; }}
        .legend-dot {{ width: 16px; height: 16px; border-radius: 50%; }}
        .legend-diamond {{ width: 16px; height: 16px; transform: rotate(45deg); }}
        .legend-line {{ width: 30px; height: 3px; }}
        .legend-ghost {{ width: 16px; height: 16px; border-radius: 50%; border: 2px solid; background: transparent; }}
        .stats {{ background: #16213e; padding: 15px; border-radius: 8px; margin-top: 20px; }}
        .stats h3 {{ margin-top: 0; color: #00d4ff; }}
        .explanation {{ background: #0d1b2a; padding: 15px; border-radius: 8px; margin-top: 20px; border-left: 4px solid #00d4ff; }}
    </style>
</head>
<body>
    <h1>{title} - 3D Visualization</h1>
    <div id="viz"></div>

    <div class="legend">
        <div class="legend-item"><div class="legend-diamond" style="background: gold; border: 2px solid black;"></div> <strong>You (Main Player)</strong></div>
        <div class="legend-item"><div class="legend-dot" style="background: blue;"></div> Other Players</div>
        <div class="legend-item"><div class="legend-dot" style="background: red;"></div> Creatures</div>
        <div class="legend-item"><div class="legend-ghost" style="border-color: cyan;"></div> Player Ghost 👻</div>
        <div class="legend-item"><div class="legend-ghost" style="border-color: orange;"></div> Creature Ghost 👻</div>
        <div class="legend-item"><div class="legend-line" style="background: yellow;"></div> Cell Boundary</div>
        <div class="legend-item"><div class="legend-line" style="background: orange;"></div> Cross-cell Messages</div>
    </div>

    <div class="stats">
        <h3>Stats</h3>
        <table>
            <tr><td><strong>Cells:</strong></td><td>{len(cells)} (each 66×66 yards)</td></tr>
            <tr><td><strong>Players:</strong></td><td>{num_players}</td></tr>
            <tr><td><strong>Creatures:</strong></td><td>{num_creatures}</td></tr>
            <tr><td><strong>Player Ghosts:</strong></td><td>{num_player_ghosts} 👻</td></tr>
            <tr><td><strong>Creature Ghosts:</strong></td><td>{num_creature_ghosts} 👻</td></tr>
            <tr><td><strong>Cross-Cell Messages:</strong></td><td>{len(messages)}</td></tr>
        </table>
    </div>

    <div class="explanation">
        <h3>What is the Ghost Actor System?</h3>
        <p>The Ghost Actor System enables entities (players/creatures) to be visible across cell boundaries. When an entity is near a cell edge (within ~15 yards), a <strong>ghost projection</strong> is created in neighboring cells. This allows cross-cell interactions like spells, damage, and visibility updates to work seamlessly.</p>
        <p><strong>Ghosts (👻)</strong> are semi-transparent copies shown slightly elevated. They represent read-only projections of entities from other cells.</p>
    </div>

    <script>
        var data = {json.dumps(traces)};
        var layout = {{
            scene: {{
                xaxis: {{title: 'X (yards)', range: [{min_plot_x}, {max_plot_x}], gridcolor: '#444'}},
                yaxis: {{title: 'Y (yards)', range: [{min_plot_y}, {max_plot_y}], gridcolor: '#444'}},
                zaxis: {{title: 'Z (yards)', range: [-5, {CELL_HEIGHT + 15}], gridcolor: '#444'}},
                aspectmode: 'manual',
                aspectratio: {{x: 1, y: 1, z: 0.3}},
                camera: {{
                    eye: {{x: 1.5, y: 1.5, z: 1.2}},
                    center: {{x: 0, y: 0, z: -0.1}}
                }},
                bgcolor: '#0f0f23'
            }},
            paper_bgcolor: '#1a1a2e',
            plot_bgcolor: '#1a1a2e',
            font: {{color: '#eee'}},
            showlegend: true,
            legend: {{x: 1, y: 1, bgcolor: 'rgba(0,0,0,0.5)'}},
            margin: {{l: 0, r: 0, t: 30, b: 0}}
        }};
        var config = {{
            responsive: true,
            displayModeBar: true,
            modeBarButtonsToRemove: ['lasso2d', 'select2d']
        }};
        Plotly.newPlot('viz', data, layout, config);
    </script>
</body>
</html>'''
    return html


def register_ghostactor_tools(mcp):
    """Register ghost actor visualization tools."""

    @mcp.tool()
    def visualize_ghost_system(
        grid_size: int = 3,
        entities_per_cell: int = 5,
        show_messages: bool = True
    ) -> str:
        """Generate interactive 3D visualization of Ghost Actor System (demo data)."""
        try:
            # Clamp grid size to reasonable bounds
            grid_size = max(2, min(grid_size, 10))
            entities_per_cell = max(1, min(entities_per_cell, 20))

            # Generate simulated data
            cells, entities, ghosts, messages = generate_demo_data(
                grid_size, entities_per_cell, show_messages
            )

            # Generate HTML with plotly
            html = generate_3d_html(cells, entities, ghosts, messages)

            # Save to temp file
            output_path = "/tmp/ghost_actor_viz.html"
            with open(output_path, "w") as f:
                f.write(html)

            return json.dumps({
                "message": "3D visualization generated successfully",
                "file": output_path,
                "open_command": f"xdg-open {output_path}",
                "stats": {
                    "cells": len(cells),
                    "entities": len(entities),
                    "ghosts": len(ghosts),
                    "messages": len(messages) if show_messages else 0,
                    "ghosts_per_entity": round(len(ghosts) / max(1, len(entities)), 1)
                }
            }, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    def visualize_ghost_system_real(
        map_id: int = 0,
        center_x: float = -9465.0,
        center_y: float = -650.0,
        radius: float = 150.0,
        show_messages: bool = True
    ) -> str:
        """Generate 3D visualization using real creature spawns from database.

        Default location: Elwynn Forest near Tower of Azora.
        Includes 3 hypothetical players: 2 together in a cell, 1 outside creating a ghost.
        """
        try:
            # Generate data from real creatures
            cells, entities, ghosts, messages, terrain_points = generate_real_data(
                map_id, center_x, center_y, radius, show_messages
            )

            if not entities:
                return json.dumps({
                    "error": "No creatures found in specified area",
                    "params": {"map": map_id, "center": [center_x, center_y], "radius": radius}
                })

            # Count entity types
            num_players = sum(1 for e in entities if e["type"] == "player")
            num_creatures = sum(1 for e in entities if e["type"] == "creature")
            num_creature_ghosts = sum(1 for g in ghosts if g["entity_type"] == "creature")
            num_player_ghosts = sum(1 for g in ghosts if g["entity_type"] == "player")

            # Generate HTML
            title = f"Ghost Actor System - Map {map_id} (Real Data)"
            html = generate_3d_html(cells, entities, ghosts, messages, title,
                                   use_world_coords=True, terrain_points=terrain_points)

            # Save to temp file
            output_path = "/tmp/ghost_actor_viz_real.html"
            with open(output_path, "w") as f:
                f.write(html)

            return json.dumps({
                "message": "3D visualization generated from real data",
                "file": output_path,
                "open_command": f"xdg-open {output_path}",
                "location": {
                    "map": map_id,
                    "center_x": center_x,
                    "center_y": center_y,
                    "radius": radius
                },
                "stats": {
                    "cells": len(cells),
                    "players": num_players,
                    "creatures": num_creatures,
                    "total_entities": len(entities),
                    "creature_ghosts": num_creature_ghosts,
                    "player_ghosts": num_player_ghosts,
                    "total_ghosts": len(ghosts),
                    "messages": len(messages)
                }
            }, indent=2)
        except Exception as e:
            import traceback
            return json.dumps({"error": str(e), "traceback": traceback.format_exc()})
