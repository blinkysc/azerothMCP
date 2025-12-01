#!/usr/bin/env python3
"""SmartAI Target Types Reference Data"""

SMART_TARGETS = {
    0: {"name": "SMART_TARGET_NONE", "desc": "No target (self)", "params": "NONE"},
    1: {"name": "SMART_TARGET_SELF", "desc": "Self", "params": "NONE"},
    2: {"name": "SMART_TARGET_VICTIM", "desc": "Current victim (highest aggro)", "params": "NONE"},
    3: {"name": "SMART_TARGET_HOSTILE_SECOND_AGGRO", "desc": "Second highest aggro", "params": "MaxDist, PlayerOnly, PowerType+1, MissingAura"},
    4: {"name": "SMART_TARGET_HOSTILE_LAST_AGGRO", "desc": "Lowest aggro", "params": "MaxDist, PlayerOnly, PowerType+1, MissingAura"},
    5: {"name": "SMART_TARGET_HOSTILE_RANDOM", "desc": "Random hostile on threat list", "params": "MaxDist, PlayerOnly, PowerType+1, MissingAura"},
    6: {"name": "SMART_TARGET_HOSTILE_RANDOM_NOT_TOP", "desc": "Random hostile (not top)", "params": "MaxDist, PlayerOnly, PowerType+1, MissingAura"},
    7: {"name": "SMART_TARGET_ACTION_INVOKER", "desc": "Unit who caused this event", "params": "NONE"},
    8: {"name": "SMART_TARGET_POSITION", "desc": "Position from event params", "params": "Uses x, y, z, o from target coordinates"},
    9: {"name": "SMART_TARGET_CREATURE_RANGE", "desc": "Creature in range", "params": "CreatureEntry (0=any), MinDist, MaxDist, Alive (0=both, 1=alive, 2=dead)"},
    10: {"name": "SMART_TARGET_CREATURE_GUID", "desc": "Creature by GUID", "params": "GUID, Entry"},
    11: {"name": "SMART_TARGET_CREATURE_DISTANCE", "desc": "Creature by distance", "params": "CreatureEntry (0=any), MaxDist, Alive (0=both, 1=alive, 2=dead)"},
    12: {"name": "SMART_TARGET_STORED", "desc": "Previously stored targets", "params": "VarID"},
    13: {"name": "SMART_TARGET_GAMEOBJECT_RANGE", "desc": "GO in range", "params": "Entry (0=any), MinDist, MaxDist"},
    14: {"name": "SMART_TARGET_GAMEOBJECT_GUID", "desc": "GO by GUID", "params": "GUID, Entry"},
    15: {"name": "SMART_TARGET_GAMEOBJECT_DISTANCE", "desc": "GO by distance", "params": "Entry (0=any), MaxDist"},
    16: {"name": "SMART_TARGET_INVOKER_PARTY", "desc": "Invoker's party members", "params": "IncludePets (0/1)"},
    17: {"name": "SMART_TARGET_PLAYER_RANGE", "desc": "Players in range", "params": "MinDist, MaxDist, MaxCount, target.o=1 for all in range"},
    18: {"name": "SMART_TARGET_PLAYER_DISTANCE", "desc": "Players by distance", "params": "MaxDist"},
    19: {"name": "SMART_TARGET_CLOSEST_CREATURE", "desc": "Closest creature", "params": "CreatureEntry (0=any), MaxDist, Dead? (0/1)"},
    20: {"name": "SMART_TARGET_CLOSEST_GAMEOBJECT", "desc": "Closest gameobject", "params": "Entry (0=any), MaxDist"},
    21: {"name": "SMART_TARGET_CLOSEST_PLAYER", "desc": "Closest player", "params": "MaxDist"},
    22: {"name": "SMART_TARGET_ACTION_INVOKER_VEHICLE", "desc": "Invoker's vehicle", "params": "NONE"},
    23: {"name": "SMART_TARGET_OWNER_OR_SUMMONER", "desc": "Owner or summoner", "params": "NONE"},
    24: {"name": "SMART_TARGET_THREAT_LIST", "desc": "All on threat list", "params": "MaxDist, PlayerOnly"},
    25: {"name": "SMART_TARGET_CLOSEST_ENEMY", "desc": "Closest enemy", "params": "MaxDist, PlayerOnly"},
    26: {"name": "SMART_TARGET_CLOSEST_FRIENDLY", "desc": "Closest friendly", "params": "MaxDist, PlayerOnly"},
    27: {"name": "SMART_TARGET_LOOT_RECIPIENTS", "desc": "All players who tagged creature", "params": "NONE"},
    28: {"name": "SMART_TARGET_FARTHEST", "desc": "Farthest target", "params": "MaxDist, PlayerOnly, IsInLOS, MinDist"},
    29: {"name": "SMART_TARGET_VEHICLE_PASSENGER", "desc": "Vehicle passenger", "params": "SeatNumber"},
    # AC Custom Targets (200+)
    201: {"name": "SMART_TARGET_PLAYER_WITH_AURA", "desc": "Player with/without aura (AC)", "params": "SpellID, Negation, MaxDist, MinDist, target.o=resize list"},
    202: {"name": "SMART_TARGET_RANDOM_POINT", "desc": "Random point (AC)", "params": "Range, Amount, SelfAsMiddle (0/1) else use xyz"},
    203: {"name": "SMART_TARGET_ROLE_SELECTION", "desc": "By role (AC)", "params": "RangeMax, TargetMask (1=Tank, 2=Healer, 4=Damage), ResizeList"},
    204: {"name": "SMART_TARGET_SUMMONED_CREATURES", "desc": "Summoned creatures (AC)", "params": "Entry"},
    205: {"name": "SMART_TARGET_INSTANCE_STORAGE", "desc": "Instance storage (AC)", "params": "DataIndex, Type (1=creature, 2=gameobject)"},
}


