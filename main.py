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
AzerothCore MCP Server - Main Entry Point

A Model Context Protocol server that provides Claude with access to:
- AzerothCore MySQL databases (world, characters, auth)
- Wiki documentation for SmartAI and database schemas
- Helper tools for understanding creature scripts and game mechanics
"""

import os
from mcp.server.fastmcp import FastMCP

from azerothmcp.config import (
    DB_CONFIG,
    DB_NAMES,
    READ_ONLY,
    WIKI_PATH,
    AZEROTHCORE_SRC_PATH,
    ENABLE_SPELL_DBC,
    ENABLE_PACKET_PARSER,
    WPP_PATH,
    MCP_PORT,
    SOAP_ENABLED,
    ENABLE_SANDBOX,
    LOG_TOOL_CALLS,
    LOG_LEVEL,
)
from azerothmcp.tools import register_all_tools

# Check for optional features
try:
    from sai_comment_generator import SaiCommentGenerator
    SAI_GENERATOR_AVAILABLE = True
except ImportError:
    SAI_GENERATOR_AVAILABLE = False

try:
    from soap_client import create_soap_client_from_env
    SOAP_AVAILABLE = True
    _soap_client = create_soap_client_from_env() if SOAP_ENABLED else None
except ImportError:
    SOAP_AVAILABLE = False
    _soap_client = None


# Initialize MCP server with SSE settings
mcp = FastMCP(
    "AzerothCore MCP Server",
    host="0.0.0.0",
    port=MCP_PORT
)

# Register all tools
register_all_tools(mcp)


def print_startup_info():
    """Print server startup information."""
    print(f"Starting AzerothCore MCP Server on http://localhost:{MCP_PORT}/sse")
    print()

    # Database status
    print(f"Database: {DB_CONFIG['host']}:{DB_CONFIG['port']} ({', '.join(DB_NAMES.values())})")
    print(f"Database Mode: {'READ-ONLY' if READ_ONLY else 'READ-WRITE'}")

    # Wiki status
    if WIKI_PATH.exists():
        print(f"Wiki: {WIKI_PATH}")
    else:
        print(f"Wiki: NOT FOUND ({WIKI_PATH})")

    # AzerothCore source status
    if AZEROTHCORE_SRC_PATH.exists():
        print(f"AzerothCore Source: {AZEROTHCORE_SRC_PATH}")
    else:
        print(f"AzerothCore Source: NOT FOUND ({AZEROTHCORE_SRC_PATH})")

    # Optional features
    if ENABLE_SPELL_DBC:
        print("Spell DBC: ENABLED")

    # Keira3 SAI Comment Generator
    if SAI_GENERATOR_AVAILABLE:
        print("Keira3 SAI Generator: ENABLED")
    else:
        print("Keira3 SAI Generator: NOT AVAILABLE (check sai_comment_generator.py)")

    # SOAP client status
    if SOAP_AVAILABLE and SOAP_ENABLED:
        if _soap_client:
            print(f"SOAP: ENABLED ({_soap_client.host}:{_soap_client.port})")
        else:
            print("SOAP: ENABLED but credentials not configured (set SOAP_USERNAME/SOAP_PASSWORD)")
    elif SOAP_AVAILABLE:
        print("SOAP: DISABLED (set SOAP_ENABLED=true to enable)")
    else:
        print("SOAP: NOT AVAILABLE (check soap_client.py)")

    # Sandbox status (programmatic tool calling)
    if ENABLE_SANDBOX:
        print("Sandbox: ENABLED (execute_investigation tool available)")
    else:
        print("Sandbox: DISABLED (set ENABLE_SANDBOX=true to enable)")

    # WowPacketParser status
    if ENABLE_PACKET_PARSER:
        wpp_dll = WPP_PATH / "WowPacketParser.dll"
        if wpp_dll.exists():
            print(f"Packet Parser: ENABLED ({WPP_PATH})")
        else:
            print(f"Packet Parser: ENABLED but WPP not found ({WPP_PATH})")
    else:
        print("Packet Parser: DISABLED (set ENABLE_PACKET_PARSER=true to enable)")

    # Logging status
    if LOG_TOOL_CALLS:
        print(f"Tool Logging: ENABLED (level={LOG_LEVEL})")
    else:
        print("Tool Logging: DISABLED (set LOG_TOOL_CALLS=true to enable)")

    print()


if __name__ == "__main__":
    print_startup_info()
    mcp.run(transport="sse")
