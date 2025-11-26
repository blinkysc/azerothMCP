# AzerothCore MCP Server

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that provides AI assistants like Claude with read-only access to AzerothCore databases and wiki documentation. This enables AI-powered assistance for understanding creature scripts, SmartAI logic, database schemas, and game mechanics.

## Features

### Database Tools
- **query_database** - Execute read-only SQL queries against world, characters, or auth databases
- **get_table_schema** - Retrieve table structure/column definitions
- **list_tables** - List tables with optional pattern filtering

### Creature/NPC Tools
- **get_creature_template** - Get full creature data by entry ID
- **search_creatures** - Search creatures by name pattern
- **get_creature_with_scripts** - Get creature template with associated SmartAI scripts

### SmartAI Tools
- **get_smart_scripts** - Retrieve SmartAI scripts for any source type
- **explain_smart_script** - Get documentation for event/action/target types
- **trace_script_chain** - Debug and visualize SmartAI execution flow, following links, timed action lists, and data triggers

### Wiki/Documentation Tools
- **search_wiki** - Search AzerothCore wiki documentation
- **read_wiki_page** - Read specific wiki pages

### Additional Entity Tools
- **get_gameobject_template** / **search_gameobjects** - GameObject lookup
- **search_spells** - Search spell_dbc by name or ID
- **get_quest_template** / **search_quests** - Quest lookup
- **get_item_template** / **search_items** - Item lookup

## Requirements

- Python 3.10+
- MySQL with AzerothCore databases
- (Optional) Local copy of [AzerothCore wiki](https://github.com/azerothcore/wiki)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/azerothMCP.git
cd azerothMCP
```

2. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file with your configuration:
```env
# Database connection
DB_HOST=localhost
DB_PORT=3306
DB_USER=acore
DB_PASSWORD=acore

# Database names
DB_WORLD=acore_world
DB_CHARACTERS=acore_characters
DB_AUTH=acore_auth

# Wiki documentation path (optional)
# Clone https://github.com/azerothcore/wiki to ~/wiki
WIKI_PATH=~/wiki/docs

# MCP server port
MCP_PORT=8080
```

## Usage

### Running the Server

Start the MCP server:

```bash
source venv/bin/activate
python server.py
```

The server starts on `http://localhost:8080/sse` using Server-Sent Events (SSE) transport.

### Connecting with Claude Desktop

Add to your Claude Desktop MCP configuration:

**Linux:** `~/.config/Claude/claude_desktop_config.json`
**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "azerothcore": {
      "url": "http://localhost:8080/sse"
    }
  }
}
```

Then restart Claude Desktop. The AzerothCore tools will be available in your conversations.

### Connecting with Claude Code

Add to your Claude Code MCP settings (`~/.claude/settings.json`):

```json
{
  "mcpServers": {
    "azerothcore": {
      "url": "http://localhost:8080/sse"
    }
  }
}
```

### Example Prompts

Once connected, you can ask things like:

- "What scripts does Hogger (entry 448) have?"
- "Show me the creature_template schema"
- "Search for creatures named 'Defias'"
- "Explain SmartAI event type 4"
- "Trace the script chain for creature 1234"
- "Find quests related to Westfall"

## Wiki Setup (Optional)

To enable wiki search functionality, clone the AzerothCore wiki:

```bash
cd ~
git clone https://github.com/azerothcore/wiki.git
```

The server will search markdown files in `~/wiki/docs` by default. Update `WIKI_PATH` in your `.env` if your wiki is in a different location.

## Security

By default, the server operates in **read-only mode**. Only `SELECT`, `SHOW`, and `DESCRIBE` queries are permitted.

To enable write operations (INSERT, UPDATE, DELETE) for full automation:

```env
READ_ONLY=false
```

**Warning:** Enabling write mode allows the AI to modify your database. Use with caution and ensure you have backups.

## License

GNU GPL v2 - See [LICENSE](LICENSE)

## Related Projects

- [AzerothCore](https://github.com/azerothcore/azerothcore-wotlk) - Open source WoW emulator
- [Model Context Protocol](https://modelcontextprotocol.io/) - Open protocol for AI context sharing
