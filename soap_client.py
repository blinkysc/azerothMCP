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
AzerothCore SOAP Client

A Python client for communicating with AzerothCore's SOAP interface.
This allows executing GM commands on a running worldserver instance.

The SOAP interface must be enabled in worldserver.conf:
    SOAP.Enabled = 1
    SOAP.IP = "127.0.0.1"
    SOAP.Port = 7878

The account used must have administrator (SEC_ADMINISTRATOR, level 3+) access.
"""

import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from base64 import b64encode


@dataclass
class SOAPResponse:
    """Response from a SOAP command execution."""
    success: bool
    message: str
    fault_string: Optional[str] = None


class AzerothCoreSOAP:
    """
    Client for AzerothCore's SOAP interface.

    Example usage:
        client = AzerothCoreSOAP("127.0.0.1", 7878, "admin", "admin_password")
        response = client.execute_command("server info")
        if response.success:
            print(response.message)
        else:
            print(f"Error: {response.fault_string}")
    """

    # SOAP envelope template for executeCommand
    SOAP_ENVELOPE = """<?xml version="1.0" encoding="UTF-8"?>
<SOAP-ENV:Envelope
    xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"
    xmlns:SOAP-ENC="http://schemas.xmlsoap.org/soap/encoding/"
    xmlns:xsi="http://www.w3.org/1999/XMLSchema-instance"
    xmlns:xsd="http://www.w3.org/1999/XMLSchema"
    xmlns:ns1="urn:AC">
    <SOAP-ENV:Body>
        <ns1:executeCommand>
            <command>{command}</command>
        </ns1:executeCommand>
    </SOAP-ENV:Body>
</SOAP-ENV:Envelope>"""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 7878,
        username: str = "",
        password: str = "",
        timeout: int = 30
    ):
        """
        Initialize the SOAP client.

        Args:
            host: SOAP server host (default: 127.0.0.1)
            port: SOAP server port (default: 7878)
            username: Account username with admin privileges
            password: Account password
            timeout: Request timeout in seconds (default: 30)
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout
        self._url = f"http://{host}:{port}/"

    def _get_auth_header(self) -> str:
        """Generate Basic Auth header value."""
        credentials = f"{self.username}:{self.password}"
        encoded = b64encode(credentials.encode("utf-8")).decode("utf-8")
        return f"Basic {encoded}"

    def _escape_xml(self, text: str) -> str:
        """Escape special XML characters in command string."""
        replacements = [
            ("&", "&amp;"),
            ("<", "&lt;"),
            (">", "&gt;"),
            ('"', "&quot;"),
            ("'", "&apos;"),
        ]
        for old, new in replacements:
            text = text.replace(old, new)
        return text

    def _parse_response(self, xml_data: bytes) -> SOAPResponse:
        """Parse SOAP response XML."""
        try:
            root = ET.fromstring(xml_data)

            # Define namespaces used in response
            namespaces = {
                "SOAP-ENV": "http://schemas.xmlsoap.org/soap/envelope/",
                "ns1": "urn:AC",
            }

            # Check for SOAP Fault
            fault = root.find(".//SOAP-ENV:Fault", namespaces)
            if fault is not None:
                fault_string = fault.find("faultstring")
                fault_detail = fault.find("detail")
                error_msg = ""
                if fault_string is not None and fault_string.text:
                    error_msg = fault_string.text
                if fault_detail is not None and fault_detail.text:
                    error_msg = fault_detail.text or error_msg
                return SOAPResponse(
                    success=False,
                    message="",
                    fault_string=error_msg or "Unknown SOAP fault"
                )

            # Look for successful response
            result = root.find(".//ns1:result", namespaces)
            if result is not None and result.text:
                return SOAPResponse(success=True, message=result.text.strip())

            # Try without namespace (some responses may vary)
            result = root.find(".//result")
            if result is not None and result.text:
                return SOAPResponse(success=True, message=result.text.strip())

            return SOAPResponse(success=True, message="Command executed (no output)")

        except ET.ParseError as e:
            return SOAPResponse(
                success=False,
                message="",
                fault_string=f"Failed to parse SOAP response: {e}"
            )

    def execute_command(self, command: str) -> SOAPResponse:
        """
        Execute a GM command on the worldserver.

        Args:
            command: The GM command to execute (without leading dot)
                    Example: "server info", "account create test test"

        Returns:
            SOAPResponse with success status and message/error

        Raises:
            ConnectionError: If unable to connect to SOAP server
        """
        # Build SOAP request
        escaped_command = self._escape_xml(command)
        soap_body = self.SOAP_ENVELOPE.format(command=escaped_command)

        # Create request with headers
        request = Request(
            self._url,
            data=soap_body.encode("utf-8"),
            headers={
                "Content-Type": "application/soap+xml; charset=utf-8",
                "Authorization": self._get_auth_header(),
            },
            method="POST"
        )

        try:
            with urlopen(request, timeout=self.timeout) as response:
                return self._parse_response(response.read())

        except HTTPError as e:
            if e.code == 401:
                return SOAPResponse(
                    success=False,
                    message="",
                    fault_string="Authentication failed. Check username/password and account security level."
                )
            elif e.code == 403:
                return SOAPResponse(
                    success=False,
                    message="",
                    fault_string="Access denied. Account requires administrator privileges (SEC_ADMINISTRATOR)."
                )
            else:
                # Try to parse error response body
                try:
                    return self._parse_response(e.read())
                except Exception:
                    return SOAPResponse(
                        success=False,
                        message="",
                        fault_string=f"HTTP error {e.code}: {e.reason}"
                    )

        except URLError as e:
            raise ConnectionError(
                f"Failed to connect to SOAP server at {self._url}: {e.reason}"
            )

        except TimeoutError:
            raise ConnectionError(
                f"Connection to SOAP server at {self._url} timed out after {self.timeout}s"
            )

    def is_available(self) -> bool:
        """
        Check if the SOAP server is available.

        Returns:
            True if server responds, False otherwise
        """
        try:
            # Use a simple command to test connectivity
            response = self.execute_command("server info")
            return response.success
        except ConnectionError:
            return False


