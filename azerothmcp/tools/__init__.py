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
MCP Tools for AzerothCore.

This package contains all the tool modules that are registered with the MCP server.
"""

from .database import register_database_tools
from .creatures import register_creature_tools
from .smartai import register_smartai_tools
from .source import register_source_tools
from .wiki import register_wiki_tools
from .gameobjects import register_gameobject_tools
from .quests import register_quest_tools
from .items import register_item_tools
from .spells import register_spell_tools
from .soap import register_soap_tools


def register_all_tools(mcp):
    """Register all tools with the MCP server."""
    register_database_tools(mcp)
    register_creature_tools(mcp)
    register_smartai_tools(mcp)
    register_source_tools(mcp)
    register_wiki_tools(mcp)
    register_gameobject_tools(mcp)
    register_quest_tools(mcp)
    register_item_tools(mcp)
    register_spell_tools(mcp)
    register_soap_tools(mcp)
