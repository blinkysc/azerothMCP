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
SOAP worldserver command tools for AzerothCore MCP Server.
"""

import json

from ..config import SOAP_ENABLED

# Import SOAP client for worldserver commands
try:
    from soap_client import create_soap_client_from_env
    SOAP_AVAILABLE = True
except ImportError:
    SOAP_AVAILABLE = False
    create_soap_client_from_env = None

# Initialize SOAP client
_soap_client = None
if SOAP_AVAILABLE and SOAP_ENABLED:
    _soap_client = create_soap_client_from_env()


def register_soap_tools(mcp):
    """Register SOAP worldserver command tools with the MCP server."""

    @mcp.tool()
    def soap_execute_command(command: str) -> str:
        """
        Execute a GM command on a running AzerothCore worldserver via SOAP.

        This allows you to interact with the live server, such as:
        - Server management: server info, server shutdown, server restart
        - Account management: account create, account set gmlevel
        - Character operations: character level, character rename
        - World modifications: reload commands, npc add
        - And any other GM command available in-game

        Args:
            command: The GM command to execute (without leading dot).
                     Example: "server info", "account create testuser testpass"

        Returns:
            JSON with success status and command output or error message.

        Requirements:
            - SOAP must be enabled in worldserver.conf (SOAP.Enabled = 1)
            - Environment variables must be set:
              - SOAP_ENABLED=true
              - SOAP_USERNAME=<admin account>
              - SOAP_PASSWORD=<account password>
            - The account must have administrator privileges (SEC_ADMINISTRATOR)

        Examples:
            - soap_execute_command("server info")
            - soap_execute_command("account create newplayer password123")
            - soap_execute_command("reload creature_template")
        """
        if not SOAP_AVAILABLE:
            return json.dumps({
                "success": False,
                "error": "SOAP client module not available. Check soap_client.py exists."
            })

        if not SOAP_ENABLED:
            return json.dumps({
                "success": False,
                "error": "SOAP is not enabled. Set SOAP_ENABLED=true in environment."
            })

        if _soap_client is None:
            return json.dumps({
                "success": False,
                "error": "SOAP client not configured. Set SOAP_USERNAME and SOAP_PASSWORD."
            })

        try:
            response = _soap_client.execute_command(command)
            return json.dumps({
                "success": response.success,
                "message": response.message if response.success else None,
                "error": response.fault_string if not response.success else None
            }, indent=2)
        except ConnectionError as e:
            return json.dumps({
                "success": False,
                "error": f"Connection failed: {e}"
            })
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e)
            })

    @mcp.tool()
    def soap_server_info() -> str:
        """
        Get information about the running AzerothCore worldserver.

        Returns server uptime, connected players, and version information.

        This is a convenience wrapper around soap_execute_command("server info").
        """
        return soap_execute_command("server info")

    @mcp.tool()
    def soap_reload_table(table_name: str) -> str:
        """
        Reload a database table on the running worldserver.

        This is useful after making database changes to apply them without restart.

        Args:
            table_name: The reload command argument. Common commands include:

                Full table reloads (no arguments needed):
                - smart_scripts
                - conditions
                - gossip_menu
                - gossip_menu_option
                - npc_trainer
                - npc_vendor
                - page_text
                - areatrigger_teleport
                - broadcast_text
                - creature_text

                Entry-specific reloads (append entry ID):
                - creature_template <entry>  (e.g., "creature_template 448")
                - quest_template <quest_id>
                - item_template <entry>
                - gameobject_template <entry>

                Aggregate reloads:
                - all (reload everything)
                - all npc
                - all quest
                - all spell
                - all scripts
                - all gossips
                - all loot

        Returns:
            JSON with success status and reload result.

        Note: Some reload commands may take time on large tables.
        """
        return soap_execute_command(f"reload {table_name}")

    @mcp.tool()
    def soap_check_connection() -> str:
        """
        Check if the SOAP connection to worldserver is working.

        Returns:
            JSON with connection status and server info if connected.

        Use this to verify SOAP is properly configured before running commands.
        """
        if not SOAP_AVAILABLE:
            return json.dumps({
                "connected": False,
                "error": "SOAP client module not available"
            })

        if not SOAP_ENABLED:
            return json.dumps({
                "connected": False,
                "error": "SOAP not enabled (set SOAP_ENABLED=true)"
            })

        if _soap_client is None:
            return json.dumps({
                "connected": False,
                "error": "SOAP credentials not configured"
            })

        try:
            response = _soap_client.execute_command("server info")
            return json.dumps({
                "connected": response.success,
                "server_info": response.message if response.success else None,
                "error": response.fault_string if not response.success else None
            }, indent=2)
        except ConnectionError as e:
            return json.dumps({
                "connected": False,
                "error": str(e)
            })
