#!/usr/bin/env python3
"""
Proc System Reference Data

Based on the QAston proc system ported from TrinityCore to AzerothCore.
This provides reference data for the spell_proc table.
"""

# ProcFlags - When the proc can trigger (bitmask)
PROC_FLAGS = {
    0x00000000: {"name": "PROC_FLAG_NONE", "description": "No proc"},
    0x00000001: {"name": "PROC_FLAG_KILLED", "description": "Killed by aggressor"},
    0x00000002: {"name": "PROC_FLAG_KILL", "description": "Kill target (requires XP/Honor reward in most cases)"},
    0x00000004: {"name": "PROC_FLAG_DONE_MELEE_AUTO_ATTACK", "description": "Done melee auto attack"},
    0x00000008: {"name": "PROC_FLAG_TAKEN_MELEE_AUTO_ATTACK", "description": "Taken melee auto attack"},
    0x00000010: {"name": "PROC_FLAG_DONE_SPELL_MELEE_DMG_CLASS", "description": "Done attack by spell with melee damage class"},
    0x00000020: {"name": "PROC_FLAG_TAKEN_SPELL_MELEE_DMG_CLASS", "description": "Taken attack by spell with melee damage class"},
    0x00000040: {"name": "PROC_FLAG_DONE_RANGED_AUTO_ATTACK", "description": "Done ranged auto attack"},
    0x00000080: {"name": "PROC_FLAG_TAKEN_RANGED_AUTO_ATTACK", "description": "Taken ranged auto attack"},
    0x00000100: {"name": "PROC_FLAG_DONE_SPELL_RANGED_DMG_CLASS", "description": "Done attack by spell with ranged damage class"},
    0x00000200: {"name": "PROC_FLAG_TAKEN_SPELL_RANGED_DMG_CLASS", "description": "Taken attack by spell with ranged damage class"},
    0x00000400: {"name": "PROC_FLAG_DONE_SPELL_NONE_DMG_CLASS_POS", "description": "Done positive spell with none damage class"},
    0x00000800: {"name": "PROC_FLAG_TAKEN_SPELL_NONE_DMG_CLASS_POS", "description": "Taken positive spell with none damage class"},
    0x00001000: {"name": "PROC_FLAG_DONE_SPELL_NONE_DMG_CLASS_NEG", "description": "Done negative spell with none damage class"},
    0x00002000: {"name": "PROC_FLAG_TAKEN_SPELL_NONE_DMG_CLASS_NEG", "description": "Taken negative spell with none damage class"},
    0x00004000: {"name": "PROC_FLAG_DONE_SPELL_MAGIC_DMG_CLASS_POS", "description": "Done positive spell with magic damage class"},
    0x00008000: {"name": "PROC_FLAG_TAKEN_SPELL_MAGIC_DMG_CLASS_POS", "description": "Taken positive spell with magic damage class"},
    0x00010000: {"name": "PROC_FLAG_DONE_SPELL_MAGIC_DMG_CLASS_NEG", "description": "Done negative spell with magic damage class"},
    0x00020000: {"name": "PROC_FLAG_TAKEN_SPELL_MAGIC_DMG_CLASS_NEG", "description": "Taken negative spell with magic damage class"},
    0x00040000: {"name": "PROC_FLAG_DONE_PERIODIC", "description": "Done periodic damage/healing"},
    0x00080000: {"name": "PROC_FLAG_TAKEN_PERIODIC", "description": "Taken periodic damage/healing"},
    0x00100000: {"name": "PROC_FLAG_TAKEN_DAMAGE", "description": "Taken any damage"},
    0x00200000: {"name": "PROC_FLAG_DONE_TRAP_ACTIVATION", "description": "On trap activation (gameobject cast)"},
    0x00400000: {"name": "PROC_FLAG_DONE_MAINHAND_ATTACK", "description": "Done main-hand melee attack (spell and auto)"},
    0x00800000: {"name": "PROC_FLAG_DONE_OFFHAND_ATTACK", "description": "Done off-hand melee attack (spell and auto)"},
    0x01000000: {"name": "PROC_FLAG_DEATH", "description": "Died in any way"},
}

