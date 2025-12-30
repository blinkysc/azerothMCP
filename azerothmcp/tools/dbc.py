#!/usr/bin/env python3
"""
DBC Tools for AzerothCore MCP Server

Tools for querying Spell.dbc and other DBC files.
"""

import json
from typing import Optional

from ..dbc_parser import get_spell_dbc, lookup_spell, get_spell_name_from_dbc
from ..data.proc_types import (
    decode_proc_flags, decode_school_mask, get_spell_family_name,
    SPELL_FAMILY_NAMES
)


def register_dbc_tools(mcp):
    """Register DBC-related tools with the MCP server."""

    @mcp.tool()
    def get_spell_from_dbc(spell_id: int) -> str:
        """Get spell data from Spell.dbc file."""
        try:
            spell = lookup_spell(spell_id)
            if not spell:
                return json.dumps({
                    "error": f"Spell {spell_id} not found in Spell.dbc"
                })

            # Add decoded proc flags
            proc_flags = int(spell.get("ProcFlags", "0x0"), 16) if isinstance(spell.get("ProcFlags"), str) else spell.get("ProcFlags", 0)
            spell["_decoded_ProcFlags"] = decode_proc_flags(proc_flags)

            # Add decoded school mask
            school = spell.get("SchoolMask", 0)
            spell["_decoded_SchoolMask"] = decode_school_mask(school)

            # Add spell family name
            family = spell.get("SpellFamilyName", 0)
            spell["_SpellFamilyNameStr"] = get_spell_family_name(family)

            return json.dumps(spell, indent=2, default=str)

        except FileNotFoundError:
            return json.dumps({
                "error": "Spell.dbc file not found",
                "hint": "Expected at ~/azerothcore/data/dbc/Spell.dbc"
            })
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    def search_spells_dbc(
        name: Optional[str] = None,
        spell_family: Optional[int] = None,
        has_proc_flags: bool = False,
        limit: int = 50
    ) -> str:
        """Search Spell.dbc by name, family, or proc configuration."""
        try:
            dbc = get_spell_dbc()

            results = []

            if name:
                results = dbc.search_by_name(name, limit)
            elif spell_family is not None:
                results = dbc.search_by_family(spell_family, limit)
            elif has_proc_flags:
                # Search for spells with non-zero ProcFlags
                for spell in dbc.records.values():
                    if spell.get("ProcFlags", 0) != 0:
                        results.append(dbc._format_spell(spell))
                        if len(results) >= limit:
                            break
            else:
                return json.dumps({
                    "error": "Provide at least one search parameter",
                    "usage": {
                        "name": "Search by spell name (partial match)",
                        "spell_family": "Search by SpellFamilyName (3=Mage, 4=Warrior, etc.)",
                        "has_proc_flags": "Find spells with proc configuration"
                    },
                    "spell_families": {
                        k: v["name"] for k, v in SPELL_FAMILY_NAMES.items()
                    }
                })

            # Compact results
            compact = []
            for spell in results:
                compact.append({
                    "Id": spell["Id"],
                    "Name": spell["Name"],
                    "Rank": spell.get("Rank", ""),
                    "Family": get_spell_family_name(spell.get("SpellFamilyName", 0)),
                    "ProcFlags": spell.get("ProcFlags", "0x0"),
                    "ProcChance": spell.get("ProcChance", 0),
                })

            return json.dumps({
                "count": len(compact),
                "spells": compact
            }, indent=2)

        except FileNotFoundError:
            return json.dumps({
                "error": "Spell.dbc file not found",
                "hint": "Expected at ~/azerothcore/data/dbc/Spell.dbc"
            })
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    def get_spell_dbc_proc_info(spell_id: int) -> str:
        """Get proc-related data from Spell.dbc for a spell."""
        try:
            dbc = get_spell_dbc()
            proc_info = dbc.get_proc_info(spell_id)

            if not proc_info:
                return json.dumps({
                    "error": f"Spell {spell_id} not found in Spell.dbc"
                })

            # Decode the proc flags
            proc_flags_val = int(proc_info["ProcFlags"], 16)
            proc_info["_decoded_ProcFlags"] = decode_proc_flags(proc_flags_val)
            proc_info["_SpellFamilyNameStr"] = get_spell_family_name(proc_info.get("SpellFamilyName", 0))

            return json.dumps(proc_info, indent=2)

        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    def get_spell_name_dbc(spell_id: int) -> str:
        """Get just the spell name from Spell.dbc."""
        try:
            name = get_spell_name_from_dbc(spell_id)
            return json.dumps({
                "spell_id": spell_id,
                "name": name
            })
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    def batch_lookup_spell_names_dbc(spell_ids: str) -> str:
        """Batch lookup spell names from Spell.dbc (comma-separated IDs)."""
        try:
            ids = [int(x.strip()) for x in spell_ids.split(",") if x.strip().isdigit()]

            if not ids:
                return json.dumps({"error": "No valid spell IDs provided"})

            results = {}
            for spell_id in ids[:100]:  # Limit to 100
                results[spell_id] = get_spell_name_from_dbc(spell_id)

            return json.dumps(results, indent=2)

        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    def compare_spell_dbc_vs_proc(spell_id: int) -> str:
        """Compare DBC proc data with spell_proc table configuration."""
        try:
            from ..db import execute_query

            # Get DBC data
            dbc = get_spell_dbc()
            dbc_spell = dbc.get(spell_id)

            # Get spell_proc data
            proc_data = execute_query(
                "SELECT * FROM spell_proc WHERE SpellId = %s",
                "world",
                (spell_id,)
            )

            result = {
                "spell_id": spell_id,
                "name": dbc_spell.get("SpellName_enUS", "Unknown") if dbc_spell else "Not in DBC"
            }

            if dbc_spell:
                result["dbc"] = {
                    "ProcFlags": hex(dbc_spell.get("ProcFlags", 0)),
                    "ProcChance": dbc_spell.get("ProcChance", 0),
                    "ProcCharges": dbc_spell.get("ProcCharges", 0),
                    "SpellFamilyName": dbc_spell.get("SpellFamilyName", 0),
                    "SpellFamilyFlags": [
                        hex(dbc_spell.get("SpellFamilyFlags0", 0)),
                        hex(dbc_spell.get("SpellFamilyFlags1", 0)),
                        hex(dbc_spell.get("SpellFamilyFlags2", 0)),
                    ],
                }
            else:
                result["dbc"] = None

            if proc_data:
                row = proc_data[0]
                result["spell_proc"] = {
                    "ProcFlags": hex(row.get("ProcFlags", 0)),
                    "Chance": row.get("Chance", 0),
                    "ProcsPerMinute": row.get("ProcsPerMinute", 0),
                    "Charges": row.get("Charges", 0),
                    "Cooldown": row.get("Cooldown", 0),
                    "SpellFamilyName": row.get("SpellFamilyName", 0),
                    "SpellFamilyMask": [
                        hex(row.get("SpellFamilyMask0", 0)),
                        hex(row.get("SpellFamilyMask1", 0)),
                        hex(row.get("SpellFamilyMask2", 0)),
                    ],
                    "SpellTypeMask": hex(row.get("SpellTypeMask", 0)),
                    "SpellPhaseMask": hex(row.get("SpellPhaseMask", 0)),
                    "HitMask": hex(row.get("HitMask", 0)),
                    "AttributesMask": hex(row.get("AttributesMask", 0)),
                }
                result["using"] = "spell_proc (overrides DBC)"
            else:
                result["spell_proc"] = None
                result["using"] = "DBC defaults"

            # Highlight differences
            if dbc_spell and proc_data:
                dbc_flags = dbc_spell.get("ProcFlags", 0)
                proc_flags = proc_data[0].get("ProcFlags", 0)
                if proc_flags != 0 and dbc_flags != proc_flags:
                    result["_note"] = "spell_proc ProcFlags differ from DBC - spell_proc values are used"

            return json.dumps(result, indent=2, default=str)

        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    def get_dbc_stats() -> str:
        """Get statistics about the loaded Spell.dbc."""
        try:
            dbc = get_spell_dbc()

            # Count spells by family
            family_counts = {}
            proc_count = 0
            for spell in dbc.records.values():
                family = spell.get("SpellFamilyName", 0)
                family_name = get_spell_family_name(family)
                family_counts[family_name] = family_counts.get(family_name, 0) + 1

                if spell.get("ProcFlags", 0) != 0:
                    proc_count += 1

            return json.dumps({
                "file": dbc.filepath,
                "total_spells": len(dbc.records),
                "spells_with_proc_flags": proc_count,
                "spells_by_family": dict(sorted(family_counts.items(), key=lambda x: -x[1])),
            }, indent=2)

        except Exception as e:
            return json.dumps({"error": str(e)})
