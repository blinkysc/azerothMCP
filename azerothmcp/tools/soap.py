#!/usr/bin/env python3
"""SOAP worldserver command tools"""

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
    """Register SOAP worldserver command tools."""

    @mcp.tool()
    def soap_execute_command(command: str) -> str:
        """Execute GM command on running worldserver via SOAP."""
        if not SOAP_AVAILABLE:
            return json.dumps({"success": False, "error": "SOAP client not available"})
        if not SOAP_ENABLED:
            return json.dumps({"success": False, "error": "SOAP not enabled (set SOAP_ENABLED=true)"})
        if _soap_client is None:
            return json.dumps({"success": False, "error": "SOAP client not configured (set SOAP_USERNAME/PASSWORD)"})

        try:
            response = _soap_client.execute_command(command)
            return json.dumps({
                "success": response.success,
                "message": response.message if response.success else None,
                "error": response.fault_string if not response.success else None
            }, indent=2)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    @mcp.tool()
    def soap_server_info() -> str:
        """Get server uptime, player count, and version info."""
        return soap_execute_command("server info")

    @mcp.tool()
    def soap_reload_table(table_name: str) -> str:
        """Hot-reload database tables without server restart."""
        return soap_execute_command(f"reload {table_name}")

    @mcp.tool()
    def soap_check_connection() -> str:
        """Test SOAP connectivity and authentication."""
        return soap_execute_command("server info")