# Common proc flag combinations
PROC_FLAG_MASKS = {
    "AUTO_ATTACK_PROC_FLAG_MASK": 0x000000CC,  # Auto attack done/taken (melee + ranged)
    "MELEE_PROC_FLAG_MASK": 0x00C0003C,        # Melee attacks (auto + spell + mainhand/offhand)
    "RANGED_PROC_FLAG_MASK": 0x000003C0,       # Ranged attacks (auto + spell)
    "SPELL_PROC_FLAG_MASK": 0x002DFFF0,        # Spell-based procs
    "PERIODIC_PROC_FLAG_MASK": 0x000C0000,     # Periodic damage/healing
    "DONE_HIT_PROC_FLAG_MASK": 0x00E557D4,     # Done any hit
    "TAKEN_HIT_PROC_FLAG_MASK": 0x001AA828,    # Taken any hit
}

# ProcFlagsExLegacy - Legacy hit type requirements (spell_proc_event table)
PROC_EX_FLAGS = {
    0x00000000: {"name": "PROC_EX_NONE", "description": "Triggers on Hit/Crit only (default)"},
    0x00000001: {"name": "PROC_EX_NORMAL_HIT", "description": "Only from normal hit (non-crit)"},
    0x00000002: {"name": "PROC_EX_CRITICAL_HIT", "description": "Only from critical hit"},
    0x00000004: {"name": "PROC_EX_MISS", "description": "On miss"},
    0x00000008: {"name": "PROC_EX_RESIST", "description": "On resist"},
    0x00000010: {"name": "PROC_EX_DODGE", "description": "On dodge"},
    0x00000020: {"name": "PROC_EX_PARRY", "description": "On parry"},
    0x00000040: {"name": "PROC_EX_BLOCK", "description": "On block"},
    0x00000080: {"name": "PROC_EX_EVADE", "description": "On evade"},
    0x00000100: {"name": "PROC_EX_IMMUNE", "description": "On immune"},
    0x00000200: {"name": "PROC_EX_DEFLECT", "description": "On deflect"},
    0x00000400: {"name": "PROC_EX_ABSORB", "description": "On absorb"},
    0x00000800: {"name": "PROC_EX_REFLECT", "description": "On reflect"},
    0x00001000: {"name": "PROC_EX_INTERRUPT", "description": "On interrupt (melee)"},
    0x00002000: {"name": "PROC_EX_FULL_BLOCK", "description": "On full block (all damage blocked)"},
    0x00008000: {"name": "PROC_EX_NOT_ACTIVE_SPELL", "description": "Spell must NOT do damage/heal"},
    0x00010000: {"name": "PROC_EX_EX_TRIGGER_ALWAYS", "description": "Always trigger regardless of hit result"},
    0x00020000: {"name": "PROC_EX_EX_ONE_TIME_TRIGGER", "description": "Trigger once only"},
    0x00040000: {"name": "PROC_EX_ONLY_ACTIVE_SPELL", "description": "Spell MUST do damage/heal"},
    0x00080000: {"name": "PROC_EX_NO_OVERHEAL", "description": "Proc only if heal did actual work (no overheal)"},
    0x00100000: {"name": "PROC_EX_NO_AURA_REFRESH", "description": "Proc only if aura was not refreshed"},
    0x00200000: {"name": "PROC_EX_ONLY_FIRST_TICK", "description": "Proc only on first tick (periodic spells)"},
}

# ProcFlagsSpellType - What type of spell triggers the proc (bitmask)
PROC_SPELL_TYPES = {
    0x00000000: {"name": "PROC_SPELL_TYPE_NONE", "description": "No spell type requirement"},
    0x00000001: {"name": "PROC_SPELL_TYPE_DAMAGE", "description": "Damage spell"},
    0x00000002: {"name": "PROC_SPELL_TYPE_HEAL", "description": "Healing spell"},
    0x00000004: {"name": "PROC_SPELL_TYPE_NO_DMG_HEAL", "description": "Other spell (no damage/heal)"},
    0x00000007: {"name": "PROC_SPELL_TYPE_MASK_ALL", "description": "Any spell type"},
}

# ProcFlagsSpellPhase - At which phase of spell execution the proc triggers (bitmask)
PROC_SPELL_PHASES = {
    0x00000000: {"name": "PROC_SPELL_PHASE_NONE", "description": "No phase requirement"},
    0x00000001: {"name": "PROC_SPELL_PHASE_CAST", "description": "On spell cast start"},
    0x00000002: {"name": "PROC_SPELL_PHASE_HIT", "description": "On spell hit"},
    0x00000004: {"name": "PROC_SPELL_PHASE_FINISH", "description": "On spell finish (after all effects)"},
    0x00000007: {"name": "PROC_SPELL_PHASE_MASK_ALL", "description": "Any phase"},
}

