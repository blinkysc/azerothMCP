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
Database connection and query execution for AzerothCore MCP Server.
"""

import mysql.connector
from mysql.connector import Error

from .config import DB_CONFIG, DB_NAMES, READ_ONLY


def get_db_connection(database: str = "world"):
    """Create a database connection to specified AzerothCore database."""
    db_name = DB_NAMES.get(database, database)
    try:
        connection = mysql.connector.connect(
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            database=db_name,
        )
        return connection
    except Error as e:
        raise Exception(f"Failed to connect to database {db_name}: {e}")


def execute_query(query: str, database: str = "world", params: tuple = None) -> list[dict]:
    """Execute a SELECT query and return results as list of dicts."""
    query_upper = query.strip().upper()
    is_read_query = query_upper.startswith(("SELECT", "SHOW", "DESCRIBE"))

    if READ_ONLY and not is_read_query:
        raise ValueError("Only SELECT, SHOW, and DESCRIBE queries are allowed (read-only mode). Set READ_ONLY=false to enable write operations.")

    connection = get_db_connection(database)
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, params)

        if is_read_query:
            results = cursor.fetchall()
            return results
        else:
            connection.commit()
            return [{"affected_rows": cursor.rowcount, "last_insert_id": cursor.lastrowid}]
    finally:
        cursor.close()
        connection.close()
