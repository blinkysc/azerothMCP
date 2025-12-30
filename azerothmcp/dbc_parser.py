#!/usr/bin/env python3
"""
DBC File Parser for AzerothCore

Parses WoW 3.3.5a DBC (DataBase Client) files.
Format: WDBC header + records + string block
"""

import struct
import os
from typing import Dict, List, Optional, Any, Tuple
from functools import lru_cache

from .config import DBC_PATH

# Default DBC path from config
DEFAULT_DBC_PATH = str(DBC_PATH)


class DBCHeader:
    """DBC file header structure."""
    HEADER_SIZE = 20
    MAGIC = b'WDBC'

    def __init__(self, data: bytes):
        if len(data) < self.HEADER_SIZE:
            raise ValueError("Invalid DBC header: too short")

        magic = data[:4]
        if magic != self.MAGIC:
            raise ValueError(f"Invalid DBC magic: {magic}, expected {self.MAGIC}")

        self.record_count, self.field_count, self.record_size, self.string_block_size = \
            struct.unpack('<4I', data[4:20])


class DBCFile:
    """Generic DBC file parser."""

    def __init__(self, filepath: str, format_string: str):
        self.filepath = filepath
        self.format_string = format_string
        self.header: Optional[DBCHeader] = None
        self.records: Dict[int, Dict[str, Any]] = {}
        self.string_block: bytes = b''
        self._loaded = False

    def load(self) -> None:
        """Load and parse the DBC file."""
        if self._loaded:
            return

        with open(self.filepath, 'rb') as f:
            header_data = f.read(DBCHeader.HEADER_SIZE)
            self.header = DBCHeader(header_data)

            # Read all records
            record_data = f.read(self.header.record_count * self.header.record_size)

            # Read string block
            self.string_block = f.read(self.header.string_block_size)

        # Parse records
        self._parse_records(record_data)
        self._loaded = True

    def _parse_records(self, data: bytes) -> None:
        """Parse all records from raw data."""
        offset = 0
        for i in range(self.header.record_count):
            record_data = data[offset:offset + self.header.record_size]
            record = self._parse_record(record_data)
            if record and 'Id' in record:
                self.records[record['Id']] = record
            offset += self.header.record_size

    def _parse_record(self, data: bytes) -> Optional[Dict[str, Any]]:
        """Parse a single record based on format string."""
        raise NotImplementedError("Subclass must implement _parse_record")

    def _read_string(self, offset: int) -> str:
        """Read a null-terminated string from the string block."""
        if offset == 0 or offset >= len(self.string_block):
            return ""
        end = self.string_block.find(b'\x00', offset)
        if end == -1:
            end = len(self.string_block)
        return self.string_block[offset:end].decode('utf-8', errors='replace')

    def get(self, record_id: int) -> Optional[Dict[str, Any]]:
        """Get a record by ID."""
        if not self._loaded:
            self.load()
        return self.records.get(record_id)

    def search(self, **kwargs) -> List[Dict[str, Any]]:
        """Search records by field values."""
        if not self._loaded:
            self.load()

        results = []
        for record in self.records.values():
            match = True
            for key, value in kwargs.items():
                if key not in record:
                    match = False
                    break
                if isinstance(value, str) and isinstance(record[key], str):
                    if value.lower() not in record[key].lower():
                        match = False
                        break
                elif record[key] != value:
                    match = False
                    break
            if match:
                results.append(record)
        return results


