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
AzerothCore Map File Parser

Parses .map files to extract terrain heightmap data for visualization.

File format (from GridTerrainData.h):
- Header: MAPS magic, version 9, offsets to sections
- AREA section: 16x16 area IDs
- MHGT section: 129x129 height vertices (V9) + 128x128 triangle heights (V8)
- MLIQ section: Liquid data (water, lava, etc.)

Grid coordinate system:
- 64x64 grids per map, each 533.33 units
- Grid (0,0) is at world coords (32*533.33, 32*533.33)
- World coords range roughly from -17066 to +17066
"""

import struct
import os
from dataclasses import dataclass
from typing import Optional, Tuple, List
import numpy as np


# Constants from GridDefines.h
MAX_NUMBER_OF_GRIDS = 64
SIZE_OF_GRIDS = 533.3333
CENTER_GRID_ID = MAX_NUMBER_OF_GRIDS // 2  # 32

# Map file constants
MAP_MAGIC = b'MAPS'
MAP_VERSION = 9
AREA_MAGIC = b'AREA'
HEIGHT_MAGIC = b'MHGT'
LIQUID_MAGIC = b'MLIQ'

# Height flags
MAP_HEIGHT_NO_HEIGHT = 0x0001
MAP_HEIGHT_AS_INT16 = 0x0002
MAP_HEIGHT_AS_INT8 = 0x0004
MAP_HEIGHT_HAS_FLIGHT_BOUNDS = 0x0008


@dataclass
class MapFileHeader:
    """Main .map file header structure."""
    magic: bytes
    version: int
    build: int
    area_offset: int
    area_size: int
    height_offset: int
    height_size: int
    liquid_offset: int
    liquid_size: int
    holes_offset: int
    holes_size: int


@dataclass
class HeightData:
    """Parsed heightmap data from a single grid tile."""
    flags: int
    grid_height: float  # Base height
    grid_max_height: float  # Max height (for scaling int values)
    v9: np.ndarray  # 129x129 vertex heights
    v8: np.ndarray  # 128x128 triangle center heights (optional)

    @property
    def has_height(self) -> bool:
        return not (self.flags & MAP_HEIGHT_NO_HEIGHT)


@dataclass
class GridTile:
    """A single map grid tile with all its data."""
    map_id: int
    grid_x: int
    grid_y: int
    header: MapFileHeader
    height_data: Optional[HeightData]

    @property
    def world_x_min(self) -> float:
        """Minimum world X coordinate for this grid."""
        return (CENTER_GRID_ID - self.grid_x - 1) * SIZE_OF_GRIDS

    @property
    def world_x_max(self) -> float:
        """Maximum world X coordinate for this grid."""
        return (CENTER_GRID_ID - self.grid_x) * SIZE_OF_GRIDS

    @property
    def world_y_min(self) -> float:
        """Minimum world Y coordinate for this grid."""
        return (CENTER_GRID_ID - self.grid_y - 1) * SIZE_OF_GRIDS

    @property
    def world_y_max(self) -> float:
        """Maximum world Y coordinate for this grid."""
        return (CENTER_GRID_ID - self.grid_y) * SIZE_OF_GRIDS

    def get_world_coords(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get world coordinate arrays matching the heightmap orientation.

        Returns X and Y coordinate arrays where:
        - x_coords[i] is the world X for heightmap row i
        - y_coords[j] is the world Y for heightmap column j

        Note: WoW maps have inverted coords - higher world coord = lower array index
        """
        # Array index 0 = max world coord, index 128 = min world coord
        x_coords = np.linspace(self.world_x_max, self.world_x_min, 129)
        y_coords = np.linspace(self.world_y_max, self.world_y_min, 129)
        return x_coords, y_coords


