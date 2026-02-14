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
MCP Tools for AzerothCore

This package contains all the tool modules that are registered with the MCP server.
Uses progressive disclosure with minimal docstrings and lazy-loaded reference data.
"""

import logging

# Import discovery tools FIRST - these enable progressive exploration
from .discovery import register_discovery_tools

# Import tool modules
from .database import register_database_tools
from .creatures import register_creature_tools
from .smartai import register_smartai_tools
from .gameobjects import register_gameobject_tools
from .quests import register_quest_tools
from .items import register_item_tools
from .spells import register_spell_tools
from .soap import register_soap_tools
from .conditions import register_condition_tools
from .waypoints import register_waypoint_tools
from .procs import register_proc_tools
from .ghostactor import register_ghostactor_tools

# Optional imports (controlled by config)
from ..config import ENABLE_WIKI, ENABLE_SOURCE_CODE, ENABLE_SANDBOX, ENABLE_PACKET_PARSER, ENABLE_DBC_PARSER, LOG_TOOL_CALLS, LOG_LEVEL
if ENABLE_WIKI:
    from .wiki import register_wiki_tools
if ENABLE_SOURCE_CODE:
    from .source import register_source_tools
if ENABLE_SANDBOX:
    from .sandbox import register_sandbox_tools
if ENABLE_PACKET_PARSER:
    from .packets import register_packet_tools
if ENABLE_DBC_PARSER:
    from .dbc import register_dbc_tools

# Configure logging based on settings
if LOG_TOOL_CALLS:
    from ..logging import tool_logger
    tool_logger.logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))


def register_all_tools(mcp):
    """Register all tools with the MCP server."""
    # Register discovery tools FIRST so AI can explore on-demand
    register_discovery_tools(mcp)

    # Register all domain-specific tools with minimal docstrings
    register_database_tools(mcp)
    register_creature_tools(mcp)
    register_smartai_tools(mcp)
    register_gameobject_tools(mcp)
    register_quest_tools(mcp)
    register_item_tools(mcp)
    register_spell_tools(mcp)
    register_soap_tools(mcp)
    register_condition_tools(mcp)
    register_waypoint_tools(mcp)
    register_proc_tools(mcp)
    register_ghostactor_tools(mcp)

    # Register optional tools if enabled
    if ENABLE_WIKI:
        register_wiki_tools(mcp)
    if ENABLE_SOURCE_CODE:
        register_source_tools(mcp)
    if ENABLE_SANDBOX:
        register_sandbox_tools(mcp)
    if ENABLE_PACKET_PARSER:
        register_packet_tools(mcp)
    if ENABLE_DBC_PARSER:
        register_dbc_tools(mcp)
