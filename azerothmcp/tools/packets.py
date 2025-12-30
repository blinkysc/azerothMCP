#!/usr/bin/env python3
"""WowPacketParser integration tools for targeted packet analysis."""

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from ..config import LOG_TOOL_CALLS

if LOG_TOOL_CALLS:
    from ..logging import tool_logger

# WowPacketParser configuration
WPP_PATH = Path(os.path.expanduser(os.getenv(
    "WPP_PATH",
    "~/WowPacketParser/WowPacketParser/bin/Release"
)))
DOTNET_PATH = os.getenv("DOTNET_PATH", os.path.expanduser("~/.dotnet/dotnet"))


def _parse_packet_header(line: str) -> Optional[dict]:
    """Parse a packet header line into structured data."""
    match = re.match(
        r'^(ServerToClient|ClientToServer): (\w+) \((0x[0-9A-Fa-f]+)\) '
        r'Length: (\d+) ConnIdx: (\d+) Time: ([\d/:. ]+) Number: (\d+)',
        line
    )
    if match:
        return {
            "direction": match.group(1),
            "opcode": match.group(2),
            "opcode_hex": match.group(3),
            "length": int(match.group(4)),
            "conn_idx": int(match.group(5)),
            "time": match.group(6).strip(),
            "number": int(match.group(7)),
        }
    return None