class SpellDBC(DBCFile):
    """Spell.dbc parser for WoW 3.3.5a."""

    # Format: n=uint32, i=int32, f=float, x=skip, s=string
    FORMAT = "niiiiiiiiiiiixixiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiifxiiiiiiiiiiiiiiiiiiiiiiiiiiiifffiiiiiiiiiiiiiiiiiiiiifffiiiiiiiiiiiiiiifffiiiiiiiiiiiiiissssssssssssssssxssssssssssssssssxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxiiiiiiiiiiixfffxxxiiiiixxfffxx"

    # Complete field names for all 234 format positions (matching format string exactly)
    FIELD_NAMES = [
        # 0-11: ID and Attributes
        "Id", "Category", "Dispel", "Mechanic",
        "Attributes", "AttributesEx", "AttributesEx2", "AttributesEx3",
        "AttributesEx4", "AttributesEx5", "AttributesEx6", "AttributesEx7",
        # 12-15: Stances (with 2 skips for uint64 padding)
        "Stances", None, "StancesNot", None,
        # 16-27: Targeting and Aura requirements
        "Targets", "TargetCreatureType", "RequiresSpellFocus", "FacingCasterFlags",
        "CasterAuraState", "TargetAuraState", "CasterAuraStateNot", "TargetAuraStateNot",
        "CasterAuraSpell", "TargetAuraSpell", "ExcludeCasterAuraSpell", "ExcludeTargetAuraSpell",
        # 28-36: Timing and proc
        "CastingTimeIndex", "RecoveryTime", "CategoryRecoveryTime", "InterruptFlags",
        "AuraInterruptFlags", "ChannelInterruptFlags", "ProcFlags", "ProcChance",
        "ProcCharges",
        # 37-48: Levels and resources
        "MaxLevel", "BaseLevel", "SpellLevel",
        "DurationIndex", "PowerType", "ManaCost", "ManaCostPerlevel",
        "ManaPerSecond", "ManaPerSecondPerLevel", "RangeIndex", "Speed",
        None,  # 48: ModalNextSpell (skipped)
        # 49-51: Stack and Totems
        "StackAmount", "Totem0", "Totem1",
        # 52-67: Reagents (8 items + 8 counts)
        "Reagent0", "Reagent1", "Reagent2", "Reagent3",
        "Reagent4", "Reagent5", "Reagent6", "Reagent7",
        "ReagentCount0", "ReagentCount1", "ReagentCount2", "ReagentCount3",
        "ReagentCount4", "ReagentCount5", "ReagentCount6", "ReagentCount7",
        # 68-70: Equipped item requirements
        "EquippedItemClass", "EquippedItemSubClassMask", "EquippedItemInventoryTypeMask",
        # 71-73: Effects
        "Effect0", "Effect1", "Effect2",
        # 74-76: Effect die sides
        "EffectDieSides0", "EffectDieSides1", "EffectDieSides2",
        # 77-79: Effect points per level (float)
        "EffectRealPointsPerLevel0", "EffectRealPointsPerLevel1", "EffectRealPointsPerLevel2",
        # 80-82: Effect base points
        "EffectBasePoints0", "EffectBasePoints1", "EffectBasePoints2",
        # 83-85: Effect mechanics
        "EffectMechanic0", "EffectMechanic1", "EffectMechanic2",
        # 86-91: Effect targets
        "EffectImplicitTargetA0", "EffectImplicitTargetA1", "EffectImplicitTargetA2",
        "EffectImplicitTargetB0", "EffectImplicitTargetB1", "EffectImplicitTargetB2",
        # 92-94: Effect radius
        "EffectRadiusIndex0", "EffectRadiusIndex1", "EffectRadiusIndex2",
        # 95-97: Effect aura
        "EffectApplyAuraName0", "EffectApplyAuraName1", "EffectApplyAuraName2",
        # 98-100: Effect amplitude
        "EffectAmplitude0", "EffectAmplitude1", "EffectAmplitude2",
        # 101-103: Effect value multiplier (float)
        "EffectValueMultiplier0", "EffectValueMultiplier1", "EffectValueMultiplier2",
        # 104-106: Chain targets
        "EffectChainTarget0", "EffectChainTarget1", "EffectChainTarget2",
        # 107-109: Item type
        "EffectItemType0", "EffectItemType1", "EffectItemType2",
        # 110-115: Misc values
        "EffectMiscValue0", "EffectMiscValue1", "EffectMiscValue2",
        "EffectMiscValueB0", "EffectMiscValueB1", "EffectMiscValueB2",
        # 116-118: Trigger spells
        "EffectTriggerSpell0", "EffectTriggerSpell1", "EffectTriggerSpell2",
        # 119-121: Points per combo (float)
        "EffectPointsPerComboPoint0", "EffectPointsPerComboPoint1", "EffectPointsPerComboPoint2",
        # 122-130: EffectSpellClassMask (9 fields: 3 effects * 3 mask parts)
        "EffectSpellClassMask0_0", "EffectSpellClassMask0_1", "EffectSpellClassMask0_2",
        "EffectSpellClassMask1_0", "EffectSpellClassMask1_1", "EffectSpellClassMask1_2",
        "EffectSpellClassMask2_0", "EffectSpellClassMask2_1", "EffectSpellClassMask2_2",
        # 131-135: Visual and icon
        "SpellVisual0", "SpellVisual1", "SpellIconID", "ActiveIconID", "SpellPriority",
        # 136-151: SpellName (16 locales) - strings
        "SpellName_enUS", "SpellName_koKR", "SpellName_frFR", "SpellName_deDE",
        "SpellName_enCN", "SpellName_enTW", "SpellName_esES", "SpellName_esMX",
        "SpellName_ruRU", "SpellName_unused1", "SpellName_ptBR", "SpellName_itIT",
        "SpellName_unused2", "SpellName_unused3", "SpellName_unused4", "SpellName_unused5",
        # 152: SpellNameFlag (skipped)
        None,
        # 153-168: Rank (16 locales) - strings
        "Rank_enUS", "Rank_koKR", "Rank_frFR", "Rank_deDE",
        "Rank_enCN", "Rank_enTW", "Rank_esES", "Rank_esMX",
        "Rank_ruRU", "Rank_unused1", "Rank_ptBR", "Rank_itIT",
        "Rank_unused2", "Rank_unused3", "Rank_unused4", "Rank_unused5",
        # 169-203: Skipped fields (RankFlags, Description[16], DescriptionFlags, ToolTip[16], ToolTipFlags)
        # 35 x's in format string
        None, None, None, None, None, None, None, None, None, None,
        None, None, None, None, None, None, None, None, None, None,
        None, None, None, None, None, None, None, None, None, None,
        None, None, None, None, None,
        # 204-207: Post-skip fields
        "ManaCostPercentage", "StartRecoveryCategory", "StartRecoveryTime", "MaxTargetLevel",
        # 208-210: SpellFamily
        "SpellFamilyName", "SpellFamilyFlags0", "SpellFamilyFlags1", "SpellFamilyFlags2",
        # 212-214: Targets and prevention
        "MaxAffectedTargets", "DmgClass", "PreventionType",
        # 215: StanceBarOrder (skipped)
        None,
        # 216-218: Effect damage multiplier (float)
        "EffectDamageMultiplier0", "EffectDamageMultiplier1", "EffectDamageMultiplier2",
        # 219-221: Skipped (MinFactionId, MinReputation, RequiredAuraVision)
        None, None, None,
        # 222-223: Totem categories
        "TotemCategory0", "TotemCategory1",
        # 224-226: Area, School, Rune
        "AreaGroupId", "SchoolMask", "RuneCostID",
        # 227-228: Skipped (SpellMissileID, PowerDisplayId)
        None, None,
        # 229-231: Effect bonus multiplier (float)
        "EffectBonusMultiplier0", "EffectBonusMultiplier1", "EffectBonusMultiplier2",
        # 232-233: Skipped (SpellDescriptionVariableID, SpellDifficultyId)
        None, None,
    ]

    def __init__(self, filepath: str = None):
        if filepath is None:
            filepath = os.path.join(DEFAULT_DBC_PATH, "Spell.dbc")
        super().__init__(filepath, self.FORMAT)

    def _parse_record(self, data: bytes) -> Optional[Dict[str, Any]]:
        """Parse a spell record."""
        record = {}
        offset = 0
        field_idx = 0

        for char in self.FORMAT:
            if field_idx < len(self.FIELD_NAMES):
                field_name = self.FIELD_NAMES[field_idx]
            else:
                field_name = None

            if char == 'n':  # uint32 (ID)
                value = struct.unpack_from('<I', data, offset)[0]
                if field_name:
                    record[field_name] = value
                offset += 4
                field_idx += 1
            elif char == 'i':  # int32
                value = struct.unpack_from('<i', data, offset)[0]
                if field_name:
                    record[field_name] = value
                offset += 4
                field_idx += 1
            elif char == 'f':  # float
                value = struct.unpack_from('<f', data, offset)[0]
                if field_name:
                    record[field_name] = value
                offset += 4
                field_idx += 1
            elif char == 'x':  # skip
                offset += 4
                field_idx += 1
            elif char == 's':  # string offset
                str_offset = struct.unpack_from('<I', data, offset)[0]
                if field_name:
                    record[field_name] = str_offset  # Store offset, resolve later
                offset += 4
                field_idx += 1
            elif char == 'X':  # skip byte
                offset += 1
                field_idx += 1

        return record

    def load(self) -> None:
        """Load and resolve strings."""
        super().load()
        # Resolve string offsets to actual strings
        for record in self.records.values():
            for key in list(record.keys()):
                if key and ('SpellName' in key or 'Rank' in key):
                    if isinstance(record[key], int):
                        record[key] = self._read_string(record[key])

    def get_spell(self, spell_id: int) -> Optional[Dict[str, Any]]:
        """Get a spell by ID with commonly used fields."""
        spell = self.get(spell_id)
        if not spell:
            return None

        # Return a cleaned-up version with key fields
        return self._format_spell(spell)

    def _format_spell(self, spell: Dict[str, Any]) -> Dict[str, Any]:
        """Format spell data for output."""
        return {
            "Id": spell.get("Id"),
            "Name": spell.get("SpellName_enUS", ""),
            "Rank": spell.get("Rank_enUS", ""),
            "Category": spell.get("Category"),
            "Dispel": spell.get("Dispel"),
            "Mechanic": spell.get("Mechanic"),
            "Attributes": hex(spell.get("Attributes", 0)),
            "AttributesEx": hex(spell.get("AttributesEx", 0)),
            "AttributesEx2": hex(spell.get("AttributesEx2", 0)),
            "AttributesEx3": hex(spell.get("AttributesEx3", 0)),
            "CastingTimeIndex": spell.get("CastingTimeIndex"),
            "RecoveryTime": spell.get("RecoveryTime"),
            "CategoryRecoveryTime": spell.get("CategoryRecoveryTime"),
            "ProcFlags": hex(spell.get("ProcFlags", 0)),
            "ProcChance": spell.get("ProcChance"),
            "ProcCharges": spell.get("ProcCharges"),
            "MaxLevel": spell.get("MaxLevel"),
            "BaseLevel": spell.get("BaseLevel"),
            "SpellLevel": spell.get("SpellLevel"),
            "DurationIndex": spell.get("DurationIndex"),
            "PowerType": spell.get("PowerType"),
            "ManaCost": spell.get("ManaCost"),
            "RangeIndex": spell.get("RangeIndex"),
            "Speed": spell.get("Speed"),
            "StackAmount": spell.get("StackAmount"),
            "Effects": [
                {
                    "Effect": spell.get(f"Effect{i}"),
                    "DieSides": spell.get(f"EffectDieSides{i}"),
                    "BasePoints": spell.get(f"EffectBasePoints{i}"),
                    "Mechanic": spell.get(f"EffectMechanic{i}"),
                    "TargetA": spell.get(f"EffectImplicitTargetA{i}"),
                    "TargetB": spell.get(f"EffectImplicitTargetB{i}"),
                    "RadiusIndex": spell.get(f"EffectRadiusIndex{i}"),
                    "AuraName": spell.get(f"EffectApplyAuraName{i}"),
                    "Amplitude": spell.get(f"EffectAmplitude{i}"),
                    "MiscValue": spell.get(f"EffectMiscValue{i}"),
                    "MiscValueB": spell.get(f"EffectMiscValueB{i}"),
                    "TriggerSpell": spell.get(f"EffectTriggerSpell{i}"),
                }
                for i in range(3)
            ],
            "SpellFamilyName": spell.get("SpellFamilyName"),
            "SpellFamilyFlags": [
                spell.get("SpellFamilyFlags0", 0),
                spell.get("SpellFamilyFlags1", 0),
                spell.get("SpellFamilyFlags2", 0),
            ],
            "MaxAffectedTargets": spell.get("MaxAffectedTargets"),
            "DmgClass": spell.get("DmgClass"),
            "SchoolMask": spell.get("SchoolMask"),
        }

    def search_by_name(self, name: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Search spells by name."""
        if not self._loaded:
            self.load()

        results = []
        name_lower = name.lower()
        for spell in self.records.values():
            spell_name = spell.get("SpellName_enUS", "")
            if spell_name and name_lower in spell_name.lower():
                results.append(self._format_spell(spell))
                if len(results) >= limit:
                    break
        return results

    def search_by_family(self, family_name: int, limit: int = 100) -> List[Dict[str, Any]]:
        """Search spells by SpellFamilyName."""
        if not self._loaded:
            self.load()

        results = []
        for spell in self.records.values():
            if spell.get("SpellFamilyName") == family_name:
                results.append(self._format_spell(spell))
                if len(results) >= limit:
                    break
        return results

    def get_proc_info(self, spell_id: int) -> Optional[Dict[str, Any]]:
        """Get proc-related information for a spell."""
        spell = self.get(spell_id)
        if not spell:
            return None

        return {
            "Id": spell.get("Id"),
            "Name": spell.get("SpellName_enUS", ""),
            "ProcFlags": hex(spell.get("ProcFlags", 0)),
            "ProcChance": spell.get("ProcChance"),
            "ProcCharges": spell.get("ProcCharges"),
            "SpellFamilyName": spell.get("SpellFamilyName"),
            "SpellFamilyFlags": [
                hex(spell.get("SpellFamilyFlags0", 0)),
                hex(spell.get("SpellFamilyFlags1", 0)),
                hex(spell.get("SpellFamilyFlags2", 0)),
            ],
            "SchoolMask": spell.get("SchoolMask"),
            "Attributes": hex(spell.get("Attributes", 0)),
            "AttributesEx": hex(spell.get("AttributesEx", 0)),
            "AttributesEx2": hex(spell.get("AttributesEx2", 0)),
            "AttributesEx3": hex(spell.get("AttributesEx3", 0)),
        }


# Singleton instance with caching
_spell_dbc_instance: Optional[SpellDBC] = None


def get_spell_dbc() -> SpellDBC:
    """Get the singleton SpellDBC instance."""
    global _spell_dbc_instance
    if _spell_dbc_instance is None:
        _spell_dbc_instance = SpellDBC()
        _spell_dbc_instance.load()
    return _spell_dbc_instance


@lru_cache(maxsize=1000)
def lookup_spell(spell_id: int) -> Optional[Dict[str, Any]]:
    """Cached spell lookup by ID."""
    dbc = get_spell_dbc()
    return dbc.get_spell(spell_id)


@lru_cache(maxsize=1000)
def get_spell_name_from_dbc(spell_id: int) -> str:
    """Get just the spell name from DBC."""
    dbc = get_spell_dbc()
    spell = dbc.get(spell_id)
    if spell:
        return spell.get("SpellName_enUS", f"Unknown Spell {spell_id}")
    return f"Unknown Spell {spell_id}"