# ProcFlagsHit - What hit result triggers the proc (bitmask)
PROC_HIT_FLAGS = {
    0x00000000: {"name": "PROC_HIT_NONE", "description": "Default: NORMAL|CRITICAL for TAKEN, +ABSORB for DONE"},
    0x00000001: {"name": "PROC_HIT_NORMAL", "description": "Non-critical hit"},
    0x00000002: {"name": "PROC_HIT_CRITICAL", "description": "Critical hit"},
    0x00000004: {"name": "PROC_HIT_MISS", "description": "Miss"},
    0x00000008: {"name": "PROC_HIT_FULL_RESIST", "description": "Full resist"},
    0x00000010: {"name": "PROC_HIT_DODGE", "description": "Dodge"},
    0x00000020: {"name": "PROC_HIT_PARRY", "description": "Parry"},
    0x00000040: {"name": "PROC_HIT_BLOCK", "description": "Block (partial or full)"},
    0x00000080: {"name": "PROC_HIT_EVADE", "description": "Evade"},
    0x00000100: {"name": "PROC_HIT_IMMUNE", "description": "Immune"},
    0x00000200: {"name": "PROC_HIT_DEFLECT", "description": "Deflect"},
    0x00000400: {"name": "PROC_HIT_ABSORB", "description": "Absorb (partial or full)"},
    0x00000800: {"name": "PROC_HIT_REFLECT", "description": "Reflect"},
    0x00001000: {"name": "PROC_HIT_INTERRUPT", "description": "Interrupt"},
    0x00002000: {"name": "PROC_HIT_FULL_BLOCK", "description": "Full block (all damage)"},
    0x00002FFF: {"name": "PROC_HIT_MASK_ALL", "description": "Any hit result"},
}

# ProcAttributes - Special proc conditions (bitmask)
PROC_ATTRIBUTES = {
    0x00000001: {"name": "PROC_ATTR_REQ_EXP_OR_HONOR", "description": "Target must give XP or honor"},
    0x00000002: {"name": "PROC_ATTR_TRIGGERED_CAN_PROC", "description": "Can proc from triggered spells"},
    0x00000004: {"name": "PROC_ATTR_REQ_MANA_COST", "description": "Triggering spell must have mana cost"},
    0x00000008: {"name": "PROC_ATTR_REQ_SPELLMOD", "description": "Triggering spell must be affected by this aura's spellmod"},
    0x00000010: {"name": "PROC_ATTR_USE_STACKS_FOR_CHARGES", "description": "Consume stack instead of charge on proc"},
    0x00000080: {"name": "PROC_ATTR_REDUCE_PROC_60", "description": "Reduced proc chance if actor level > 60"},
    0x00000100: {"name": "PROC_ATTR_CANT_PROC_FROM_ITEM_CAST", "description": "Cannot proc from item-casted spells"},
}

# SpellFamilyNames - For filtering by spell family
SPELL_FAMILY_NAMES = {
    0: {"name": "SPELLFAMILY_GENERIC", "description": "Generic spells"},
    1: {"name": "SPELLFAMILY_UNK1", "description": "Events, holidays"},
    3: {"name": "SPELLFAMILY_MAGE", "description": "Mage spells"},
    4: {"name": "SPELLFAMILY_WARRIOR", "description": "Warrior spells"},
    5: {"name": "SPELLFAMILY_WARLOCK", "description": "Warlock spells"},
    6: {"name": "SPELLFAMILY_PRIEST", "description": "Priest spells"},
    7: {"name": "SPELLFAMILY_DRUID", "description": "Druid spells"},
    8: {"name": "SPELLFAMILY_ROGUE", "description": "Rogue spells"},
    9: {"name": "SPELLFAMILY_HUNTER", "description": "Hunter spells"},
    10: {"name": "SPELLFAMILY_PALADIN", "description": "Paladin spells"},
    11: {"name": "SPELLFAMILY_SHAMAN", "description": "Shaman spells"},
    12: {"name": "SPELLFAMILY_UNK2", "description": "Silence resistance spells"},
    13: {"name": "SPELLFAMILY_POTION", "description": "Potion spells"},
    15: {"name": "SPELLFAMILY_DEATHKNIGHT", "description": "Death Knight spells"},
    17: {"name": "SPELLFAMILY_PET", "description": "Pet spells"},
}

