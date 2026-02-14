#!/usr/bin/env python3
"""
Proc System Tools for AzerothCore MCP Server

Tools for working with the QAston proc system (spell_proc table).
"""

import json
from typing import Optional

from ..db import execute_query


def _load_proc_types():
    """Lazy load proc type reference data."""
    from ..data.proc_types import (
        PROC_FLAGS, PROC_SPELL_TYPES, PROC_SPELL_PHASES,
        PROC_HIT_FLAGS, PROC_ATTRIBUTES, SPELL_FAMILY_NAMES,
        SCHOOL_MASK, SPELL_PROC_SCHEMA,
        decode_proc_flags, decode_proc_hit, decode_proc_spell_type,
        decode_proc_spell_phase, decode_proc_attributes, decode_school_mask,
        get_spell_family_name
    )
    return {
        "PROC_FLAGS": PROC_FLAGS,
        "PROC_SPELL_TYPES": PROC_SPELL_TYPES,
        "PROC_SPELL_PHASES": PROC_SPELL_PHASES,
        "PROC_HIT_FLAGS": PROC_HIT_FLAGS,
        "PROC_ATTRIBUTES": PROC_ATTRIBUTES,
        "SPELL_FAMILY_NAMES": SPELL_FAMILY_NAMES,
        "SCHOOL_MASK": SCHOOL_MASK,
        "SPELL_PROC_SCHEMA": SPELL_PROC_SCHEMA,
        "decode_proc_flags": decode_proc_flags,
        "decode_proc_hit": decode_proc_hit,
        "decode_proc_spell_type": decode_proc_spell_type,
        "decode_proc_spell_phase": decode_proc_spell_phase,
        "decode_proc_attributes": decode_proc_attributes,
        "decode_school_mask": decode_school_mask,
        "get_spell_family_name": get_spell_family_name,
    }


