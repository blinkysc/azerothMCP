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
Wiki documentation tools for AzerothCore MCP Server.
"""

import json

from ..config import WIKI_PATH


def register_wiki_tools(mcp):
    """Register wiki documentation tools with the MCP server."""

    @mcp.tool()
    def search_wiki(query: str, max_results: int = 10) -> str:
        """
        Search the AzerothCore wiki documentation for relevant information.

        Args:
            query: Search terms (searches file names and content)
            max_results: Maximum number of results to return

        Returns:
            List of matching wiki pages with snippets
        """
        results = []
        query_lower = query.lower()
        query_terms = query_lower.split()

        try:
            for md_file in WIKI_PATH.glob("*.md"):
                try:
                    content = md_file.read_text(encoding='utf-8', errors='ignore')
                    content_lower = content.lower()
                    filename_lower = md_file.stem.lower()

                    score = 0

                    for term in query_terms:
                        if term in filename_lower:
                            score += 10
                        if term in content_lower:
                            score += content_lower.count(term)

                    if score > 0:
                        snippet = ""
                        for term in query_terms:
                            idx = content_lower.find(term)
                            if idx != -1:
                                start = max(0, idx - 100)
                                end = min(len(content), idx + 200)
                                snippet = "..." + content[start:end].replace("\n", " ").strip() + "..."
                                break

                        results.append({
                            "file": md_file.name,
                            "score": score,
                            "snippet": snippet[:300] if snippet else content[:200].replace("\n", " ") + "..."
                        })
                except Exception:
                    continue

            results.sort(key=lambda x: x["score"], reverse=True)
            results = results[:max_results]

            return json.dumps(results, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    def read_wiki_page(filename: str) -> str:
        """
        Read a specific wiki documentation page.

        Args:
            filename: The wiki file name (e.g., 'smart_scripts.md', 'creature_template.md')

        Returns:
            The content of the wiki page (may be truncated if very large)
        """
        try:
            wiki_file = WIKI_PATH / filename
            if not wiki_file.exists():
                wiki_file = WIKI_PATH / f"{filename}.md"

            if not wiki_file.exists():
                return json.dumps({
                    "error": f"Wiki page '{filename}' not found",
                    "hint": "Use search_wiki to find available pages"
                })

            content = wiki_file.read_text(encoding='utf-8', errors='ignore')

            max_size = 50000
            if len(content) > max_size:
                return json.dumps({
                    "warning": f"Content truncated (original: {len(content)} chars)",
                    "content": content[:max_size] + "\n\n... [TRUNCATED - use search_wiki for specific sections] ..."
                }, indent=2)

            return content
        except Exception as e:
            return json.dumps({"error": str(e)})
