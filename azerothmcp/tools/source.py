#!/usr/bin/env python3
"""AzerothCore source code tools"""

import json
import subprocess

from ..config import AZEROTHCORE_SRC_PATH


def register_source_tools(mcp):
    """Register source code-related tools."""

    @mcp.tool()
    def search_azerothcore_source(pattern: str, path_filter: str = None, context_lines: int = 3, max_results: int = 50) -> str:
        """Search AzerothCore C++ source code for patterns."""
        if not AZEROTHCORE_SRC_PATH.exists():
            return json.dumps({"error": "AzerothCore source path not configured"})

        try:
            grep_cmd = ['grep', '-r', '-n', '-i']
            if context_lines > 0:
                grep_cmd.extend(['-C', str(context_lines)])
            grep_cmd.append(pattern)
            
            search_path = AZEROTHCORE_SRC_PATH / path_filter if path_filter else AZEROTHCORE_SRC_PATH
            grep_cmd.append(str(search_path))

            result = subprocess.run(grep_cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0 and result.returncode != 1:
                return json.dumps({"error": "Search failed", "stderr": result.stderr})
            
            output_lines = result.stdout.split('\n')[:max_results]
            return json.dumps({"matches": output_lines, "total": len(output_lines)}, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    def read_source_file(file_path: str, start_line: int = None, num_lines: int = None) -> str:
        """Read specific source file from AzerothCore."""
        if not AZEROTHCORE_SRC_PATH.exists():
            return json.dumps({"error": "AzerothCore source path not configured"})

        try:
            full_path = (AZEROTHCORE_SRC_PATH / file_path).resolve()
            if not str(full_path).startswith(str(AZEROTHCORE_SRC_PATH.resolve())):
                return json.dumps({"error": "Path traversal not allowed"})
            if not full_path.exists():
                return json.dumps({"error": f"File not found: {file_path}"})

            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                if start_line is not None:
                    all_lines = f.readlines()
                    if num_lines:
                        lines = all_lines[start_line-1:start_line-1+num_lines]
                    else:
                        lines = all_lines[start_line-1:]
                    content = ''.join(lines)
                else:
                    content = f.read()

            return json.dumps({"file": file_path, "content": content}, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})