def register_proc_tools(mcp):
    """Register proc-related tools with the MCP server."""

    @mcp.tool()
    def get_spell_proc(spell_id: int) -> str:
        """Get proc configuration for a spell from spell_proc table."""
        try:
            ref = _load_proc_types()

            result = execute_query(
                "SELECT * FROM spell_proc WHERE SpellId = %s",
                "world",
                (spell_id,)
            )

            if not result:
                # Check spell_proc_event (legacy table) as fallback
                legacy = execute_query(
                    "SELECT * FROM spell_proc_event WHERE entry = %s",
                    "world",
                    (spell_id,)
                )
                if legacy:
                    return json.dumps({
                        "message": f"Spell {spell_id} found in legacy spell_proc_event table (not spell_proc)",
                        "legacy_data": legacy[0],
                        "hint": "Consider migrating to spell_proc table for better control"
                    }, indent=2, default=str)

                return json.dumps({
                    "message": f"No proc configuration found for spell {spell_id}",
                    "hint": "Spell may use default DBC proc data or have no proc effect"
                })

            row = result[0]

            # Decode all bitmask fields
            enhanced = dict(row)
            enhanced["_decoded"] = {
                "ProcFlags": ref["decode_proc_flags"](row.get("ProcFlags", 0)),
                "SpellTypeMask": ref["decode_proc_spell_type"](row.get("SpellTypeMask", 0)),
                "SpellPhaseMask": ref["decode_proc_spell_phase"](row.get("SpellPhaseMask", 0)),
                "HitMask": ref["decode_proc_hit"](row.get("HitMask", 0)),
                "AttributesMask": ref["decode_proc_attributes"](row.get("AttributesMask", 0)),
                "SchoolMask": ref["decode_school_mask"](row.get("SchoolMask", 0)),
                "SpellFamilyName": ref["get_spell_family_name"](row.get("SpellFamilyName", 0)),
            }

            return json.dumps(enhanced, indent=2, default=str)

        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    def search_spell_procs(
        spell_family: Optional[int] = None,
        proc_flags: Optional[int] = None,
        has_ppm: bool = False,
        limit: int = 50
    ) -> str:
        """Search spell_proc entries by criteria."""
        try:
            ref = _load_proc_types()

            query_parts = ["SELECT * FROM spell_proc WHERE 1=1"]
            params = []

            if spell_family is not None:
                query_parts.append("AND SpellFamilyName = %s")
                params.append(spell_family)

            if proc_flags is not None:
                query_parts.append("AND (ProcFlags & %s) != 0")
                params.append(proc_flags)

            if has_ppm:
                query_parts.append("AND ProcsPerMinute > 0")

            query_parts.append(f"LIMIT {min(limit, 100)}")

            results = execute_query(" ".join(query_parts), "world", tuple(params))

            if not results:
                return json.dumps({"message": "No proc entries found matching criteria"})

            # Compact results with family names
            compact = []
            for row in results:
                compact.append({
                    "SpellId": row.get("SpellId"),
                    "SpellFamily": ref["get_spell_family_name"](row.get("SpellFamilyName", 0)),
                    "ProcFlags": hex(row.get("ProcFlags", 0)),
                    "Chance": row.get("Chance"),
                    "PPM": row.get("ProcsPerMinute"),
                    "Cooldown": row.get("Cooldown"),
                    "Charges": row.get("Charges"),
                })

            return json.dumps({
                "count": len(compact),
                "procs": compact
            }, indent=2, default=str)

        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    def explain_proc_flags(
        proc_flags: Optional[int] = None,
        hit_mask: Optional[int] = None,
        spell_type_mask: Optional[int] = None,
        spell_phase_mask: Optional[int] = None,
        attributes_mask: Optional[int] = None
    ) -> str:
        """Decode and explain proc bitmask values."""
        ref = _load_proc_types()
        result = {}

        if proc_flags is not None:
            result["ProcFlags"] = {
                "value": hex(proc_flags),
                "decoded": ref["decode_proc_flags"](proc_flags)
            }

        if hit_mask is not None:
            result["HitMask"] = {
                "value": hex(hit_mask),
                "decoded": ref["decode_proc_hit"](hit_mask)
            }

        if spell_type_mask is not None:
            result["SpellTypeMask"] = {
                "value": hex(spell_type_mask),
                "decoded": ref["decode_proc_spell_type"](spell_type_mask)
            }

        if spell_phase_mask is not None:
            result["SpellPhaseMask"] = {
                "value": hex(spell_phase_mask),
                "decoded": ref["decode_proc_spell_phase"](spell_phase_mask)
            }

        if attributes_mask is not None:
            result["AttributesMask"] = {
                "value": hex(attributes_mask),
                "decoded": ref["decode_proc_attributes"](attributes_mask)
            }

        if not result:
            # Return summary of all flag types
            result = {
                "usage": "Pass a bitmask value to decode. Examples:",
                "examples": {
                    "proc_flags": "explain_proc_flags(proc_flags=0x00000014) - melee attacks",
                    "hit_mask": "explain_proc_flags(hit_mask=0x00000003) - normal or crit",
                    "spell_type_mask": "explain_proc_flags(spell_type_mask=0x00000001) - damage spells",
                },
                "common_proc_flags": {
                    "0x00000004": "DONE_MELEE_AUTO_ATTACK",
                    "0x00000010": "DONE_SPELL_MELEE_DMG_CLASS",
                    "0x00000014": "Any melee attack done",
                    "0x00010000": "DONE_SPELL_MAGIC_DMG_CLASS_NEG",
                    "0x00040000": "DONE_PERIODIC",
                },
                "common_hit_masks": {
                    "0x00000001": "NORMAL hit only",
                    "0x00000002": "CRITICAL hit only",
                    "0x00000003": "Normal OR Critical",
                },
            }

        return json.dumps(result, indent=2)

    @mcp.tool()
    def list_proc_flag_types() -> str:
        """List all available proc flag types and their meanings."""
        ref = _load_proc_types()

        return json.dumps({
            "ProcFlags": [
                {"value": hex(k), **v}
                for k, v in sorted(ref["PROC_FLAGS"].items())
            ],
            "SpellTypeMask": [
                {"value": hex(k), **v}
                for k, v in sorted(ref["PROC_SPELL_TYPES"].items())
            ],
            "SpellPhaseMask": [
                {"value": hex(k), **v}
                for k, v in sorted(ref["PROC_SPELL_PHASES"].items())
            ],
            "HitMask": [
                {"value": hex(k), **v}
                for k, v in sorted(ref["PROC_HIT_FLAGS"].items())
            ],
            "AttributesMask": [
                {"value": hex(k), **v}
                for k, v in sorted(ref["PROC_ATTRIBUTES"].items())
            ],
            "SpellFamilyNames": [
                {"id": k, **v}
                for k, v in sorted(ref["SPELL_FAMILY_NAMES"].items())
            ],
        }, indent=2)

    @mcp.tool()
    def diagnose_spell_proc(spell_id: int) -> str:
        """Diagnose potential issues with a spell's proc configuration."""
        try:
            ref = _load_proc_types()

            issues = []
            info = {}

            # Check spell_proc
            proc = execute_query(
                "SELECT * FROM spell_proc WHERE SpellId = %s",
                "world",
                (spell_id,)
            )

            # Check legacy spell_proc_event
            legacy = execute_query(
                "SELECT * FROM spell_proc_event WHERE entry = %s",
                "world",
                (spell_id,)
            )

            if proc and legacy:
                issues.append({
                    "severity": "WARNING",
                    "issue": "Spell exists in BOTH spell_proc AND spell_proc_event tables",
                    "fix_hint": "spell_proc takes precedence. Remove from spell_proc_event if migrated."
                })

            if not proc and not legacy:
                issues.append({
                    "severity": "INFO",
                    "issue": "No proc configuration found in database",
                    "fix_hint": "Spell uses default DBC data. Add to spell_proc for custom behavior."
                })
                return json.dumps({
                    "spell_id": spell_id,
                    "has_proc_config": False,
                    "issues": issues
                }, indent=2)

            config = proc[0] if proc else None
            info["source"] = "spell_proc" if proc else "spell_proc_event (legacy)"

            if config:
                # Check for common configuration issues
                proc_flags = config.get("ProcFlags", 0)
                chance = config.get("Chance", 0)
                ppm = config.get("ProcsPerMinute", 0)
                cooldown = config.get("Cooldown", 0)
                charges = config.get("Charges", 0)

                if proc_flags == 0:
                    issues.append({
                        "severity": "WARNING",
                        "issue": "ProcFlags is 0 - proc will use DBC default flags",
                        "fix_hint": "Set explicit ProcFlags for better control"
                    })

                if chance == 0 and ppm == 0:
                    issues.append({
                        "severity": "INFO",
                        "issue": "Both Chance and ProcsPerMinute are 0",
                        "fix_hint": "Uses DBC chance. Set Chance (0-100) or PPM for custom rate."
                    })

                if chance > 100:
                    issues.append({
                        "severity": "ERROR",
                        "issue": f"Chance ({chance}) exceeds 100%",
                        "fix_hint": "Chance should be 0-100"
                    })

                if ppm > 0 and chance > 0:
                    issues.append({
                        "severity": "WARNING",
                        "issue": "Both PPM and Chance are set",
                        "fix_hint": "PPM takes precedence - Chance is ignored when PPM > 0"
                    })

                if cooldown < 0:
                    issues.append({
                        "severity": "ERROR",
                        "issue": f"Cooldown ({cooldown}) is negative",
                        "fix_hint": "Cooldown should be >= 0 milliseconds"
                    })

                # Check SpellFamilyMask usage
                sfm0 = config.get("SpellFamilyMask0", 0)
                sfm1 = config.get("SpellFamilyMask1", 0)
                sfm2 = config.get("SpellFamilyMask2", 0)
                sfn = config.get("SpellFamilyName", 0)

                if (sfm0 or sfm1 or sfm2) and sfn == 0:
                    issues.append({
                        "severity": "WARNING",
                        "issue": "SpellFamilyMask set but SpellFamilyName is 0 (GENERIC)",
                        "fix_hint": "SpellFamilyMask usually needs matching SpellFamilyName"
                    })

                info["config"] = {
                    "ProcFlags": hex(proc_flags),
                    "ProcFlags_decoded": ref["decode_proc_flags"](proc_flags),
                    "Chance": chance,
                    "ProcsPerMinute": ppm,
                    "Cooldown_ms": cooldown,
                    "Charges": charges,
                    "SpellFamily": ref["get_spell_family_name"](sfn),
                }

            return json.dumps({
                "spell_id": spell_id,
                "has_proc_config": True,
                "info": info,
                "total_issues": len(issues),
                "issues": issues
            }, indent=2, default=str)

        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    def get_spell_proc_schema() -> str:
        """Get the spell_proc table schema with field documentation."""
        ref = _load_proc_types()

        return json.dumps({
            "table": "spell_proc",
            "description": "QAston proc system configuration table (ported from TrinityCore)",
            "fields": ref["SPELL_PROC_SCHEMA"],
            "related_tables": {
                "spell_proc_event": "Legacy proc table (spell_proc takes precedence)",
                "spell_enchant_proc_data": "Enchantment proc configuration"
            },
            "usage_example": {
                "description": "Example: Configure Killing Machine to proc on melee crits",
                "SpellId": 51124,
                "SchoolMask": 0,
                "SpellFamilyName": 15,
                "SpellFamilyMask0": 0,
                "SpellFamilyMask1": 0,
                "SpellFamilyMask2": 0,
                "ProcFlags": "0x00000004",
                "SpellTypeMask": 1,
                "SpellPhaseMask": 2,
                "HitMask": 2,
                "AttributesMask": 0,
                "ProcsPerMinute": 0,
                "Chance": 0,
                "Cooldown": 0,
                "Charges": 0,
            }
        }, indent=2)

    @mcp.tool()
    def compare_proc_tables(spell_id: int) -> str:
        """Compare spell_proc and spell_proc_event entries for a spell."""
        try:
            ref = _load_proc_types()

            proc = execute_query(
                "SELECT * FROM spell_proc WHERE SpellId = %s",
                "world",
                (spell_id,)
            )

            legacy = execute_query(
                "SELECT * FROM spell_proc_event WHERE entry = %s",
                "world",
                (spell_id,)
            )

            result = {"spell_id": spell_id}

            if proc:
                row = proc[0]
                result["spell_proc"] = {
                    "exists": True,
                    "ProcFlags": hex(row.get("ProcFlags", 0)),
                    "SpellTypeMask": hex(row.get("SpellTypeMask", 0)),
                    "SpellPhaseMask": hex(row.get("SpellPhaseMask", 0)),
                    "HitMask": hex(row.get("HitMask", 0)),
                    "Chance": row.get("Chance"),
                    "PPM": row.get("ProcsPerMinute"),
                    "Cooldown": row.get("Cooldown"),
                }
            else:
                result["spell_proc"] = {"exists": False}

            if legacy:
                row = legacy[0]
                result["spell_proc_event"] = {
                    "exists": True,
                    "procFlags": hex(row.get("procFlags", 0)),
                    "procEx": hex(row.get("procEx", 0)),
                    "procPhase": hex(row.get("procPhase", 0)),
                    "CustomChance": row.get("CustomChance"),
                    "ppmRate": row.get("ppmRate"),
                    "Cooldown": row.get("Cooldown"),
                }
            else:
                result["spell_proc_event"] = {"exists": False}

            if proc and legacy:
                result["active_table"] = "spell_proc (takes precedence)"
                result["recommendation"] = "Consider removing spell_proc_event entry"
            elif proc:
                result["active_table"] = "spell_proc"
            elif legacy:
                result["active_table"] = "spell_proc_event (legacy)"
                result["recommendation"] = "Consider migrating to spell_proc for better control"
            else:
                result["active_table"] = "None (using DBC defaults)"

            return json.dumps(result, indent=2, default=str)

        except Exception as e:
            return json.dumps({"error": str(e)})