def _iter_packets(parsed_path: Path, opcode_filter: str = None, limit: int = None):
    """Iterate over packets in a parsed file, optionally filtering by opcode."""
    current_packet = None
    current_lines = []
    count = 0

    with open(parsed_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            header = _parse_packet_header(line)

            if header:
                if current_packet:
                    current_packet["content"] = "\n".join(current_lines).strip()
                    if opcode_filter is None or current_packet["opcode"] == opcode_filter:
                        yield current_packet
                        count += 1
                        if limit and count >= limit:
                            return

                current_packet = header
                current_lines = []
            elif current_packet:
                current_lines.append(line.rstrip())

    # Last packet
    if current_packet:
        current_packet["content"] = "\n".join(current_lines).strip()
        if opcode_filter is None or current_packet["opcode"] == opcode_filter:
            yield current_packet


def _packet_matches(packet: dict, opcode: str, entry_id: int,
                   content_search: str, range_start: int, range_end: int) -> bool:
    """Check if a packet matches the given filters."""
    if opcode and packet["opcode"] != opcode:
        return False
    if range_start is not None and packet["number"] < range_start:
        return False
    if range_end is not None and packet["number"] > range_end:
        return False
    if entry_id is not None:
        if f"Entry: {entry_id}" not in packet.get("content", ""):
            return False
    if content_search:
        if content_search.lower() not in packet.get("content", "").lower():
            return False
    return True


# ============================================================================
# Creature Response Parser
# ============================================================================
def _parse_creature_response(content: str) -> Optional[dict]:
    """Parse creature query response content into structured data."""
    creature = {}
    for line in content.split('\n'):
        line = line.strip()
        if line.startswith("Entry:"):
            creature["entry"] = int(line.split(":")[1].strip())
        elif "Name:" in line and "[0]" in line:
            creature["name"] = line.split("Name:")[1].strip()
        elif line.startswith("Title:"):
            title = line.split(":", 1)[1].strip()
            if title:
                creature["title"] = title
        elif line.startswith("CreatureType:"):
            match = re.search(r'(\d+) \((\w+)\)', line)
            if match:
                creature["type"] = {"id": int(match.group(1)), "name": match.group(2)}
        elif line.startswith("UnitClass:"):
            match = re.search(r'(\d+) \((\w+)\)', line)
            if match:
                creature["unit_class"] = {"id": int(match.group(1)), "name": match.group(2)}
        elif line.startswith("Classification:"):
            match = re.search(r'(\d+) \((\w+)\)', line)
            if match:
                creature["rank"] = {"id": int(match.group(1)), "name": match.group(2)}
        elif "CreatureDisplayID:" in line and "[0]" in line:
            creature["display_id"] = int(line.split(":")[1].strip())
        elif line.startswith("HpMulti:"):
            creature["hp_multi"] = float(line.split(":")[1].strip())
    return creature if creature.get("entry") else None


# ============================================================================
# Gameobject Response Parser
# ============================================================================
def _parse_gameobject_response(content: str) -> Optional[dict]:
    """Parse gameobject query response content."""
    go = {}
    for line in content.split('\n'):
        line = line.strip()
        if line.startswith("Entry:"):
            go["entry"] = int(line.split(":")[1].strip())
        elif "Name:" in line and "[0]" in line:
            go["name"] = line.split("Name:")[1].strip()
        elif line.startswith("Type:"):
            match = re.search(r'(\d+) \((\w+)\)', line)
            if match:
                go["type"] = {"id": int(match.group(1)), "name": match.group(2)}
        elif line.startswith("DisplayID:"):
            go["display_id"] = int(line.split(":")[1].strip())
        elif line.startswith("IconName:"):
            val = line.split(":", 1)[1].strip()
            if val:
                go["icon"] = val
    return go if go.get("entry") else None


# ============================================================================
# Quest Response Parser
# ============================================================================
def _parse_quest_response(content: str) -> Optional[dict]:
    """Parse quest info response content."""
    quest = {}
    for line in content.split('\n'):
        line = line.strip()
        if line.startswith("Quest ID:"):
            quest["id"] = int(line.split(":")[1].strip())
        elif line.startswith("QuestType:"):
            match = re.search(r'(\d+) \((\w+)\)', line)
            if match:
                quest["type"] = match.group(2)
        elif line.startswith("QuestLevel:"):
            quest["level"] = int(line.split(":")[1].strip())
        elif line.startswith("QuestMinLevel:"):
            quest["min_level"] = int(line.split(":")[1].strip())
        elif line.startswith("QuestSortID:"):
            quest["zone_or_sort"] = int(line.split(":")[1].strip())
        elif line.startswith("RewardMoney:"):
            quest["reward_money"] = int(line.split(":")[1].strip())
        elif line.startswith("RewardXPDifficulty:"):
            quest["reward_xp_difficulty"] = int(line.split(":")[1].strip())
        elif line.startswith("LogTitle:"):
            quest["title"] = line.split(":", 1)[1].strip()
        elif line.startswith("LogDescription:"):
            quest["description"] = line.split(":", 1)[1].strip()
    return quest if quest.get("id") else None


# ============================================================================
# Monster Move Parser (for waypoints)
# ============================================================================
def _parse_monster_move(content: str, header: dict) -> Optional[dict]:
    """Parse monster move packet for waypoint extraction."""
    move = {"packet_num": header["number"], "time": header["time"]}
    points = []

    for line in content.split('\n'):
        line = line.strip()
        if line.startswith("MoverGUID:"):
            match = re.search(r'Entry: (\d+)', line)
            if match:
                move["entry"] = int(match.group(1))
            match = re.search(r'Low: (\d+)', line)
            if match:
                move["guid_low"] = int(match.group(1))
        elif line.startswith("Position:"):
            match = re.search(r'X: ([-\d.]+) Y: ([-\d.]+) Z: ([-\d.]+)', line)
            if match:
                move["start_pos"] = {
                    "x": float(match.group(1)),
                    "y": float(match.group(2)),
                    "z": float(match.group(3))
                }
        elif "(MovementSpline) MoveTime:" in line:
            move["move_time"] = int(line.split(":")[1].strip())
        elif "(MovementSpline)" in line and "Points:" in line:
            match = re.search(r'X: ([-\d.]+) Y: ([-\d.]+) Z: ([-\d.]+)', line)
            if match:
                points.append({
                    "x": float(match.group(1)),
                    "y": float(match.group(2)),
                    "z": float(match.group(3))
                })

    if points:
        move["waypoints"] = points
    return move if move.get("entry") else None


# ============================================================================
# Chat Message Parser
# ============================================================================
def _parse_chat_message(content: str, header: dict) -> Optional[dict]:
    """Parse chat message packet."""
    chat = {"packet_num": header["number"], "time": header["time"]}

    for line in content.split('\n'):
        line = line.strip()
        if line.startswith("SlashCmd:"):
            match = re.search(r'(\d+) \((\w+)\)', line)
            if match:
                chat["type"] = match.group(2)
        elif line.startswith("SenderGUID:"):
            match = re.search(r'Entry: (\d+)', line)
            if match:
                chat["sender_entry"] = int(match.group(1))
        elif line.startswith("Sender Name:"):
            name = line.split(":", 1)[1].strip()
            if name:
                chat["sender_name"] = name
        elif line.startswith("Text:"):
            chat["text"] = line.split(":", 1)[1].strip()
        elif line.startswith("Language:"):
            match = re.search(r'(\d+) \((\w+)\)', line)
            if match:
                chat["language"] = match.group(2)

    return chat if chat.get("text") else None


# ============================================================================
# Spell Cast Parser
# ============================================================================
def _parse_spell_cast(content: str, header: dict) -> Optional[dict]:
    """Parse spell go/start packet."""
    spell = {"packet_num": header["number"], "time": header["time"]}

    for line in content.split('\n'):
        line = line.strip()
        if "(Cast) CasterGUID:" in line or "(Cast) CasterUnit:" in line:
            match = re.search(r'Entry: (\d+)', line)
            if match:
                spell["caster_entry"] = int(match.group(1))
            match = re.search(r'Low: (\d+)', line)
            if match:
                spell["caster_guid"] = int(match.group(1))
        elif "(Cast) SpellID:" in line:
            match = re.search(r'SpellID: (\d+)', line)
            if match:
                spell["spell_id"] = int(match.group(1))
        elif "(Cast) HitTargetsCount:" in line:
            spell["hit_count"] = int(line.split(":")[1].strip())
        elif "HitTarget:" in line:
            match = re.search(r'Entry: (\d+)', line)
            if match:
                if "hit_targets" not in spell:
                    spell["hit_targets"] = []
                spell["hit_targets"].append(int(match.group(1)))

    return spell if spell.get("spell_id") else None


# ============================================================================
# Emote Parser
# ============================================================================
def _parse_emote(content: str, header: dict) -> Optional[dict]:
    """Parse emote packet."""
    emote = {"packet_num": header["number"], "time": header["time"]}

    for line in content.split('\n'):
        line = line.strip()
        if line.startswith("SenderGUID:") or line.startswith("Guid:"):
            match = re.search(r'Entry: (\d+)', line)
            if match:
                emote["entry"] = int(match.group(1))
        elif line.startswith("EmoteID:"):
            match = re.search(r'(\d+)', line)
            if match:
                emote["emote_id"] = int(match.group(1))

    return emote if emote.get("emote_id") else None


def register_packet_tools(mcp):
    """Register packet analysis tools."""

    # ========================================================================
    # Core Navigation Tools
    # ========================================================================

    @mcp.tool()
    def list_packet_types(parsed_file: str, limit: int = 50) -> str:
        """List packet types (opcodes) in a parsed WPP output file with counts.

        Args:
            parsed_file: Path to parsed .txt file (e.g., ~/packet_parsed.txt)
            limit: Maximum number of different opcodes to return (default 50)
        """
        try:
            parsed_path = Path(parsed_file).expanduser()
            if not parsed_path.exists():
                return json.dumps({"error": f"File not found: {parsed_file}"})

            opcode_counts = {}
            with open(parsed_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if line.startswith(('ServerToClient:', 'ClientToServer:')):
                        header = _parse_packet_header(line)
                        if header:
                            opcode = header["opcode"]
                            opcode_counts[opcode] = opcode_counts.get(opcode, 0) + 1

            sorted_opcodes = sorted(opcode_counts.items(), key=lambda x: -x[1])[:limit]
            return json.dumps({
                "total_unique_opcodes": len(opcode_counts),
                "showing": len(sorted_opcodes),
                "opcodes": [{"name": name, "count": count} for name, count in sorted_opcodes],
                "_hint": "Use search_packets(opcode='OPCODE_NAME') to find specific packets"
            }, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    def search_packets(
        parsed_file: str,
        opcode: str = None,
        entry_id: int = None,
        content_search: str = None,
        packet_range: str = None,
        limit: int = 10
    ) -> str:
        """Search for packets in parsed WPP output with filters. Context-efficient.

        Args:
            parsed_file: Path to parsed .txt file
            opcode: Filter by opcode name (e.g., 'SMSG_QUERY_CREATURE_RESPONSE')
            entry_id: Search for packets containing 'Entry: {id}' in content
            content_search: Search for text in packet content (case-insensitive)
            packet_range: Packet number range 'start-end' (e.g., '400-500')
            limit: Maximum packets to return (default 10, max 50)
        """
        try:
            parsed_path = Path(parsed_file).expanduser()
            if not parsed_path.exists():
                return json.dumps({"error": f"File not found: {parsed_file}"})

            limit = min(limit, 50)
            range_start, range_end = None, None
            if packet_range:
                parts = packet_range.split('-')
                if len(parts) == 2:
                    range_start, range_end = int(parts[0]), int(parts[1])

            results = []
            for packet in _iter_packets(parsed_path):
                if _packet_matches(packet, opcode, entry_id, content_search, range_start, range_end):
                    results.append(packet)
                    if len(results) >= limit:
                        break

            return json.dumps({
                "count": len(results),
                "limit": limit,
                "filters": {"opcode": opcode, "entry_id": entry_id, "content_search": content_search, "packet_range": packet_range},
                "packets": results,
            }, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    def get_packet_by_number(parsed_file: str, packet_number: int) -> str:
        """Get a specific packet by its number from parsed WPP output.

        Args:
            parsed_file: Path to parsed .txt file
            packet_number: The packet number to retrieve
        """
        try:
            parsed_path = Path(parsed_file).expanduser()
            if not parsed_path.exists():
                return json.dumps({"error": f"File not found: {parsed_file}"})

            for packet in _iter_packets(parsed_path):
                if packet["number"] == packet_number:
                    return json.dumps(packet, indent=2)
                if packet["number"] > packet_number:
                    break

            return json.dumps({"error": f"Packet {packet_number} not found"})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    def get_packets_around(parsed_file: str, packet_number: int, context: int = 5) -> str:
        """Get packets around a specific packet number for context.

        Args:
            parsed_file: Path to parsed .txt file
            packet_number: Center packet number
            context: Number of packets before and after (default 5, max 20)
        """
        try:
            parsed_path = Path(parsed_file).expanduser()
            if not parsed_path.exists():
                return json.dumps({"error": f"File not found: {parsed_file}"})

            context = min(context, 20)
            start, end = max(0, packet_number - context), packet_number + context
            packets = []

            for packet in _iter_packets(parsed_path):
                if start <= packet["number"] <= end:
                    packets.append(packet)
                if packet["number"] > end:
                    break

            return json.dumps({"center": packet_number, "range": f"{start}-{end}", "count": len(packets), "packets": packets}, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

    # ========================================================================
    # Structured Extraction Tools
    # ========================================================================

    @mcp.tool()
    def extract_creature_queries(parsed_file: str, entry: int = None, limit: int = 20) -> str:
        """Extract creature query responses from parsed packets. Useful for getting creature data.

        Args:
            parsed_file: Path to parsed .txt file
            entry: Optional creature entry ID to filter
            limit: Maximum results (default 20)
        """
        try:
            parsed_path = Path(parsed_file).expanduser()
            if not parsed_path.exists():
                return json.dumps({"error": f"File not found: {parsed_file}"})

            creatures = []
            for packet in _iter_packets(parsed_path, "SMSG_QUERY_CREATURE_RESPONSE"):
                creature = _parse_creature_response(packet["content"])
                if creature and (entry is None or creature.get("entry") == entry):
                    creatures.append(creature)
                    if len(creatures) >= limit:
                        break

            return json.dumps({"count": len(creatures), "filter_entry": entry, "creatures": creatures}, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    def extract_gameobject_queries(parsed_file: str, entry: int = None, limit: int = 20) -> str:
        """Extract gameobject query responses from parsed packets.

        Args:
            parsed_file: Path to parsed .txt file
            entry: Optional GO entry ID to filter
            limit: Maximum results (default 20)
        """
        try:
            parsed_path = Path(parsed_file).expanduser()
            if not parsed_path.exists():
                return json.dumps({"error": f"File not found: {parsed_file}"})

            gameobjects = []
            for packet in _iter_packets(parsed_path, "SMSG_QUERY_GAMEOBJECT_RESPONSE"):
                go = _parse_gameobject_response(packet["content"])
                if go and (entry is None or go.get("entry") == entry):
                    gameobjects.append(go)
                    if len(gameobjects) >= limit:
                        break

            return json.dumps({"count": len(gameobjects), "filter_entry": entry, "gameobjects": gameobjects}, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    def extract_quest_queries(parsed_file: str, quest_id: int = None, limit: int = 20) -> str:
        """Extract quest info responses from parsed packets.

        Args:
            parsed_file: Path to parsed .txt file
            quest_id: Optional quest ID to filter
            limit: Maximum results (default 20)
        """
        try:
            parsed_path = Path(parsed_file).expanduser()
            if not parsed_path.exists():
                return json.dumps({"error": f"File not found: {parsed_file}"})

            quests = []
            for packet in _iter_packets(parsed_path, "SMSG_QUERY_QUEST_INFO_RESPONSE"):
                quest = _parse_quest_response(packet["content"])
                if quest and (quest_id is None or quest.get("id") == quest_id):
                    quests.append(quest)
                    if len(quests) >= limit:
                        break

            return json.dumps({"count": len(quests), "filter_quest_id": quest_id, "quests": quests}, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    def extract_monster_moves(parsed_file: str, entry: int = None, limit: int = 50) -> str:
        """Extract monster movement packets for waypoint analysis.

        Args:
            parsed_file: Path to parsed .txt file
            entry: Optional creature entry to filter
            limit: Maximum results (default 50)
        """
        try:
            parsed_path = Path(parsed_file).expanduser()
            if not parsed_path.exists():
                return json.dumps({"error": f"File not found: {parsed_file}"})

            moves = []
            for packet in _iter_packets(parsed_path, "SMSG_ON_MONSTER_MOVE"):
                move = _parse_monster_move(packet["content"], packet)
                if move and (entry is None or move.get("entry") == entry):
                    moves.append(move)
                    if len(moves) >= limit:
                        break

            return json.dumps({"count": len(moves), "filter_entry": entry, "moves": moves}, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    def extract_chat_messages(parsed_file: str, chat_type: str = None, sender_entry: int = None, limit: int = 50) -> str:
        """Extract chat messages (creature text, yells, says, etc.).

        Args:
            parsed_file: Path to parsed .txt file
            chat_type: Filter by type (MonsterSay, MonsterYell, MonsterEmote, etc.)
            sender_entry: Filter by sender creature entry
            limit: Maximum results (default 50)
        """
        try:
            parsed_path = Path(parsed_file).expanduser()
            if not parsed_path.exists():
                return json.dumps({"error": f"File not found: {parsed_file}"})

            messages = []
            for packet in _iter_packets(parsed_path, "SMSG_CHAT"):
                chat = _parse_chat_message(packet["content"], packet)
                if chat:
                    if chat_type and chat.get("type") != chat_type:
                        continue
                    if sender_entry and chat.get("sender_entry") != sender_entry:
                        continue
                    messages.append(chat)
                    if len(messages) >= limit:
                        break

            return json.dumps({"count": len(messages), "filters": {"chat_type": chat_type, "sender_entry": sender_entry}, "messages": messages}, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    def extract_spell_casts(parsed_file: str, spell_id: int = None, caster_entry: int = None, limit: int = 50) -> str:
        """Extract spell cast packets (SMSG_SPELL_GO).

        Args:
            parsed_file: Path to parsed .txt file
            spell_id: Filter by spell ID
            caster_entry: Filter by caster creature entry
            limit: Maximum results (default 50)
        """
        try:
            parsed_path = Path(parsed_file).expanduser()
            if not parsed_path.exists():
                return json.dumps({"error": f"File not found: {parsed_file}"})

            casts = []
            for packet in _iter_packets(parsed_path, "SMSG_SPELL_GO"):
                spell = _parse_spell_cast(packet["content"], packet)
                if spell:
                    if spell_id and spell.get("spell_id") != spell_id:
                        continue
                    if caster_entry and spell.get("caster_entry") != caster_entry:
                        continue
                    casts.append(spell)
                    if len(casts) >= limit:
                        break

            return json.dumps({"count": len(casts), "filters": {"spell_id": spell_id, "caster_entry": caster_entry}, "casts": casts}, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    def extract_emotes(parsed_file: str, entry: int = None, limit: int = 50) -> str:
        """Extract emote packets.

        Args:
            parsed_file: Path to parsed .txt file
            entry: Filter by creature entry
            limit: Maximum results (default 50)
        """
        try:
            parsed_path = Path(parsed_file).expanduser()
            if not parsed_path.exists():
                return json.dumps({"error": f"File not found: {parsed_file}"})

            emotes = []
            for packet in _iter_packets(parsed_path, "SMSG_EMOTE"):
                emote = _parse_emote(packet["content"], packet)
                if emote and (entry is None or emote.get("entry") == entry):
                    emotes.append(emote)
                    if len(emotes) >= limit:
                        break

            return json.dumps({"count": len(emotes), "filter_entry": entry, "emotes": emotes}, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

    # ========================================================================
    # Advanced Tools
    # ========================================================================

    @mcp.tool()
    def parse_pkt_targeted(
        pkt_file: str,
        opcode_filters: str = None,
        entry_filters: str = None,
        packet_limit: int = 1000,
        output_path: str = None
    ) -> str:
        """Parse a .pkt file with WowPacketParser using filters. Returns path to output.

        Args:
            pkt_file: Path to .pkt file
            opcode_filters: Comma-separated opcode names (e.g., 'SMSG_QUERY_CREATURE_RESPONSE,SMSG_CHAT')
            entry_filters: Entry filter in WPP format (e.g., 'Unit:5000:10000,GameObject:7000')
            packet_limit: Maximum packets to parse (default 1000)
            output_path: Custom output path (default: alongside .pkt file)
        """
        try:
            pkt_path = Path(pkt_file).expanduser()
            if not pkt_path.exists():
                return json.dumps({"error": f"PKT file not found: {pkt_file}"})

            wpp_dll = WPP_PATH / "WowPacketParser.dll"
            if not wpp_dll.exists():
                return json.dumps({"error": f"WowPacketParser not found at {WPP_PATH}"})

            config_content = f'''<?xml version="1.0" encoding="utf-8"?>
<configuration>
    <appSettings>
        <add key="Filters" value="{opcode_filters or ''}"/>
        <add key="EntryFilters" value="{entry_filters or ''}"/>
        <add key="FilterPacketsNum" value="{packet_limit}"/>
        <add key="DumpFormat" value="1"/>
        <add key="TargetedDatabase" value="2"/>
        <add key="ShowEndPrompt" value="false"/>
        <add key="Threads" value="1"/>
        <add key="DBEnabled" value="false"/>
    </appSettings>
</configuration>
'''

            with tempfile.NamedTemporaryFile(mode='w', suffix='.config', delete=False) as f:
                f.write(config_content)
                temp_config = f.name

            try:
                cmd = [DOTNET_PATH, str(wpp_dll), f"--ConfigFile={temp_config}", str(pkt_path)]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=str(WPP_PATH))

                # Find output file
                candidates = [pkt_path.with_suffix(".txt"), pkt_path.parent / f"{pkt_path.stem}_parsed.txt"]
                output_file = next((c for c in candidates if c.exists()), None)

                if output_file:
                    return json.dumps({
                        "success": True,
                        "output_file": str(output_file),
                        "filters_applied": {"opcodes": opcode_filters, "entries": entry_filters, "limit": packet_limit},
                        "_hint": f"Use search_packets('{output_file}') to explore results"
                    }, indent=2)
                else:
                    return json.dumps({"success": False, "error": "Output file not found", "stderr": result.stderr[-500:] if result.stderr else None})
            finally:
                os.unlink(temp_config)
        except subprocess.TimeoutExpired:
            return json.dumps({"error": "Parsing timed out after 5 minutes"})
        except Exception as e:
            return json.dumps({"error": str(e)})