class MapParser:
    """Parser for AzerothCore .map terrain files."""

    def __init__(self, maps_path: str):
        """
        Initialize parser with path to maps directory.

        Args:
            maps_path: Path to the maps/ directory containing .map files
        """
        self.maps_path = maps_path
        self._cache = {}

    def get_map_filename(self, map_id: int, grid_x: int, grid_y: int) -> str:
        """Generate the filename for a specific map tile."""
        # Format: MMMXXYY.map where MMM=mapId, XX=gridX, YY=gridY
        return f"{map_id:03d}{grid_x:02d}{grid_y:02d}.map"

    def get_map_filepath(self, map_id: int, grid_x: int, grid_y: int) -> str:
        """Get full path to a map file."""
        return os.path.join(self.maps_path, self.get_map_filename(map_id, grid_x, grid_y))

    def world_to_grid(self, x: float, y: float) -> Tuple[int, int]:
        """
        Convert world coordinates to grid coordinates.

        Args:
            x: World X coordinate
            y: World Y coordinate

        Returns:
            Tuple of (grid_x, grid_y)
        """
        grid_x = int(CENTER_GRID_ID - (x / SIZE_OF_GRIDS))
        grid_y = int(CENTER_GRID_ID - (y / SIZE_OF_GRIDS))
        return (grid_x, grid_y)

    def grid_to_world_center(self, grid_x: int, grid_y: int) -> Tuple[float, float]:
        """
        Get the world coordinates of the center of a grid tile.

        Args:
            grid_x: Grid X coordinate
            grid_y: Grid Y coordinate

        Returns:
            Tuple of (world_x, world_y) at grid center
        """
        world_x = (CENTER_GRID_ID - grid_x - 0.5) * SIZE_OF_GRIDS
        world_y = (CENTER_GRID_ID - grid_y - 0.5) * SIZE_OF_GRIDS
        return (world_x, world_y)

    def parse_header(self, data: bytes) -> MapFileHeader:
        """Parse the main file header."""
        magic = data[0:4]
        values = struct.unpack('<IIIIIIIIII', data[4:44])

        return MapFileHeader(
            magic=magic,
            version=values[0],
            build=values[1],
            area_offset=values[2],
            area_size=values[3],
            height_offset=values[4],
            height_size=values[5],
            liquid_offset=values[6],
            liquid_size=values[7],
            holes_offset=values[8],
            holes_size=values[9]
        )

    def parse_height_data(self, data: bytes, header: MapFileHeader) -> Optional[HeightData]:
        """Parse the height/terrain data section."""
        if header.height_size == 0:
            return None

        offset = header.height_offset

        # Read height header
        section_magic = data[offset:offset+4]
        if section_magic != HEIGHT_MAGIC:
            return None

        flags = struct.unpack('<I', data[offset+4:offset+8])[0]

        # Check if this tile has height data
        if flags & MAP_HEIGHT_NO_HEIGHT:
            grid_height = struct.unpack('<f', data[offset+8:offset+12])[0]
            return HeightData(
                flags=flags,
                grid_height=grid_height,
                grid_max_height=grid_height,
                v9=np.full((129, 129), grid_height, dtype=np.float32),
                v8=np.full((128, 128), grid_height, dtype=np.float32)
            )

        grid_height = struct.unpack('<f', data[offset+8:offset+12])[0]
        grid_max_height = struct.unpack('<f', data[offset+12:offset+16])[0]

        data_offset = offset + 16

        # Parse height values based on format flags
        if flags & MAP_HEIGHT_AS_INT8:
            # 8-bit heights - need to scale
            v9_size = 129 * 129
            v8_size = 128 * 128
            v9_raw = np.frombuffer(data[data_offset:data_offset+v9_size], dtype=np.uint8)
            v8_raw = np.frombuffer(data[data_offset+v9_size:data_offset+v9_size+v8_size], dtype=np.uint8)

            # Scale to actual heights
            height_range = grid_max_height - grid_height
            v9 = (v9_raw.astype(np.float32) / 255.0) * height_range + grid_height
            v8 = (v8_raw.astype(np.float32) / 255.0) * height_range + grid_height

        elif flags & MAP_HEIGHT_AS_INT16:
            # 16-bit heights - need to scale
            v9_size = 129 * 129 * 2
            v8_size = 128 * 128 * 2
            v9_raw = np.frombuffer(data[data_offset:data_offset+v9_size], dtype=np.uint16)
            v8_raw = np.frombuffer(data[data_offset+v9_size:data_offset+v9_size+v8_size], dtype=np.uint16)

            # Scale to actual heights
            height_range = grid_max_height - grid_height
            v9 = (v9_raw.astype(np.float32) / 65535.0) * height_range + grid_height
            v8 = (v8_raw.astype(np.float32) / 65535.0) * height_range + grid_height

        else:
            # Full float heights
            v9_size = 129 * 129 * 4
            v8_size = 128 * 128 * 4
            v9 = np.frombuffer(data[data_offset:data_offset+v9_size], dtype=np.float32).copy()
            v8 = np.frombuffer(data[data_offset+v9_size:data_offset+v9_size+v8_size], dtype=np.float32).copy()

        # Reshape to 2D arrays
        v9 = v9.reshape((129, 129))
        v8 = v8.reshape((128, 128))

        return HeightData(
            flags=flags,
            grid_height=grid_height,
            grid_max_height=grid_max_height,
            v9=v9,
            v8=v8
        )

    def load_tile(self, map_id: int, grid_x: int, grid_y: int) -> Optional[GridTile]:
        """
        Load a single map tile.

        Args:
            map_id: Map ID (0=Eastern Kingdoms, 1=Kalimdor, etc.)
            grid_x: Grid X coordinate (0-63)
            grid_y: Grid Y coordinate (0-63)

        Returns:
            GridTile with parsed data, or None if file doesn't exist
        """
        cache_key = (map_id, grid_x, grid_y)
        if cache_key in self._cache:
            return self._cache[cache_key]

        filepath = self.get_map_filepath(map_id, grid_x, grid_y)

        if not os.path.exists(filepath):
            return None

        with open(filepath, 'rb') as f:
            data = f.read()

        if len(data) < 44:
            return None

        header = self.parse_header(data)

        if header.magic != MAP_MAGIC:
            return None

        height_data = self.parse_height_data(data, header)

        tile = GridTile(
            map_id=map_id,
            grid_x=grid_x,
            grid_y=grid_y,
            header=header,
            height_data=height_data
        )

        self._cache[cache_key] = tile
        return tile

    def load_tiles_for_area(
        self,
        map_id: int,
        min_x: float,
        min_y: float,
        max_x: float,
        max_y: float
    ) -> List[GridTile]:
        """
        Load all tiles that cover a world coordinate area.

        Args:
            map_id: Map ID
            min_x, min_y: Minimum world coordinates
            max_x, max_y: Maximum world coordinates

        Returns:
            List of GridTile objects covering the area
        """
        grid_min = self.world_to_grid(max_x, max_y)  # Note: inverted due to coord system
        grid_max = self.world_to_grid(min_x, min_y)

        tiles = []
        for gx in range(grid_min[0], grid_max[0] + 1):
            for gy in range(grid_min[1], grid_max[1] + 1):
                if 0 <= gx < MAX_NUMBER_OF_GRIDS and 0 <= gy < MAX_NUMBER_OF_GRIDS:
                    tile = self.load_tile(map_id, gx, gy)
                    if tile:
                        tiles.append(tile)

        return tiles

    def get_height_at(self, map_id: int, x: float, y: float) -> Optional[float]:
        """
        Get terrain height at a specific world coordinate.

        Args:
            map_id: Map ID
            x: World X coordinate
            y: World Y coordinate

        Returns:
            Height value or None if tile not found
        """
        grid_x, grid_y = self.world_to_grid(x, y)
        tile = self.load_tile(map_id, grid_x, grid_y)

        if not tile or not tile.height_data:
            return None

        # Calculate position within tile (0-1)
        local_x = (tile.world_x_max - x) / SIZE_OF_GRIDS
        local_y = (tile.world_y_max - y) / SIZE_OF_GRIDS

        # Clamp to valid range
        local_x = max(0, min(1, local_x))
        local_y = max(0, min(1, local_y))

        # Map to heightmap indices
        hx = int(local_x * 128)
        hy = int(local_y * 128)

        hx = max(0, min(128, hx))
        hy = max(0, min(128, hy))

        return float(tile.height_data.v9[hy, hx])

    def get_available_tiles(self, map_id: int) -> List[Tuple[int, int]]:
        """
        Get list of available grid tiles for a map.

        Args:
            map_id: Map ID

        Returns:
            List of (grid_x, grid_y) tuples for available tiles
        """
        tiles = []
        prefix = f"{map_id:03d}"

        for filename in os.listdir(self.maps_path):
            if filename.startswith(prefix) and filename.endswith('.map'):
                try:
                    grid_x = int(filename[3:5])
                    grid_y = int(filename[5:7])
                    tiles.append((grid_x, grid_y))
                except ValueError:
                    continue

        return sorted(tiles)


# Map ID constants for common maps
MAP_EASTERN_KINGDOMS = 0
MAP_KALIMDOR = 1
MAP_OUTLAND = 530
MAP_NORTHREND = 571