def register_smartai_tools(mcp):
    """Register SmartAI-related tools with the MCP server."""

    @mcp.tool()
    def get_smart_scripts(entryorguid: int, source_type: int = 0) -> str:
        """
        Get SmartAI scripts for a creature, gameobject, or other source.
        Includes auto-generated human-readable comments for each script row.

        Args:
            entryorguid: The entry or GUID of the source
            source_type: 0=Creature, 1=GameObject, 2=AreaTrigger, 3=Event,
                        4=Gossip, 5=Quest, 6=Spell, 7=Transport, 8=Instance, 9=TimedActionList

        Returns:
            All smart_scripts rows for this entity with generated comments, ordered by id
        """
        try:
            results = execute_query(
                """SELECT * FROM smart_scripts
                   WHERE entryorguid = %s AND source_type = %s
                   ORDER BY id""",
                "world",
                (entryorguid, source_type)
            )
            if not results:
                return json.dumps({
                    "message": f"No SmartAI scripts found for entryorguid={entryorguid}, source_type={source_type}",
                    "hint": "If this is a creature, check if it uses SmartAI (AIName='SmartAI' in creature_template)"
                })

            # Add Keira3-style comments
            name = get_entity_name(entryorguid, source_type)
            results = add_sai_comments(results, name)

            return json.dumps(results, indent=2, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    def explain_smart_script(event_type: int = None, action_type: int = None, target_type: int = None) -> str:
        """
        Get documentation explaining SmartAI event types, action types, or target types.
        Includes parameter documentation from AzerothCore source code.

        Args:
            event_type: SmartAI event type number to explain
            action_type: SmartAI action type number to explain
            target_type: SmartAI target type number to explain

        Returns:
            Explanation of the requested SmartAI component with parameters
        """
        result = {}

        if event_type is not None:
            event_info = SMART_EVENTS.get(event_type)
            if event_info:
                result["event_type"] = {
                    "id": event_type,
                    "name": event_info["name"],
                    "description": event_info["desc"],
                    "parameters": event_info["params"]
                }
            else:
                result["event_type"] = {"error": f"Unknown event type: {event_type}"}

        if action_type is not None:
            action_info = SMART_ACTIONS.get(action_type)
            if action_info:
                result["action_type"] = {
                    "id": action_type,
                    "name": action_info["name"],
                    "description": action_info["desc"],
                    "parameters": action_info["params"]
                }
            else:
                result["action_type"] = {"error": f"Unknown action type: {action_type}"}

        if target_type is not None:
            target_info = SMART_TARGETS.get(target_type)
            if target_info:
                result["target_type"] = {
                    "id": target_type,
                    "name": target_info["name"],
                    "description": target_info["desc"],
                    "parameters": target_info["params"]
                }
            else:
                result["target_type"] = {"error": f"Unknown target type: {target_type}"}

        if not result:
            return json.dumps({
                "error": "Please provide at least one of: event_type, action_type, target_type",
                "hint": "Example: explain_smart_script(event_type=4) for SMART_EVENT_AGGRO"
            })

        return json.dumps(result, indent=2)

    @mcp.tool()
    def trace_script_chain(entryorguid: int, source_type: int = 0, start_event: int = None, max_depth: int = 10) -> str:
        """
        Trace the execution flow of SmartAI scripts for debugging.

        Follows:
        - Event links (link column -> triggers another script ID)
        - Timed action list calls (action_type 80)
        - Random timed action lists (action_type 87, 88)
        - SetData triggers (action_type 45 -> can trigger event_type 38)
        - Timed events (action_type 67 creates, event_type 59 triggers)

        Args:
            entryorguid: Entry or GUID of the creature/gameobject
            source_type: 0=Creature, 1=GameObject, 2=AreaTrigger, etc.
            start_event: Optional - only trace from scripts with this event_type
            max_depth: Maximum recursion depth for following chains (default 10)

        Returns:
            Visual execution flow showing script chains and their triggers
        """
        # Event type names for readable output
        event_names = {
            0: "UPDATE_IC", 1: "UPDATE_OOC", 2: "HEALTH_PCT", 3: "MANA_PCT",
            4: "AGGRO", 5: "KILL", 6: "DEATH", 7: "EVADE", 8: "SPELLHIT",
            9: "RANGE", 10: "OOC_LOS", 11: "RESPAWN", 12: "TARGET_HEALTH_PCT",
            17: "SUMMONED_UNIT", 19: "ACCEPTED_QUEST", 20: "REWARD_QUEST",
            21: "REACHED_HOME", 22: "RECEIVE_EMOTE", 25: "RESET", 26: "IC_LOS",
            34: "MOVEMENTINFORM", 37: "AI_INIT", 38: "DATA_SET", 39: "WAYPOINT_START",
            40: "WAYPOINT_REACHED", 52: "TEXT_OVER", 54: "JUST_SUMMONED",
            58: "WAYPOINT_ENDED", 59: "TIMED_EVENT_TRIGGERED", 60: "UPDATE",
            61: "LINK", 62: "GOSSIP_SELECT", 63: "JUST_CREATED", 64: "GOSSIP_HELLO",
            66: "EVENT_PHASE_CHANGE", 77: "COUNTER_SET", 82: "SUMMONED_UNIT_DIES",
        }

        # Action type names for readable output
        action_names = {
            1: "TALK", 2: "SET_FACTION", 11: "CAST", 12: "SUMMON_CREATURE",
            22: "SET_EVENT_PHASE", 23: "INC_EVENT_PHASE", 24: "EVADE",
            29: "FOLLOW", 37: "DIE", 41: "FORCE_DESPAWN", 45: "SET_DATA",
            53: "WP_START", 54: "WP_PAUSE", 55: "WP_STOP", 63: "SET_COUNTER",
            67: "CREATE_TIMED_EVENT", 69: "MOVE_TO_POS", 73: "TRIGGER_TIMED_EVENT",
            80: "CALL_TIMED_ACTIONLIST", 85: "SELF_CAST",
            87: "CALL_RANDOM_TIMED_ACTIONLIST", 88: "CALL_RANDOM_RANGE_TIMED_ACTIONLIST",
        }

        # Target type names
        target_names = {
            0: "NONE", 1: "SELF", 2: "VICTIM", 5: "HOSTILE_RANDOM",
            7: "ACTION_INVOKER", 8: "POSITION", 12: "STORED",
            17: "PLAYER_RANGE", 19: "CLOSEST_CREATURE", 21: "CLOSEST_PLAYER",
            23: "OWNER_OR_SUMMONER", 24: "THREAT_LIST",
        }

        def get_event_name(et):
            return event_names.get(et, f"EVENT_{et}")

        def get_action_name(at):
            return action_names.get(at, f"ACTION_{at}")

        def get_target_name(tt):
            return target_names.get(tt, f"TARGET_{tt}")

        try:
            # Get all scripts for this entity
            scripts = execute_query(
                """SELECT * FROM smart_scripts
                   WHERE entryorguid = %s AND source_type = %s
                   ORDER BY id""",
                "world",
                (entryorguid, source_type)
            )

            if not scripts:
                return json.dumps({
                    "error": f"No scripts found for entryorguid={entryorguid}, source_type={source_type}"
                })

            # Build a lookup by script ID
            script_by_id = {s["id"]: s for s in scripts}

            # Track visited to prevent infinite loops
            visited = set()

            # Store the trace results
            trace_results = []

            # Timed action lists we need to fetch
            timed_lists_to_fetch = set()

            # Data triggers we discover
            data_triggers = []

            # Timed events created
            timed_events = []

            def format_script(script, indent=0):
                """Format a single script line for display."""
                prefix = "  " * indent
                event = get_event_name(script["event_type"])
                action = get_action_name(script["action_type"])
                target = get_target_name(script["target_type"])

                # Phase info
                phase_str = ""
                if script["event_phase_mask"] != 0:
                    phase_str = f" [phase_mask={script['event_phase_mask']}]"

                # Chance info
                chance_str = ""
                if script["event_chance"] != 100:
                    chance_str = f" [{script['event_chance']}% chance]"

                comment = script.get("comment", "")
                comment_str = f' -- "{comment}"' if comment else ""

                return f"{prefix}[{script['id']}] {event} -> {action} @ {target}{phase_str}{chance_str}{comment_str}"

            def trace_script(script_id, depth=0):
                """Recursively trace a script and its chains."""
                if depth > max_depth:
                    return [f"{'  ' * depth}... (max depth reached)"]

                if script_id in visited:
                    return [f"{'  ' * depth}-> [LOOP] Already visited script {script_id}"]

                if script_id not in script_by_id:
                    return [f"{'  ' * depth}-> [ERROR] Script ID {script_id} not found!"]

                visited.add(script_id)
                script = script_by_id[script_id]
                lines = [format_script(script, depth)]

                action_type = script["action_type"]

                # Check for timed action list calls
                if action_type == 80:  # CALL_TIMED_ACTIONLIST
                    list_id = script["action_param1"]
                    if list_id:
                        timed_lists_to_fetch.add(list_id)
                        lines.append(f"{'  ' * (depth+1)}-> CALLS TimedActionList {list_id}")

                # Check for random timed action list calls
                elif action_type == 87:  # CALL_RANDOM_TIMED_ACTIONLIST
                    for i in range(1, 7):
                        list_id = script.get(f"action_param{i}")
                        if list_id:
                            timed_lists_to_fetch.add(list_id)
                    lines.append(f"{'  ' * (depth+1)}-> CALLS RANDOM TimedActionList from params")

                elif action_type == 88:  # CALL_RANDOM_RANGE_TIMED_ACTIONLIST
                    start_id = script["action_param1"]
                    end_id = script["action_param2"]
                    if start_id and end_id:
                        for list_id in range(start_id, end_id + 1):
                            timed_lists_to_fetch.add(list_id)
                        lines.append(f"{'  ' * (depth+1)}-> CALLS RANDOM TimedActionList {start_id}-{end_id}")

                # Check for SetData
                elif action_type == 45:  # SET_DATA
                    data_id = script["action_param1"]
                    data_value = script["action_param2"]
                    data_triggers.append({
                        "from_script": script_id,
                        "data_id": data_id,
                        "data_value": data_value,
                        "target": get_target_name(script["target_type"])
                    })
                    lines.append(f"{'  ' * (depth+1)}-> SETS DATA id={data_id} value={data_value} on {get_target_name(script['target_type'])}")

                # Check for timed event creation
                elif action_type == 67:  # CREATE_TIMED_EVENT
                    event_id = script["action_param1"]
                    min_time = script["action_param2"]
                    max_time = script["action_param3"]
                    timed_events.append({
                        "event_id": event_id,
                        "min_time": min_time,
                        "max_time": max_time,
                        "from_script": script_id
                    })
                    lines.append(f"{'  ' * (depth+1)}-> CREATES TimedEvent {event_id} (fires in {min_time}-{max_time}ms)")

                # Check for timed event trigger
                elif action_type == 73:  # TRIGGER_TIMED_EVENT
                    event_id = script["action_param1"]
                    lines.append(f"{'  ' * (depth+1)}-> TRIGGERS TimedEvent {event_id}")

                # Follow link chains
                link = script.get("link", 0)
                if link and link != 0:
                    lines.append(f"{'  ' * (depth+1)}-> LINKS TO script {link}:")
                    lines.extend(trace_script(link, depth + 2))

                return lines

            # Filter scripts by start_event if specified
            if start_event is not None:
                entry_scripts = [s for s in scripts if s["event_type"] == start_event]
            else:
                entry_scripts = scripts

            # Trace each entry point
            for script in entry_scripts:
                if script["id"] not in visited:
                    trace_results.append(f"\n=== Event: {get_event_name(script['event_type'])} ===")
                    trace_results.extend(trace_script(script["id"]))

            # Fetch and trace timed action lists
            timed_list_traces = {}
            for list_id in timed_lists_to_fetch:
                timed_scripts = execute_query(
                    """SELECT * FROM smart_scripts
                       WHERE entryorguid = %s AND source_type = 9
                       ORDER BY id""",
                    "world",
                    (list_id,)
                )
                if timed_scripts:
                    timed_list_traces[list_id] = timed_scripts

            # Format timed action lists
            if timed_list_traces:
                trace_results.append("\n" + "=" * 50)
                trace_results.append("TIMED ACTION LISTS REFERENCED:")
                trace_results.append("=" * 50)

                for list_id, timed_scripts in timed_list_traces.items():
                    trace_results.append(f"\n--- TimedActionList {list_id} ---")
                    for ts in timed_scripts:
                        delay = ts.get("event_param1", 0)
                        action = get_action_name(ts["action_type"])
                        target = get_target_name(ts["target_type"])
                        comment = ts.get("comment", "")

                        detail = ""
                        if ts["action_type"] == 11:  # CAST
                            detail = f" spell={ts['action_param1']}"
                        elif ts["action_type"] == 1:  # TALK
                            detail = f" group={ts['action_param1']}"
                        elif ts["action_type"] == 12:  # SUMMON
                            detail = f" creature={ts['action_param1']}"

                        trace_results.append(f"  [{ts['id']}] +{delay}ms: {action}{detail} @ {target} -- {comment}")

            # Show data triggers if any
            if data_triggers:
                trace_results.append("\n" + "=" * 50)
                trace_results.append("DATA TRIGGERS (may trigger DATA_SET events on targets):")
                trace_results.append("=" * 50)
                for dt in data_triggers:
                    trace_results.append(f"  Script {dt['from_script']}: SET_DATA({dt['data_id']}, {dt['data_value']}) -> {dt['target']}")

            # Show timed events if any
            if timed_events:
                trace_results.append("\n" + "=" * 50)
                trace_results.append("TIMED EVENTS CREATED:")
                trace_results.append("=" * 50)
                for te in timed_events:
                    trace_results.append(f"  Script {te['from_script']}: Event {te['event_id']} (triggers in {te['min_time']}-{te['max_time']}ms)")

                # Check if there are scripts waiting for these events
                trace_results.append("\nScripts listening for TIMED_EVENT_TRIGGERED (event_type=59):")
                for te in timed_events:
                    listeners = [s for s in scripts if s["event_type"] == 59 and s["event_param1"] == te["event_id"]]
                    if listeners:
                        for l in listeners:
                            trace_results.append(f"  -> Script {l['id']} listens for event {te['event_id']}")
                    else:
                        trace_results.append(f"  -> [WARNING] No script found listening for event {te['event_id']}!")

            # Summary
            trace_results.append("\n" + "=" * 50)
            trace_results.append("SUMMARY:")
            trace_results.append("=" * 50)
            trace_results.append(f"  Total scripts: {len(scripts)}")
            trace_results.append(f"  Scripts traced: {len(visited)}")
            trace_results.append(f"  Timed action lists: {len(timed_list_traces)}")
            trace_results.append(f"  Data triggers: {len(data_triggers)}")
            trace_results.append(f"  Timed events: {len(timed_events)}")

            # Check for potential issues
            issues = []
            for script in scripts:
                link = script.get("link", 0)
                if link and link != 0 and link not in script_by_id:
                    issues.append(f"Script {script['id']} links to non-existent script {link}")

                if script["event_chance"] == 0:
                    issues.append(f"Script {script['id']} has 0% event_chance (will never trigger)")

            if issues:
                trace_results.append("\n[!] POTENTIAL ISSUES DETECTED:")
                for issue in issues:
                    trace_results.append(f"  - {issue}")

            return "\n".join(trace_results)

        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    def generate_sai_comments(entryorguid: int, source_type: int = 0) -> str:
        """
        Generate human-readable comments for SmartAI scripts using Keira3's comment generator.

        This tool fetches SmartAI scripts and generates descriptive comments explaining
        what each script row does, similar to what Keira3 generates.

        Args:
            entryorguid: The entry or GUID of the creature/gameobject
            source_type: 0=Creature, 1=GameObject, 2=AreaTrigger, 9=TimedActionList

        Returns:
            SmartAI scripts with generated comments
        """
        if not SAI_GENERATOR_AVAILABLE:
            return json.dumps({"error": "SAI comment generator not available. Check sai_comment_generator.py"})

        try:
            scripts = execute_query(
                """SELECT * FROM smart_scripts
                   WHERE entryorguid = %s AND source_type = %s
                   ORDER BY id""",
                "world",
                (entryorguid, source_type)
            )

            if not scripts:
                return json.dumps({
                    "message": f"No SmartAI scripts found for entryorguid={entryorguid}, source_type={source_type}"
                })

            name = get_entity_name(entryorguid, source_type)

            generator = SaiCommentGenerator(mysql_query_func=_mysql_query_for_sai)
            results = []

            for script in scripts:
                comment = generator.generate_comment(scripts, script, name)
                results.append({
                    "id": script.get("id"),
                    "event_type": script.get("event_type"),
                    "action_type": script.get("action_type"),
                    "target_type": script.get("target_type"),
                    "comment": comment,
                    "full_row": script
                })

            return json.dumps({
                "entity_name": name,
                "entryorguid": entryorguid,
                "source_type": source_type,
                "script_count": len(results),
                "scripts_with_comments": results
            }, indent=2, default=str)

        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    def generate_comment_for_script(
        entity_name: str,
        event_type: int,
        action_type: int,
        target_type: int = 1,
        event_param1: int = 0,
        event_param2: int = 0,
        event_param3: int = 0,
        event_param4: int = 0,
        event_param5: int = 0,
        event_param6: int = 0,
        action_param1: int = 0,
        action_param2: int = 0,
        action_param3: int = 0,
        action_param4: int = 0,
        action_param5: int = 0,
        action_param6: int = 0,
        target_param1: int = 0,
        target_param2: int = 0,
        target_param3: int = 0,
        target_param4: int = 0,
        target_o: float = 0,
        event_phase_mask: int = 0,
        event_flags: int = 0,
        source_type: int = 0
    ) -> str:
        """
        Generate a human-readable comment for a SmartAI script row BEFORE inserting it.
        Use this when creating new SmartAI scripts to get the proper comment field value.

        Args:
            entity_name: Name of the creature/gameobject (e.g. "Hogger")
            event_type: SmartAI event type
            action_type: SmartAI action type
            target_type: SmartAI target type (default 1 = SELF)
            event_param1-6: Event parameters
            action_param1-6: Action parameters
            target_param1-4: Target parameters
            target_o: Target orientation
            event_phase_mask: Phase mask for the event
            event_flags: Event flags (e.g. 1 = NOT_REPEATABLE)
            source_type: 0=Creature, 1=GameObject, 2=AreaTrigger, 9=TimedActionList

        Returns:
            Generated comment string suitable for the 'comment' column
        """
        if not SAI_GENERATOR_AVAILABLE:
            return json.dumps({"error": "SAI comment generator not available"})

        try:
            script = {
                "id": 0,
                "link": 0,
                "source_type": source_type,
                "event_type": event_type,
                "event_phase_mask": event_phase_mask,
                "event_flags": event_flags,
                "event_param1": event_param1,
                "event_param2": event_param2,
                "event_param3": event_param3,
                "event_param4": event_param4,
                "event_param5": event_param5,
                "event_param6": event_param6,
                "action_type": action_type,
                "action_param1": action_param1,
                "action_param2": action_param2,
                "action_param3": action_param3,
                "action_param4": action_param4,
                "action_param5": action_param5,
                "action_param6": action_param6,
                "target_type": target_type,
                "target_param1": target_param1,
                "target_param2": target_param2,
                "target_param3": target_param3,
                "target_param4": target_param4,
                "target_o": target_o,
            }

            generator = SaiCommentGenerator(mysql_query_func=_mysql_query_for_sai)
            comment = generator.generate_comment([script], script, entity_name)

            return json.dumps({
                "comment": comment,
                "script_preview": script
            }, indent=2, default=str)

        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    def generate_comments_for_scripts_batch(entity_name: str, scripts_json: str) -> str:
        """
        Generate comments for multiple SmartAI script rows at once.
        Use this when creating a full set of scripts for an entity.

        Args:
            entity_name: Name of the creature/gameobject (e.g. "Hogger")
            scripts_json: JSON array of script objects, each with at minimum:
                         event_type, action_type, target_type, and any relevant params

        Example scripts_json:
            [
                {"id": 0, "event_type": 4, "action_type": 11, "action_param1": 12345, "target_type": 2},
                {"id": 1, "event_type": 0, "action_type": 11, "action_param1": 67890, "target_type": 2}
            ]

        Returns:
            The scripts with generated comments added
        """
        if not SAI_GENERATOR_AVAILABLE:
            return json.dumps({"error": "SAI comment generator not available"})

        try:
            scripts = json.loads(scripts_json)

            defaults = {
                "id": 0, "link": 0, "source_type": 0,
                "event_type": 0, "event_phase_mask": 0, "event_flags": 0,
                "event_param1": 0, "event_param2": 0, "event_param3": 0,
                "event_param4": 0, "event_param5": 0, "event_param6": 0,
                "action_type": 0, "action_param1": 0, "action_param2": 0,
                "action_param3": 0, "action_param4": 0, "action_param5": 0,
                "action_param6": 0, "target_type": 1, "target_param1": 0,
                "target_param2": 0, "target_param3": 0, "target_param4": 0,
                "target_o": 0,
            }

            for script in scripts:
                for key, default_val in defaults.items():
                    if key not in script:
                        script[key] = default_val

            generator = SaiCommentGenerator(mysql_query_func=_mysql_query_for_sai)

            for script in scripts:
                script["comment"] = generator.generate_comment(scripts, script, entity_name)

            return json.dumps({
                "entity_name": entity_name,
                "script_count": len(scripts),
                "scripts": scripts
            }, indent=2, default=str)

        except json.JSONDecodeError as e:
            return json.dumps({"error": f"Invalid JSON: {e}"})
        except Exception as e:
            return json.dumps({"error": str(e)}