# SchoolMask - Spell school bitmask
SCHOOL_MASK = {
    0x00: {"name": "SPELL_SCHOOL_MASK_NONE", "description": "None"},
    0x01: {"name": "SPELL_SCHOOL_MASK_NORMAL", "description": "Physical"},
    0x02: {"name": "SPELL_SCHOOL_MASK_HOLY", "description": "Holy"},
    0x04: {"name": "SPELL_SCHOOL_MASK_FIRE", "description": "Fire"},
    0x08: {"name": "SPELL_SCHOOL_MASK_NATURE", "description": "Nature"},
    0x10: {"name": "SPELL_SCHOOL_MASK_FROST", "description": "Frost"},
    0x20: {"name": "SPELL_SCHOOL_MASK_SHADOW", "description": "Shadow"},
    0x40: {"name": "SPELL_SCHOOL_MASK_ARCANE", "description": "Arcane"},
    0x7E: {"name": "SPELL_SCHOOL_MASK_MAGIC", "description": "All magic schools"},
    0x7F: {"name": "SPELL_SCHOOL_MASK_ALL", "description": "All schools"},
}

# spell_proc table schema documentation
SPELL_PROC_SCHEMA = {
    "SpellId": "The spell ID that has this proc configuration (PRIMARY KEY)",
    "SchoolMask": "Bitmask for matching by spell school (0 = no restriction)",
    "SpellFamilyName": "Spell family ID for filtering (0 = no restriction)",
    "SpellFamilyMask0": "First 32 bits of SpellFamilyFlags mask",
    "SpellFamilyMask1": "Second 32 bits of SpellFamilyFlags mask",
    "SpellFamilyMask2": "Third 32 bits of SpellFamilyFlags mask",
    "ProcFlags": "Bitmask defining when proc triggers (see PROC_FLAGS)",
    "SpellTypeMask": "Type of spell: damage/heal/other (see PROC_SPELL_TYPES)",
    "SpellPhaseMask": "Phase: cast/hit/finish (see PROC_SPELL_PHASES)",
    "HitMask": "Hit result requirement (see PROC_HIT_FLAGS)",
    "AttributesMask": "Special attributes (see PROC_ATTRIBUTES)",
    "DisableEffectsMask": "Bitmask of effects to disable (1=eff0, 2=eff1, 4=eff2)",
    "ProcsPerMinute": "PPM-based chance (weapon speed adjusted), 0 = use Chance",
    "Chance": "Fixed percentage chance (0-100), ignored if ProcsPerMinute > 0",
    "Cooldown": "Cooldown in milliseconds between procs",
    "Charges": "Number of times proc can occur (0 = infinite)",
}


def decode_proc_flags(value: int) -> list:
    """Decode a ProcFlags bitmask into individual flags."""
    flags = []
    for flag_val, info in PROC_FLAGS.items():
        if flag_val != 0 and (value & flag_val):
            flags.append({"value": hex(flag_val), **info})
    return flags


def decode_proc_hit(value: int) -> list:
    """Decode a ProcFlagsHit bitmask into individual flags."""
    flags = []
    for flag_val, info in PROC_HIT_FLAGS.items():
        if flag_val != 0 and flag_val != 0x00002FFF and (value & flag_val):
            flags.append({"value": hex(flag_val), **info})
    return flags


def decode_proc_spell_type(value: int) -> list:
    """Decode a ProcFlagsSpellType bitmask into individual flags."""
    flags = []
    for flag_val, info in PROC_SPELL_TYPES.items():
        if flag_val != 0 and flag_val != 0x00000007 and (value & flag_val):
            flags.append({"value": hex(flag_val), **info})
    return flags


def decode_proc_spell_phase(value: int) -> list:
    """Decode a ProcFlagsSpellPhase bitmask into individual flags."""
    flags = []
    for flag_val, info in PROC_SPELL_PHASES.items():
        if flag_val != 0 and flag_val != 0x00000007 and (value & flag_val):
            flags.append({"value": hex(flag_val), **info})
    return flags


def decode_proc_attributes(value: int) -> list:
    """Decode a ProcAttributes bitmask into individual flags."""
    flags = []
    for flag_val, info in PROC_ATTRIBUTES.items():
        if value & flag_val:
            flags.append({"value": hex(flag_val), **info})
    return flags


def decode_school_mask(value: int) -> list:
    """Decode a SchoolMask bitmask into individual schools."""
    if value == 0:
        return [{"value": "0x00", "name": "None", "description": "No school restriction"}]
    schools = []
    for mask_val, info in SCHOOL_MASK.items():
        if mask_val != 0 and mask_val < 0x7E and (value & mask_val):
            schools.append({"value": hex(mask_val), **info})
    return schools


def get_spell_family_name(family_id: int) -> str:
    """Get the name of a spell family by ID."""
    if family_id in SPELL_FAMILY_NAMES:
        return SPELL_FAMILY_NAMES[family_id]["name"]
    return f"UNKNOWN_FAMILY_{family_id}"