def create_soap_client_from_env() -> Optional[AzerothCoreSOAP]:
    """
    Create a SOAP client using environment variables.

    Environment variables:
        SOAP_HOST: SOAP server host (default: 127.0.0.1)
        SOAP_PORT: SOAP server port (default: 7878)
        SOAP_USERNAME: Account username
        SOAP_PASSWORD: Account password
        SOAP_TIMEOUT: Request timeout in seconds (default: 30)

    Returns:
        AzerothCoreSOAP client if credentials are configured, None otherwise
    """
    username = os.getenv("SOAP_USERNAME", "")
    password = os.getenv("SOAP_PASSWORD", "")

    if not username or not password:
        return None

    return AzerothCoreSOAP(
        host=os.getenv("SOAP_HOST", "127.0.0.1"),
        port=int(os.getenv("SOAP_PORT", "7878")),
        username=username,
        password=password,
        timeout=int(os.getenv("SOAP_TIMEOUT", "30")),
    )


# =============================================================================
# CLI for testing
# =============================================================================

if __name__ == "__main__":
    import sys

    print("AzerothCore SOAP Client Test")
    print("=" * 40)

    client = create_soap_client_from_env()

    if client is None:
        print("Error: SOAP credentials not configured.")
        print("Set SOAP_USERNAME and SOAP_PASSWORD environment variables.")
        print()
        print("Example:")
        print("  export SOAP_USERNAME=admin")
        print("  export SOAP_PASSWORD=admin_pass")
        print("  python soap_client.py")
        sys.exit(1)

    print(f"Connecting to {client.host}:{client.port}...")

    # Test with server info command
    command = "server info" if len(sys.argv) < 2 else " ".join(sys.argv[1:])
    print(f"Executing: {command}")
    print()

    try:
        response = client.execute_command(command)
        if response.success:
            print("Success!")
            print("-" * 40)
            print(response.message)
        else:
            print("Failed!")
            print("-" * 40)
            print(f"Error: {response.fault_string}")
            sys.exit(1)
    except ConnectionError as e:
        print(f"Connection Error: {e}")
        sys.exit(1)
