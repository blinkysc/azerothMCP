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
AzerothCore source code tools for MCP Server.
"""

import json

from ..config import AZEROTHCORE_SRC_PATH


def register_source_tools(mcp):
    """Register source code-related tools with the MCP server."""

    @mcp.tool()
    def get_smartai_source(
        event_type: int = None,
        action_type: int = None,
        target_type: int = None,
        context_lines: int = 50
    ) -> str:
        """
        Get the actual C++ implementation from AzerothCore source for SmartAI types.
        Reads directly from SmartScript.cpp to show exactly how each type is handled.

        Args:
            event_type: SmartAI event type number (handled in SmartScript::ProcessEvent)
            action_type: SmartAI action type number (handled in SmartScript::ProcessAction)
            target_type: SmartAI target type number (handled in SmartScript::GetTargets)
            context_lines: Number of lines to extract after the case statement (default 50)

        Returns:
            The actual C++ source code for the requested SmartAI implementation
        """
        smart_script_cpp = AZEROTHCORE_SRC_PATH / "src/server/game/AI/SmartScripts/SmartScript.cpp"

        if not smart_script_cpp.exists():
            return json.dumps({
                "error": f"SmartScript.cpp not found at {smart_script_cpp}",
                "hint": "Set AZEROTHCORE_SRC_PATH environment variable to your AzerothCore directory"
            })

        try:
            content = smart_script_cpp.read_text(encoding='utf-8', errors='ignore')
            lines = content.split('\n')
            results = {}

            def extract_case_block(search_pattern: str, max_lines: int = 50) -> str:
                """Extract a case block from the source code."""
                for i, line in enumerate(lines):
                    if search_pattern in line and 'case ' in line:
                        block_lines = [lines[i]]
                        brace_depth = 0
                        started = False

                        for j in range(i + 1, min(i + max_lines + 50, len(lines))):
                            block_lines.append(lines[j])

                            brace_depth += lines[j].count('{') - lines[j].count('}')

                            if '{' in lines[j]:
                                started = True

                            stripped = lines[j].strip()
                            if started and brace_depth <= 0 and (stripped.startswith('break;') or stripped.startswith('case ') or stripped.startswith('default:')):
                                if stripped.startswith('break;'):
                                    break
                                else:
                                    block_lines.pop()
                                    break

                            if len(block_lines) >= max_lines:
                                block_lines.append("... [truncated]")
                                break

                        return '\n'.join(block_lines)

                return None

            if event_type is not None:
                event_names = {
                    0: "SMART_EVENT_UPDATE_IC", 1: "SMART_EVENT_UPDATE_OOC", 2: "SMART_EVENT_HEALTH_PCT",
                    3: "SMART_EVENT_MANA_PCT", 4: "SMART_EVENT_AGGRO", 5: "SMART_EVENT_KILL",
                    6: "SMART_EVENT_DEATH", 7: "SMART_EVENT_EVADE", 8: "SMART_EVENT_SPELLHIT",
                }
                enum_name = event_names.get(event_type, f"SMART_EVENT_{event_type}")
                source = extract_case_block(enum_name, context_lines)
                if source:
                    results["event_implementation"] = {
                        "type": event_type,
                        "file": "SmartScript.cpp",
                        "function": "ProcessEvent",
                        "source": source
                    }
                else:
                    results["event_implementation"] = {"error": f"Could not find case for event_type {event_type}"}

            if action_type is not None:
                action_names = {
                    0: "SMART_ACTION_NONE", 1: "SMART_ACTION_TALK", 2: "SMART_ACTION_SET_FACTION",
                    11: "SMART_ACTION_CAST", 12: "SMART_ACTION_SUMMON_CREATURE", 41: "SMART_ACTION_FORCE_DESPAWN",
                    45: "SMART_ACTION_SET_DATA", 80: "SMART_ACTION_CALL_TIMED_ACTIONLIST",
                }
                enum_name = action_names.get(action_type, f"SMART_ACTION_{action_type}")
                source = extract_case_block(enum_name, context_lines)
                if source:
                    results["action_implementation"] = {
                        "type": action_type,
                        "file": "SmartScript.cpp",
                        "function": "ProcessAction",
                        "source": source
                    }
                else:
                    results["action_implementation"] = {"error": f"Could not find case for action_type {action_type}"}

            if target_type is not None:
                target_names = {
                    0: "SMART_TARGET_NONE", 1: "SMART_TARGET_SELF", 2: "SMART_TARGET_VICTIM",
                    5: "SMART_TARGET_HOSTILE_RANDOM", 7: "SMART_TARGET_ACTION_INVOKER",
                    12: "SMART_TARGET_STORED", 19: "SMART_TARGET_CLOSEST_CREATURE",
                    21: "SMART_TARGET_CLOSEST_PLAYER", 24: "SMART_TARGET_THREAT_LIST",
                    25: "SMART_TARGET_CLOSEST_ENEMY", 26: "SMART_TARGET_CLOSEST_FRIENDLY",
                }
                enum_name = target_names.get(target_type, f"SMART_TARGET_{target_type}")
                source = extract_case_block(enum_name, context_lines)
                if source:
                    results["target_implementation"] = {
                        "type": target_type,
                        "file": "SmartScript.cpp",
                        "function": "GetTargets",
                        "source": source
                    }
                else:
                    results["target_implementation"] = {"error": f"Could not find case for target_type {target_type}"}

            if not results:
                return json.dumps({
                    "error": "Please provide at least one of: event_type, action_type, target_type",
                    "hint": "Example: get_smartai_source(target_type=25) for SMART_TARGET_CLOSEST_ENEMY"
                })

            return json.dumps(results, indent=2)

        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    def search_azerothcore_source(
        pattern: str,
        file_pattern: str = "*.cpp",
        max_results: int = 10,
        context_lines: int = 3
    ) -> str:
        """
        Search the AzerothCore source code for a pattern.
        Useful for finding implementations, definitions, or usages.

        Args:
            pattern: Text or regex pattern to search for
            file_pattern: Glob pattern for files to search (default: *.cpp)
            max_results: Maximum number of matches to return (default: 10)
            context_lines: Lines of context before/after match (default: 3)

        Returns:
            Matching source code snippets with file locations
        """
        src_path = AZEROTHCORE_SRC_PATH / "src"

        if not src_path.exists():
            return json.dumps({
                "error": f"AzerothCore source not found at {src_path}",
                "hint": "Set AZEROTHCORE_SRC_PATH environment variable"
            })

        try:
            results = []
            pattern_lower = pattern.lower()

            for filepath in src_path.glob(f"**/{file_pattern}"):
                try:
                    content = filepath.read_text(encoding='utf-8', errors='ignore')
                    lines = content.split('\n')

                    for i, line in enumerate(lines):
                        if pattern_lower in line.lower() or (pattern in line):
                            start = max(0, i - context_lines)
                            end = min(len(lines), i + context_lines + 1)
                            snippet = '\n'.join(f"{start + j + 1}: {lines[start + j]}" for j in range(end - start))

                            results.append({
                                "file": str(filepath.relative_to(AZEROTHCORE_SRC_PATH)),
                                "line": i + 1,
                                "snippet": snippet
                            })

                            if len(results) >= max_results:
                                break

                except Exception:
                    continue

                if len(results) >= max_results:
                    break

            if not results:
                return json.dumps({"message": f"No matches found for '{pattern}' in {file_pattern}"})

            return json.dumps({
                "matches": len(results),
                "results": results
            }, indent=2)

        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    def read_source_file(
        relative_path: str,
        start_line: int = 1,
        num_lines: int = 100
    ) -> str:
        """
        Read a specific file from the AzerothCore source code.

        Args:
            relative_path: Path relative to AzerothCore root (e.g., "src/server/game/AI/SmartScripts/SmartScript.cpp")
            start_line: Line number to start reading from (default: 1)
            num_lines: Number of lines to read (default: 100)

        Returns:
            The requested source code with line numbers
        """
        filepath = AZEROTHCORE_SRC_PATH / relative_path

        if not filepath.exists():
            return json.dumps({
                "error": f"File not found: {filepath}",
                "hint": f"Path should be relative to {AZEROTHCORE_SRC_PATH}"
            })

        try:
            content = filepath.read_text(encoding='utf-8', errors='ignore')
            lines = content.split('\n')

            start_idx = max(0, start_line - 1)
            end_idx = min(len(lines), start_idx + num_lines)

            snippet_lines = []
            for i in range(start_idx, end_idx):
                snippet_lines.append(f"{i + 1}: {lines[i]}")

            return json.dumps({
                "file": relative_path,
                "start_line": start_idx + 1,
                "end_line": end_idx,
                "total_lines": len(lines),
                "content": '\n'.join(snippet_lines)
            }, indent=2)

        except Exception as e:
            return json.dumps({"error": str(e)})
