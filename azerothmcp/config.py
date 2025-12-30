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
Configuration management for AzerothCore MCP Server.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER", "acore"),
    "password": os.getenv("DB_PASSWORD", "acore"),
}

DB_NAMES = {
    "world": os.getenv("DB_WORLD", "acore_world"),
    "characters": os.getenv("DB_CHARACTERS", "acore_characters"),
    "auth": os.getenv("DB_AUTH", "acore_auth"),
}

# Read-only mode (set to "false" to enable write operations)
READ_ONLY = os.getenv("READ_ONLY", "true").lower() != "false"

# Enable spell_dbc tool (only needed for custom spells)
ENABLE_SPELL_DBC = os.getenv("ENABLE_SPELL_DBC", "false").lower() == "true"

# Enable visualization tools (2D/3D waypoint visualization - requires matplotlib/plotly)
ENABLE_VISUALIZATION = os.getenv("ENABLE_VISUALIZATION", "false").lower() == "true"

# Enable packet parser tools (requires WowPacketParser)
ENABLE_PACKET_PARSER = os.getenv("ENABLE_PACKET_PARSER", "false").lower() == "true"

# Enable DBC parser tools (for reading Spell.dbc directly)
ENABLE_DBC_PARSER = os.getenv("ENABLE_DBC_PARSER", "true").lower() == "true"

# DBC files path
DBC_PATH = Path(os.path.expanduser(os.getenv("DBC_PATH", "~/azerothcore/data/dbc")))

# WowPacketParser paths
WPP_PATH = Path(os.path.expanduser(os.getenv("WPP_PATH", "~/WowPacketParser/WowPacketParser/bin/Release")))
DOTNET_PATH = os.getenv("DOTNET_PATH", os.path.expanduser("~/.dotnet/dotnet"))

# Enable wiki search tools (disabled by default to reduce token usage)
ENABLE_WIKI = os.getenv("ENABLE_WIKI", "false").lower() == "true"

# Enable source code search tools (disabled by default to reduce token usage)
ENABLE_SOURCE_CODE = os.getenv("ENABLE_SOURCE_CODE", "false").lower() == "true"

# Wiki path for documentation
WIKI_PATH = Path(os.path.expanduser(os.getenv("WIKI_PATH", "~/wiki/docs")))

# AzerothCore source path (for reading SmartAI implementations)
AZEROTHCORE_SRC_PATH = Path(os.path.expanduser(os.getenv("AZEROTHCORE_SRC_PATH", "~/azerothcore")))

# MCP Server configuration
MCP_PORT = int(os.getenv("MCP_PORT", 8080))

# SOAP configuration
SOAP_ENABLED = os.getenv("SOAP_ENABLED", "false").lower() == "true"

# Sandbox configuration (programmatic tool calling)
ENABLE_SANDBOX = os.getenv("ENABLE_SANDBOX", "true").lower() == "true"

# Logging configuration
LOG_TOOL_CALLS = os.getenv("LOG_TOOL_CALLS", "true").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Maps data path (for terrain visualization)
MAPS_PATH = Path(os.path.expanduser(os.getenv("MAPS_PATH", "~/azerothcore/data/maps")))

# Visualization host (for remote access to generated visualizations)
VIZ_HOST = os.getenv("VIZ_HOST", "localhost")
VIZ_PORT = int(os.getenv("VIZ_PORT", 8888))


def get_config() -> dict:
    """Return all configuration as a dictionary."""
    return {
        "DB_CONFIG": DB_CONFIG,
        "DB_NAMES": DB_NAMES,
        "READ_ONLY": READ_ONLY,
        "ENABLE_SPELL_DBC": ENABLE_SPELL_DBC,
        "ENABLE_VISUALIZATION": ENABLE_VISUALIZATION,
        "ENABLE_PACKET_PARSER": ENABLE_PACKET_PARSER,
        "ENABLE_DBC_PARSER": ENABLE_DBC_PARSER,
        "DBC_PATH": str(DBC_PATH),
        "ENABLE_WIKI": ENABLE_WIKI,
        "ENABLE_SOURCE_CODE": ENABLE_SOURCE_CODE,
        "ENABLE_SANDBOX": ENABLE_SANDBOX,
        "LOG_TOOL_CALLS": LOG_TOOL_CALLS,
        "LOG_LEVEL": LOG_LEVEL,
        "WIKI_PATH": str(WIKI_PATH),
        "AZEROTHCORE_SRC_PATH": str(AZEROTHCORE_SRC_PATH),
        "MCP_PORT": MCP_PORT,
        "SOAP_ENABLED": SOAP_ENABLED,
        "MAPS_PATH": str(MAPS_PATH),
        "VIZ_HOST": VIZ_HOST,
        "VIZ_PORT": VIZ_PORT,
        "WPP_PATH": str(WPP_PATH),
        "DOTNET_PATH": DOTNET_PATH,
    }
