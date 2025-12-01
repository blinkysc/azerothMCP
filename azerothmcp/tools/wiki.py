#!/usr/bin/env python3
"""Wiki documentation tools"""

import json

from ..config import WIKI_PATH


def register_wiki_tools(mcp):
    """Register wiki documentation tools."""

    @mcp.tool()
    def search_wiki(query: str, max_results: int = 10) -> str:
        """Search AzerothCore wiki documentation."""
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
        """Read a specific wiki documentation page."""
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
